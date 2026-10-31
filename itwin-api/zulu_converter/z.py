import struct
import sys
import os
import time
import sql_exec
import coord
import potreb
import pyodbc
import sql_words
import transl
import tg
import ur
import zulu_ctp
import zulu_uch
import sqlite3
import tempfile

import networkx as nx

import pypxlib
from pypxlib import Table
from auxiliary import *
#from dom import doma

import config
import connect
import nasos
import d_xml
import del_fragments
import export_tgid


from functools import partial

print = partial(print, flush=True)


from r import r_get

#---------------------------------------------------------------------------

def coord_round(coord):
    if coord is None:
        return None
    x, y = coord

    return (round(x, 4), round(y, 4))

#---------------------------------------------------------------------------

def get_by_coord(d, coord, df):
#    x, y = coord
    return d.get(coord_round(coord), df)
#    return d.get((round(x, 4), round(y, 4)), df)

#---------------------------------------------------------------------------

class Zulu(object):
    def __init__(self):
#        self.Tnv_r = -24
#        self.Tvn = 20

        self.Tnv_r = -38
        self.Tvn = 20

        self.id_ist = None

        self.dict_obj = dict()
        self.dict_types = dict()
        self.dict_table = dict()
        self.dict_db_id = dict()
        self.dict_db_id_new = dict()
        self.dict_nodes_coord = dict()
        self.dict_pumps = dict()
        self.dict_zd = dict()
        self.dict_zd2 = dict()
        self.dict_ctp = dict()
        self.dict_ur = dict()  # Удельные расходы
        self.dict_tr = dict()  # Расчетные температуры
        self.dict_ist = dict()
        self.dict_rs = dict()

        self.dict_peremych = dict()
        self.dict_dross = dict()

        self.set_nodes_unknown = set()
        self.set_lines_unknown = set()
        
        self.graph = nx.Graph()

#---------------------------------------------------------------------------

    def exec(self, q, message=True):
#        return
        """
        Выполнить запрос
        """
        try:
#            print(q)
            self.cursor.execute(q)
            self.conn.commit()
            ret = True
        except pyodbc.Error as e:
            if message:
                print('----------------')
    #            print(str(e.args[1], 'utf8'))
                print(e)
                print(q)
                print('----------------')
#                exit(0)
        else:
#            print('Ok!')
            pass

        return True

    qqq = 0

    def insert(self, q):
#        self.qqq += 1
#        return self.qqq

        self.exec(q)

#        return self.cursor.lastrowid

        return getLastID(self.cursor)

#---------------------------------------------------------------------------

    def set_filename(self, filename):
        self.filename = filename

#---------------------------------------------------------------------------

#    def connect(self, host, user, password, baza, typ_mas = 0):
    def connect(self, sqlite_file):

        typ_mas = 0
        self.off_shx = []

        '''
        self.host = host
        self.user = user
        self.password = password
        self.typ_mas = typ_mas

#        self.conn = connector.connectToMsSQL(self.host, self.user, self.password, baza)

        c = {}

        c['server'] = self.host
        c['user'] = self.user
        c['password'] = self.password

        c['db'] = baza
        c['port'] = 1433
        '''

#        self.conn = connect.connect_ms_sql(**c)
        
        try:        
            os.remove(sqlite_file)
        except FileNotFoundError:
            pass

        self.conn = connect.connect_sqlite(sqlite_file)

        self.cursor = self.conn.cursor()

#---------------------------------------------------------------------------

    def read_zulu_b01_init(self, b01_off, loc0):

        
        with open(self.filename+".b01","rb") as f:
            f.seek(b01_off)

            (x1, y1) = read_xy(f)
            (x2, y2) = read_xy(f)

            size = read_short(f)

#          print('size=', size)

            for i in range(size):
                id = read_long(f)
                off = read_long(f)

                loc = read_char(f)
                typ = read_char(f)

                cc1 = read_char(f)
                regim = read_char(f)

                l11_2 = read_short(f)

                typ2 = read_long(f)
                ll2 = read_long(f)

                off += b01_off
                if loc == 4: off += 8

                if loc == loc0 or (loc0 == -1 and not loc in [0,2]):
#                    print('++', loc0, loc, id, off, loc, typ, cc1, regim, l11_2, typ2, ll2)
                    self.dict_obj[id] = (id, off, loc, typ, cc1, regim, l11_2, typ2, ll2)

#---------------------------------------------------------------------------

    def set_pump_and_ctp(self, coor):
        pump = get_by_coord(self.dict_pumps, coor[0], None)

        if not pump is None:
             externalCodeID, n0, n1, n2, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr = pump
             self.dict_pumps[coord_round(coor[0])] = (externalCodeID, n0, n1, coor[-1], Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr)

        pump = get_by_coord(self.dict_pumps, coor[-1], None)

        if not pump is None:
             externalCodeID, n0, n1, n2, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr = pump
             self.dict_pumps[coord_round(coor[-1])] = (externalCodeID, n0, coor[0], n2, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr)



#---------------------------------------------------------------------------

        dross = get_by_coord(self.dict_dross, coor[0], None)

        if not dross is None:
             externalCodeID, n0, n1, n2, regim, H_geo, H, Kreg = dross
             self.dict_dross[coord_round(coor[0])] = (externalCodeID, n0, n1, coor[-1], regim, H_geo, H, Kreg)

        dross = get_by_coord(self.dict_dross, coor[-1], None)

        if not dross is None:
             externalCodeID, n0, n1, n2, regim, H_geo, H, Kreg = dross
             self.dict_dross[coord_round(coor[-1])] = (externalCodeID, n0, coor[0], n2, regim, H_geo, H, Kreg)

#---------------------------------------------------------------------------

        zd2 = get_by_coord(self.dict_zd2, coor[0], None)

        if not zd2 is None:
             externalCodeID, n0, n1, n2, regim, Dpod,Dobr,Per_pod,Per_obr = zd2
             self.dict_zd2[coord_round(coor[0])] = (externalCodeID, n0, n1, coor[-1], regim, Dpod,Dobr,Per_pod,Per_obr)

        zd2 = get_by_coord(self.dict_zd2, coor[-1], None)

        if not zd2 is None:
             externalCodeID, n0, n1, n2, regim, Dpod,Dobr,Per_pod,Per_obr = zd2
             self.dict_zd2[coord_round(coor[-1])] = (externalCodeID, n0, coor[0], n2, regim, Dpod,Dobr,Per_pod,Per_obr)

#---------------------------------------------------------------------------


        ctp = get_by_coord(self.dict_ctp, coor[0], None)

        if not ctp is None:
             externalCodeID, n0, n1, n2, Hpod, Hobr, name_ctp, heatSourceID, T1, T2, T3, r = ctp
             self.dict_ctp[coord_round(coor[0])] = (externalCodeID, n0, n1, coor[-1], Hpod, Hobr, name_ctp, heatSourceID, T1, T2, T3, r)

        ctp = get_by_coord(self.dict_ctp, coor[-1], None)

        if not ctp is None:
             externalCodeID, n0, n1, n2, Hpod, Hobr, name_ctp, heatSourceID, T1, T2, T3, r = ctp
             self.dict_ctp[coord_round(coor[-1])] = (externalCodeID, n0, coor[0], n2, Hpod, Hobr, name_ctp, heatSourceID, T1, T2, T3, r)


        zd = get_by_coord(self.dict_zd, coor[0], None)

        if not zd is None:
             externalCodeID, n0, n1, n2, regim, Dpod,Dobr,Per_pod,Per_obr = zd
             self.dict_zd[coord_round(coor[0])] = (externalCodeID, n0, n1, coor[-1], regim, Dpod,Dobr,Per_pod,Per_obr)

        zd = get_by_coord(self.dict_zd, coor[-1], None)

        if not zd is None:
             externalCodeID, n0, n1, n2, regim, Dpod,Dobr,Per_pod,Per_obr = zd
             self.dict_zd[coord_round(coor[-1])] = (externalCodeID, n0, coor[0], n2, regim, Dpod,Dobr,Per_pod,Per_obr)

#---------------------------------------------------------------------------

    def read_zulu_b01(self):
      """
      Прочитать b01
      """

#      print('++', self.dict_types)

      n_dr = 1
      n_ns = 1
      n_pm = 1

      with open(self.filename+".b01","rb") as f:

          for (id, off, loc, typ, cc1, regim, lll_2, typ2, ll2) in self.dict_obj.values():

              coor = read_xyz(f, off, loc)

