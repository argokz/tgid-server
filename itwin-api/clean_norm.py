for path in ['database/corrosion_indicators.py', 'database/defects.py']:
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    t = t.replace('(search or \"\"\").strip()', '(search or \"\").strip()')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(t)
    print('Cleaned', path)
