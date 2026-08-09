# -*- coding: utf-8 -*-
"""step6b: 从 CRU 源码提取用户可见字符串，在 exe 中定位，生成对照表"""
import os, re, glob, csv, collections

SRC = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3-src\CRU\CRU'
EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
OUT_CSV = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_code.csv'

# ---------- 1. 从源码提取字符串 ----------
BANNED = ['#include', '.h"', '.hpp"', '.cpp"', '.c"', '.dll"', '.exe"', '.ico"', '.bmp"',
          'ADL_', 'atiadl', 'atiddx', 'GetProcAddress', 'HKEY_', 'SOFTWARE',
          'monitortests', 'Patreon', 'CRU.exe', 'restart', 'reset-all', 'VistaAltFix',
          'ChangeDisplaySettings', 'IsAppThemed', 'LoadLibrary', 'GetProcAddress',
          'ADL_Main_Control', 'ADL_Adapter_', 'ADL_Display_', 'EDID_OVERRIDE',
          'Device Parameters', 'Keyboard Layouts', 'CurrentControlSet',
          'Borlndmm', 'Dinkumware', 'RTL', 'SystemFunction036', 'InitializeCriticalSection',
          'GetThemeBackground', 'IsThemeBackground', 'QueryPerformance',
          '\\Registry', '\\Device', 'System32', 'Windows\\', 'Program Files',
          'GetSystemMetrics', 'GetDeviceCaps', 'EnumDisplayDevices',
          'SetProcessDPIAware', 'GetDpiForSystem', 'GetDpiForMonitor',
          'MakeUserSYS', 'MakeSystemSYS', 'NtQuery', 'ZwQuery',
          ]

src_strings = collections.OrderedDict()  # txt -> set(files)
for f in sorted(glob.glob(os.path.join(SRC, '*.cpp')) + glob.glob(os.path.join(SRC, '*.h')) + glob.glob(os.path.join(SRC, '*.hpp'))):
    fname = os.path.basename(f)
    content = open(f, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'L?"((?:[^"\\]|\\.){2,120})"', content):
        s = m.group(1)
        # 跳过纯转义/格式
        t = s.strip()
        if len(t) < 2:
            continue
        if not re.search(r'[A-Za-z]', t):
            continue
        bad = False
        for b in BANNED:
            if b.lower() in s.lower():
                bad = True
                break
        if bad:
            continue
        # 纯 API 风格
        if re.fullmatch(r'[A-Z][A-Z0-9_]{2,}', t):
            continue
        # 路径
        if '\\\\' in s or s.startswith(('C:', '/', '\\')):
            continue
        src_strings.setdefault(s, set()).add(fname)

print('源码提取字符串(含重复):', len(src_strings))

# ---------- 2. 在 exe 中定位 ----------
data = open(EXE, 'rb').read()

def find_all(hay, needle):
    res = []
    start = 0
    while True:
        i = hay.find(needle, start)
        if i < 0:
            break
        res.append(i)
        start = i + 1
    return res

located = []
not_found = []
for s, files in src_strings.items():
    offs = find_all(data, s.encode('ascii', errors='ignore'))
    if offs:
        located.append((s, offs, sorted(files), 'ANSI'))
        continue
    offs = find_all(data, s.encode('utf-16le'))
    if offs:
        located.append((s, offs, sorted(files), 'UTF16'))
        continue
    not_found.append(s)

print('在 exe 中定位到:', len(located), '(ANSI/UTF16 混合)  未找到:', len(not_found))
enc_count = collections.Counter(x[3] for x in located)
print('编码分布:', dict(enc_count))

# ---------- 3. 输出 ----------
with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fout:
    w = csv.writer(fout)
    w.writerow(['原文', 'exe偏移', '编码', '源码文件', '次数'])
    for s, offs, files, enc in sorted(located, key=lambda x: -len(x[0])):
        w.writerow([s, ';'.join(hex(o) for o in offs[:6]), enc, ','.join(files), len(offs)])

print()
print('=== 定位到的字符串（前 100 条）===')
for s, offs, files, enc in sorted(located, key=lambda x: -len(x[0]))[:100]:
    print('  [%2d][%s] %-68s @%s' % (len(s), enc, s[:68], hex(offs[0])))
