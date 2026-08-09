# -*- coding: utf-8 -*-
"""step11c: 验证中文版 exe — PE 结构、dfm 资源、代码字符串、字节级 diff"""
import struct, sys, os
sys.path.insert(0, r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区')
import pefile

ORIG = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
NEW = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\CRU_zh-CN\CRU.exe'
DFM_ZH = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm_zh'

orig = open(ORIG, 'rb').read()
new = open(NEW, 'rb').read()

print('=== 1. PE 结构合法性 ===')
try:
    pe = pefile.PE(NEW)
    print('✓ pefile 解析成功')
    print('  入口点: 0x%x, ImageBase: 0x%x' % (pe.OPTIONAL_HEADER.AddressOfEntryPoint, pe.OPTIONAL_HEADER.ImageBase))
    print('  SizeOfImage: 0x%x' % pe.OPTIONAL_HEADER.SizeOfImage)
    print('  节表:')
    for s in pe.sections:
        print('    %-8s VMA=0x%x vsize=0x%x raw=0x%x@0x%x' % (s.Name.decode('ascii','replace').strip('\0'), s.VirtualAddress, s.Misc_VirtualSize, s.SizeOfRawData, s.PointerToRawData))
    if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
        print('✓ 资源目录解析成功')
    else:
        print('✗ 资源目录解析失败')
except Exception as e:
    print('✗ PE 解析失败:', e)
    raise SystemExit(1)

print()
print('=== 2. dfm 资源内容验证 ===')
from step3_dfm_parser import DfmParser
ok = 0
total = 0
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id != 10 or not entry.directory:
        continue
    for e2 in entry.directory.entries:
        name = str(e2.name)
        if not e2.directory:
            continue
        for e3 in e2.directory.entries:
            raw = pe.get_data(e3.data.struct.OffsetToData, e3.data.struct.Size)
            total += 1
            if raw[:4] != b'TPF0':
                print('  ✗ %s 不是 dfm' % name)
                continue
            p = DfmParser(raw)
            p.pos = 4
            p.parse()
            if p.pos != len(raw):
                print('  ✗ %s 解析未到末尾 %d/%d' % (name, p.pos, len(raw)))
            else:
                ok += 1
print('dfm 资源解析: %d/%d 通过' % (ok, total))

# 抽查中文
print()
print('=== 3. 界面中文抽查 ===')
p = None
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id != 10 or not entry.directory:
        continue
    for e2 in entry.directory.entries:
        if str(e2.name) == 'TDISPLAYFORM' and e2.directory:
            for e3 in e2.directory.entries:
                raw = pe.get_data(e3.data.struct.OffsetToData, e3.data.struct.Size)
                p = DfmParser(raw)
                p.pos = 4
                p.parse()
            break
if p:
    zh_cn = [txt for obj, cls, prop, txt, raw in p.string_props if any('\u4e00' <= c <= '\u9fff' for c in txt)]
    print('TDISPLAYFORM 中文属性 %d 条，示例:' % len(zh_cn))
    for t in zh_cn[:10]:
        print('    %s' % t[:50])

print()
print('=== 4. 代码字符串替换验证（GBK）===')
checks = ['错误', '导入', '导出', '删除', '手动', '未知显示器', '自定义分辨率工具']
for c in checks:
    gbk = c.encode('gbk')
    n = new.count(gbk)
    print('  "%s" (GBK) 出现 %d 次' % (c, n))

print()
print('=== 5. 字节级 diff（除预期区域外应无差异）===')
# 找出所有差异位置
diffs = [i for i in range(min(len(orig), len(new))) if orig[i] != new[i]]
print('总差异字节数:', len(diffs))
if len(orig) != len(new):
    print('文件大小不同: %d → %d (+%d)' % (len(orig), len(new), len(new)-len(orig)))

# 差异按区域聚类
if diffs:
    ranges = []
    s = prev = diffs[0]
    for i in diffs[1:]:
        if i - prev > 64:
            ranges.append((s, prev))
            s = i
        prev = i
    ranges.append((s, prev))
    print('差异区域 %d 个:' % len(ranges))
    for a, b in ranges[:20]:
        print('  0x%x - 0x%x (%d 字节)' % (a, b, b-a+1))

# 检查 .text 代码段是否零改动
print()
print('=== 6. .text 代码段零改动检查 ===')
text_sec = None
for s in pe.sections:
    if s.Name.decode('ascii','replace').strip('\0') == '.text':
        text_sec = s
        break
if text_sec:
    t_orig = orig[text_sec.PointerToRawData:text_sec.PointerToRawData+text_sec.SizeOfRawData]
    t_new = new[text_sec.PointerToRawData:text_sec.PointerToRawData+text_sec.SizeOfRawData]
    n_diff = sum(1 for a, b in zip(t_orig, t_new) if a != b)
    print('.text 代码段差异字节: %d %s' % (n_diff, '✓ 零改动' if n_diff == 0 else '⚠️ 有改动!'))
