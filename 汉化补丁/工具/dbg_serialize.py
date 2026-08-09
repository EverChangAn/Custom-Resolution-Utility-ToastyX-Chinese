# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区')
from collections import OrderedDict
import pefile

EXE = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3\CRU.exe'
pe = pefile.PE(EXE)
resources = []
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if not entry.directory:
        continue
    for e2 in entry.directory.entries:
        if not e2.directory:
            continue
        for e3 in e2.directory.entries:
            name_str = str(e2.name) if e2.name is not None else None
            rva = e3.data.struct.OffsetToData
            raw = pe.get_data(rva, e3.data.struct.Size)
            resources.append((entry.id, name_str, e2.id, e3.data.lang, raw))

types = OrderedDict()
for type_id, name_str, name_id, lang, raw in resources:
    types.setdefault(type_id, []).append((name_str, name_id, lang, raw))

def names_of(items):
    seen = OrderedDict()
    for name_str, name_id, lang, raw in items:
        key = (name_str, name_id)
        seen.setdefault(key, []).append((lang, raw))
    return seen

type_list = list(types.items())

out = bytearray()
def put_dir(named, ided):
    out.extend(struct.pack('<HHHHHH', 0, 0, 0, 0, len(named), len(ided)))
    for name_off, off, is_dir in named:
        out.extend(struct.pack('<II', 0x80000000 | name_off, off | (0x80000000 if is_dir else 0)))
    for nid, off, is_dir in ided:
        out.extend(struct.pack('<II', nid & 0x7FFFFFFF, off | (0x80000000 if is_dir else 0)))

name_str_list = []
for tid, items in types.items():
    for (name_str, name_id), lang_items in names_of(items).items():
        if name_str is not None and name_str not in name_str_list:
            name_str_list.append(name_str)
for s in name_str_list:
    us = s.encode('utf-16le')
    out.extend(struct.pack('<H', len(s)))
    out.extend(us)
print('字符串区:', len(out))

named, ided = [], []
for type_id, items in type_list:
    if next(iter(names_of(items).items()))[0][0] is not None:
        named.append((0, 0, True))
    else:
        ided.append((type_id, 0, True))
put_dir(named, ided)
print('+root:', len(out))

n_type = 0
n_lang = 0
for type_id, items in type_list:
    ns = names_of(items)
    named, ided = [], []
    for (name_str, name_id), lang_items in ns.items():
        if name_str is not None:
            named.append((0, 0, True))
        else:
            ided.append((name_id, 0, True))
    put_dir(named, ided)
    n_type += 1
    for (name_str, name_id), lang_items in ns.items():
        named, ided = [], []
        for lang, raw in lang_items:
            ided.append((lang, 0, False))
        put_dir(named, ided)
        n_lang += 1
print('+type+lang 目录:', len(out), '(type块=%d, lang块=%d)' % (n_type, n_lang))

print()
print('期望: str=912 root=72 type=7个 lang=25个')
print('type 块期望大小:', 304 + 144 + 24 + 120 + 200 + 24 + 24, '= 840')
print('实际目录总: ', len(out), ' 期望: ', 912 + 72 + 840 + 25 * 24)
