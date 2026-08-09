# -*- coding: utf-8 -*-
"""step4: 从全部 dfm 提取字符串，去重+过滤，生成中英对照 Excel"""
import glob, os, collections, re
from step3_dfm_parser import DfmParser

DFM_DIR = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm'
OUT_XLSX = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\CRU翻译对照表.xlsx'

# ---- 需要过滤的字符串 ----
def should_skip(txt):
    t = txt.strip()
    if not t:
        return True
    # 纯空白/纯标点/纯数字
    if not re.search(r'[A-Za-z\x80-\xff]', t):
        return True
    # 字体名
    if t in ('Tahoma', 'MS Sans Serif', 'Segoe UI', 'Arial', 'Default', 'DEFAULT_CHARSET'):
        return True
    # 纯格式串（只有 %s %d 等无实质文字）
    if re.fullmatch(r'[%\d\.\s\-+\(\)\[\]\{\}%a-zA-Z]*', t) and '%' in t and not re.search(r'[A-Za-z]{3,}', t):
        return True
    return False

def ptype_was_utf8(raw):
    try:
        raw.decode('utf-8')
        return True
    except Exception:
        return False

entries = {}   # txt -> {txt, files:{file:count}, props:set, types:set}
for f in sorted(glob.glob(os.path.join(DFM_DIR, '*.dfm'))):
    name = os.path.basename(f)
    data = open(f, 'rb').read()
    p = DfmParser(data)
    p.pos = 4
    p.parse()
    for obj_name, cls, pname, txt, raw in p.string_props:
        if should_skip(txt):
            continue
        e = entries.setdefault(txt, {'txt': txt, 'files': collections.Counter(), 'props': set(), 'len': len(raw), 'utf8': False})
        e['files'][name] += 1
        e['props'].add(pname)
        if ptype_was_utf8(raw):
            e['utf8'] = True

print('去重后待翻译字符串:', len(entries))

# ---- 输出 CSV 预览 ----
with open(r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_raw.csv', 'w', encoding='utf-8-sig', newline='') as fout:
    import csv
    w = csv.writer(fout)
    w.writerow(['原文', '出现文件', '属性', '原始字节长度'])
    for txt, e in sorted(entries.items(), key=lambda x: -x[1]['len']):
        w.writerow([txt, ';'.join('%s×%d' % (k, v) for k, v in e['files'].items()), ','.join(sorted(p.decode('ascii', 'replace') for p in e['props'])), e['len']])

print('CSV 预览已写入 strings_raw.csv')
# 打印最长的 30 条
for txt, e in sorted(entries.items(), key=lambda x: -x[1]['len'])[:30]:
    print('  [%3d] %s' % (e['len'], txt[:90]))
