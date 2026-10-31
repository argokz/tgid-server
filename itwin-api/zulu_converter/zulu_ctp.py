import ur
import potreb

from r import r_get

def ctp(self, Nist, externalCodeID, node_name, x, y, H_geo, coor, id_new, r):
    '''
    Обработка ЦТП
    Ввод
    self
    Nist
    externalCodeID код РС
    node_name имя узла
    x, y, H_geo, coor, координаты и высота
    id_new номер nodes
    r 
    '''
    N_schem = int(r_get(r, 'N_schem', 0))
    Qo_t    = r_get(r, 'Qo_t', 0)
    Qsv_t   = r_get(r, 'Qsv_t', 0)
    Qgv_t   = r_get(r, 'Qgv_t', 0)
    Hnz_ras = r_get(r, 'Hnz_ras', 0)
    Hnz_obr = r_get(r, 'Hnz_obr', 0)

    Qgv_t   = r_get(r, 'Qgv_sred', 0)

    if node_name[:3] != "ЦТП" and node_name[:3] != "ТРП":
        node_name = "ЦТП "+node_name
#    print('ЦТП', node_name)

    specExpendID = ur.getUR(self, Nist, r_get(r, 'T1_r', 0), r_get(r, 'T2_r', 0), r_get(r, 'T3_r', 0))
    calcTemperatureID = ur.getTR(self, Nist, r)

#    name2 = '{} {} {} {} {}'.format(Nist, N_schem, r_get(r, 'T1_r', None), r_get(r, 'T2_r', None), r_get(r, 'T3_r', None))

#    node_name2 = 'G = {} Got = {}'.format(r_get(r, 'Gsum_pod', None), r_get(r, 'Gset_nal', None))
    node_name2 = node_name

    id_new1 = self.insertNode(externalCodeID, node_name2, (x+1, y), H_geo, self.fileID)

    T1 = r_get(r, 'T3_r', 0)
    T2 = r_get(r, 'T2_r', 0)
#    T3 = T1-0.5
    T3 = T1

#    uf = (T1-T3)/(T3-T2)
    uf = 0.0001
    uf = 0

    volWaterHS = 26
    volWaterVS = 26

    setLeakageRet = Qo_t*volWaterHS+Qsv_t*volWaterVS

    setLeakageRet = setLeakageRet*0.25/100

#    Tnv_r = r_get(r, 'Tnv_r', None)

    insert = '''INSERT INTO [heatSources] (nodeID, name, hSourceCode, tvb_tr, tvn_r, tn_5, t1_r, tx_r, t3_r, hSourcePowerInst, uf, tg_r) 
             VALUES ({}, \'{}\', \'{}\', {}, {}, {}, {}, {}, {}, {}, {}, {})'''\
         .format(id_new1, node_name, node_name, self.Tvn, self.Tvn, self.Tnv_r, T1, r_get(r, 'Thv', 0), T3, 0, uf, r_get(r, 'Tgv', 0))
    heatSourceID = self.insert(insert)

#    insert = 'INSERT INTO [setPressNodes] (nodeID,pressFlow,pressRet,fileID, fragment_resultID, kod_m, uzel_m) VALUES ({},{},{},{},{}, \'РС{}\', \'{}\')'\
#         .format(id_new1, Hnz_obr+Hnz_ras-H_geo, Hnz_obr-H_geo, self.fileID, self.fileID, Nist, node_name)

    kod_m = 'РС{}'.format(Nist)

    pP = Hnz_obr+Hnz_ras-H_geo
    pO = Hnz_obr-H_geo

    if pP <= 0: pP = 50
    if pO <= 0: pO = 20

    insert = 'INSERT INTO [setPressNodes] (nodeID,pressFlow,pressRet,fileID, fragment_resultID, kod_m, uzel_m) VALUES ({},{},{},{},{}, \'{}\', \'{}\')'\
         .format(id_new1, pP, pO, self.fileID, self.fileID, kod_m, node_name)
    
    self.insert(insert)

    consumerStateID = 1

    kv = self.kv1

    if N_schem == 2:
