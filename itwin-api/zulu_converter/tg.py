from collections import namedtuple

import pyodbc

import math
#import connector
import array

#################################################################################


def InitOtoplTempStructure(row, ot, tempstruct_norm) :
#    tempstruct.feat = "Otop"
#    print(row)

    ot["THOR"] = row.get("tn_5") # Расчетная температура наружного воздуха
    ot["THK"] = row.get("tn_1") # Температура наружного воздуха конца отопительного сезона
    ot["TVR"] = row.get("tvn_r") # Расчетная температура воздуха внутри помещения

    ot["TAURP"] = row.get("t1_r")  # Расчетная темп-ра сетевой воды в подающем трубопроводе
    ot["TAURO"] = row.get("t2_r")  #      -"-                       в обратном
    ot["TAURS"] = row.get("t3_r")  #      -"-                       после узла смешения

    ot["QR"] = row.get("q_r")  # Расчетная тепловая нагузка на отопление
    ot["TSMIN"] = row.get("t1_2r")  # Температура нижней срезки  сетевой воды
    ot["TSMAX"] = row.get("t1_4r")  # Температура верхней срезки  сетевой воды
    ot["T2MIN"] = row.get("t2_2r")  # Температура нижней срезки обратной воды

#    tempstruct.ot->TEC[0] = 0;   # Наименование ТЭЦ
#    tempstruct.ot->MAG[0] = 0;   # Наименование магистали
#    tempstruct.ot->GDN[0] = 0;   # Начало отопительного сезона
#    tempstruct.ot->GDK[0] = 0;   # Конец отопительного сезона

    ot["KSR"] = row.get("uf")  # Поправка коэффициента смешения
    ot["V"] = row.get("v")  # Скорость ветра
    ot["TB"] = row.get("tvb_tr")  # Требуемая температура воздуха внутри отап-х помещениях

    ot["QMAX"] = 100


    ot["KOL"] = -ot["THOR"] + ot["THK"] + 1

#    tempstruct_norm.feat = "Otop"
#    tempstruct_norm.DeleteStruct(tempstruct_norm.ot);
#    tempstruct_norm.ot = new OTOP();
#    (*tempstruct_norm.ot) = (*tempstruct.ot);
#    tempstruct_norm.ot->TSMIN = 0;
#    tempstruct_norm.ot->TSMAX = 200;
#    tempstruct_norm.ot->T2MIN = 0;


#################################################################################

def InitPovTempStructure(row, pov, tempstruct_norm):
#  tempstruct.feat=Pov;
#  tempstruct.DeleteStruct(tempstruct.pov);
#  tempstruct.pov=new POV();

  pov["THOR"] = row.get("tn_5"); # Расчетная температура наружного воздуха
  pov["THK"] = row.get("tn_1"); # Температура наружного воздуха конца отопительного сезона
  pov["TVR"] = row.get("tvn_r"); # Расчетная температура воздуха внутри помещения

  pov["TAURP"] = row.get("t1_r");  # Расчетная темп-ра сетевой воды в подающем трубопроводе
  pov["TAURO"] = row.get("t2_r");  #      -"-                       в обратном
  pov["TAURS"] = row.get("t3_r");  #      -"-                       после узла смешения

  pov["QOR"] = row.get("q_r");  # Расчетная тепловая нагузка на отопление
  pov["QGW"] = row.get("q_gv");   # Среднечасовая нагрузка горячего водоснабжения, Гкал/ч
  pov["TSMIN"] = row.get("t1_2r");  # Температура нижней срезки  сетевой воды
  pov["TSMAX"] = row.get("t1_4r");  # Температура верхней срезки  сетевой воды

  pov["TVRO"] = row.get("tg_r");  # Температура горячей воды в точке водоразбора
  pov["TV"] = row.get("tx_r");  # Температура холодной воды
  pov["TB"] = row.get("tvb_tr");  # Требуемая температура воздуха внутри отап-х помещениях

  pov["NEDOG"] = row.get("t_gv1");  #  Величина недогрева водопроводной воды в первой ступени подогревателя горячего водоснабжения, Град. C
  pov["KSR"] = row.get("uf");  # Поправка коэффициента смешения
  pov["V"] = row.get("v");  # Скорость ветра

    
