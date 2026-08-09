# -*- coding: utf-8 -*-
"""解析二进制 dfm (TPF0) 格式，统计属性类型分布，验证能否完整解析"""
import glob, os, collections, sys

class DfmError(Exception):
    pass

class DfmParser:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.type_stats = collections.Counter()
        self.string_props = []

    def read_byte(self):
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_shortstr(self):
        l = self.read_byte()
        s = self.data[self.pos:self.pos+l]
        if len(s) != l:
            raise DfmError('短字符串越界 pos=%d' % self.pos)
        self.pos += l
        return s

    def skip(self, n):
        self.pos += n
        if self.pos > len(self.data):
            raise DfmError('跳过越界')

    def read_value(self, ptype):
        if ptype == 0x00:   # null
            return None
        elif ptype == 0x01: # 字符串列表: [0x06 len data]*, 0x00 结束
            items = []
            while True:
                b = self.data[self.pos]
                if b == 0:
                    self.pos += 1
                    break
                if b != 0x06:
                    raise DfmError('字符串列表内未知标记 0x%02x @pos=%d' % (b, self.pos))
                self.pos += 1
                l = self.read_byte()
                s = self.data[self.pos:self.pos+l]
                if len(s) != l:
                    raise DfmError('列表字符串越界 pos=%d' % self.pos)
                self.pos += l
                items.append(s)
            return ('strlist', items)
        elif ptype == 0x02: # int8
            v = self.data[self.pos]; self.skip(1); return v
        elif ptype == 0x03: # int16
            v = int.from_bytes(self.data[self.pos:self.pos+2], 'little'); self.skip(2); return v
        elif ptype == 0x04: # int32
            v = int.from_bytes(self.data[self.pos:self.pos+4], 'little'); self.skip(4); return v
        elif ptype == 0x05: # ?
            v = int.from_bytes(self.data[self.pos:self.pos+4], 'little'); self.skip(4); return v
        elif ptype == 0x06: # 字符串: 1字节长度 + 数据
            l = self.read_byte()
            s = self.data[self.pos:self.pos+l]
            if len(s) != l:
                raise DfmError('字符串越界 pos=%d l=%d' % (self.pos, l))
            self.pos += l
            return ('str', s)
        elif ptype == 0x07: # 枚举/标识符
            s = self.read_shortstr()
            return ('enum', s)
        elif ptype == 0x08: # vaFalse（布尔 False，无值）
            return ('bool', False)
        elif ptype == 0x09: # vaTrue（布尔 True，无值）
            return ('bool', True)
        elif ptype == 0x0a: # vaBinary: 4字节长度 + 数据
            l = int.from_bytes(self.data[self.pos:self.pos+4], 'little'); self.skip(4)
            s = self.data[self.pos:self.pos+l]
            if len(s) != l:
                raise DfmError('二进制数据越界 pos=%d l=%d' % (self.pos, l))
            self.pos += l
            return ('binary', s)
        elif ptype == 0x0b: # vaSet: [len+name]*, 0x00 结束
            items = []
            while True:
                b = self.data[self.pos]
                if b == 0:
                    self.pos += 1
                    break
                items.append(self.read_shortstr())
            return ('set', items)
        elif ptype == 0x14: # vaUTF8String: 4字节长度 + UTF-8 数据
            l = int.from_bytes(self.data[self.pos:self.pos+4], 'little'); self.skip(4)
            s = self.data[self.pos:self.pos+l]
            if len(s) != l:
                raise DfmError('UTF-8 字符串越界 pos=%d l=%d' % (self.pos, l))
            self.pos += l
            return ('str', s)
        elif ptype == 0x0c: # 布尔(1字节)?
            v = self.data[self.pos]; self.skip(1); return ('bool', v)
        elif ptype == 0x0f: # ?
            l = self.read_byte()
            s = self.data[self.pos:self.pos+l]
            self.pos += l
            return ('raw', s)
        else:
            raise DfmError('未知属性类型 0x%02x @pos=%d (上下文: %s)' % (ptype, self.pos, self.data[self.pos-8:self.pos+8].hex()))

    def parse_object(self):
        name = self.read_shortstr()
        cls = self.read_shortstr()
        props = []
        while True:
            b = self.data[self.pos]
            if b == 0:
                self.pos += 1
                break
            pname = self.read_shortstr()
            ptype = self.read_byte()
            self.type_stats[ptype] += 1
            value = self.read_value(ptype)
            props.append((pname, ptype, value))
            if ptype in (0x06, 0x14):
                s = value[1]
                try:
                    txt = s.decode('utf-8') if ptype == 0x14 else s.decode('ascii')
                except Exception:
                    txt = ''
                self.string_props.append((name, cls, pname, txt, s))
        children = []
        while True:
            b = self.data[self.pos]
            if b == 0:
                self.pos += 1
                break
            children.append(self.parse_object())
        return (name, cls, props, children)

    def parse(self):
        sig = self.data[:4]
        assert sig == b'TPF0', '签名错误: %r' % sig
        self.pos = 4
        root = self.parse_object()
        return root

def main():
    files = sorted(glob.glob(r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm\*.dfm'))
    all_types = collections.Counter()
    total_str = 0
    for f in files:
        data = open(f, 'rb').read()
        try:
            p = DfmParser(data)
            root = p.parse()
            if p.pos != len(data):
                print('⚠ %s: 解析到 %d/%d 未到文件尾' % (os.path.basename(f), p.pos, len(data)))
            else:
                print('✓ %s: 完整解析 (%d 字节, %d 属性, %d 字符串)' % (os.path.basename(f), len(data), sum(p.type_stats.values()), len(p.string_props)))
            all_types.update(p.type_stats)
            total_str += len(p.string_props)
        except Exception as e:
            print('✗ %s: %s' % (os.path.basename(f), e))
    print()
    print('=== 类型分布 ===')
    for t, c in sorted(all_types.items()):
        print('  0x%02x: %d' % (t, c))
    print()
    print('字符串属性总数:', total_str)

if __name__ == '__main__':
    main()
