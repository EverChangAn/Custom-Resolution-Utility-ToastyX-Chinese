# -*- coding: utf-8 -*-
"""用 pefile 解析 CRU.exe 资源，列出 RCDATA 资源并检测 dfm 格式"""
import pefile
import struct

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
pe = pefile.PE(EXE)

def get_raw(rva, size):
    for sec in pe.sections:
        if sec.VirtualAddress <= rva < sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData):
            return pe.get_data(rva, size)
    return None

print('=== 资源目录 ===')
if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        type_id = entry.id
        print(f'\n类型 {type_id} ({entry.name or "ID"})')
        if not entry.directory:
            continue
        for e2 in entry.directory.entries:
            name = e2.name if e2.name else f'ID:{e2.id}'
            if not e2.directory:
                continue
            for e3 in e2.directory.entries:
                rva = e3.data.struct.OffsetToData
                size = e3.data.struct.Size
                raw = get_raw(rva, size)
                sig = raw[:16] if raw else b''
                is_text = sig.startswith(b'object')
                is_bin = sig.startswith(b'TPF0')
                fmt = '文本dfm' if is_text else ('二进制dfm(TPF0)' if is_bin else '其他')
                lang = str(e3.data.lang)
                print(f'  {str(name):30s} lang={lang} size={size:6d} fmt={fmt} 头={sig[:20]!r}')
                if is_text or is_bin:
                    # 保存资源数据到文件
                    out = rf'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\res_{type_id}_{e2.id}.bin'
                    with open(out, 'wb') as f:
                        f.write(raw)
else:
    print('无资源目录')
