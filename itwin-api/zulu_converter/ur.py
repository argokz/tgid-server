from r import r_get

# Удельные расходы и все такое

def getUR(self, Nist, T1, T2, T3):

    ur_name = f'УР-{Nist}'
    ur_name = f'РС{Nist}'

    specExpendID = self.dict_ur.get(Nist, None)

    if not specExpendID:
        if T1-10 > T2:
            q = f'''INSERT INTO [specExpends] (specExpendID, fileID, calcHLdep, calcHLindep, avgHLGVScloseMix) 
                    VALUES(\'{ur_name}\', {self.fileID}, {1000/(T1-T2)}, {1000/(T1-T2-10)}, {18.2})'''

        else:
            q = f'INSERT INTO [specExpends] (specExpendID, fileID) VALUES(\'{ur_name}\', {self.fileID})'


        specExpendID = self.insert(q)

        self.dict_ur[Nist] = specExpendID

    return specExpendID



def getUR1(self, Nist):
    ur_name = 'УР-1_1'
#    Nist = -1

    specExpendID = self.dict_ur.get(Nist, None)

    if not specExpendID:
        q = f'''INSERT INTO [specExpends] 
             (specexpendid, fileid, calchldep, calchlindep, calchlventil, calchlcond, calchlclosesys, calchlopensys, calcexpendhwopen, circhlosopen, avghlgvscloseparall, avghlgvsclosemix, avghlgvscloseconseq, avghlgvsclosepreon, avghlgvsclosesummer, avghlgvsopensummer)
            VALUES(\'{ur_name}\', {self.fileID}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1}, {1})'''

        specExpendID = self.insert(q)

        self.dict_ur[Nist] = specExpendID

    return specExpendID


'''

def getUR_ctp_0(self, name, r):

    ur_name = 'УР-для {}'.format(name)

    ur_o = 1000/(r_get(r, 'T1_r', None)-r_get(r, 'T1to_so', None))

    specExpendID = self.insert('INSERT INTO [specExpends] (specExpendID, fileID, calcHLdep, calcHLindep) VALUES(\'{}\', {}, {}, {})'\
            .format(ur_name, self.fileID, ur_o, ur_o))

    return specExpendID
'''


def getUR_ctp(self, name, T1, T2, T3):

    ur_name = f'УР-после {name}'

    if T1-10 > T2:
        q = 'INSERT INTO [specExpends] (specExpendID, fileID, calcHLdep, calcHLindep, avgHLGVScloseMix) VALUES(\'{}\', {}, {}, {}, {})'\
            .format(ur_name, self.fileID_ctp, 1000/(T1-T2), 1000/(T1-T2-10), 18.2)
    else:
        q = 'INSERT INTO [specExpends] (specExpendID, fileID) VALUES(\'{}\', {})'\
            .format(ur_name, self.fileID_ctp)

    specExpendID = self.insert(q)

    return specExpendID


def getTR(self, Nist, r):
    T1, T2, T3 = r_get(r, 'T1_r', 0), r_get(r, 'T2_r', 0), r_get(r, 'T3_r', 0)
#    print(f'!!! {T1} {T2} {T3}')

    tr_name = f'ТР-{Nist}'
    tr_name = f'РС{Nist}'

    calcTemperatureID = self.dict_tr.get(Nist, None)

    if not calcTemperatureID:

        q = f'''INSERT INTO [calcTemperatures]
             (calcTemperatureID, fileID,  Tn_r, Tn_r_v, Tr_co_1_zco, Tr_co_2_zco, Tr_co_3_zco, Tr_to_1_nco, Tr_to_2_nco) 
             VALUES(\'{tr_name}\', {self.fileID}, {self.Tnv_r}, {self.Tnv_r}, {T1}, {T2}, {T3}, {T1}, {T2+2})'''
        
        calcTemperatureID = self.insert(q)

#        print(q)

        self.dict_tr[Nist] = calcTemperatureID

    return calcTemperatureID


def getTR_ctp_0(self, name, r):

    tr_name = f'ТР-для {name}'

#    ur_o = 1000/(r_get(r, 'T1_r', None)-r_get(r, 'T1to_so', None))
    T1 = r_get(r, 'T1_r', None)
    T2 = r_get(r, 'T1to_so', None)
    T3 = 95

    '''
  tn_isl float DEFAULT 2.5, -- COMMENT 'Расчетная температура наружного воздуха излома температурного графика',
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



    q = 'INSERT INTO [calcTemperatures] (calcTemperatureID, fileID,  Tx, Tn_r, Tn_r_v, Tr_co_1_zco, Tr_co_2_zco, Tr_co_3_zco, Tr_to_1_nco, Tr_to_2_nco) VALUES(\'{}\', {}, {}, {}, {}, {}, {}, {}, {}, {})'\
         .format(tr_name, self.fileID,
         r_get(r, 'Thv', None), self.Tnv_r, self.Tnv_r, T1, T2, T3, T1, T2)
    
    specExpendID = self.insert(q)

    return specExpendID



def getTR_ctp(self, name, T1, T2, T3, r):

    tr_name = f'ТР-после {name}'

#    q = 'INSERT INTO [specExpends] (specExpendID, fileID, calcHLdep, calcHLindep, avgHLGVScloseMix) VALUES(\'{}\', {}, {}, {}, {})'\
#         .format(ur_name, self.fileID, 1000/(T1-T2), 1000/(T1-T2-10), 18.2)

    q = 'INSERT INTO [calcTemperatures] (calcTemperatureID, fileID,  Tn_r, Tn_r_v, Tr_co_1_zco, Tr_co_2_zco, Tr_co_3_zco, Tr_to_1_nco, Tr_to_2_nco) VALUES(\'{}\', {}, {}, {}, {}, {}, {}, {}, {})'\
         .format(tr_name, self.fileID_ctp,
         self.Tnv_r, self.Tnv_r, T1, T2, T3, T1, T2)


    specExpendID = self.insert(q)

    return specExpendID



def getRS(self, Nist):
    ur_name = f'РС{Nist}'

    externalCodeID = self.dict_rs.get(Nist, None)

    if not externalCodeID:
        externalCodeID = self.insert('INSERT INTO [externalCodes] (name, fileID) VALUES (\'{}\', {})'.format(ur_name, self.fileID))
        self.dict_rs[Nist] = externalCodeID

    return externalCodeID


def getRS_ctp(self, name_ctp, heatSourceID):
    externalCodeID = self.insert('INSERT INTO [externalCodes] (name, fileID, heatSourceID) VALUES (\'{}\', {}, {})'.format(name_ctp, self.fileID_ctp, heatSourceID))
    return externalCodeID