#  pov["TEC[0]"] = 0;   # Наименование ТЭЦ
#  pov["MAG[0]"] = 0;   # Наименование магистали
#  pov["GDN[0]"] = 0;   # Начало отопительного сезона
#  pov["GDK[0]"] = 0;   # Конец отопительного сезона
  
  tpow["QMAX"] = 100;

  pov["KOL"] = -pov["THOR"] + pov["THK"] + 1;


#  tempstruct_norm.feat=Pov;
#  tempstruct_norm.DeleteStruct(tempstruct_norm.pov);
#  tempstruct_norm.pov=new POV();
#  (*tempstruct_norm.pov)=(*tempstruct.pov); 
#  tempstruct_norm.pov->TSMIN=0;
#  tempstruct_norm.pov->TSMAX=200;
  #tempstruct_norm.pov->T2MIN=0;



#################################################################################







#def CalculateOT(OTOP &tg, OTDATA& data) :
def CalculateOT(tg, data_tn, data_tau01, data_tau02, data_tau03, data_tau01v, data_tb, data_QO) :


  ##///////////////////////////////////////////////////////////////////////////
  pr = 0  # Спросить у Надежды Ивановны
  Ok = True

  ex = 0.001

#  int i, kl, tm, n;
#  double DTAU, TETA, DTR;
#  double ur, uf, t, tbn, eq, ex=0.001, dq;
#  double qopc, qq, qocn, qoc, qocnv, qocv, tbv;

  kl = int(tg.get("THK") - tg.get("THOR"));

  for i in range(0, kl+1) : 
      data_tn[i] = tg.get("THOR")+(kl-i)

  qr = tg.get("QR")
  if qr == 0 : qr = 1

  tg["QMAX"] = tg.get("QMAX") / qr;

  uf = tg.get("KSR");
  DTAU = tg.get("TAURP") - tg.get("TAURO");
  TETA = tg.get("TAURS") + tg.get("TAURO");
  DTR  = TETA/2.0 - tg.get("TVR");
  TETA = tg.get("TAURS") - tg.get("TAURO");

  for i in range(0, kl+1) :
    t   = data_tn.get(i);
    tm  = 1;
    tbn = tg.get("TB");
    qq  = qopc = (tg.get("TB") - t) / (tg.get("TVR") - tg.get("THOR"));

    n   = 100;

    while True :
      ex = 0.01;              # по деффициту мощности
      data_tau01[i] = t + qopc * ( tg.get("TVR")-tg.get("THOR") + (0.5+uf)*DTAU/(1+uf) + DTR/math.pow(qopc,0.2) );
      qocn = qopc;
      qoc  = qocn;

      while True :                    # по нижней верхней срезке
        data_tau02[i] = data_tau01[i] - DTAU*qopc;
        data_tau03[i] = data_tau02[i] + TETA*qopc;

        jjj = 1

        while True :                  # Температура внутри помещения
#          print("1 qoc", qoc, 'jjj', jjj)
          jjj+=1

          
          qoc   = qocn;
          data_tb[i] = t + (tg.get("TB")-t)*qoc/qq;  # qopc; ????

          # соответствует Qo/QOR ( см. Зингер стр.160 )
          qocn = (data_tau01[i]-data_tb[i])/((0.5+uf)/(1+uf)*DTAU+DTR/math.pow(qoc,0.2))
          eq   = abs((qoc-qocn)/qoc)
          if  eq < ex : break;

        if data_tau01[i] < tg.get("TSMIN") or data_tau01[i]>tg.get("TSMAX") or data_tau02[i]<tg.get("T2MIN") :
          # срезка
          if data_tau01[i] < tg.get("TSMIN") : 
             tm = 0; 
             data_tau01[i]=tg.get("TSMIN")

          if data_tau01[i] > tg.get("TSMAX") :
             tm = 0
             data_tau01[i]=tg.get("TSMAX")

          if data_tau02[i] < tg.get("T2MIN") :
            tm = 0;
            if data_tau01[i] < tg.get("TSMAX") : data_tau01[i] = data_tau01[i]+0.05;
            else : tm = 1;

          jjj = 1
          while True :

