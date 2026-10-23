import os
import re
from collections import defaultdict

map_b5 = defaultdict(set)


# [Claude 2026-10-18] Разбирает строку b5.txt (11 полей через запятую) и добавляет запись в map_b5[схема].
# Строки с другим числом полей молча пропускаются; параметр id не используется.
def read_b5_line(line, id):
    words = re.split(',', line)

    if len(words) == 11:
        cxema,name1,po1,name2,po2,typ,x1,y1,x2,y2,t = words
#        print(cxema,name1,po1,name2,po2,typ,x1,y1,x2,y2,t)
        map_b5[cxema].add((name1,po1,name2,po2,typ,x1,y1,x2,y2,t))

#        if name2 == '':
#            exit(0)

# [Claude 2026-10-18] Возвращает множество записей b5 для схемы cxema или None.
def get_b5(cxema):
    s = map_b5.get(cxema, None)
    return s

#    if s is None: return None;

#    return sorted(s)


# [Claude 2026-10-18] Читает b5.txt (cp1251) из каталога модуля и заполняет map_b5.
def open_b5():
    parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
#    print(parent_dir)
#    exit(0)
    
    with open(parent_dir+'/b5.txt', mode='r', encoding='cp1251') as file:
        id = 10

        for line in file:
            line = line.rstrip()
            read_b5_line(line, id)

#            print(line)
        
    

if __name__ == "__main__":
    open_b5()
    qq = get_b5('7.10')

    for x in qq:
        print(x)