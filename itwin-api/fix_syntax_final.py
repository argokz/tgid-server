with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('cast: str = \"\"\",', 'cast: str = \"\",')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(t)

with open('database/defects.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('\\\"\\\"\\\"(', '\"\"\"(').replace('\\\"\\\"\\\"', '\"\"\"')
t = t.replace('    if line_id is not None:\n        _add_filter(clauses, values, "d.lineid = {param}", line_id)\n        if node_id is not None:', '    if line_id is not None:\n        _add_filter(clauses, values, "d.lineid = {param}", line_id)\n    if node_id is not None:')
with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(t)

print('Fixed syntax final.')
