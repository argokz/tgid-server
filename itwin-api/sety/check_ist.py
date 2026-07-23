import sys
import pyodbc

from sety.any.colors import cprint
from sety.any.colors import nbsp

from sety.w_print import make_link

def check_ist(conn, fileID, calculationid):

    q = f'''
---------------------------------------
select 
    count(n.id),

--    n.fileid,
    fr.name, 
    ec.id, 
    ec.name,

    hs1.name,
    hs2.name,
    n1.externalnodename,
    n2.externalnodename,
    ec1.name,
    ec2.name,
    n1.id,
    n2.id,
    fr1.name,
    fr2.name


--    ec.externalcodeid, 
--    ec.heatsourceid,

--    n.externalnodename,

--    o.ist

from nodes n 
join externalcodes ec on ec.id=n.externalcodeid
join us_out o on o.nodeid=n.id and calculationid={calculationid}
join fragments fr on fr.id=n.fileid
left join heatsources hs1 on hs1.id=ec.heatsourceid
join heatsources hs2 on hs2.id=o.ist
left join nodes n1 on n1.id=hs1.nodeid
left join nodes n2 on n2.id=hs2.nodeid
left join externalcodes ec1 on ec1.id=n1.externalcodeid
left join externalcodes ec2 on ec2.id=n2.externalcodeid
left join fragments fr1 on fr1.id=n1.fileid
left join fragments fr2 on fr2.id=n2.fileid


where 
    n.fileID in ({fileID}) and 
    n.removed=0
    and o.externalsign=1
    and o.ist <> 0
    and (ec.heatsourceid <> o.ist or ec.heatsourceid is null)
    and n.internalNodeID is null

group by
    fr.name, 
    ec.id, 
    ec.name,

    hs1.name,
    hs2.name,
    n1.externalnodename,
    n2.externalnodename,
    ec1.name,
    ec2.name,
    n1.id,
    n2.id,
    fr1.name,
    fr2.name

order by 
    fr.name,
    ec.name
---------------------------------------

    '''

    ec_name_old = ''

    number = 0

    try:
        cursor = conn.cursor()
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            cnt, fr_name, ec_id, ec_name, hs1_name, hs2_name, n1_name, n2_name, n1_kod, n2_kod, n1_id, n2_id, fr1, fr2 = row

            if number == 0:
                
                cprint(f'[b]Уточните в Расчетных схемах (РС) Код источника:[/b]', color='red')
#                cprint(f'[b]Возможные ошибки при указании Источников тепла в Расчетных схемах:[/b]', color='red')
                    
            if n1_name is not None:
                link1 = make_link(f'[{n1_kod} {n1_name}]', 'node', n1_id)

                hs1_name = f'[b]{hs1_name}[/b] {link1}'
                    
            if n2_name is not None:
                link2 = make_link(f'[{n2_kod} {n2_name}]', 'node', n2_id)
                hs2_name = f'[b]{hs2_name}[/b] {link2}'
                

            if hs1_name is None:
                    if ec_name != ec_name_old:
                        cprint(f'  В РС [b]{ec_name}[/b] Источник не задан')
            else:                 
                    if ec_name != ec_name_old:
                        cprint(f'  В РС [b]{ec_name}[/b] задан источник  {hs1_name} ([b]{fr1}[/b])')
#            cprint(f'       в {cnt} узлах получен источник {hs2_name} ([b]{fr2}[/b])')

            cprint(f'      теперь в {cnt} узлах уточните Код РС, т.к. поток теплоносителя в них получен от источника {hs2_name} ([b]{fr2}[/b])')
            
            number += 1
            ec_name_old = ec_name




    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

