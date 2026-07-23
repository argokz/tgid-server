with open('database/defects.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('cast: str = \"\"\",', 'cast: str = \"\",')
with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(t)

with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('row[\"label\"] or \"\"\",', 'row[\"label\"] or \"\",')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(t)

print('Fixed cast default parameter.')
