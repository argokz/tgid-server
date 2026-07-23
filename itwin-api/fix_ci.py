with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('cast: str = \"\"\"', 'cast: str = \"\"')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed corrosion_indicators.py')