#        Qgv_t /= 1000
        kv = self.kv_sm
    elif N_schem == 3:
        kv = self.kv_pr


    self.dict_ctp[coor[0]] = (externalCodeID, coor[0], None, None, 0, 0, node_name, heatSourceID, T1, T2, T3, r)
    nagr, gvs, shema, shema_v = potreb.get_nagr_gvs_ctp(N_schem)

#    specExpendID2 = ur.getUR_ctp_0(self, node_name, r)
#    calcTemperatureID2 = ur.getTR_ctp_0(self, node_name, r)

    specExpendID2 = specExpendID
    calcTemperatureID2 = calcTemperatureID

    if shema != '':
        insert = f'''INSERT INTO [generalizedConsumers] 
             (consumerStateID, nodeID, specExpendID, calcTemperatureID, {nagr}, calcHLventil, {gvs}
             ,perspCalcHLdep, perspCalcHLventil, perspAvgHLGVSopenSysFlow, {shema}, setLeakageRet
             ,calcTempDep,calcTempHRconseq,calcTempHRmix,calcTempHRparall,calcTempHRpreON,calcTempIndep, varCoeffID
             
             ) 
             VALUES ({consumerStateID}, {id_new}, {specExpendID2}, {calcTemperatureID2}
             , {Qo_t}, {Qsv_t}, {Qgv_t}
             , {Qo_t}, {Qsv_t}, {Qgv_t}
             , {shema_v}, {setLeakageRet}
             , {self.Tvn}, {self.Tvn}, {self.Tvn}, {self.Tvn}, {self.Tvn}, {self.Tvn}, {kv}
             )'''

    else:

        insert = f'''INSERT INTO [generalizedConsumers] 
             (consumerStateID, nodeID, specExpendID, calcTemperatureID, {nagr}, calcHLventil, {gvs}
             ,perspCalcHLdep, perspCalcHLventil, perspAvgHLGVSopenSysFlow, varCoeffID
             
             ) 
             VALUES ({consumerStateID}, {id_new}
             , {specExpendID2}, {calcTemperatureID2}
             , {Qo_t}, {Qsv_t}, {Qgv_t}
             , {Qo_t}, {Qsv_t}, {Qgv_t}, {kv}
             )'''

#    print(insert)
    
    self.insert(insert)

    return

    id_new1 = self.insertNode(externalCodeID, node_name2, (x-1, y), H_geo, self.fileID)

    Hzdan = 0

    mixFactCoeff = 0
    if (T3-T2) != 0: mixFactCoeff = (T1-T3)/(T3-T2)


    n1, n2 = potreb.get_cxema_ctp(N_schem, Qo_t,Qsv_t,Qgv_t)

    nagr, gvs = potreb.get_nagr_gvs_ctp_real(N_schem)

    automDegID = 2 # 1- неавтоматизировнная 2 автоматизировнная

    insert = '''INSERT INTO [realConsumers] 
         (automDegID, consumerStateID, name, nodeID, {}, calcHLventil, {}, schemeNum, specExpendID, buildHeight, mixFactCoeff, calcTemperatureID, volWaterHS, volWaterVS, setLeakageRet, calcTempHR, calcTempVS) 
         VALUES ({}, {}, \'{}\', {}, {}, {}, {}, \'{}.{}\', {}, {}, {}, {}, {}, {}, {}, {}, {})'''\
         .format(nagr, gvs,
         automDegID, consumerStateID, node_name2, id_new1, Qo_t, Qsv_t, Qgv_t, n1, n2, specExpendID2, Hzdan, mixFactCoeff, calcTemperatureID2, volWaterHS, volWaterVS, setLeakageRet, self.Tvn, self.Tvn)

    self.insert(insert)