#              if coor[0] == (0,0) : continue

              typ_name = self.dict_types.get(typ, None)
              table = self.dict_table.get(typ, None)
              id2 = self.dict_db_id.get((typ, id), -1)


#              print(id, 'id2', id2, 'off:', off, 'typ:', typ, 'cc1?:', cc1, 'loc:', loc, 'regim:', regim, lll_2, typ2, ll2)
#              exit(0)

#              if loc == 0 and typ == 13:  # Вспомогательный участок
              if loc == 0 and id2 == -1:  # Участки без данных
                   id_new_1 = get_by_coord(self.dict_db_id_new, coor[0], -1)
                   id_new_2 = get_by_coord(self.dict_db_id_new, coor[-1], -1)

#                   print(id_new_1, id_new_2)

                   if id_new_1 >= 0 and id_new_2 >= 0:
                       id_new = self.insertLine(id_new_1, id_new_2, coor, coor[0], coor[-1], regim)
                       if id_new > 0:
                           pipeSectStateIDflow = 2 if regim in [1, 3] else 1
                           pipeSectStateIDret = 2 if regim in [1, 2] else 1

                           L = 1
                           diameterCondit, diameterExternal, diameterInternal, wallThickness = (1000, 1000, 1000, 1)

                           insert = f'''INSERT INTO [heatPipeSections] 
                                    (pipeSectStateIDflow,pipeSectStateIDret, lineID, pipeSectLength, diameterCondit, diameterExternal, diameterInternal, wallThickness) 
                                    VALUES ({pipeSectStateIDflow}, {pipeSectStateIDret}, {id_new}, {L}, {diameterCondit}, {diameterExternal}, {diameterInternal}, {wallThickness})'''

                           self.insert(insert)
                   else:
                       print('message1', coor[0], typ, typ_name, id_new_1, id_new_2)

              elif id2 == -1 and loc == 2:  # Узлы без данных
                  Nist = 0
                  externalCodeID = ur.getRS(self, Nist)

#                  print('typ=', typ)

                  if get_by_coord(self.dict_nodes_coord, coor[0], None):
                     print('Уже было 1', coord.xy_to_s(coor[0]), typ_name, node_name)

                  x, y = coor[0]

                  s_coord = coord.xy_to_shape_2(x, y, 0)
                  s_coord1 = coord.xy_to_shape_1(x, y)

                  if typ == 244:  # 44Опора
                    i = f'INSERT INTO [opora] (shape) VALUES ({s_coord})'
                    self.insert(i)
                  elif typ == 22: # 22Компенсатор
                    i = f'INSERT INTO [kompensator] (shape) VALUES ({s_coord})'
                    self.insert(i)
#                  elif typ == 23: # 23Профиль
#                    continue
#                  elif typ == 24: # 24Пересечение
#                    continue

                  elif typ == 92: # Повреждение
                    i = f'INSERT INTO [defect] (shape) VALUES ({s_coord1})'
#                    print(i)
                    self.insert(i)
#                  elif typ == 26: # Аварийная емкость
#                    continue
                  else:
#                      print('??????', coord.xy_to_s(coor[0]), typ, typ_name)

                      if not (typ, typ_name) in self.set_nodes_unknown:
                          print('message2','    ', typ, typ_name)
                          self.set_nodes_unknown.add((typ, typ_name))

                      self.dict_nodes_coord[coord_round(coor[0])] = id

                      (x, y) = coor[0]

                      node_name = typ_name
                      H_geo = 0
                      
                      id_new = self.insertNode(externalCodeID, node_name, coor[0], H_geo, self.fileID)


              elif id2 >= 0:
#                  print(typ_name, 'id:', id, 'id2:', id2)

                  Nist = 0
                  externalCodeID = ur.getRS(self, Nist)

                  if id2 != -1:
                      r = table[id2]
#                      print(id2, r)

                      Nist = int(r_get(r, 'Nist', 0))
                      externalCodeID = ur.getRS(self, Nist)
                  
                  if loc == 2 :
#                       print(coord.xy_to_s(coor[0]))
                       node_name = r_get(r, 'Name', '')
                       prim = r_get(r, 'Prim', '')
                       if prim != '' and not prim is None:
                           node_name += ' ' + prim


                       if node_name == '' or node_name is None: 
                            node_name = f'#{id}'

                            if typ == 7: 
                                node_name = f'ДР{n_dr}'
                                n_dr += 1
                            elif typ == 11: 
                                node_name = f'ПМ{n_pm}'
                                n_pm += 1
                            elif typ == 4: 
                                node_name = f'НС{n_ns}'
                                n_ns += 1

                       H_geo = r_get(r, 'H_geo', 0)

#                       print(node_name)
#                       if node_name is None: node_name = ''

#                       if not typ in [3, 2, 1, 8, 5,     7, ]:
#                           node_name = f'{typ_name} - {node_name}'
#                       elif typ == 5:
#                            node_name = ''

#                       node_name = '{} - id={} id2={}'.format(node_name, id, id2)
#                       node_name = '{} - {}'.format(Nist, node_name)


                       if get_by_coord(self.dict_nodes_coord, coor[0], None):
                          print('Уже было 2', coord.xy_to_s(coor[0]), typ_name, node_name)

                       self.dict_nodes_coord[coord_round(coor[0])] = id

                       (x, y) = coor[0]
                       
                       id_new = self.insertNode(externalCodeID, node_name, coor[0], H_geo, self.fileID)
                       
                       if typ == 2: # Узел
                           Gpod = r_get(r, 'Gpod', 0)
                           Gobr = r_get(r, 'Gobr', 0)

                           '''
                           Тут вставить обработку подпитки
                           '''

                       elif typ == 3: # Потребитель
                          adres = r_get(r, 'Adres', '')
                          insert = potreb.read_potreb(self, r, Nist, regim, id_new, node_name, adres, x, y)
                          self.insert(insert)

                       elif typ == 8: # ЦТП
                           zulu_ctp.ctp(self, Nist, externalCodeID, node_name, x, y, H_geo, coor, id_new, r) 

                       elif typ == 1: # Источник
                           Pt_pod = r_get(r, 'Pt_pod', 0)
                           Pt_obr = r_get(r, 'Pt_obr', 0)

                           H_ras = r_get(r, 'H_ras', 0)   # Расчетный pасполаг. напоp на выходе из источника, м
                           H_obr = r_get(r, 'H_obr', 0)   # Расчетный напоp в обpатн. тp-де на источнике, м

                           Mode = r_get(r, 'Mode', 0)     # Режим работы источника

                           if H_obr != 0 and not H_obr is None:
                               Pt_obr = H_obr-H_geo
                               Pt_pod = Pt_obr + H_ras

#                           print('-------------------------------------------------')
#                           print(f'Источник {typ}, {node_name} {table} {id2}')
#                           print(coord.xy_to_s(coor[0]))
#                           print(r)

                           if node_name == '': node_name = f'Источник {Nist}'

#      GetNameValue(string("t1_r"), t1);
#      GetNameValue(string("t2_r"), t2);
#      GetNameValue(string("t3_r"), t3);
                           t1 = r_get(r, 'T1_r', 0) 
                           t2 = 70
                           t3 = 95
                           uf = 2.2

                           if t1 == 0: t1 = 150

                           if t3 != t2: uf = (t1-t3)/(t3-t2)

#                           print(node_name, 'uf', uf, t1, t2, t3)

                           insert = f'''INSERT INTO [heatSources] 
                                    (nodeID, name, hSourceCode, tvb_tr, tvn_r, tn_5, t1_r, tx_r, hSourcePowerInst, dt2_co, uf) 
                                    VALUES ({id_new}, \'{node_name}\', \'{node_name}\', {self.Tvn}, {self.Tvn}, {self.Tnv_r}, {r_get(r, 'T1_r', 0)}, {r_get(r, 'Thz_r', 0)}, {r_get(r, 'Qmax', 0)}, {2}, {uf})'''


#                           print('>>>>>>>>>>>>>>', node_name, Mode)
                            
                           '''
         <record key="0" value="Выделенный источник" />
         <record key="3" value="Подпитка неограничена" />
         <record key="4" value="Подпитка ограничена заданным значением" />
         <record key="1" value="Подпитки нет, фиксирован располагаемый напор" />
         <record key="2" value="Подпитки нет, фиксировано давление в обратке" />
                           '''
                           id_ist = getLastID(self.cursor)

                           id_ist = self.insert(insert)

                           self.id_ist = id_ist

                           self.dict_ist[Nist] = (Nist, id_ist, x, y, node_name, self.Tnv_r, r_get(r, 'T1_r', 0), r_get(r, 'Thz_r', 0), Mode, H_ras, H_obr, coor[0])

                           if Mode in (1, 2): 
                               xx, yy = coor[0]
