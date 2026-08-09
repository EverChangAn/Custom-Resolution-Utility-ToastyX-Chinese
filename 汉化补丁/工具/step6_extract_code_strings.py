# -*- coding: utf-8 -*-
"""step6: 提取 exe 非资源段（.data/.text）的硬编码字符串，去重过滤，生成对照表"""
import re, struct, collections, csv

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
OUT_CSV = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_code.csv'

data = open(EXE, 'rb').read()

# ---- 节信息 ----
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
coff = e_lfanew + 4
machine, nsec, ts, p_sym, n_sym, opt_size, chars = struct.unpack_from('<HHIIIHH', data, coff)
opt = coff + 20
sec_tab = opt + opt_size
sections = []
for i in range(nsec):
    off = sec_tab + i*40
    name = data[off:off+8].rstrip(b'\0').decode('ascii', errors='replace')
    vsize, vaddr, raw_size, raw_ptr = struct.unpack_from('<IIII', data, off+8)
    sections.append((name, vaddr, vsize, raw_ptr, raw_size))

def sec_of(off):
    for name, vaddr, vsize, raw_ptr, raw_size in sections:
        if raw_ptr <= off < raw_ptr + raw_size:
            return name
    return '?'

# ---- 已知 dfm 字符串（避免重复）----
dfm_strings = set()
try:
    import csv as _csv
    for r in _csv.reader(open(r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_raw.csv', encoding='utf-8-sig')):
        dfm_strings.add(r[0])
except Exception:
    pass

# ---- 过滤规则 ----
BANNED_SUB = ['.h', '.hpp', '.cpp', '.c"', '.dll', '.exe', '.ico', '.bmp', '.rc', '.inf', '.txt',
              'ADL_', 'atiddx', 'atiadl', 'GetProcAddress', 'RegQueryValue',
              'HKEY_', 'SOFTWARE', '://', 'Patreon', 'monitortests', 'CRU.exe',
              'VistaAltFix', 'InitCommonControls', 'LoadLibrary', 'IsAppThemed',
              'Borlndmm', 'Dinkumware', 'hrdir', '_ExceptionHandler', 'borlndmm',
              '__isSameTypeID', 'IsThemeBackground', 'InitializeCriticalSection',
              'printf', 'scanf', 'SystemFunction036', 'GetSystemMetrics',
              'ClassGUID', 'TMultiReadExclusiveWriteSynchronizer',
              'Unexpected', 'memory', 'Memory', 'heap', 'Heap', 'malloc', 'alloc',
              'vtablePtr', 'tpClass', 'tpcFlags', 'dttPtr', 'varType', 'typeID',
              'reThrow', 'XDF_ISDELPHIEXCEPTION', 'tpid', 'tpMask', 'TM_IS',
              'DTCVF', 'IS_STRUC', 'IS_CLASS', 'tpcDtorCount', 'ERRcInitDtc',
              'tppBaseType', 'tpaElemType', 'etdCount', 'elemCount', 'topTypPtr',
              'tgtTypPtr', 'srcTypPtr', 'dtvtPtr', 'derv->', 'CF_HAS', 'CPP_',
              'Borland C++', 'P.J. Plauger', 'FATAL', 'RTTI', 'GetMem', 'FreeMem',
              'ReallocMem', 'environment block', 'command line argument',
              'current directory', 'DOS mode', 'Win32', 'floating point formats',
              'MBCS table', 'code page access']

# 代码符号特征（含这些的跳过，但保留 %d/%s 格式串）
CODE_SYMS = ['->', '::', '&&', '||', '==', '!=', '>=', '<=', '(', ')', '{', '}', ';', '=', '<', '>', '*', '"', '@', '$', '#']

def is_ui_string(s):
    t = s.strip()
    if len(t) < 2 or len(t) > 80:
        return False
    if not re.search(r'[A-Za-z]', t):
        return False
    # 含代码符号（排除纯格式串 %d %s）
    for sym in CODE_SYMS:
        if sym in s:
            # 允许 % 开头的格式符
            if sym == '%':
                continue
            return False
    for b in BANNED_SUB:
        if b.lower() in s.lower():
            return False
    # 纯大写缩写/API 风格（连续大写+下划线）
    if re.fullmatch(r'[A-Z][A-Z_0-9]{2,}', t):
        return False
    # 文件路径风格
    if s.startswith(('C:\\', '\\', '/')):
        return False
    # 数字为主的
    if not re.search(r'[A-Za-z]{2,}', t):
        return False
    # RTTI 风格（# $ @ 开头已在 CODE_SYMS 拦截）
    return True

# ---- 扫描可读字符串 ----
str_re = re.compile(rb'[\x20-\x7E]{4,}')
found = collections.defaultdict(list)   # txt -> [(offset, sec)]
for m in str_re.finditer(data):
    s = m.group().decode('ascii', errors='ignore')
    off = m.start()
    sec = sec_of(off)
    if sec in ('.rsrc', '.reloc', '.idata', '.edata', '.tls'):
        continue
    if not is_ui_string(s):
        continue
    if s in dfm_strings:
        continue
    found[s].append((off, sec))

# 输出 CSV
rows = sorted(found.items(), key=lambda x: -len(x[0]))
with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fout:
    w = csv.writer(fout)
    w.writerow(['原文', '出现位置(偏移/段)', '次数'])
    for s, locs in rows:
        secs = collections.Counter(x[1] for x in locs)
        w.writerow([s, ';'.join('%s@%s×%d' % (hex(x[0]), x[1], 1) for x in locs[:4]), len(locs)])

print('提取到代码段字符串:', len(rows))
print()
for s, locs in rows[:60]:
    print('  [%d] %s' % (len(s), s[:80]))
