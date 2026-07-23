import math

#-----------------------------------------------------------------------------------

def soprDR(diam, debug):
    n = 1
    if diam == 0: return 0
    if n == 0: n = 1

    sopr = 1e4 / math.pow(diam, 4.) * n

#    if debug:
#        print(f'ДР S={sopr}, diam={diam}')
    

    return sopr

#-----------------------------------------------------------------------------------

def Sopr_ventil(pr, pr_out, debug):
    S = 0

    G_ventil = pr_out.get('G_ventil', 0)
    a8 = pr.get('a8', 0) # Расчетные потери напора в калориферах

    if G_ventil != 0:
         S = a8 / math.pow(G_ventil, 2.);

#    if debug:
#        print(f'Вентиляция S={S} a8={a8} G_ventil={G_ventil}')

    return S

#-----------------------------------------------------------------------------------

def Sopr_otopln(pr, pr_out, debug):
    S = 0

    G_otopln = pr_out.get('G_otopln', 0)
    a7 = pr.get('a7', 0) # Расчетные потери напора в отопит.системе (подогревателе)

    pr_a19_co = 1 # Число параллельно включенных подогревателей СО

    if G_otopln != 0:
         S = a7 / math.pow(G_otopln / pr_a19_co, 2.);

    a17 = pr.get('a17', 0)
    gvps = pr.get('gvps', 0)
    gvpw = pr.get('gvpw', 0)
    G_gvpw = pr_out.get('G_gvpw', 0)
    G_gvps = pr_out.get('G_gvps', 0)

    if (gvps != 0 or gvpw != 0) and a17 == 1: #/*'О'*/: 
        S = a7 / math.pow(G_otopln + G_gvps + G_gvpw, 2.);

#    if debug:
#        print(f'a7={a7} G_otopln={G_otopln} S={S}')

    return S

#-----------------------------------------------------------------------------------

def Sopr_otoplz(pr, pr_out, debug):
    S = 0

    G_otoplz = pr_out.get('G_otoplz', 0)
    a7 = pr.get('a7', 0) # Расчетные потери напора в отопит.системе (подогревателе)

    if G_otoplz != 0:
        S = a7 / math.pow(G_otoplz, 2.)

    a17 = pr.get('a17', 0)
    gvps = pr.get('gvps', 0)
    gvpw = pr.get('gvpw', 0)
    G_gvpw = pr_out.get('G_gvpw', 0)
    G_gvps = pr_out.get('G_gvps', 0)

    if (gvps != 0 or gvpw != 0) and a17 == 1: #/*'О'*/: 
        S = a7 / math.pow(G_otoplz + G_gvps + G_gvpw, 2.)

#    if debug:
#        print(f'a7={a7} G_otoplz={G_otoplz} S={S}')

    return S

#-----------------------------------------------------------------------------------

def Sopr_gvs(pr, pr_out, debug):
    

    a17 = pr.get('a17', 0)
    G_gvsm = pr_out.get('G_gvsm', 0)
    G_gvpw = pr_out.get('G_gvpw', 0)
    G_gvpr = pr_out.get('G_gvpr', 0)
    G_gvps = pr_out.get('G_gvps', 0)
    G_otopln = pr_out.get('G_otopln', 0)
    G_otoplz = pr_out.get('G_otoplz', 0)

    if G_gvps != 0:
       ras = G_otopln + G_otoplz
       if a17 == 1: #/*'О'*/) 
           ras += G_gvps

    elif G_gvpw != 0:
       ras = G_otopln + G_otoplz
       if a17 == 1: #/*'О'*/) 
            ras += G_gvpw

    elif G_gvpr != 0:
       ras = G_gvpr

    elif G_gvsm != 0:
       ras = G_gvsm
    else:
       #        ras = 1e-12;
       pass

    S = 0

#    if debug:
#        print('ГВС', a17, G_otoplz+G_otopln, ras)

    if ras != 0 : 
        S = pr.get('a23', 0) / math.pow(ras, 2.)
#                            l->Z = pr->gvpr + pr->gvps + pr->gvpw + pr->gvsm;
    return S

#-----------------------------------------------------------------------------------