#                               xx += 100

                               n0 = coor[0]
                               id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)
                            
                               id_new_ns = self.insertNode(externalCodeID, node_name, (xx+10, yy), H_geo, self.fileID)

                               insert = f'INSERT INTO [pumpStations] (nodeID) VALUES ({id_new_ns})'
#                               self.dict_pumps[coord_round(())] = (externalCodeID, coor[0], None, None, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr)
                               self.insert(insert)
                               
                               id1 = self.insert(f'''INSERT INTO [linesobj] 
                                    (nodeID1, nodeID2, externalSignLineID) 
                                    VALUES ({id_n0},{id_new_ns},1)''')

                               self.insert(f'''INSERT INTO [dampers] 
                                        (lineID, damperArmatureStateID, diameterCondit) 
                                        VALUES ({id1}, 1, 0)''')


                               n1P = self.insertInnerNode(id_new_ns, 2, externalCodeID, 40000, 40000, id_n0)
                               n1O = self.insertInnerNode(id_new_ns, 3, externalCodeID, 40000, 41000, id_n0)

                               if Mode == 1: # Подпитки нет, фиксирован располагаемый напор
                                   self.insertInnerPump(n1O, n1P, 5, H_ras, 0, '')

                               if Mode == 2: # Подпитки нет, фиксировано давление в обратке
                                   n3O = self.insertInnerNode(id_new_ns, 3, externalCodeID, 40000, 40500, id_n0)
                                   self.insertInnerPump(n3O, n1P, 5, H_ras + 10, 0, '')
                                   Kreg = 0
                                   self.insertInnerRD(n1O, n3O, 3, H_obr - H_geo, Kreg)




#    def insertInnerRD(self, n1, n2, externalSignLineID, H, Kreg):



                           if id_ist > 0:

                               if Mode == 0:
                                   if Pt_pod == 0: Pt_pod = 60
                                   if Pt_obr == 0: Pt_obr = 20
                                   insert = f'INSERT INTO [setPressNodes] (nodeID,pressFlow,pressRet,fileID) VALUES ({id_new},{Pt_pod},{Pt_obr},{self.fileID})'
                                   self.insert(insert)

                               q = f'UPDATE [externalCodes] SET heatSourceID={id_ist} WHERE id={externalCodeID}'
                               self.exec(q)
                               self.conn.commit()


                               tg.calc(self.conn, id_ist)

                       elif typ == 4: # Насосная станция
                           Hpod = r_get(r, 'Hpod', 0)
                           Hobr = r_get(r, 'Hobr', 0)
                           Npod = r_get(r, 'Npod', 0)
                           Nobr = r_get(r, 'Nobr', 0)
                           Mark_pod = r_get(r, 'Mark_pod', '')
                           Mark_obr = r_get(r, 'Mark_obr', '')

                           Type_pod = int(r_get(r, 'Type_pod', -1))   # Способ задания насоса на 
                           Type_obr = int(r_get(r, 'Type_obr', -1))

                           Pr_pod = r_get(r, 'Pr_pod', None)   #  Напор после насоса
                           Pr_obr = r_get(r, 'Pr_obr', None)
                           
#                           print("Type", Type_pod, Type_obr, Pr_pod, Pr_obr, Mark_pod, Mark_obr)

                           insert = f'INSERT INTO [pumpStations] (nodeID) VALUES ({id_new})'

                           self.dict_pumps[coord_round(coor[0])] = (externalCodeID, coor[0], None, None, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr)

                           self.insert(insert)

                       elif typ == 5: # Задвижка
                           Dpod = r_get(r, 'Dpod', 0)
                           Dobr = r_get(r, 'Dobr', 0)
                           Per_pod = r_get(r, 'Per_pod', 0)
                           Per_obr = r_get(r, 'Per_obr', 0)
#                           print(Dpod, Dobr)

                           self.dict_zd2[coord_round(coor[0])] = (externalCodeID, coor[0], None, None, regim, Dpod,Dobr,Per_pod,Per_obr)

                           '''
#                           print('Задвижка regim=', regim)
                           self.dict_zd[coord_round(coor[0])] = (externalCodeID, coor[0], None, None, regim, Dpod,Dobr,Per_pod,Per_obr)
                           id_new1 = self.insertNode(externalCodeID, node_name, (x+1, y), H_geo, self.fileID, False)
                           '''

                       elif typ == 11: # Перемычка
#                            print('-------------------------------------------------')
#                            print('Перемычка')
#                            print(r)
#                            print(coord.xy_to_s(coor[0]))

                            '''

                            Nist = r_get(r, 'Nist', 0)
                            H_geo = r_get(r, 'H_geo', 0)
                            H_ras = r_get(r, 'H_ras', 0)
                            H_pod = r_get(r, 'H_pod', 0)
                            H_obr = r_get(r, 'H_obr', 0)
                            Ppod = r_get(r, 'Ppod', 0)
                            Pobr = r_get(r, 'Pobr', 0)
                            Time = r_get(r, 'Time', 0)
                            Tpod = r_get(r, 'Tpod', 0)
                            Tobr = r_get(r, 'Tobr', 0)
                            Dist = r_get(r, 'Dist', 0)
                            Tb = r_get(r, 'Tb', 0)
                            Hstat = r_get(r, 'Hstat', 0)
                            '''
                            self.dict_peremych[coord_round(coor[0])] = (externalCodeID, coor[0], regim)
#                            print('+++++', externalCodeID, coord_round(coor[0]))

#                            print(self.dict_peremych)
#                            self.peremychka()
#                            exit(0)

                       elif typ == 7: # Дросселирующий узел
                            H = r_get(r, 'H', 0)
                            Kreg = r_get(r, 'Kreg', 0)

                            self.dict_dross[coord_round(coor[0])] = (externalCodeID, coor[0], None, None, regim, H_geo, H, Kreg)
#                            print('-------------------------------------------------')
#                            print(f'Дросселирующий узел {typ}, {node_name} {table} {id2}')
#                            print(coord.xy_to_s(coor[0]))

#                            print('Дросселирующий узел regim=', regim)
#                            print('+', regim, H, Kreg)
#                       elif typ == 11: # Перемычка
#                            pass
                       elif typ == 12: # Обобщенный потребитель

                          adres = r_get(r, 'Adres', '')

#                          print(f'Nist={Nist}')

                          insert = potreb.read_obob_potreb(self, r, Nist, regim, id_new, node_name, adres, x, y)
                          self.insert(insert)

                       else:
                           if typ != 10:
                               print('-------------------------------------------------')
                               print(f'Неизвестный тип объекта {typ}, {node_name} {table} {id2}')
                               print(coord.xy_to_s(coor[0]))
                               print(r)

                  elif loc == 0 :
                       zulu_uch.uch(self, r, coor, typ, regim)
                  else:
                        print('loc = ', loc)

              else:
#                pass
                if loc != 6:
                    print('message3',f'=== {typ_name} id2={id2} id={id}, off={off}, loc={loc}, typ={typ}, cc1, regim={regim}, lll_2={lll_2}, typ2={typ2}, ll2={ll2}')
                    (x, y, lf, text, alpha, l1_2, l2) = read_xyz6(f, off, loc)
                    print('message4',x, y, lf, text, alpha, l1_2, l2)




#---------------------------------------------------------------------------

    def read_zulu_b01_geo(self):
        """
        Читать геобазу
        """

        print('Начал geo')
        
        
        self.tableL = sql_words.isprSqlWord(transl.translit3(self.table_name))
        print(f'0,"{self.tableL}","{self.table_name}"')

#        self.exec('DROP TABLE [{}_text]'.format(self.tableL))
#        self.exec('CREATE TABLE [{}_text](id INT NOT NULL IDENTITY , text NTEXT, shape geometry, PRIMARY KEY (id))'.format(self.tableL))
        self.is_text = False
        self.is_geo = False

        with open(self.filename+".b01","rb") as f:
            for (id, off, loc, typ, cc1, regim, lll_2, typ2, ll2) in self.dict_obj.values():
#                if loc != 2 and loc != 0 and loc != 5:
#                    print(id, off, loc, typ, cc1, regim, lll_2, typ2, ll2)

