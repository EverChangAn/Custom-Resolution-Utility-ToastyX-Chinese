# -*- coding: utf-8 -*-
"""step11a-v2: 基于已验证的 step3 解析器，记录原始字节段，重序列化 dfm"""
import glob, os, json, struct, sys

sys.path.insert(0, r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区')
from step3_dfm_parser import DfmParser, DfmError

DFM_DIR = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm'
OUT_DIR = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm_zh'
FINAL = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\final_translations.json'
os.makedirs(OUT_DIR, exist_ok=True)

T = json.load(open(FINAL, encoding='utf-8'))

class RecParser(DfmParser):
    """记录每个属性的 (name_bytes, ptype, raw_value_bytes, str_text_or_None)"""
    def __init__(self, data):
        super().__init__(data)
        self.rec_props = []     # 收集属性记录（解析时填充）

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
            start = self.pos
            str_text = None
            # 用原始字节记录值（不依赖类型解析）——但字符串类型需要解码
            if ptype in (0x06, 0x14):
                # 解析字符串拿到文本（用于查字典）
                value = self.read_value(ptype)
                str_text = value[1].decode('utf-8' if ptype == 0x14 else 'ascii', errors='replace')
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, str_text))
            elif ptype == 0x01:
                # 字符串列表：逐步读
                self.read_value(ptype)
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x02:
                self.pos += 1
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x03:
                self.pos += 2
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x04:
                self.pos += 4
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x05:
                self.pos += 4
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x07:
                self.read_shortstr()
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype in (0x08, 0x09):
                raw_value = b''
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x0a:
                l = int.from_bytes(self.data[self.pos:self.pos+4], 'little')
                self.pos += 4 + l
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x0b:
                while True:
                    b = self.data[self.pos]
                    if b == 0:
                        self.pos += 1
                        break
                    self.read_shortstr()
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x0c:
                self.pos += 1
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            elif ptype == 0x0f:
                l = self.read_byte()
                self.pos += l
                raw_value = self.data[start:self.pos]
                props.append((pname, ptype, raw_value, None))
            else:
                raise DfmError('未知类型 0x%02x @pos=%d' % (ptype, self.pos))
        children = []
        while True:
            b = self.data[self.pos]
            if b == 0:
                self.pos += 1
                break
            child = self.parse_object()
            children.append(child)
        return (name, cls, props, children)

# ---------- 序列化 ----------
def wshortstr(buf, s):
    buf.append(bytes([len(s)]))
    buf.append(s)

def serialize_node(node, buf):
    name, cls, props, children = node
    wshortstr(buf, name)
    wshortstr(buf, cls)
    for pname, ptype, raw_value, str_text in props:
        wshortstr(buf, pname)
        if ptype in (0x06, 0x14) and str_text is not None and str_text in T:
            # 翻译：类型替换为 vaUTF8String (0x14)，数据 UTF-8
            payload = T[str_text].encode('utf-8')
            buf.append(b'\x14')
            buf.append(struct.pack('<I', len(payload)))
            buf.append(payload)
        else:
            buf.append(bytes([ptype]))
            buf.append(raw_value)
    buf.append(b'\x00')
    for child in children:
        serialize_node(child, buf)
    buf.append(b'\x00')

# ---------- 处理 ----------
report = []
for f in sorted(glob.glob(os.path.join(DFM_DIR, '*.dfm'))):
    data = open(f, 'rb').read()
    p = RecParser(data)
    p.pos = 4
    root = p.parse_object()
    assert p.pos == len(data), '解析未到末尾: %s %d/%d' % (f, p.pos, len(data))

    buf = [b'TPF0']
    serialize_node(root, buf)
    new_data = b''.join(buf)
    out = os.path.join(OUT_DIR, os.path.basename(f))
    open(out, 'wb').write(new_data)
    report.append((os.path.basename(f), len(data), len(new_data)))

print('=== dfm 重序列化报告 ===')
total_delta = 0
for name, old, new in report:
    total_delta += new - old
    print('  %-35s %6d → %6d (%+d)' % (name, old, new, new-old))
print('总字节变化: %+d' % total_delta)

# ---------- 回验 ----------
print()
print('=== 回验新 dfm（step3 解析器）===')
ok = 0
for f in sorted(glob.glob(os.path.join(OUT_DIR, '*.dfm'))):
    data = open(f, 'rb').read()
    try:
        p = DfmParser(data)
        p.pos = 4
        p.parse()
        assert p.pos == len(data)
        ok += 1
    except Exception as e:
        print('  ✗ %s: %s' % (os.path.basename(f), e))
total = len(glob.glob(os.path.join(OUT_DIR, '*.dfm')))
print('回验通过: %d/%d' % (ok, total))
