# -*- coding: utf-8 -*-
"""诊断：逐步解析 TADDCEADATAFORM，打印每个属性，定位错位点"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区')
from step3_dfm_parser import DfmParser, DfmError

data = open(r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm\TADDCEADATAFORM.dfm', 'rb').read()

class DiagParser(DfmParser):
    def parse_object(self, depth=0):
        try:
            name = self.read_shortstr()
            cls = self.read_shortstr()
        except Exception as e:
            print('  '*depth, '对象名读取失败:', e); raise
        print('  '*depth + '对象 %s (%s) @pos=%d' % (name.decode('ascii','replace'), cls.decode('ascii','replace'), self.pos))
        props = []
        while True:
            b = self.data[self.pos]
            if b == 0:
                self.pos += 1
                break
            pname = self.read_shortstr()
            ptype = self.read_byte()
            try:
                value = self.read_value(ptype)
                disp = str(value)[:60]
                print('  '*depth + '  属性 %-22s 类型0x%02x 值=%s @pos=%d' % (pname.decode('ascii','replace'), ptype, disp, self.pos))
            except DfmError as e:
                print('  '*depth + '  ✗ 属性 %-22s 类型0x%02x 读取失败: %s' % (pname.decode('ascii','replace'), ptype, e))
                raise
            props.append((pname, ptype, value))
        children = []
        while True:
            b = self.data[self.pos]
            if b == 0:
                self.pos += 1
                break
            children.append(self.parse_object(depth+1))
        return (name, cls, props, children)

p = DiagParser(data)
try:
    p.pos = 4
    root = p.parse_object()
    print('解析完成, 结束位置 %d/%d' % (p.pos, len(data)))
except Exception as e:
    print('失败:', e)
    print('当前位置 pos=%d, 剩余字节: %s' % (p.pos, data[p.pos:p.pos+40].hex()))