#                print('message5',id, off, loc, typ, cc1, regim, lll_2, typ2, ll2)

                if loc == 5 :  # Геобаза
                    continue
                    coor = read_xyz_debug(f, off, loc)

#                    if id == 129:
#                        coor = read_xyz_debug(f, off, loc)
#                        exit(0)

                    s = coord.xy_to_shape(coor)

#                    if self.tableL.lower() == 'irtish':
                    print('message6',id, s)

                    (street, dom) = ('', '')
                    is_addres = False

#                    print(self.tableL, self.table[0])

                    '''
                    if self.tableL == 'doma':
                        for (street, dom, x, y) in doma:
                            if coord.find3(coor, x, y):
                                is_addres = True
                                break
                                '''

                    if not self.is_geo:
                       self.exec(f'DROP TABLE [{self.tableL}]')
                       if self.tableL == 'doma':
                           self.exec(f'CREATE TABLE [{self.tableL}](id INTEGER PRIMARY KEY AUTOINCREMENT , street  text, number_1 text, kod text, uzel text, type_con INT,  color_f INT, shape geometry)')
                       else:
                           self.exec(f'CREATE TABLE [{self.tableL}](id INTEGER PRIMARY KEY AUTOINCREMENT , text TEXT, shape geometry)')
                       self.is_geo = True
                    
                    if is_addres:
                        i = f'INSERT INTO [{self.tableL}] (shape, street, number_1) VALUES ({s}, \'{street}\', \'{dom}\')'
                    else:
                        i = f'INSERT INTO [{self.tableL}] (shape) VALUES ({s})'
                        i = f'INSERT INTO [{self.tableL}] (text, shape) VALUES (\'{id}\', {s})'

                    self.insert(i)
                elif loc == 6 :  # Геобаза
                    continue
                    (x, y, lf, text, alpha, l1_2, l2) = read_xyz6(f, off, loc)
#                    print((x, y, lf, text, alpha, l1_2, l2))
                    s = coord.xy_to_shape_2(x, -y, alpha)

                    if not self.is_text:
                        self.exec('DROP TABLE [{}_text]'.format(self.tableL))
                        self.exec(f'''CREATE TABLE [{self.tableL}_text]
                            (
                                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                text text, 
                                shape geometry 
                            )
                             ''')

                        self.is_text = True

                    i = 'INSERT INTO [{}_text] (shape, text) VALUES ({}, \'{}\')'.format(self.tableL, s, text)

#                    print(i)
                    self.insert(i)
                elif not loc  in [2,0] :  # Геобаза
                    continue
                    print('geo :: loc =', loc)
        print('Закончил geo')
#-------------------------------------------------------------------------------------------------------------------

    def peremychka(self):

        print('====================================')
        print('Перемычки')

#        for k, v in self.dict_db_id_new.items():
#            print(k, v)
#        print('-----------------------')

        for v in self.dict_peremych.values():
                (externalCodeID, n0, regim) = v
#                print(v)

#            if Hpod != 0 or Hobr != 0:
                id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)
            
#                print(n0, id_n0)

                n1P = self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40000, id_n0)
                n1O = self.insertInnerNode(id_n0, 3, externalCodeID, 40000, 41000, id_n0)

                otkr = regim != 1

                self.insertInnerLine(n1P, n1O, 3, otkr)

#        print('====================================')

#-------------------------------------------------------------------------------------------------------------------

    def dross(self):

        print('====================================')
        print('Дроссели')

#        for k, v in self.dict_db_id_new.items():
#            print(k, v)
#        print('-----------------------')

        for v in self.dict_dross.values():
            externalCodeID, n0, n1, n2, regim, H_geo, H, Kreg = v

            id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)
            id_n1 = get_by_coord(self.dict_db_id_new, n1, -1)
            id_n2 = get_by_coord(self.dict_db_id_new, n2, -1)

            n1P =  self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40000, id_n1)
            n2P =  self.insertInnerNode(id_n0, 2, externalCodeID, 41000, 40000, id_n2)
            n1O =  self.insertInnerNode(id_n0, 3, externalCodeID, 40000, 41000, id_n1)
            n2O =  self.insertInnerNode(id_n0, 3, externalCodeID, 41000, 41000, id_n2)

            if regim == 3:
                self.insertInnerRD(n1P, n2P, 2, H-H_geo, Kreg)
                self.insertInnerLine(n1O, n2O, 3)

            elif regim == 4:
                self.insertInnerLine(n1P, n2P, 2)
                self.insertInnerRD(n2O, n1O, 3, H-H_geo, Kreg)

            elif regim == 5:
                self.insertInnerRR(n1P, n2P, 2, H, Kreg)
                self.insertInnerLine(n1O, n2O, 3)

            elif regim == 6:
                self.insertInnerLine(n1P, n2P, 2)
#                self.insertInnerRR(n2O, n1O, 3, H, Kreg)
                self.insertInnerRR(n1O, n2O, 3, H, Kreg)

            elif regim == 1:  # шайба переделать
                self.insertInnerLine(n1P, n2P, 2)
                self.insertInnerLine(n1O, n2O, 3)
            
            else:
                print(f'Режим {regim} не сделан')



#        print('====================================')

#-------------------------------------------------------------------------------------------------------------------

    def zd2(self):

        print('====================================')
        print('Задвижки')

#        for k, v in self.dict_db_id_new.items():
#            print(k, v)
#        print('-----------------------')

        for v in self.dict_zd2.values():
            (externalCodeID, n0, n1, n2, regim, Dpod,Dobr,Per_pod,Per_obr) = v

            id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)
            id_n1 = get_by_coord(self.dict_db_id_new, n1, -1)
            id_n2 = get_by_coord(self.dict_db_id_new, n2, -1)

            n1P =  self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40000, id_n1)
            n2P =  self.insertInnerNode(id_n0, 2, externalCodeID, 41000, 40000, id_n2)
            n1O =  self.insertInnerNode(id_n0, 3, externalCodeID, 40000, 41000, id_n1)
            n2O =  self.insertInnerNode(id_n0, 3, externalCodeID, 41000, 41000, id_n2)

            is_open = regim != 1

            if Dpod == 0: Dpod = 0
            if Dobr == 0: Dobr = 0

            self.insertInnerZD(n1P, n2P, 2, Dpod*1000, is_open)
            self.insertInnerZD(n1O, n2O, 3, Dobr*1000, is_open)


#        print('====================================')



#-------------------------------------------------------------------------------------------------------------------

    def pumps(self):

#        print('------ pumps ----')
        print('====================================')
        print('Насосы')
        for (externalCodeID, n0, n1, n2, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr) in self.dict_pumps.values():
#            print(coord.xy_to_s(n0), coord.xy_to_s(n1), coord.xy_to_s(n2), Hpod, Hobr)
            print(externalCodeID, n0, n1, n2, Hpod, Hobr, Npod, Nobr, Mark_pod, Mark_obr, Type_pod, Type_obr, Pr_pod, Pr_obr)
            print(Mark_pod, '-', Mark_obr)
            print(Type_pod, Type_obr)


            if Type_pod == 4:
                Hpod = 100

            if Type_obr == 4:
                Hobr = 100

            if Hpod != 0 or Hobr != 0 or Npod != 0 or Nobr != 0:
                id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)
                id_n1 = get_by_coord(self.dict_db_id_new, n1, -1)
                id_n2 = get_by_coord(self.dict_db_id_new, n2, -1)
            
                n1P =  self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40000, id_n1)
                n2P =  self.insertInnerNode(id_n0, 2, externalCodeID, 41000, 40000, id_n2)
                n1O =  self.insertInnerNode(id_n0, 3, externalCodeID, 40000, 41000, id_n1)
                n2O =  self.insertInnerNode(id_n0, 3, externalCodeID, 41000, 41000, id_n2)

                """  
                Подача
            <record key="0" value="По умолчанию" />
            <record key="1" value="Характеристика" />
            <record key="2" value="Напор на насосе" />
            <record key="3" value="Регулятор напора после насоса" />
            <record key="4" value="Регулятор давления после насоса" />
            <record key="5" value="Регулятор располагаемого напора" />
            <record key="6" value="Регулятор давления до насоса" />
            <record key="7" value="Регулятор напора до насоса" />


            Обратка

            <record key="0" value="По умолчанию" />
            <record key="1" value="Характеристика" />
            <record key="2" value="Напор на насосе" />
            <record key="3" value="Регулятор напора до насоса" />
            <record key="4" value="Регулятор давления до насоса" />
            <record key="5" value="Регулятор располагаемого напора" />


                """

                if Type_pod == 4:
                    n3P = self.insertInnerNode(id_n0, 2, externalCodeID, 40500, 40000, -1)
