# -*- coding: utf-8 -*-
"""step8: 代码字符串源码上下文核查 — 判断每条是否确认是 UI 文本"""
import os, re, glob, csv, collections

SRC = r'C:\Users\Administrator\WorkBuddy\CRU汉化\原始文件\cru-1.5.3-src\CRU\CRU'
CODE_CSV = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\strings_code.csv'
OUT = r'C:\Users\Administrator\WorkBuddy\CRU汉化\汉化工作区\code_strings_audit.csv'

# UI 输出 API（在这些附近 = 界面文本）
UI_APIS = ['MessageBox', 'ShowMessage', 'MessageDlg', 'SetWindowText', 'Text =', 'Caption =',
           'Items->Add', 'AddObject', '->Add(', 'AddString', 'Label', 'Hint =', 'Title',
           'ListBox', 'ComboBox', 'Edit->Text', '->Text =', 'Form->Caption']
# 危险用途（绝对不能翻）
DANGER = ['RegSetValue', 'RegQueryValue', 'RegOpenKey', 'RegCreateKey', 'RegDeleteKey',
          'fopen', 'fwrite', 'fread', 'CreateFile', 'WriteFile', 'ReadFile',
          'strcmp', 'strncmp', 'wcscmp', 'lstrcmp', 'CompareString', '== "', '!= "',
          'GetProcAddress', 'LoadLibrary', 'Format("', 'sscanf', 'atoi', 'atof', 'strtol',
          'FindWindow', 'CreateWindow', 'RegisterClass', 'GetWindowText',
          'URLDownloadToFile', 'ShellExecute', 'WinExec', 'system(']

# 读待核查列表
rows = list(csv.reader(open(CODE_CSV, encoding='utf-8-sig')))
targets = [r[0] for r in rows[1:]]

# 源码文件缓存
files = {}
for f in glob.glob(os.path.join(SRC, '*.cpp')) + glob.glob(os.path.join(SRC, '*.h')):
    files[os.path.basename(f)] = open(f, encoding='utf-8', errors='replace').readlines()

results = []
for s in targets:
    hits = []   # (file, line_no, context, cat)
    for fname, lines in files.items():
        for i, line in enumerate(lines):
            # 字符串作为字面量出现（含引号）
            if '"' + s + '"' in line or 'L"' + s + '"' in line:
                ctx = line.strip()
                cat = 'UI' if any(a in line for a in UI_APIS) else None
                dng = any(a in line for a in DANGER)
                if dng:
                    cat = '危险'
                elif cat is None:
                    # 看同语句是否有 UI 特征（消息/赋值）
                    if 'Message' in line or 'msg' in line.lower() or '->' in line:
                        cat = '待核'
                    else:
                        cat = '待核'
                hits.append((fname, i+1, ctx[:120], cat))
    # 聚合判断
    cats = collections.Counter(h[3] for h in hits)
    if not hits:
        final = '源码未直接出现(可能被拼接)'
    elif cats.get('危险', 0) > 0:
        final = '危险-不翻'
    elif cats.get('UI', 0) > 0:
        final = '确认UI-可翻'
    else:
        # 细分待核：按源码用法模式
        ctx_all = ' '.join(h[2] for h in hits)
        if 'snprintf' in ctx_all or 'sprintf' in ctx_all or 'Format' in ctx_all:
            final = '显示格式串-可翻(保留占位符)'
        elif 'TextWidth' in ctx_all or 'Canvas' in ctx_all:
            final = '布局测量-不翻'
        elif 'FatalError' in ctx_all or 'Message' in ctx_all:
            final = '错误弹窗-可翻'
        elif '"' in ctx_all and ('],' in ctx_all or '}' in ctx_all or '","' in ctx_all or re.search(r'"[^"]*",\s*$', ' '.join(h[2] for h in hits))):
            final = '数组数据-可翻'
        else:
            final = '待核-需人工确认'
    results.append((s, len(hits), final, hits[:4]))

# 输出
with open(OUT, 'w', encoding='utf-8-sig', newline='') as fout:
    w = csv.writer(fout)
    w.writerow(['原文', '出现次数', '判定', '上下文示例'])
    for s, n, final, hits in results:
        ctxs = ' | '.join('%s:%d: %s' % (f, l, c) for f, l, c, _ in hits[:3])
        w.writerow([s, n, final, ctxs])

stats = collections.Counter(r[2] for r in results)
print('=== 核查统计 ===')
for k, v in stats.items():
    print('  %s: %d 条' % (k, v))
print()
print('=== 危险/待核 明细 ===')
for s, n, final, hits in results:
    if final != '确认UI-可翻':
        print('  [%s] %s' % (final, s[:70]))
        for f, l, c, _ in hits[:2]:
            print('      %s:%d: %s' % (f, l, c[:100]))
