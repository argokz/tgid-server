with open('database/defects.py', 'r', encoding='utf-8') as f:
    t = f.read()
t = t.replace('if clauses else \"\"\", values', 'if clauses else \"\", values')
with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed defects.py return statement.')
