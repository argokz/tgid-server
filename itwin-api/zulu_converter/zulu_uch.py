from tubes import read_tube

from r import r_get

def uch(self, r, coor, typ, regim):
    node_name1 = r_get(r, 'Begin_uch', None) if not r_get(r, 'Begin_uch', None) is None else ''
    node_name2 = r_get(r, 'End_uch', None) if not r_get(r, 'End_uch', None) is None else ''

    c1 = coor[0]
    c2 = coor[-1]

    ctp = self.dict_ctp.get(c1, None)
    if not ctp is None:
         (x, y) = c1
         c1 = (x+1, y)

    zd = self.dict_zd.get(c1, None)
    if not zd is None:
         (x, y) = c1
         c1 = (x+1, y)

    id1 = self.dict_nodes_coord.get(c1, -1)
    id2 = self.dict_nodes_coord.get(c2, -1)

    id_new_1 = self.dict_db_id_new.get(c1, -1)
    id_new_2 = self.dict_db_id_new.get(c2, -1)

    if id_new_1 == -1:
        (x, y) = c1

        id_new_1 = self.insertNode(self.externalCodeID, node_name1, (x, y), 0, self.fileID)
        self.dict_nodes_coord[c1] = id

    if id_new_2 == -1:
        (x, y) = c2
        id_new_2 = self.insertNode(self.externalCodeID, node_name2, (x, y), 0, self.fileID)
        self.dict_nodes_coord[c2] = id

    self.set_pump_and_ctp(coor)

    if id_new_1 < 0 or id_new_2 < 0:
         print('Error')

    if id_new_1 >= 0 and id_new_2 >= 0:
        if typ == 6: # Участок
            id_new = self.insertLine(id_new_1, id_new_2, coor, c1, c2, -1)
            insert = read_tube(r, regim, id_new)
            self.insert(insert)

            if zd:
#               print(zd)
               (externalCodeID, cc1, cc2, cc3, regim, Dpod,Dobr,Per_pod,Per_obr) = zd

               id_new_1_0 = self.dict_db_id_new.get((x, y), -1)
               id_lz = self.insertLine(id_new_1_0, id_new_1, None, coor[0], c1, regim)
               insert = 'INSERT INTO [dampers] (lineID, damperArmatureStateID, diameterCondit) VALUES ({},{},{})'.format(id_lz, regim+1, 1000)
#               insert = 'INSERT INTO [dampers] (lineID, damperArmatureStateID, diameterCondit,partDempOpen) VALUES ({},{},{},{})'.format(id_lz, regim+1, Dpod, Per_pod)

               self.insert(insert)
        
        else:
            print('Неизвестный тип линейного объекта')
#            assert(True, 'Неизвестный тип линейного объекта')
