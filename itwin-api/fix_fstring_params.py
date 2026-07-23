with open('database/defects.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('d.nodeid1 = {param}', 'd.nodeid1 = ')
text = text.replace('OR d.nodeid2 = {param}', 'OR d.nodeid2 = ')
text = text.replace('AND (selected_line.nodeid1 = {param} OR selected_line.nodeid2 = {param})', 'AND (selected_line.nodeid1 =  OR selected_line.nodeid2 = )')
with open('database/defects.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('database/corrosion_indicators.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('EXTRACT(YEAR FROM COALESCE(indicator.data_ustanovki, indicator.data_planirovaniya))::int=', 'EXTRACT(YEAR FROM COALESCE(indicator.data_ustanovki, indicator.data_planirovaniya))::int={param}')
text = text.replace('::int={param}', '::int=')
text = text.replace('::int=', '::int={param}')
with open('database/corrosion_indicators.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed fstring params.')