#                    print('n3P')
#                    n3P, n2P = n2P, n3P

                if Type_obr == 4:
                    n3O = self.insertInnerNode(id_n0, 3, externalCodeID, 40500, 41000, -1)
#                    print('n3O')
#                    n3O, n2O = n2O, n3O
#                    n2O, n1O = n1O, n2O


                if Type_pod != 4:
                    if Hpod != 0 or Npod != 0:
                        self.insertInnerPump(n1P, n2P, 2, Hpod, Npod, Mark_pod)
                    else:
                        self.insertInnerLine(n1P, n2P, 2)

                if Type_obr != 4:
                    if Hobr != 0 or Nobr != 0:
                        self.insertInnerPump(n2O, n1O, 3, -Hobr, Nobr, Mark_obr)
                    else:
                        self.insertInnerLine(n2O, n1O, 3)

                if Type_pod == 4:
                    self.insertInnerPump(n1P, n3P, 2, Pr_pod + 10, Nobr, Mark_obr)
                    self.insertInnerRD(n3P, n2P, 2, Pr_pod, Kreg=0)

                if Type_obr == 4:
                    self.insertInnerPump(n3O, n1O, 3, Hobr, Nobr, Mark_obr)
                    self.insertInnerRD(n2O, n3O, 3, Pr_obr, Kreg=0)

#        print(self.graph)


        print('number_connected_components:', nx.number_connected_components(self.graph))
#        print([len(c) for c in sorted(nx.connected_components(self.graph), key=len, reverse=True)])

        for (externalCodeID, n0, n1, n2, Hpod, Hobr, name_ctp, heatSourceID, T1, T2, T3, r) in self.dict_ctp.values():
               (x, y) = n0
               pp = ''
               for c in nx.node_connected_component(self.graph, (x+1, y)):
                    id = get_by_coord(self.dict_db_id_new, c, -1)
                    if pp != '': pp += ','
                    pp += '{}'.format(id)

               externalCodeID = ur.getRS_ctp(self, name_ctp, heatSourceID)


               q = f'UPDATE nodes SET externalCodeID={externalCodeID}, fileID={self.fileID_ctp} WHERE id IN ({pp})'
               self.exec(q)

               specExpendID = ur.getUR_ctp(self, name_ctp, T1, T2, T3)
               calcTemperatureID = ur.getTR_ctp(self, name_ctp, T1, T2, T3, r)

               q = 'UPDATE realConsumers SET specExpendID={}, calcTemperatureID={} WHERE nodeID IN ({})'.format(specExpendID, calcTemperatureID, pp)
               self.exec(q)

               print('heatSourceID', heatSourceID)

               tg.calc(self.conn, heatSourceID)


        print('===================')

        for qq  in self.dict_ist.values():
            Nist, id_ist, x, y, node_name, T1, T2, T3, Mode, H_ras, H_obr, n0 = qq

            """
            if Mode in (2, 3):

#                print(n0)
#                exit(0)

                id_n0 = get_by_coord(self.dict_db_id_new, n0, -1)

                n1P = self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40000, id_n0)
                n1O = self.insertInnerNode(id_n0, 3, externalCodeID, 40000, 41000, id_n0)

                if Mode == 2: # Подпитки нет, фиксировано давление в обратке
                    self.insertInnerPump(n1O, n1P, 5, H_ras, 0, '')

                if Mode == 1: # Подпитки нет, фиксирован располагаемый напор
                    n3P = self.insertInnerNode(id_n0, 2, externalCodeID, 40000, 40500, id_n0)

                    self.insertInnerPump(n1O, n3P, 5, 200, 0, '')
                    Kreg = 0
                    self.insertInnerRD(n3P, n1P, 2, H_obr + H_ras, Kreg)
            """


            specExpendID = self.dict_ur.get(Nist, -1)
            calcTemperatureID = self.dict_tr.get(Nist, -1)
            externalCodeID = self.dict_rs.get(Nist, None)

            if specExpendID != -1:
                self.exec('UPDATE [specExpends] SET specExpendID=\'{}\' WHERE id={}'.format(node_name, specExpendID))
            if calcTemperatureID != -1:
                '''
  T1_isl_2stup float DEFAULT 70, -- COMMENT 'Расчетная температура сетевой воды на входе ТП в т.изл.темп. граф.',
  Tr_co_1_zco float DEFAULT 150, -- COMMENT 'Расчетная температура воды в подающем трубопроводе, зависимая СО',
  Tr_co_2_zco float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе, зависимая СО',
  Tr_co_3_zco float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения, зависимая СО',
  Tr_to_1_nco float DEFAULT 150, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО',
  Tr_to_2_nco float DEFAULT 80, -- COMMENT 'Расчетная температура сетевой воды на выходе подогревателя, независимой СО',
  Tr_co_1m_nco float DEFAULT 140, -- COMMENT 'Расчетная температура воды в подающем трубопроводе местной СО, независимая СО',
  Tr_co_2m_nco float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе местной СО, независимая СО',
  Tr_co_3m_nco float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения местной СО, независимая СО',
  Tr_1_cv float DEFAULT 150, -- COMMENT 'Расч.темп. сет.воды на входе вентиляции или воздушной системы отопления',
  Tr_2_cv float DEFAULT 70, -- COMMENT 'Расч.темп. сет.воды на выходе вентиляции или воздушной системы отопления',
  Tr_co_1_zco_pr float DEFAULT 150, -- COMMENT 'Расчетная температура воды в подающем трубопроводе, зависимая СО, парал.ГВС',
  Tr_co_2_zco_pr float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе, зависимая СО, парал.ГВС',
  Tr_co_3_zco_pr float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения, зависимая СО, парал.ГВС',
  Tr_to_1_pr float DEFAULT 150, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, парал.ГВС',
  Tr_to_2_pr float DEFAULT 80, -- COMMENT 'Расчетная температура сетевой воды на выходе подогревателя, независимой СО, парал.ГВС',
  Tr_co_1m_nco_pr float DEFAULT 140, -- COMMENT 'Расчетная температура воды в подающем трубопроводе местной СО, независимая СО, парал.ГВС',
  Tr_co_2m_nco_pr float DEFAULT 80, -- COMMENT 'Расчетная температура воды в обратном трубопроводе местной СО, независимая СО, парал.ГВС',
  Tr_co_3m_nco_pr float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения местной СО, независимая СО, парал.ГВС',
  T2_isl_2stup_pr float DEFAULT 30, -- COMMENT 'Расчетная температура сетевой воды на выходе 2 ступени подогревателя т.изл.темп. граф., парал.ГВС',
  Tr_co_1_zco_sm float DEFAULT 150, -- COMMENT 'Расчетная температура воды в подающем трубопроводе, зависимая СО,смеш.ГВС',
  Tr_co_2_zco_sm float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе, зависимая СО, смеш.ГВС',
  Tr_co_3_zco_sm float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения, зависимая СО,смеш.ГВС',
  Tr_to_1_sm float DEFAULT 150, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, смеш.ГВС',
  Tr_to_2_sm float DEFAULT 70, -- COMMENT 'Расчетная температура сетевой воды на выходе подогревателя, независимой СО, смеш.ГВС',
  Tr_co_1m_nco_sm float DEFAULT 140, -- COMMENT 'Расчетная температура воды в подающем трубопроводе местной СО, независимая СО, смеш.ГВС',
  Tr_co_2m_nco_sm float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе местной СО, независимая СО, смеш.ГВС',
  Tr_co_3m_nco_sm float DEFAULT 70, -- COMMENT 'Расчетная температура воды после узла смешения местной СО, независимая СО, смеш.ГВС',
  T2_isl_2stup_sm float DEFAULT 41.7, -- COMMENT 'Расчетная температура сетевой воды на выходе системы отопления в т.изл.темп. граф.,смеш.ГВС',
  delta_tg_sm float DEFAULT 5, -- COMMENT 'Недогрев водопроводной воды в первой ступени системы горячего водоснабжения до T2_isl_2stup_sm',
  Tr_co_1_zco_ps float DEFAULT 150, -- COMMENT 'Расчетная температура воды в подающем трубопроводе, зависимая СО,посл.ГВС',
  Tr_co_2_zco_ps float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе, зависимая СО, посл.ГВС',
  Tr_co_3_zco_ps float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения, зависимая СО,посл.ГВС',
  Tr_to_1_ps float DEFAULT 150, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, посл.ГВС',
  Tr_to_2_ps float DEFAULT 80, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, посл.ГВС',
  Tr_co_1m_nco_ps float DEFAULT 140, -- COMMENT 'Расчетная температура воды в подающем трубопроводе местной СО, независимая СО, посл.ГВС',
  Tr_co_2m_nco_ps float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе местной СО, независимая СО, посл.ГВС',
  Tr_co_3m_nco_ps float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения местной СО, независимая СО, посл.ГВС',
  T2_isl_2stup_ps float DEFAULT 41.7, -- COMMENT 'Расчетная температура сетевой воды на выходе системы отопления в т.изл.темп. граф.,посл.ГВС',
  delta_tg_ps float DEFAULT 5, -- COMMENT 'Недогрев водопроводной воды в первой ступени системы горячего водоснабжения до T2_isl_2stup_ps',
  Tr_co_1_zco_pw float DEFAULT 150, -- COMMENT 'Расчетная температура воды в подающем трубопроводе, зависимая СО,предвкл.ГВС',
  Tr_co_2_zco_pw float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе, зависимая СО, предвкл.ГВС',
  Tr_co_3_zco_pw float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения, зависимая СО,предвкл.ГВС',
  Tr_to_1_pw float DEFAULT 150, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, предвкл.ГВС',
  Tr_to_2_pw float DEFAULT 80, -- COMMENT 'Расчетная температура сетевой воды на входе подогревателя, независимой СО, предвкл.ГВС',
  Tr_co_1m_nco_pw float DEFAULT 140, -- COMMENT 'Расчетная температура воды в подающем трубопроводе местной СО, независимая СО, предвкл.ГВС',
  Tr_co_2m_nco_pw float DEFAULT 70, -- COMMENT 'Расчетная температура воды в обратном трубопроводе местной СО, независимая СО,предвкл.ГВС',
  Tr_co_3m_nco_pw float DEFAULT 95, -- COMMENT 'Расчетная температура воды после узла смешения местной СО, независимая СО, предвкл.ГВС',
  T2_isl_2stup_pw float DEFAULT 41.7, -- COMMENT 'Расчетная температура сетевой воды на выходе системы отопления в т.изл.темп. граф.,предвкл.ГВС',
'''


                self.exec('''UPDATE [calcTemperatures] SET calcTemperatureID=\'{}\' 
,
T1_isl_2stup=70,
--Tr_co_1_zco=150,
--Tr_co_2_zco=70,
--Tr_co_3_zco=95,
--Tr_to_1_nco=150,
--Tr_to_2_nco=80,
--Tr_co_1m_nco=140,
--Tr_co_2m_nco=70,
--Tr_co_3m_nco=95,
Tr_1_cv=150,
Tr_2_cv=70,
Tr_co_1_zco_pr=150,
Tr_co_2_zco_pr=70,
Tr_co_3_zco_pr=95,
Tr_to_1_pr=150,
Tr_to_2_pr=72,
Tr_co_1m_nco_pr=140,
Tr_co_2m_nco_pr=80,
Tr_co_3m_nco_pr=95,
T2_isl_2stup_pr=30,

Tr_co_1_zco_sm=150,
Tr_co_2_zco_sm=70,
Tr_co_3_zco_sm=95,
Tr_to_1_sm=150,
Tr_to_2_sm=72,
Tr_co_1m_nco_sm=95,
Tr_co_2m_nco_sm=70,
Tr_co_3m_nco_sm=95,
T2_isl_2stup_sm=41.7,
delta_tg_sm=5,
Tr_co_1_zco_ps=150,
Tr_co_2_zco_ps=70,
Tr_co_3_zco_ps=95,
Tr_to_1_ps=150,
Tr_to_2_ps=80,
Tr_co_1m_nco_ps=140,
Tr_co_2m_nco_ps=70,
Tr_co_3m_nco_ps=95,
T2_isl_2stup_ps=41.7,
delta_tg_ps=5,
Tr_co_1_zco_pw=150,
Tr_co_2_zco_pw=70,
Tr_co_3_zco_pw=95,
Tr_to_1_pw=150,
Tr_to_2_pw=80,
Tr_co_1m_nco_pw=140,
Tr_co_2m_nco_pw=70,
Tr_co_3m_nco_pw=95,
T2_isl_2stup_pw=41.7
WHERE id={}'''.format(node_name, calcTemperatureID))


