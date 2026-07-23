import os

files = [
    'database/calculations.py',
    'database/corrosion_indicators.py',
    'database/defects.py'
]

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Clean escaped quotes
    text = text.replace('\"\"', '\"\"\"')
    text = text.replace('\"\"', '\"\"\"')
    text = text.replace('\"\"\"\"', '\"\"\"')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Cleaned quotes in:', fp)
