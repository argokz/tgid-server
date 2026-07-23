with open('database/defects.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('\"\"', '\"\"\"')

with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated defects.py')