#                self.exec('UPDATE [calcTemperatures] SET calcTemperatureID=\'{}\' WHERE id={}'.format(node_name, calcTemperatureID))

            if externalCodeID != -1:
#                node_name = node_name[:5]
                q = 'UPDATE [externalCodes] SET name=\'{}\' WHERE id={}'.format(node_name, externalCodeID )
                self.exec(q)
#                print('2!', q)

                kod_m = 'РС{}'.format(Nist)

                q = 'UPDATE [setPressNodes] SET kod_m=\'{}\' WHERE kod_m=\'{}\''.format(node_name, kod_m )

                self.exec(q)



#                if T1-10 > T2:
#                    self.exec('UPDATE [specExpends] SET namecalcHLdep={}, calcHLindep={}  WHERE id={} )'.format(specExpendID, 1000/(T1-T2), 1000/(T1-T2-10)))


#        if self.id_ist:
#            q = 'UPDATE [externalCodes] SET heatSourceID={} WHERE heatSourceID IS NULL'.format(self.id_ist)
#            print('4!', q)
#            self.exec(q)

#-------------------------------------------------------------------------------------------------------------------

    def insertLine(self, id1, id2, coor, c1, c2, regim):

        if regim != -1:
            print(f'regim={regim}')
            return -1
        '''
        Добавить линейный объект
        '''
        s_coord = ''
        if coor:
            s_coord = coord.coord_to_s(coor)

        q = 'INSERT INTO [linesobj] (nodeID1,nodeID2, coords) VALUES ({},{},\'{}\')'.format(id1, id2, s_coord)

        self.graph.add_edge(c1, c2)
#        print(coord.xy_to_s(c1), '-', coord.xy_to_s(c2))
        
        return self.insert(q)

#---------------------------------------------------------------------------

    def insertNode(self, externalCodeID, node_name, xy, H_geo, fileID, view=True):
        '''
        Добавить узел
        '''
        (x, y) = xy

        self.externalCodeID = externalCodeID

        if node_name == '':
            view = False

        node_name = node_name[:50]
        node_name = node_name.replace('\'', '\'\'')

        q = 'INSERT INTO [nodes] (externalCodeID, externalNodeName, x, y, geoMarkTopTube, geoMarkNodeArea, fileID, displaySign) VALUES ({}, \'{}\',{},{},{},{},{},{})'\
             .format(externalCodeID, node_name, x*100, y*100, H_geo, H_geo, fileID, 0 if view else 1)
#        print(q)

        self.graph.add_node((x,y))
             
        id = self.insert(q)

        self.dict_db_id_new[coord_round(xy)] = id
#        self.dict_db_id_new[(round(x, 4), round(x, 4))] = id

#        print(coord.xy_to_s((x,y)), id)

        return id

#---------------------------------------------------------------------------

    def insertInnerNode(self, id_n0, externalSignID, externalCodeID, x, y, id_n1):
        n1P = self.insert('INSERT INTO [nodes] (externalSignID, internalNodeID, externalCodeID, x, y, geoMarkTopTube, geoMarkNodeArea, fileID) VALUES ({}, {}, {}, {},{},{},{},{})'\
                          .format(externalSignID, id_n0, externalCodeID, x, y, 0, 0, self.fileID))

        if id_n1 and id_n1 > 0:
            self.insert('INSERT INTO [connectNodes] (nodeID, connectID) VALUES ({},{})'.format(n1P, id_n1))
        
        return n1P

#---------------------------------------------------------------------------

    def insertInnerLine(self, n1, n2, externalSignLineID, is_open = True):
        id1 = self.insert('INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({},{},{})'.format(n1, n2, externalSignLineID))

        L = 1
        Dpod = 1000
        Dobr = 1000
        Proklad = 4

        code_open = 1
        if not is_open:
            code_open = 2;

        self.insert(f'''INSERT INTO [heatPipeSections] 
            (lineID, pipeSectLength, diameterCondit, diameterInternal, diameterExternal, tubingTypeID,
            pipeSectStateIDflow, pipeSectStateIDret
            ) VALUES ({id1}, {L}, {Dpod}, {Dpod}, {Dpod}, {Proklad}, {code_open}, {code_open})''')

