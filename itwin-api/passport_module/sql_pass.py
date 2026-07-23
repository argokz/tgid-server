
def ms_passport(id):
    q = f'''
select 
ms.id,
ms.data_zapolneniya,
ms.energosistema,
mag.naimenovanie_magistrali,
ms.nomer_pasporta,
ms.vid_seti,
ist.naimenovanie_istochnika,
ms.opisanie_uchastka_ms,
ms.proektnaya_organizatsiya,
ms.nomer_proekta,
ms.kadastrovyy_nomer,
ms.obschaya_dlina_trassy,
ms.rabochee_davlenie,
ms.rabochaya_temperatura,
ms.god_postroyki,
ms.god_vvoda_v_ekspluatatsiyu
 
from uchastok_ms ms
join magistrali mag on mag.id=ms.magistral
left join istochniki_teplosnabzheniya ist on ist.id=ms.istochniki_teplosnabzheniya
where ms.id={id}
'''

    return q



def rs_passport(id):

    q = f'''
select 
rs.id,
rs.data_zapolneniya,
rs.uzel_podklyucheniya,
--rs.predpriyatie_vladelets
org.naimenovanie,
rs.registratsionnyy_nomer,
rs.adres_predpriyatiya_vladeltsa,
rs.naznachenie_rs,
rs.rabochaya_sreda,
rs.rabochee_davlenie,
rs.rabochaya_temperatura
 
from uchastok_rs rs
left join organizatsii_vladeltsy org on org.id=rs.predpriyatie_vladelets
where rs.id={id}
'''

    return q

def passport(ms_rs, id):
    if ms_rs == 'ms':
        return ms_passport(id);
    if ms_rs == 'rs':
        return rs_passport(id);

    return ''
