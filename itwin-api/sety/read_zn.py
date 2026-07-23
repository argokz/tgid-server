import pyodbc
import sys

ec_ist = dict()



def read_zn0(conn, fileID):


    q = f'''

select distinct
ec.id, max(usP.ist)

FROM setPressNodes zn

join nodes n on n.id=zn.nodeid
join externalCodes ec on ec.id=n.externalCodeID

join (
select n0.id, ec0.name as kod, n0.externalnodename as name , n0.fileID
from  nodes n0
join externalCodes ec0 on ec0.id=n0.externalCodeID
) n0 on n0.kod = ec.name and n0.name = n.externalnodename

LEFT JOIN 
(
SELECT 
c.fileID,
max(c.id) AS cid
FROM CALCULATION c
LEFT JOIN fragments fr ON fr.id=c.fileID
GROUP BY c.fileID
) calc ON calc.fileID=n0.fileid
JOIN US_OUT usP ON usP.nodeID=n0.id AND usP.externalSign=1 and usP.calculationid=cid
where n.fileid={fileID}
group by ec.id 

'''

    try:
        cursor = conn.cursor()
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            ec_id, ist = row
#            print(row)

            ec_ist[ec_id] = ist

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

#    print(ec_ist)
