import re

map_col = dict()

#------------------------------------------------------

def initColumnRusName(database):
    
    initColumnRusNameFile(database, f'{database}.txt1')
    initColumnRusNameFile(database, f'{database}.txt2')
    initColumnRusNameFile(database, f'{database}.txt3')
    initColumnRusNameFile(database, f'{database}.txt4')

#------------------------------------------------------

def initColumnRusNameFile(database, klfn):
    print(database, klfn)

    with open(klfn, 'r', encoding='cp1251', errors='replace') as file: 
        for line in file:
            line = line.rstrip()
            if line == '' or line[0] == '-': 
                continue

            m = re.match(r'"(.+?)"\s*,\s*"(.+?)"\s*,\s*"(.*?)"\s*(,\s*"(.+?)")?', line)
            if m:
                name_e = m.group(1)
                name_col_e = m.group(2)
                name_col_r = m.group(3)
                a4 = m.group(4)
                name_full = m.group(5)

                d = database.lower();
                table = name_e.lower();
                column = name_col_e.lower();
                
                map_col[table, column] = (name_col_r, name_full)

            else:
                if line != '' and line[0] != '-':
                    print('Error!', line)
                
#------------------------------------------------------


def r_names(col):
    words = re.split(r'\|', col)
#    print(words)

    if len(words) == 1:
        return map_col.get(('?', words[0].lower()), (words[0].lower(), ''))
    
    if len(words) == 2:
        return map_col.get((words[0].lower(), words[1].lower()), (words[1].lower(), ''))

    return (col, col)

#------------------------------------------------------

if __name__ == "__main__":

    initColumnRusName('gid')
#    print(map_col)

#    q = r_names('heatPipeSectionsdiameterinternal')
    q = r_names('heatPipeSections|diameterinternal')

    print(q)