#            print("2 qoc", qoc, 'jjj', jjj)
            jjj+=1

#            print('data_tau01[i]', data_tau01[i], 'data_tb[i]', data_tb[i], 'uf', uf)

            qocn  = (data_tau01[i]-data_tb[i])/((0.5+uf)/(1+uf)*DTAU+DTR/math.pow(qoc,0.2));
            eq    = abs((qoc-qocn)/qoc)
            qoc   = qocn;
            data_tb[i] = t+(tg.get("TB")-t)*qoc/qq;
            if eq < ex : break

          qopc = qocn;

        else : tm = 1;

        if tm != 0 : break; # по нижней верхней срезке

      if qoc > tg.get("QMAX") and n >= 1 :
        qopc = tg.get("QMAX")
        tbn  = t + qopc*(tg.get("TB") - t)/qq
        data_defm = abs((tg.get("QMAX") - qq)*100/tg.get("QMAX"))

        qopc = (tbn - t)/(tg.get("TVR") - tg.get("THOR"))
        dq   = ex+1
        n -= 1

      else : dq = ex-1

      if dq < ex : break

    data_QO[i] = qocn;
    if tg.get("V") > 3 :      # Поправка на ветер
      data_tau01v[i] = data_tau01[i]+(data_tau01[i]-tg.get("TB"))*(tg.get("V")/100);
      qocnv = qocn;

      while True :
        qocv = qocnv;
        if pr == 1 : tbv = tg.get("TB")
        else :       tbv = t + (tg.get("TB")-t)*qocv/qq
        qocnv = (data_tau01v[i]-tbv)/((0.5+uf)/(1+uf)*DTAU+DTR/math.pow(qocv,0.2))
        eq    = abs((qocv-qocnv)/qocv)
        if eq < ex : break

      if qocnv > tg.get("QMAX") :
        qocnv = tg.get("QMAX")
        tbn   = t+qocnv*(tg.get("TB")-t)/qq
        qocnv = (tbn-t)/(tg.get("TVR")-tg.get("THOR"))
        data_tau01v[i] = t+qocnv*(tg.get("TVR")-tg.get("THOR")+(0.5+uf)*DTAU/(1+uf)+DTR/math.pow(qocnv,0.2))

      if data_tau01[i] <= tg.get("TSMIN") : data_tau01v[i] = tg.get("TSMIN") # срезка
      if data_tau01v[i] > tg.get("TSMAX") : data_tau01v[i] = tg.get("TSMAX")

    else : data_tau01v[i] = data_tau01[i]

  tg["QMAX"] = tg.get("QMAX") * tg.get("QR")

  return Ok



def CalculatePOV(tg, data_tn, data_tau01, data_tau02, data_tau03, data_tau01v, data_tb, data_QO) :

  Ok = True

# --------------------------------------------------------------------------
  
  ex=0.001
  isr=0

