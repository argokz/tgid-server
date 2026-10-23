import pyodbc
import re
import os
import sys


# [Claude 2026-10-18] Формирует для INSERT строку колонок (в кавычках, нижний регистр) и строку значений (None -> NULL).
# Возвращает (table, scols, svals).
def initInsert(table, cols, vals) :
    insert = ""
    scols = ""
    svals = ""
    i = 0

    for v1 in vals :
        if scols != "" : scols += ","

#       scols += "["+cols[i]+"]"
        scols += '"'+cols[i].lower()+'"'
#        scols += '"'+cols[i]+'"'
                
        if svals != "" : svals += ","

        if v1 is None or (v1 is None and cols[i].lower() == "id"):
#            svals += "DEFAULT"
            svals += "NULL"
        else :
            svals += typeValidate2(cols[i], v1)

        i += 1

#   table = table.replace(".", "].[")

    return (table, scols, svals)



# [Claude 2026-10-18] Текст INSERT одной строки в таблицу "table".
def createInsert(table, cols, vals):

    (table, scols, svals) = initInsert(table, cols, vals)
#    insert = "INSERT INTO ["+table+"] ("+scols+") VALUES ("+svals+")"
    insert = "INSERT INTO \"" + table.lower() + "\" ("+scols+") VALUES\n("+svals+")"

    return insert


# [Claude 2026-10-18] То же, что createInsert (дубликат).
def createInsert0(table, cols, vals):
    (table, scols, svals) = initInsert(table, cols, vals)

#    insert = "INSERT INTO ["+table+"] ("+scols+") VALUES ("+svals+")"
    insert = "INSERT INTO \"" + table.lower() + "\" ("+scols+") VALUES\n("+svals+")"

    return insert

# [Claude 2026-10-18] Продолжение многострочного INSERT: ',
# (значения)'.
def createInsertDop(table, cols, vals):
    (table, scols, svals) = initInsert(table, cols, vals)

    insert = ",\n("+svals+")"

    return insert


# [Claude 2026-10-18] Заглушка: всегда возвращает 1 (код получения SCOPE_IDENTITY ниже недостижим).
def getLastID(cursor):
    return 1
#    LAST_INSERT_ID = "SELECT LAST_INSERT_ID()"
    LAST_INSERT_ID = "SELECT SCOPE_IDENTITY() AS id"

    cursor.execute(LAST_INSERT_ID)
    result = cursor.fetchone()

#    print (result['id'])
    
    if result != None :
        result = result['id']
    else:
        print("Ошибка не вернулся последний ID ")

#    print (4)
    
    
    return result


# [Claude 2026-10-18] Выполняет INSERT с commit, возвращает getLastID (всегда 1). При ошибке печатает запрос и завершает процесс (os._exit).
def execInsert(conn, insert, tab) :

    id = 0
    cursor = conn.cursor()
#    isID = insert.find("[id]") >= 0 or insert.find("[ID]") >= 0
    isID = False

    if isID : 
       try :
#         print("SET IDENTITY_INSERT {} ON".format(tab))
         cursor.execute("SET IDENTITY_INSERT [{}] ON".format(tab))
         conn.commit()
       except pyodbc.Error as e:
         pass
    
    try:
#        print(insert)
        cursor.execute(insert)
        conn.commit()
        id = getLastID(cursor)
    
    except pyodbc.Error as e:
        if isID :  print("SET IDENTITY_INSERT [{}] ON".format(tab))
        print (insert)
        if isID :  print("SET IDENTITY_INSERT [{}] OFF".format(tab))
        print (e)
        sys.stdout.flush()
        os._exit(1)

    if isID : 
       try :
#         print("SET IDENTITY_INSERT {} OFF".format(tab))
         cursor.execute("SET IDENTITY_INSERT [{}] OFF".format(tab))
         conn.commit()
       except pyodbc.Error as e:
         pass

    cursor.close()

    return id
