import re

for fp in ['database/defects.py', 'database/corrosion_indicators.py']:
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    text = re.sub(r'\\"+"', '"""', text)
    text = re.sub(r'"{4,}', '"""', text)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Cleaned', fp)
