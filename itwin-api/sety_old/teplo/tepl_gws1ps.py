import math


from sety.teplo.m import srlog
from sety.teplo.t import getS28

#-----------------------------------------------
# Расход тепла на ГВС ступень I
# последовательная схема
#-----------------------------------------------



def getF1(node, pr, pr2, tr):

  Q_gvs_sred = pr.get('gvps', 0)

#  Wsr = pr2->G_otopln+pr2->G_otoplz
#  if (pr.get('a17', 0) == 'О')  Wsr += pr2->G_gvps
#  Wsr *= 1000

  Q = Q_gvs_sred*getS28().ps*1e6 #  Средняя тепловая нагрузка на горячее водоснабжение

  Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 18))

#  G0_s, dGbo

  if pr.get('otopln', 0) != 0:
    G0_s = pr.get('otopln', 0)/(tr.get('Tr_to_1_nco', 0)-tr.get('Tr_to_2_nco', 0)) #расчетный расход сет.воды на отопление

  else:
    G0_s = pr.get('otoplz', 0)/(tr.get('Tr_co_1_zco', 0)-tr.get('Tr_co_2_zco', 0)) #расчетный расход сет.воды на отопление


  dGbo = Q*(pr.get('Tr_gvs', 60)-(tr.get('T2_isl_2stup_ps', 0)-tr.get('delta_tg_ps', 0)))/(tr.get('T1_isl_2stup', 0)-tr.get('T2_isl_2stup_ps', 0))/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))#расчетная добавка за счет ГВС
  
#/ Если повышенный

#  const PC *pc
#  const TN *tn
  """
  Тут проверяем ТГ

  pc = getPC(node)
  if pc:
      tn = getTN(pc->kod_ist)

      if tn and tn->tip == 3: #/*'П'*/
          dGbo = 0
  """


  Wsr = G0_s*1000000+dGbo                     #расчетный расход сет.воды на вход


#  t1is = pr.get('T1_isl_2stup', 0) #  Расчетная температура воды на входе 2 ступени ГВС в точке излома темпер.графика 
  t2is = tr.get('T2_isl_2stup_ps', 0) #  Расчетная температура воды на выходе 2 ступени ГВС в точке излома темпер.графика
  tgvs = pr.get('Tr_gvs', 60)       #  Расчетная температура горячей воды в местах водоразбора                         

  Wp = Wsr  # Расход на 1 ступени
  Wv = Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 5))  # Водопроводная вода



  Wm = min(Wp, Wv) # Расход минимальный
  Wb = max(Wp, Wv) # Расход максимальный

  tx = tr.get('Tx', 0)

  dt = tr.get('delta_tg_ps', 0)  #  Недогрев водопроводной воды в первой ступени системы горячего водоснабжения
  
  QIsr = Q*(t2is-dt-tr.get('Tx', 18))/(pr.get('Tr_gvs', 60) - tr.get('Tx', 18))
  tau2isl = t2is - QIsr/Wsr # Температура на выходе потребителя

  if tau2isl < tr.get('Tx', 0): 
        tau2isl = tr.get('Tx', 0)+1

  dtsr = srlog(tau2isl-tr.get('Tx', 0), t2is-(t2is-dt))

  kF1 = QIsr/dtsr

#  wout << "kf1 = " << kF1 << endl

#  if Gx*Wsr <= 0:
#    print(pr)
#    print(f'{Q}/({pr.get('Tr_gvs', 60)} - {tr.get('Tx', 5)})')
#    print(pr.get('Tr_gvs', 60), tr.get('Tx', 18))
#    print(Gx, Wsr)

#    exit(0)

  F1 = kF1/math.sqrt(Gx*Wsr)

  return F1


def getE1(node, pr, pr2, tr):

  Q_gvs_sred = pr.get('gvps', 0)

                        #Балансовая нагрузка 
  Q = Q_gvs_sred*getS28().ps*1e6 #  Средняя тепловая нагрузка на горячее водоснабжение


  Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 18))

#  G0_s, dGbo

  if pr.get('otopln', 0) != 0:
    G0_s = pr.get('otopln', 0)/(tr.get('Tr_to_1_nco', 0)-tr.get('Tr_to_2_nco', 0)) #расчетный расход сет.воды на отопление
  else:
    G0_s = pr.get('otoplz', 0)/(tr.get('Tr_co_1_zco', 0)-tr.get('Tr_co_2_zco', 0)) #расчетный расход сет.воды на отопление

  dGbo = Q*(pr.get('Tr_gvs', 60)-(tr.get('T2_isl_2stup_ps', 0)-tr.get('Tx', 0)))/(tr.get('T1_isl_2stup', 0)-tr.get('T2_isl_2stup_ps', 0))/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))#расчетная добавка за счет ГВС

#/ Если повышенный

#  const PC *pc
#  const TN *tn

  """
  Тут проверяем ТГ

  pc = getPC(node)
  if (pc) tn = getTN(pc->kod_ist)

  if tn && tn->tip == 3: #/*'П'*/
    dGbo = 0
    """


  Wsr = G0_s*1000000+dGbo                     #расчетный расход сет.воды на вход

  Wp = Wsr  # Расход на 1 ступени
  Wv = Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))  # Водопроводная вода

  Wm = min(Wp, Wv) # Расход минимальный
  Wb = max(Wp, Wv) # Расход максимальный


  F1 = getF1(node, pr, pr2, tr)

  E1 = 1/(0.35*Wm/Wb+0.65+math.sqrt(Wm/Wb)/F1)

  return E1
