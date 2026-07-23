with open('database/calculations.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('\"\"\"\"\"', '\"\"\"').replace('\"\"\"\"', '\"\"\"').replace('\"\"\"\"', '\"\"\"')
with open('database/calculations.py', 'w', encoding='utf-8') as f:
    f.write(c)

with open('database/defects.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('\"\"\"\"\"\"', '\"\"\"').replace('\"\"\"\"\"', '\"\"\"').replace('\"\"\"\"', '\"\"\"')
with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(c)

with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('\"\"\"\"\"', '\"\"\"').replace('\"\"\"\"', '\"\"\"').replace('\"\"\"\"', '\"\"\"')
c = c.replace('EXTRACT(YEAR FROM COALESCE(indicator.data_ustanovki, indicator.data_planirovaniya))::int={param}', 'EXTRACT(YEAR FROM COALESCE(indicator.data_ustanovki, indicator.data_planirovaniya))::int=')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Fixed exact 3 files.')