#  double qq[100];
  kol = tg.get("THK") - tg.get("THOR")
  tg["QMAX"] = tg.get("QMAX") / tg.get("QOR")

  for i in range(0, kol+1)  : data.tn[i]=tg.get("THOR")+(kol-i);

  u = (tg.get("TAURP")-tg.get("TAURS")) / (tg.get("TAURS")-tg.get("TAURO"));
  if tg.get("KSR") != 0.0 : u = tg.get("KSR");

  DTAU = tg.get("TAURP") - tg.get("TAURO");
  t    = DTAU;
  TETA = tg.get("TAURS") + tg.get("TAURO");
  DTR  = TETA / 2.0 - tg.get("TVR");
  TETA = tg.get("TAURS") - tg.get("TAURO");
  NC   = tg.get("QGW") / tg.get("QOR");
  dlt  = 1.2 * NC * DTAU;
  tis  = tg.get("THK");

  for i in range(0, kol+1)  : # отопительный температурный график
    t = data.tn[i];
    qq[i] = qopc = (tg.get("TB")-t)/(tg.get("TVR")-tg.get("THOR"));

    data_t01[i] = t+qopc*(tg.get("TVR")-tg.get("THOR")+(0.5+u)*DTAU/(1+u)+DTR/pow(qopc,0.2));
    data_t02[i] = data_t01[i]-qopc*DTAU;

    if data_t01[i] >= tg.get("TVRO") and isr==0 :
       isr=1
       tis=t
       t02is = data_t02[i]

  if tis == tg.get("THK") :  t02is = data_t02[0];

  twis   = t02is-tg.get("NEDOG");
  dlt2is = dlt * (twis - tg.get("TV")) / (tg.get("TVRO") - tg.get("TV"));
  data_defm   = 0;
  defn   = 0;

  for i in range (0, kol+1) : # повышенный температурный график
    t    = data.tn[i];
    nn   = 1000;
    tbn  = tg.get("TB");
    qopc = qq[i];
    psr  = 0;

    while True :                 # по дефициту мощности

      if nn < 1000 :
        data_t01[i] = t+qopc*(tg.get("TVR")-tg.get("THOR")+(0.5+u)*DTAU/(1+u)+DTR/pow(qopc,0.2));
        data_t02[i] = data_t01[i]-qopc*DTAU;

      dlt2=dlt2is*(data_t02[i]-tg.get("TV"))/(t02is-tg.get("TV"));
      dlt1=(dlt-dlt2);
      if dlt2 > dlt : dlt1=0;
      data.tau01[i]=data_t01[i]+dlt1;
      data.tau02[i]=data_t02[i]-dlt2;

      if data.tau01[i]<tg.get("TSMIN") or data.tau01[i]>tg.get("TSMAX") :
        if data.tau01[i]<tg.get("TSMIN") : ts=tg.get("TSMIN");
        if data.tau01[i]>tg.get("TSMAX") : ts=tg.get("TSMAX");

        data.tau02[i]=ts-(ts-t)*(data.tau01[i]-data.tau02[i])/(data.tau01[i]-t);

        if data.tau01[i]<tg.get("TSMIN") : data.tau01[i]=tg.get("TSMIN");
        if data.tau01[i]>tg.get("TSMAX") : data.tau01[i]=tg.get("TSMAX");

      # Срезка для отопительного графика
      if data_t01[i]<tg.get("TSMIN") or data_t01[i]>tg.get("TSMAX") :
        if data_t01[i]<tg.get("TSMIN") : ts=tg.get("TSMIN");
        if data_t01[i]>tg.get("TSMAX") : ts=tg.get("TSMAX");

        data_t02[i]=ts-(ts-t)*(data_t01[i]-data_t02[i])/(data_t01[i]-t);

        if data_t01[i]<tg.get("TSMIN") : data_t01[i]=tg.get("TSMIN");
        if data_t01[i]>tg.get("TSMAX") : data_t01[i]=tg.get("TSMAX");

      tmp = tg.get("QOR");
      data_tg[i] = (tmp/DTAU*(dlt1+dlt2))/(1.2*tg.get("QGW")/(tg.get("TVRO")-tg.get("TV")))+tg.get("TV");

      gg  = dlt/DTAU;               # тепло на ГВ в II ступени
      go  = (data_t01[i]-data_t02[i])/DTAU;   # тепло на отопление
      qoc = go+gg;

      if qoc>tg.get("QMAX") and nn>=1 :
        tbn -= 0.05
        qopc=(tbn-t)/(tg.get("TVR")-tg.get("THOR"))

        dq = abs((tg.get("QMAX")-qoc)/tg.get("QMAX"))

        defn = abs((tg.get("QMAX")-(qq[i]+gg))*100/tg.get("QMAX"))

        if data_defm < defn :
            data_defm = defn

