# -*- coding: utf-8 -*-
"""step11b-0: 统计原 exe 资源段布局，核算重建空间"""
import struct, glob, os

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
data = open(EXE, 'rb').read()

# 节表
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
coff = e_lfanew + 4
machine, nsec, ts, p_sym, n_sym, opt_size, chars = struct.unpack_from('<HHIIIHH', data, coff)
opt = coff + 20
opt_magic = struct.unpack_from('<H', data, opt)[0]
num_rva = struct.unpack_from('<I', data, opt + 92)[0]
dd_start = opt + 96
dd = []
for i in range(16):
    rva, size = struct.unpack_from('<II', data, dd_start + i*8)
    dd.append((rva, size))
secs = []
for i in range(nsec):
    off = opt + opt_size + i*40
    name = data[off:off+8].rstrip(b'\0').decode('ascii', 'replace')
    vsize, vaddr, raw_size, raw_ptr = struct.unpack_from('<IIII', data, off+8)
    secs.append((name, vaddr, vsize, raw_ptr, raw_size))

size_of_image = struct.unpack_from('<I', data, opt+56)[0]
file_align = struct.unpack_from('<I', data, opt+36)[0]
sec_align = struct.unpack_from('<I', data, opt+32)[0]

print('=== 节表 ===')
for name, vaddr, vsize, raw_ptr, raw_size in secs:
    print('  %-8s VMA=0x%06x vsize=0x%x raw=0x%x@0x%x' % (name, vaddr, vsize, raw_size, raw_ptr))
print('SizeOfImage=0x%x FileAlign=0x%x SecAlign=0x%x' % (size_of_image, file_align, sec_align))
print('文件总大小:', len(data))

rsrc_rva, rsrc_size = dd[2]
reloc_rva, reloc_size = dd[5]
print()
print('资源目录 RVA=0x%x size=0x%x' % (rsrc_rva, rsrc_size))
print('.rsrc 可用虚拟空间: 0x%x - 0x%x = 0x%x (%d 字节)' % (reloc_rva, rsrc_rva, reloc_rva-rsrc_rva, reloc_rva-rsrc_rva))

# 统计资源数据总量（用 pefile）
import pefile
pe = pefile.PE(EXE)
total_data = 0
count = 0
dfm_old = 0
dfm_new = 0
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if not entry.directory:
        continue
    for e2 in entry.directory.entries:
        if not e2.directory:
            continue
        for e3 in e2.directory.entries:
            sz = e3.data.struct.Size
            total_data += sz
            count += 1
            if entry.id == 10:
                dfm_old += sz

print()
print('资源总数:', count, ' 数据总量:', total_data, '(0x%x)' % total_data)
print('原 dfm 数据总量:', dfm_old)

# 新 dfm 总大小
new_dfm_total = sum(len(open(f,'rb').read()) for f in glob.glob(r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm_zh\*.dfm'))
print('新 dfm 数据总量:', new_dfm_total, '(+%d)' % (new_dfm_total - dfm_old))

# 目录结构估算：三级目录 + 数据入口
dir_bytes = 16 + count * 8  # 根(类型) + 每资源一个入口
dir_bytes += 16 + count * 8 # 名称级（假设每资源一个名称条目，实际有分组）
dir_bytes += 16 + count * 8 # 语言级
dir_bytes += count * 16     # 数据入口
print('目录结构估算: ~%d 字节' % dir_bytes)

need = total_data + (new_dfm_total - dfm_old) + dir_bytes
avail = reloc_rva - rsrc_rva
print()
print('重建后需要: ~%d 字节 (0x%x)' % (need, need))
print('可用: %d 字节' % avail)
print('是否够用:', 'YES' if need <= avail else 'NO — 需要扩展方案')
