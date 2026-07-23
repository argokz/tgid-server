import os

for path in ['database/defects.py', 'database/corrosion_indicators.py']:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    # Replace escaped quotes
    while '\"\"' in text:
        text = text.replace('\"\"', '\"\"\"')
    while '\"\"\"\"' in text:
        text = text.replace('\"\"\"\"', '\"\"\"')
        
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Cleaned', path)