#        data_defm = (data_defm < defn) ? defn : data_defm;  # if(defm<defn) defm=defn;
        psr = 1
        nn -=1
      else :dq=ex;

      if dq < ex : break

    data.tb[i]=tbn;

    if tg.get("V")>3 :   # Учет ветра
      data.tau01v[i] = data.tau01[i]+(data.tau01[i]-tbn)*(tg.get("V")/100.);
      if psr==1 :
        data.tau01v[i] = data.tau01[i];
      else :
        qocnv=qoc;

        while True:
          qocv=qocnv
          tbv=t+(tbn-t)*qocv/qopc
          qocnv=(data.tau01v[i]-tbv)/((0.5+u)/(1+u)*DTAU+DTR/pow(qocv,0.2))
          eq = abs((qocv-qocnv)/qocv)
          if eq < ex : break


        if qocnv>tg.get("QMAX") :
          qocnv=tg.get("QMAX");
          tbn=t+qocnv*(tg.get("TB")-t)/qq[i];
          qocnv=(tbn-t)/(tg.get("TVR")-tg.get("THOR"));
          data.tau01v[i]=t+qocnv*(tg.get("TVR")-tg.get("THOR")+(0.5+u)*DTAU/(1+u)+DTR/pow(qocnv,0.2));

      if data.tau01[i]<=tg.get("TSMIN") : data.tau01v[i]=tg.get("TSMIN")  #  срезка
      if data.tau01v[i]>tg.get("TSMAX") : data.tau01v[i]=tg.get("TSMAX")

    else : data.tau01v[i]=data.tau01[i]

    # Пересчет отопительного графика с учетом дефицита мощности
    qopc=(tg.get("TB")-t)/(tg.get("TVR")-tg.get("THOR"));
    if qopc > tg.get("QMAX") :  qopc=tg.get("QMAX");

    data_t01[i]=t+qopc*(tg.get("TVR")-tg.get("THOR")+(0.5+u)*DTAU/(1+u)+DTR/pow(qopc,0.2));
    data_t02[i]=data_t01[i]-qopc*DTAU;

    # Срезка для отопительного графика срезка
    if data_t01[i]<tg.get("TSMIN") or data_t01[i]>tg.get("TSMAX") :
      if data_t01[i]<tg.get("TSMIN") :  ts=tg.get("TSMIN")
      if data_t01[i]>tg.get("TSMAX") :  ts=tg.get("TSMAX")

      data_t02[i] = ts-(ts-t)*(data_t01[i]-data_t02[i])/(data_t01[i]-t);

      if data_t01[i] < tg.get("TSMIN") : data_t01[i]=tg.get("TSMIN")
      if data_t01[i] > tg.get("TSMAX") : data_t01[i]=tg.get("TSMAX")

  tg["QMAX"]=tg.get("QMAX")*tg.get("QOR");

  return Ok





"""
def Calculate(ot) :
{
  TempStruct->Init();
  if (TempStruct->feat==Otop) :
    Tip_name="Отопительный";
    OTOP * ot=(TempStruct->ot);     
    OTDATA * data = (TempStruct->ot_data);
    data->Init((*ot).KOL);
    CString sError;

    if not CheckInputOT((*ot), sError ) :
      AfxMessageBox(sError);
      return FALSE;
    else :
      CalculateOT((*ot), (*data));
      TempStruct->DeleteStruct(TempStruct->array_ptr);
      TempStruct->InitArray(7);
      TempStruct->array_ptr[0]=(*data).tn;
      TempStruct->array_ptr[1]=(*data).QO;
      TempStruct->array_ptr[2]=(*data).tau01;
      TempStruct->array_ptr[3]=(*data).tau02;
      TempStruct->array_ptr[4]=(*data).tau03;
      TempStruct->array_ptr[5]=(*data).tau01v;
      TempStruct->array_ptr[6]=(*data).tb;

      return True
"""


