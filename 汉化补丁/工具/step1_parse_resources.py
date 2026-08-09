# -*- coding: utf-8 -*-
"""解析 CRU.exe 的 PE 资源目录，列出全部资源并检测 dfm 格式"""
import struct

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
data = open(EXE, 'rb').read()

e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
assert data[e_lfanew:e_lfanew+4] == b'PE\0\0'
coff = e_lfanew + 4
machine, nsec, ts, p_sym, n_sym, opt_size, chars = struct.unpack_from('<HHIIIHH', data, coff)
opt = coff + 20
opt_magic = struct.unpack_from('<H', data, opt)[0]
num_rva = struct.unpack_from('<I', data, opt + 92)[0]  # NumberOfRvaAndSizes
dd_start = opt + 96  # DataDirectory 起点（PE32）
dd = []
for i in range(min(num_rva, 16)):
    rva, size = struct.unpack_from('<II', data, dd_start + i*8)
    dd.append((rva, size))
rsrc_rva, rsrc_size = dd[2]

# 节表
secs = []
for i in range(nsec):
    off = opt + opt_size + i*40
    name = data[off:off+8].rstrip(b'\0').decode('ascii', errors='replace')
    vsize, vaddr, raw_size, raw_ptr = struct.unpack_from('<IIII', data, off+8)
    secs.append((name, vaddr, vsize, raw_ptr, raw_size))

def rva2off(rva):
    for name, vaddr, vsize, raw_ptr, raw_size in secs:
        if vaddr <= rva < vaddr + max(vsize, raw_size):
            return raw_ptr + (rva - vaddr)
    return None

RSRC_TYPES = {1:'CURSOR',2:'BITMAP',3:'ICON',6:'MENU',9:'STRING',10:'RCDATA',11:'MESSAGETABLE',16:'VERSION',24:'MANIFEST'}
res_types = {}
group_icons = {}

# .rsrc 节的原始文件偏移（资源目录内的偏移都相对它）
rsrc_raw_off = None
for name, vaddr, vsize, raw_ptr, raw_size in secs:
    if name == '.rsrc':
        rsrc_raw_off = raw_ptr
        break
assert rsrc_raw_off is not None, '.rsrc 节未找到'

def parse_dir(off, level, path):
    n_named, n_id = struct.unpack_from('<HH', data, off)
    entries = n_named + n_id
    p = off + 16
    for i in range(entries):
        name_id, off_to_data = struct.unpack_from('<II', data, p + i*8)
        if off_to_data & 0x80000000:
            # 子目录：相对资源基址的偏移
            sub_off = rsrc_raw_off + (off_to_data & 0x7FFFFFFF)
            parse_dir(sub_off, level+1, path + [(name_id, off_to_data)])
        else:
            # DATA_ENTRY：相对资源基址的偏移
            entry_off = rsrc_raw_off + off_to_data
            rva, size, codepage, reserved = struct.unpack_from('<IIII', data, entry_off)
            raw_off = rva2off(rva)
            path_str = '/'.join(str(x[0]) for x in path + [(name_id, 0)])
            res_types.setdefault(path_str, []).append((raw_off, size, codepage))

parse_dir(rsrc_rva, 0, [])

print('=== 资源清单（类型ID/名称ID → 数量）===')
for k, v in sorted(res_types.items(), key=lambda x: (len(x[0].split('/')), x[0])):
    print(f'  {k}: {len(v)} 个资源')

# 重点看 RCDATA (10) 资源 —— dfm 窗体
print()
print('=== RCDATA 资源明细（10/*）===')
rcdata = []
for k, v in res_types.items():
    parts = k.split('/')
    if parts[0] == '10':
        for off, size, cp in v:
            name = parts[1] if len(parts) > 1 else '?'
            sig = data[off:off+16]
            is_text = sig.startswith(b'object')
            is_bin = sig.startswith(b'TPF0')
            fmt = '文本dfm' if is_text else ('二进制dfm(TPF0)' if is_bin else '其他')
            rcdata.append((name, off, size, fmt, sig[:24]))
            print(f'  名称={name:35s} 偏移=0x{off:x} 大小={size:6d} 格式={fmt} 头={sig[:20]}')

print()
print(f'RCDATA 总数: {len(rcdata)}')
