import numpy as np
import pyodbc

class Insert:
    cols = set()
    max_insert = 1000

    def __init__(self, table_name, conn):
        self.row = {}
        self.row0 = {}
        self.table_name = table_name
        self.ins = ''
        self.n = 0
        self.conn = conn
        self.cursor = self.conn.cursor()

    def add_col(self, col, def_val=None):
        self.cols.add(col)
        self.row[col] = def_val
        self.row0[col] = def_val

    def exec(self):
        if self.n > 0:
#            print('----------------------------------')
#            print(self.ins)
            try:
                self.cursor.execute(self.ins)
                self.conn.commit()
            except pyodbc.Error as ex:
                print(ex)
                print('----------------')
                print(self.ins)
                print('----------------')
                exit(0)

    def addRow(self):
        if self.n == self.max_insert:
            self.exec()
            self.ins = ''
            self.n = 0
        
        if self.n == 0:
            cols = self.db_insert_cols()
            self.ins = f'insert into {self.table_name} ({cols}) values\n'

        self.row = self.row0.copy()

        self.n += 1

    def db_write(self, col, val=None):
        if col not in self.cols:
            print(f'Нет колонки {col} в таблице {self.table_name}')
            exit(0)
        
        if type(val) is str:
            val = val.replace('\'', '\'\'')
            val = val.replace('\r\n', '\\n')
            val = val.replace('\n', '\\n')
            val = f'\'{val}\''

        if val != val:
            val = 'null'

        self.row[col] = val

    def db_insert_cols(self):
        vals = ''
        for k, v in self.row.items():
            if vals != '': vals += ','
            vals += k
            
        return vals;

    def db_insert_vals(self):
        vals = ''
        for k, v in self.row.items():
            if vals != '': vals += ','
            if v is None:
                vals += 'NULL'
            else:
                vals += str(v)

        if self.n > 1:   
            self.ins += ',\n'

        self.ins += f'({vals})'

    def insert_text(self):
        cols = self.db_insert_cols()
        return self.ins
    
    
