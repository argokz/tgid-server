with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('\\\"\\\"\\\"(', '\"\"\"(').replace('\\\"\\\"\\\"', '\"\"\"')
t = t.replace('        if season_year is not None:', '    if season_year is not None:')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed corrosion_indicators.py indentation.')
