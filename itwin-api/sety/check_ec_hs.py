import sys
import pyodbc

from sety.any.colors import cprint
from sety.any.colors import nbsp


def check_ec_hs(conn, fileID):

    q = f'''
select distinct ec.id, ec.name
from externalcodes ec
join nodes n on n.externalcodeid =ec.id
left join generalizedconsumers gc on gc.nodeid=n.id
left join realconsumers rc on rc.nodeid=n.id
where n.fileid={fileID}
and n.removed=0
and (not rc.id is null or not gc.id is null)
order by ec.name
    '''


    q = f'''
select distinct ec.id, ec.name

from externalcodes ec
join nodes n on n.externalcodeid =ec.id
left join generalizedconsumers gc on gc.nodeid=n.id
left join realconsumers rc on rc.nodeid=n.id
left join heatsources hs on hs.id=ec.heatSourceID
left join nodes ns on ns.id=hs.nodeid
where
n.fileid={fileID}
and n.removed=0
and (not rc.id is null or not gc.id is null)
and (
    hs.id is null
    or ns.id is null
    or ns.removed <> 0
)
order by ec.name
    '''



    number = 0


    try:
        cursor = conn.cursor()
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            id, name = row

            if number == 0:
                cprint(f'Не указан Источник тепла в Расчетных схемах, Укажите, т.к. расчет теплогидравлического режима без этого невозможен:', color='red')
                    
            cprint(nbsp(f'   {name}'), color='red')
            number += 1

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)


    return number