#---------------------------------------------------------------------------

    def insertInnerPump(self, n1, n2, externalSignLineID, dH, N, Mark, is_open = True):
        if (dH < 0) : 
            (n1, n2) = (n2, n1)
            dH = -dH
            
        id1 = self.insert(f'INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({n1},{n2},{externalSignLineID})')

        code_open = 1
        if not is_open:
            code_open = 2;

        idS = 'NULL'
        r0 = 'NULL'
        r1 = 'NULL'
        r2 = 'NULL'

        if Mark != '' and not Mark is None:
            v = zulu.std_nas.get(Mark, None)

            if v is None:
                Mark1 = Mark
                Mark = Mark.replace(' ', '')
                v = zulu.std_nas.get(Mark, None)


            if not v is None:
                idS, H, Q = v
                r0, r1, r2, pog = nasos.Appr( H, Q, N)
            else:
                print(f'Не заданы параметры для насоса {Mark}')

        self.insert(f'''INSERT INTO [pumps] 
            (lineID, thrust, parallAgregCount, number, r0, r1, r2, r0_z, r1_z, r2_z, standardPumpID) 
            VALUES ({id1}, {dH}, {N}, \'{Mark}\', {r0}, {r1}, {r2}, {r0}, {r1}, {r2}, {idS})''')

#---------------------------------------------------------------------------

    def insertInnerLineOrPump(self, n1, n2, externalSignLineID, dH, is_open = True):
        if (dH < 0) : (n1, n2) = (n2, n1)
            
        id1 = self.insert('INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({},{},{})'.format(n1, n2, externalSignLineID))

        L = 1
        Dpod = 1000
        Dobr = 1000
        Proklad = 4

        code_open = 1
        if not is_open:
            code_open = 2;

        if dH != 0:
            self.insert(f'INSERT INTO [pumps] (lineID, thrust) VALUES ({id1}, {dH})')
        else:
            self.insert(f'''INSERT INTO [heatPipeSections] 
                    (lineID, pipeSectLength, diameterCondit, diameterInternal, diameterExternal, tubingTypeID,
                    pipeSectStateIDflow, pipeSectStateIDret
                    ) VALUES ({id1}, {L}, {Dpod}, {Dpod}, {Dpod}, {Proklad}, {code_open}, {code_open})''')

#---------------------------------------------------------------------------

    def insertInnerRR(self, n1, n2, externalSignLineID, ras, Kreg):
        id1 = self.insert(f'INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({n1},{n2},{externalSignLineID})')
        self.insert(f'INSERT INTO [consumptRegulators] (lineID, regConsMean, regValveCap) VALUES ({id1}, {ras}, {Kreg})')

    def insertInnerZD(self, n1, n2, externalSignLineID, diam, is_open):
        id1 = self.insert(f'INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({n1},{n2},{externalSignLineID})')
        self.insert(f'INSERT INTO [dampers] (lineID, damperArmatureStateID, diameterCondit) VALUES ({id1}, {1 if is_open else 2}, {diam})')

    def insertInnerRD(self, n1, n2, externalSignLineID, H, Kreg):
        id1 = self.insert(f'INSERT INTO [linesobj] (nodeID1, nodeID2, externalSignLineID) VALUES ({n1},{n2},{externalSignLineID})')
        is_open = True

        if externalSignLineID == 2: 
            pipelineSignID = 1
            nodeID = n2
        elif externalSignLineID == 3: 
            pipelineSignID = 2
            nodeID = n1

        h = H
        deltaH = 0.1
        kv = Kreg

        self.insert(f'''INSERT INTO [pressRegulators] (lineID, regulatorStateID, pipelineSignID, h, nodeID, deltaH, regValveRelCap) 
                        VALUES ({id1}, {1 if is_open else 2}, {pipelineSignID}, {h}, {nodeID}, {deltaH}, {kv})''')

#---------------------------------------------------------------------------

    def read_zulu_b00(self, loc0):
        self.table_name = ''

#        print(self.filename+".b00")


        with open(self.filename+".b00","rb") as f:
            f.seek(0x0E)
            fn = read_string_zero(f, 40, 'cp866')
#            print('!!!', fn, loc0)
            self.table_name = fn

            if (loc0 == 2):

                insert = 'INSERT INTO [fragments] (name, t_or, t_vr) VALUES (\'{}\', {}, {})'.format(self.table_name, self.Tnv_r, self.Tnv_r)
                self.fileID = self.insert(insert)

                insert = 'INSERT INTO [varCoefficients] (kodkv, fileID) VALUES (\'КВ1\', {})'.format(self.fileID)
                self.kv1 = self.insert(insert)
#                insert = 'INSERT INTO [varCoefficients] (kodkv, fileID, kvpot, gvz) VALUES (\'КВ пар\', {}, 0, {})'.format(self.fileID, 0.5)
                insert = 'INSERT INTO [varCoefficients] (kodkv, fileID, kvpot, gvz) VALUES (\'КВ пар\', {}, 0, {})'.format(self.fileID, 1)
                self.kv_pr = self.insert(insert)
                insert = 'INSERT INTO [varCoefficients] (kodkv, fileID, kvpot, gvz) VALUES (\'КВ смеш\', {}, 0, {})'.format(self.fileID, 0.0001)
                self.kv_sm = self.insert(insert)

                insert = 'INSERT INTO [fragments] (name, t_or, t_vr) VALUES (\'{}\', {}, {})'.format(self.table_name + ' ЦТП', self.Tnv_r, self.Tnv_r)
                self.fileID_ctp = self.insert(insert)

                insert = f'INSERT INTO [varCoefficients] (kodkv, fileID) VALUES (\'КВ1\', {self.fileID_ctp})'
                self.kv1_ctp = self.insert(insert)
                insert = f'INSERT INTO [varCoefficients] (kodkv, fileID, kvpot, gvz) VALUES (\'КВ пар\', {self.fileID_ctp}, 0, {1})'
                self.kv_pr_ctp = self.insert(insert)
                insert = f'INSERT INTO [varCoefficients] (kodkv, fileID, kvpot, gvz) VALUES (\'КВ смеш\', {self.fileID_ctp}, 0, {0.0001})'
                self.kv_sm_ctp = self.insert(insert)


            self.dict_obj = dict()

            f.seek(0x55E)

            while f:
                try:
                    n1 = read_short(f)
                    if not n1: break

                    n2 = read_short(f)

                    size = read_long(f)
                    off = read_long(f)

#                        print('n1=', n1, n2, 'off=', off, 'size=', size)

                    if n1 > 0:
                        self.read_zulu_b01_init(off, loc0)

                except EOFError: 
                    break

            self.read_zulu_b01()

            if loc0 >= 5 or loc0 == -1:
                print('----Geo--')
                self.read_zulu_b01_geo()


            return fn

#-----------------------------------------------------------------
    def read_db_db(self, id, db_name, db_path):
        dir_name = os.path.dirname(self.filename)
        dir_name = db_path
        pre, ext = os.path.splitext(db_name)


#        print(pre, ext, dir_name, self.filename, db_name)
#        exit(0)

#        print('------------------------------------------')
#        print(dir_name + '/' + pre + '.db')
#        exit(0)
#        print(db_name)

#        print(dir_name + '/' + pre + '.db')

#        print(dir_name + '/' + pre + '.db')
#        exit(0)

        tn = dir_name + '/' + pre + '.db'

#        table = Table(tn, px_encoding='cp1251', encoding='cp1251')

        try:
            tab = Table
            tab.PX_ENCODING = 'cp1251'
            table = tab(tn, px_encoding='cp1251', encoding='cp1251')

#            table = Table(tn, px_encoding='cp1251', encoding='cp1251')
            self.dict_table[id] = table

            num = 0

            for r in table:
    #            if db_name == 'nasos.zb':
    #            if db_name == 'istok.zb':
    #                print('<<<', r)
                v = r_get(r, 'Sys', None)
                self.dict_db_id[(id, v)] = num
                num += 1
        except Exception as e:
            print('!!!', e, tn)
            exit(0)

#-----------------------------------------------------------------
    def read_db_sqlite(self, id, db_name):
        dir_name = os.path.dirname(self.filename)
        pre, ext = os.path.splitext(db_name)

        print('------------------------------------------')
