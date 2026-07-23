with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('if clauses else \"\"\", values', 'if clauses else \"\", values')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed corrosion_indicators.py return statement.')
