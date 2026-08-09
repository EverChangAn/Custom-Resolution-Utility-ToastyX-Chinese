# -*- coding: utf-8 -*-
"""保存全部 RCDATA (dfm) 资源到独立文件，名称=资源名"""
import pefile, os

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
OUT = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\dfm'
os.makedirs(OUT, exist_ok=True)

pe = pefile.PE(EXE)

def get_raw(rva, size):
    for sec in pe.sections:
        if sec.VirtualAddress <= rva < sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData):
            return pe.get_data(rva, size)
    return None

saved = []
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id != 10 or not entry.directory:
        continue
    for e2 in entry.directory.entries:
        name = str(e2.name) if e2.name else f'ID{e2.id}'
        if not e2.directory:
            continue
        for e3 in e2.directory.entries:
            raw = get_raw(e3.data.struct.OffsetToData, e3.data.struct.Size)
            if raw and raw.startswith(b'TPF0'):
                path = os.path.join(OUT, name + '.dfm')
                with open(path, 'wb') as f:
                    f.write(raw)
                saved.append((name, len(raw)))

print(f'已保存 {len(saved)} 个 dfm 资源:')
for n, s in saved:
    print(f'  {n:35s} {s:6d} 字节')