"""
  if (TempStruct->feat==Pov) :
    Tip_name="Повышенный";
    POV * ot=(TempStruct->pov);     
    POVDATA * data = (TempStruct->pov_data);
    data->Init((*ot).KOL);
    CString sError;
    if not CheckInputPOV((*ot), sError ) :

      AfxMessageBox(sError);
      return FALSE;
    else :
      CalculatePOV((*ot), (*data));
      TempStruct->DeleteStruct(TempStruct->array_ptr);
      TempStruct->InitArray(6);
      TempStruct->array_ptr[0]=(*data).tn;
      TempStruct->array_ptr[1]=(*data).tau01;
      TempStruct->array_ptr[2]=(*data).tau02;
      TempStruct->array_ptr[3]=(*data).tau01v;
      TempStruct->array_ptr[4]=(*data).tb;
      TempStruct->array_ptr[5]=(*data).tg;

      return True

  if ( (TempStruct->feat==SkkPov)or(TempStruct->feat==SkkPon) ) :
    if (TempStruct->feat==SkkPov) Tip_name="Скорректированный повышенный";
    else Tip_name="Скорректированный пониженный";
    SKK * ot=(TempStruct->skk);     
    SKDATA * data = (TempStruct->skk_data);
    data->Init((*ot).KOL);
    CString sError;

    if not CheckInputSK((*ot), sError ) :
      AfxMessageBox(sError);
      return FALSE;
    else :
      CalculateSK((*ot), (*data));
      TempStruct->DeleteStruct(TempStruct->array_ptr);
      TempStruct->InitArray(5);
      TempStruct->array_ptr[0]=(*data).tn;
      TempStruct->array_ptr[1]=(*data).tau01;
      TempStruct->array_ptr[2]=(*data).tau03;
      TempStruct->array_ptr[3]=(*data).tau02;       
      TempStruct->array_ptr[4]=(*data).tau01v;      

      return True

"""


def calc(conn, id)  :
#    return
    q = f"SELECT * FROM  heatSources WHERE id={id}"

    cursor = conn.cursor()

    cursor.execute(q)
    row = cursor.fetchone()

#    print(q)
#    print(row)

    columns = [column[0] for column in cursor.description]
#    print(columns)
#    print(dict(zip(columns, row[0])))
#    next()

#    print('!====================')
#    print(columns)
#    print(row)
#    print('!====================')

    row0 = dict(zip(columns, row))

#    return
    #print(r[0])

    typ = row0.get("graphTypeID", 0);

    ot = dict()
    tempstruct_norm_ot = dict()

    data = dict()    
    data_tn = dict()
    data_tau01 = dict()
    data_tau02 = dict()
    data_tau03 = dict()
    data_tau01v = dict()
    data_tb = dict()
    data_QO = dict()


    if typ == 1 or typ == 0 :
        InitOtoplTempStructure(row0, ot, tempstruct_norm_ot);
        CalculateOT(ot, data_tn, data_tau01, data_tau02, data_tau03, data_tau01v, data_tb, data_QO)

    if typ == 2 :
        CalculatePOV(ot, data_tn, data_tau01, data_tau02, data_tau03, data_tau01v, data_tb, data_QO)


    q = f"DELETE FROM deployedTempGraphs WHERE hSourceID={id}"
#    print(q)
    cursor.execute(q)
        
    for i in data_tn:
#          print("{:.1f},{:.1f},{:.1f},{:.1f}".format(data_tn.get(i), data_tau01.get(i), data_tau02.get(i), data_tau03.get(i)))
          q = f'''INSERT INTO deployedTempGraphs 
            (hSourceID,tn,t1,t2,t3,tv,t_bn) 
            VALUES ({id},{data_tn.get(i)},{data_tau01.get(i)},{data_tau02.get(i)},{data_tau03.get(i)},{data_tau01v.get(i)},{data_tb.get(i)} )'''
#          print(q)
          try :
            cursor.execute(q)
          except pyodbc.Error as e:
            print(e)


    #print(data)

    conn.commit()

    cursor.close()
#    conn.close()


if __name__ == '__main__':
    baza = 'UstGID2'

    conn = connector.connectToMsSQL('localhost', '', '', baza)
    cursor = conn.cursor()

    q = 'select id from heatSources'

    cursor.execute(q)

    ids = []

    while True:
        row = cursor.fetchone()
        if not row: break
        id,  = row

        ids.append(id)

    for id in ids:
        calc(conn, id)