#        print(dir_name + '/' + pre + '.db')
        print(db_name)
#        exit(0)

#        print(dir_name + '/' + pre + '.db')

        try:

            table = Table(dir_name + '/' + pre + '.db', px_encoding='cp1251', encoding='cp1251')
            self.dict_table[id] = table

            num = 0

            for r in table:
    #            if db_name == 'nasos.zb':
    #            if db_name == 'istok.zb':
    #                print('<<<', r)
                v = r_get(r, 'Sys', None)
                self.dict_db_id[(id, v)] = num
                num += 1
        except:
            print('!!!')


#-----------------------------------------------------------------

    def read_db(self, id, db_name, name):

        path, ext = os.path.splitext(db_name)
        path = os.path.dirname(self.filename)

#        exit(0)

        if args.path_db != '':
            db_name, ext = os.path.splitext(db_name)
            fn = f'{path}/{db_name}.db'
#            print(args.path_db, fn, db_name)
#            exit(0)
            self.read_db_db(id, db_name, args.path_db)
            return



#        print('!!', db_name, self.filename)
#        exit(0)

#        db_name = db_name.replace(r'D:\ZuluData\Москва\Слой для анализа нагрузок\Фрагмент', r'D:\zulu\fr2\fr')

#        if ext == '.zb1':
#            db_name, ext = os.path.splitext(db_name)
#            fn = f'{path}/{db_name}.db'
#            print(fn)
#            exit(0)
#            self.read_db_db(id, db_name)
#            self.read_db_sqlite(id, db_name)
#            return

#        path = os.path.dirname(self.filename)
        
#        print(self.filename)
#        exit(0)
#        print(path, ext)

#        if not os.path.exists(self.filename + ext):
#            return

#        print(self.filename + ext)


#        tn, typ, connstr = d_xml.read_d_xml(self.filename + ext)

#        print(f'|{self.filename}|')
#        exit(0)

        if os.path.isfile(self.filename + '.sqlite'):
            conn = connect.connect_sqlite(self.filename + '.sqlite')
#        elif os.path.isfile(self.filename + '.mdf'):
#            conn = connect.connect_mdf(self.filename + '.mdf')
        elif os.path.isfile(self.filename + '.mdb'):
            conn = connect.connect_mdb(self.filename + '.mdb')
        else:
            print(f'Неизвестный файл {self.filename}')
            exit(0)

        cursor = conn.cursor()

        result = cursor.tables()
        result = set(l[2] for l in result)

#        for t in result:   
#            print('!', t)


#        conn = connect.connect_sqlite('D:/map/piter/piter.sqlite')
#        print(id, db_name)

        map_tab = {

        'Источник': 'istok',  #22-23.d00
        'Узел': 'kamera',  #22-23.d01
        'Потpебитель':'uzvvod',   #  22-23.d02
        'Насосная станция': 'NASOS',  #22-23.d03
        'Задвижка': 'ZADVIGKA',  #22-23.d04
        'Участки': 'uch',  #22-23.d05
        'Дросселирующий узел': 'DROSSEL',  #22-23.d06
        'ЦТП': 'ctp',  #22-23.d07
        'Граница балансовой принадлежности': 'GRANIZA',  #22-23.d08
        'Узел учета': 'PRIBOR',  #22-23.d09
        'Перемычка': 'Peremich',  #22-23.d10
        'Обобщенный потребитель': 'OP',  #22-23.d11
        #'Вспомогательный участок': '',  #
        }


        tn0 = map_tab.get(name, None)

        if tn0 is None:
            print('-------------')
            print(f'Нет {db_name} {name}')
            return

#        print('==', name, tn0)

        tn = tn0

        for tn1 in result:
#            print(tn1, tn0, tn0.lower() in tn1.lower())
            if tn0.lower() in tn1.lower():
                tn = tn1
                break

#        print('tn =', tn)

        #        tn = 'fr_'+tn

        q = f'select * from [{tn}]'

        try:
            cursor.execute(q)

            num = 0

            table = {}

            while True:
                row = cursor.fetchone()
                if not row: break

                map_row = dict()

                for col, v in zip(cursor.description, row):
                    if v:
                        map_row[col[0].lower()] = v

#                print(map_row)

                table[num] = map_row
    #            print(row)

#                v = row[0]
                id2 =  row[0]

                self.dict_db_id[(id, id2)] = num

#                print(id, v, num)
                
                num += 1

            self.dict_table[id] = table


#        except:
        except pyodbc.Error as ex:
            print(ex, file=sys.stderr)
            exit(0)
            
#-----------------------------------------------------------------

    def read_zulu_b02(self):
#      print('read_zulu_b02', self.filename+".b02")

      with open(self.filename+".b02","rb") as f:

        f.seek(4)
        nn = read_long(f)
#        print('nn=', nn)

        off = 0x2016  #  Это для Днепропетровска

        yes = False

        for i in range(nn):
            f.seek(off)

            n1 = read_long(f)

            if n1 is None: break

            n2 = read_short(f)

#            print('(', n1, n2, ')', end=' ')

            name = read_string_zero(f, 40)
#            print('name=', name)

            db_name = read_string_zero(f, 80)

            f.seek(off + 0x137-0x7)

            n2 = read_short(f)
            n3 = read_short(f)

            plus = ' '

            if db_name != '':
                self.read_db(n1, db_name, name)
                plus = '+'

#            print(yes, i, n1, n2, n3, name, db_name)
#            print(f'{plus} {i:2d} {n1:3d} {n2:2d} {n3:2d} {name:20} {db_name}')
            print(f'{plus} {name:20} {db_name}')


#            print('b02>> ', n1, name)
            self.dict_types[n1] = name

            yes = True
            off += 0x137
            
#        print('<<<yes', yes)

#        exit(0)

#            if n2 == 0: break
        return yes

#---------------------------------------------------------------------------

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')  # Устанавливаем кодировку UTF-8

    t1 = time.time()


    args = config.init()

    print('================================================================')
    print(args.path)

    zulu = Zulu()

    zulu.Tnv_r = args.Tn
#    self.Tvn = 20

    zulu.set_filename(args.path)

#    zulu.connect(args.server, args.user, args.password, args.database)

#    sqlite_file = 'D:/Qt/gid8/python/zulu2/1/baza.sqlite'
    path_out = 'D:/Qt/gid8/python/zulu2/2'
    path_out = args.path_out

#    sqlite_file = 'D:/Qt/gid8/python/zulu2/1/baza2.sqlite'

    tdir = tempfile.gettempdir()
    sqlite_file = os.path.join(tdir, 'baza.sqlite')

    zulu.connect(sqlite_file)

    sql_file = os.path.dirname(os.path.abspath(__file__)) + '/full_tgid.sql'


    sql_exec.sqlfile_exec(zulu.conn, sql_file)

#    if args.reset:
    del_fragments.del_baza(zulu.conn, args.name, args.central_meridian, args.false_east, args.false_north, args.Tn)

    zulu.std_nas = nasos.open_nasos_std()

#    zulu.exec('ALTER TABLE nodes DISABLE TRIGGER all')

    if zulu.read_zulu_b02() and not args.nogidr:
        print('<< Точечные')
        zulu.read_zulu_b00(2) # Точечные
        print('<< Линейные')
        zulu.read_zulu_b00(0) # Линейные
        print('<< Остальные')

        zulu.dross()
        zulu.pumps()
        zulu.peremychka()
        zulu.zd2()
        print('<< Закончили')
#    else:
#       zulu.read_zulu_b00(-1)

    zulu.read_zulu_b00(-1)

    # Ms SQL

    q = '''
update n
set n.externalNodeName = n2.externalNodeName
from nodes n
join connectNodes cn on n.id=cn.nodeID
join nodes n2 on n2.id=cn.connectID'''

    # Sqlite

    q = '''
UPDATE nodes
SET externalNodeName = (
    SELECT n2.externalNodeName
    FROM connectNodes cn
    JOIN nodes n2 ON n2.id = cn.connectID
    WHERE nodes.id = cn.nodeID
)
WHERE EXISTS (
    SELECT 1 FROM connectNodes cn WHERE nodes.id = cn.nodeID
);
    '''


    zulu.exec(q)

#    zulu.exec('ALTER TABLE nodes ENABLE TRIGGER all')


    export_tgid.run_export_tgid(sqlite_file, path_out)


    t2 = time.time()
    print(f'Время конвертации {t2-t1:0.2f} секунд', flush=True)


