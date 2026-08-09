# -*- coding: utf-8 -*-
"""step11b-v4: 回写 exe
方案：1) Python 原地替换代码字符串（GBK、长度校验）→ 2) Windows UpdateResource API 更新 dfm 资源
"""
import struct, json, csv, os, shutil
import ctypes
from ctypes import wintypes

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
WORK = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\CRU_zh-CN\CRU.exe'
DFM_ZH = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm_zh'
FINAL = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\final_translations.json'
CODE_CSV = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_code.csv'
os.makedirs(os.path.dirname(WORK), exist_ok=True)

T = json.load(open(FINAL, encoding='utf-8'))

# ============ 1. 复制 + 原地替换代码字符串 ============
data = bytearray(open(EXE, 'rb').read())

# .rsrc raw 区起点（代码字符串查找边界）
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
coff = e_lfanew + 4
machine, nsec, ts, p_sym, n_sym, opt_size, chars = struct.unpack_from('<HHIIIHH', data, coff)
opt = coff + 20
sec_tab = opt + opt_size
rsrc_raw_ptr = None
for i in range(nsec):
    off = sec_tab + i*40
    name = data[off:off+8].rstrip(b'\0').decode('ascii', 'replace')
    vsize, vaddr, raw_size, raw_ptr = struct.unpack_from('<IIII', data, off+8)
    if name == '.rsrc':
        rsrc_raw_ptr = raw_ptr
        break

code_strings = []
for r in csv.reader(open(CODE_CSV, encoding='utf-8-sig')):
    if r[0] in T and '%' not in r[0]:
        code_strings.append((r[0], T[r[0]]))

replaced_code = 0
replaced_ustr = 0
skipped_long = []

def is_ustr_inline(idx, ascii_len):
    """检测 VCL UnicodeString 内联字面量：前 8 字节 = ff ff ff ff + 长度"""
    if idx < 8:
        return False
    return data[idx-8:idx-4] == b'\xff\xff\xff\xff' and struct.unpack_from('<I', data, idx-4)[0] == ascii_len

for en, zh in code_strings:
    ascii_bytes = en.encode('ascii', errors='ignore')
    pos = 0
    found = 0
    while True:
        idx = data.find(ascii_bytes, pos, rsrc_raw_ptr)
        if idx < 0:
            break
        if is_ustr_inline(idx, len(ascii_bytes)):
            # UnicodeString 内联：UTF-8 + 更新 Len（字符数）
            utf8 = zh.encode('utf-8')
            if len(utf8) <= len(ascii_bytes):
                struct.pack_into('<I', data, idx-4, len(zh))
                data[idx:idx+len(utf8)] = utf8
                found += 1
                replaced_ustr += 1
            else:
                skipped_long.append((en, 'UStr', len(ascii_bytes), len(utf8)))
            pos = idx + 1
            continue
        # C 字符串：GBK + 边界检查
        before_ok = idx == 0 or data[idx-1] == 0 or not (0x20 <= data[idx-1] < 0x7F)
        after_ok = data[idx+len(ascii_bytes)] == 0
        if before_ok and after_ok:
            gbk = zh.encode('gbk')
            if len(gbk) <= len(ascii_bytes):
                data[idx:idx+len(ascii_bytes)] = gbk + b'\x00' * (len(ascii_bytes) - len(gbk))
                found += 1
            else:
                skipped_long.append((en, 'CStr', len(ascii_bytes), len(gbk)))
        pos = idx + 1
    if found:
        replaced_code += 1

print('代码字符串替换: %d 条 (其中 UnicodeString 内联 %d 处)' % (replaced_code, replaced_ustr))
if skipped_long:
    print('跳过 %d 处:' % len(skipped_long))
    for en, kind, al, gl in skipped_long[:15]:
        print('  [%s] %-40s %d→%d' % (kind, en[:40], al, gl))

open(WORK, 'wb').write(data)

# ============ 2. Windows API 更新 dfm 资源 ============
RT_RCDATA = 10
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
BeginUpdateResourceW = k32.BeginUpdateResourceW
BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
BeginUpdateResourceW.restype = wintypes.HANDLE
UpdateResourceW = k32.UpdateResourceW
UpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPVOID, wintypes.WORD, wintypes.LPVOID, wintypes.DWORD]
UpdateResourceW.restype = wintypes.BOOL
EndUpdateResourceW = k32.EndUpdateResourceW
EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
EndUpdateResourceW.restype = wintypes.BOOL

dfm_map = {}
for f in os.listdir(DFM_ZH):
    if f.endswith('.dfm'):
        dfm_map[f[:-4]] = open(os.path.join(DFM_ZH, f), 'rb').read()

hUpdate = BeginUpdateResourceW(WORK, False)
if not hUpdate:
    print('BeginUpdateResource 失败, error=%d' % ctypes.get_last_error())
    raise SystemExit(1)

updated = 0
for name, payload in dfm_map.items():
    buf = ctypes.create_string_buffer(payload)
    ok = UpdateResourceW(hUpdate, ctypes.c_void_p(RT_RCDATA), ctypes.c_wchar_p(name), 0, buf, len(payload))
    if not ok:
        print('UpdateResource 失败: %s error=%d' % (name, ctypes.get_last_error()))
    else:
        updated += 1

if not EndUpdateResourceW(hUpdate, False):
    print('EndUpdateResource 失败, error=%d' % ctypes.get_last_error())
    raise SystemExit(1)

print('UpdateResource 更新 dfm: %d/%d' % (updated, len(dfm_map)))
print()
print('已生成:', WORK, '大小:', os.path.getsize(WORK))
