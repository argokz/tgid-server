import sql_obj

ms_rs = '''
select ms.id as msID, NULL as rsID, ms.opisanie_uchastka_ms as name
from uchastok_ms ms
UNION ALL
select NULL as msID, rs.id as rsID, rs.naimenovanie_uchastka_rs as name
from uchastok_rs rs
'''


#-------------------------------------------------------------------------------------

def get_xml_path(tab1, tab2, name, defect, prefix):
    s = f"""'{name}' ="
STUFF(
( SELECT concat(', ', rtt2.name) AS n FROM {defect} r2 
LEFT JOIN {tab1} rt2 ON r2.id=rt2.objID
LEFT JOIN {tab2} rtt2 ON rtt2.id=rt2.activityID
WHERE r2.id={prefix}.id 
FOR XML PATH('')
, TYPE
).value('.', 'NVARCHAR(MAX)'), 1, 1, '')"""
        
    return s;



#-------------------------------------------------------------------------------------

def node_name(node):
    
    return f'''case when {node}.nodeName is null or {node}.nodeName ='' then {node}.externalNodeName else {node}.nodeName end'''

#-------------------------------------------------------------------------------------

def node_name_sw(napr, node1, node2):
    
    n1 = node_name(node1)
    n2 = node_name(node2)

    return f'''case ({napr}) when 1 then ({n1}) else ({n2}) end'''

#-------------------------------------------------------------------------------------

def node_name_sw_1(ps_rn, napr, node1, node2):

    name = node_name_sw(napr, node1, node2)

    return f'''CASE {ps_rn} WHEN 1 THEN {name} else '' end'''


#-------------------------------------------------------------------------------------

def node_name_rn(ps_rn, node):
    name = node_name(node)
    return f'''CASE {ps_rn} WHEN 1 THEN {name} else '' end'''


#-------------------------------------------------------------------------------------

def make_lookups(tab_name, cols, join_tabs):

    joins = ''
    n_joint = 1
    obj_par2 = ''
    obj_par = ''

    for col in cols:
        jtab = join_tabs.get(col, None)
        if jtab:
             obj_par2 += f'\n, j_{n_joint}.name as {col}'
             joins += f'\nleft join {jtab} j_{n_joint} on j_{n_joint}.id={tab_name}.{col}'
             n_joint += 1
        else:
            obj_par2 += f',\n  {col}'
        
        obj_par += f',\n  {col}'

    return obj_par, obj_par2, joins


#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------

def ps_add2(ps2, tab, cols, join_tabs, join_dop, xml_tabs=dict(), line=True, node=True):

    node_param = ''
    node_join = ''

    
    if line:
        if node_param != '': node_param += ',\n'
        node_param += f'''
        {node_name('nn1')} as name1,
        {node_name('nn2')} as name2'''
    
    if node:
        if node_param != '': node_param += ',\n'
        node_param += f'''{node_name('n')} as kamera'''
        node_join = f''' left join nodes n on n.id=z.n_id '''


    if len(cols) > 0:
        joins = ''
        n_joint = 1

        obj_par = ''
        for col in cols:
            jtab = join_tabs.get(col, None)
            if jtab:
                col2 = col.replace('.', '_')

                obj_par += f'\n, j_{n_joint}.name as {col2}'
                if col.find('.') != -1:
                    joins += f'\nleft join {jtab} j_{n_joint} on j_{n_joint}.id={col}'
                else:
                    joins += f'\nleft join {jtab} j_{n_joint} on j_{n_joint}.id=z.{col}'
                n_joint += 1

            else:
                if col.find(' ') != -1 or col.find('.') != -1:
                    obj_par += f',\n  {col}'
                else:
                    obj_par += f',\n  z.{col}'


    q = f'''
---------------------------------------------------------------------------------------------
select 
{node_param}
{obj_par}

from {tab} z
join (values {ps2}) ps2(obj_id, n_id, l_id, ps_id, nodeID1, nodeID2, ord, ps_ord) on ps2.obj_id=z.id

left join nodes nn1 on nn1.id=ps2.nodeID1
left join nodes nn2 on nn2.id=ps2.nodeID2

join heatPipeSections hps on hps.lineID=ps2.l_id
join linesobj l on l.id=ps2.l_id


{node_join}
{joins}
{join_dop}

--order by ps2.ps_ord
--order by ps2.ps_ord, ps2.l_id, ps2.obj_id
-- десктоп 921fc9e (19.12.2024): строки по трубам в порядке id трубы
order by ps2.l_id, ps2.obj_id
--, p.ps_rn
---------------------------------------------------------------------------------------------
    '''


    return q;


#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------

def ps_add(ps2, cols, join_tabs, xml_tabs=dict(), line=True, node=True):
    q = ps2


    node_param = ''
    node_join = ''

    
    if line:
        if node_param != '': node_param += ',\n'
        node_param += f'''
--        {node_name_rn('ps_rn', 'nn1')} as name1,
--        {node_name_rn('ps_rn', 'nn2')} as name2
        {node_name('nn1')} as name1,
        {node_name('nn2')} as name2'''

    
    if node:
        if node_param != '': node_param += ',\n'
        node_param += f'''{node_name('n')} as kamera'''
        node_join = f''' left join nodes n on n.id=z.n_id '''


    if len(cols) > 0:
        joins = ''
        n_joint = 1

        obj_par = ''
        for col in cols:
            jtab = join_tabs.get(col, None)
            if jtab:
                obj_par += f'\n, j_{n_joint}.name as {col}'
                joins += f'\nleft join {jtab} j_{n_joint} on j_{n_joint}.id=z.{col}'
                n_joint += 1

            else:
                if col.find(' ') != -1:
                    obj_par += f',\n  {col}'
                    
#                elif not col in {'god_vvoda_v_ekspluatatsiyu', 'primechanie'}:
#                    obj_par += f',\n  nullif(z.{col}, 0) as {col}'
                else:
                    obj_par += f',\n  z.{col}'


    q = f'''
---------------------------------------------------------------------------------------------
select 
{node_param}
{obj_par}

from (
{ps2}
) z

join nodes nn1 on nn1.id=z.nodeID1
join nodes nn2 on nn2.id=z.nodeID2
{node_join}
{joins}

order by z.ps_ord, z.ps_rn
---------------------------------------------------------------------------------------------
    '''

    return q;

#-------------------------------------------------------------------------------------
# PostGIS-аналоги пространственных методов MS SQL, на которых написан десктопный паспорт.
# MS SQL: obj.shape.STPointN(1).STDistance(l.shape) < 0.3
# PostGIS: ST_DWithin(<первая точка obj.shape>, l.shape, 0.3) — использует GiST-индекс.

NEAR_TOLERANCE = 0.3


def first_point(geom):
    '''Первая точка геометрии как STPointN(1) в MS SQL: для линии — начало,
    для полигона — первая вершина внешнего кольца, для точки — сама точка.'''
    g = f'ST_GeometryN({geom}, 1)'
    return f'COALESCE(ST_PointN({g}, 1), ST_PointN(ST_ExteriorRing({g}), 1), {g})'


def obj_anchor(geom, use_first_point=False):
    return first_point(geom) if use_first_point else geom


def near(anchor, geom, other):
    '''anchor в пределах NEAR_TOLERANCE от other. Первое условие — по самой колонке geom
    (следует из второго): его может использовать GiST-индекс, выражение anchor — нет.'''
    cond = f'ST_DWithin({geom}, {other}, {NEAR_TOLERANCE})'
    if anchor != geom:
        cond += f' and ST_DWithin({anchor}, {other}, {NEAR_TOLERANCE})'
    return cond


#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------

def get_obj_ps(mark_line, mark_pts, obj, cols = [], hps_cols = (), use_first_point=False):
    '''Объекты obj, привязанные к трубам участка (в пределах NEAR_TOLERANCE).
    По умолчанию — расстояние от всей геометрии объекта, как в десктопе с 921fc9e (19.12.2024:
    ST_Distance(z.shape, l.shape) вместо ST_PointN(z.shape, 1)); use_first_point=True — от первой точки.'''
    anchor = obj_anchor('z.shape', use_first_point)
    obj_par = ''
    obj_par1 = ''
    obj_par2 = ''
    if len(cols) > 0:
        '''
        if col in hps_cols:
            obj_par = ',' + ','.join(col for col in cols if not ' ' in col)
        else:
            obj_par = ',z.' + ',z.'.join(col for col in cols if not ' ' in col)
            '''
        obj_par1 = ''
        obj_par2 = ''
        for col in cols:
            if not ' ' in col:
                obj_par2 += f',z.{col}'
                if col in hps_cols:
                    obj_par1 += f',hps.{col}'
                else:
                    obj_par1 += f',z.{col}'

    q = f'''
---------------------------------------------------------------------------------------------
select 
obj_id,
n_id,
l_id,
ps_id,
nodeID1,
nodeID2,
ord,
ps_ord
{obj_par2}

from (
select 
n.id as n_id,
z.id as obj_id,
l.id as l_id,

mark_line.pts as ps_id,
-- десктоп 921fc9e: узлы и порядок самой трубы, а не участка ПТС (каждая труба — своя строка)
l.nodeID1,
l.nodeID2,
mark_line.ord,
mark_line.ord AS ps_ord,

-- Объект относится к ближайшей трубе участка, камера — ближайший к нему узел.
-- В десктопе было два независимых ROW_NUMBER (rn по трубе, rn2 по узлу) и условие
-- rn=1 and rn2=1: при нескольких трубах и узлах рядом эти строки не совпадали и объект
-- выпадал из формы. Одна нумерация: труба, затем узел.
ROW_NUMBER() OVER (PARTITION BY z.id ORDER BY ST_Distance({anchor}, l.shape), l.id,
                   ST_Distance({anchor}, n.shape), n.id) AS rn,
1 AS rn2

{obj_par1}

from linesobj l
join nodes n1 on n1.id=l.nodeID1
JOIN heatPipeSections hps on hps.lineID=l.id

join (values {mark_line}) mark_line(ord, id, napr, pts) on mark_line.id=l.id
--join (values {mark_pts}) mark_pts(ord, id, nodeID1, nodeID2) on mark_pts.id=mark_line.pts


join {obj} z on {near(anchor, 'z.shape', 'l.shape')}
left join nodes n on n.removed=0 and n.fileID=n1.fileID and {near(anchor, 'z.shape', 'n.shape')}


where l.removed=0
) z  where rn=1 and rn2=1
---------------------------------------------------------------------------------------------
    '''

#    print(q)
#    exit(0)

    return q

#-------------------------------------------------------------------------------------


def get_obj_ps2(mark_line, mark_pts, obj, use_first_point=False):
    anchor = obj_anchor('z.shape', use_first_point)

    q = f'''
---------------------------------------------------------------------------------------------
select 
obj_id,
n_id,
l_id,
ps_id,
nodeID1,
nodeID2,
ord,
ps_ord

from (
select 
n.id as n_id,
z.id as obj_id,
l.id as l_id,

mark_line.pts as ps_id,
-- десктоп 921fc9e: узлы и порядок самой трубы, а не участка ПТС (каждая труба — своя строка)
l.nodeID1,
l.nodeID2,
mark_line.ord,
mark_line.ord AS ps_ord,

-- Объект относится к ближайшей трубе участка, камера — ближайший к нему узел.
-- В десктопе было два независимых ROW_NUMBER (rn по трубе, rn2 по узлу) и условие
-- rn=1 and rn2=1: при нескольких трубах и узлах рядом эти строки не совпадали и объект
-- выпадал из формы. Одна нумерация: труба, затем узел.
ROW_NUMBER() OVER (PARTITION BY z.id ORDER BY ST_Distance({anchor}, l.shape), l.id,
                   ST_Distance({anchor}, n.shape), n.id) AS rn,
1 AS rn2


from linesobj l
join nodes n1 on n1.id=l.nodeID1
JOIN heatPipeSections hps on hps.lineID=l.id

join (values {mark_line}) mark_line(ord, id, napr, pts) on mark_line.id=l.id
--join (values {mark_pts}) mark_pts(ord, id, nodeID1, nodeID2) on mark_pts.id=mark_line.pts


join {obj} z on {near(anchor, 'z.shape', 'l.shape')}
left join nodes n on n.removed=0 and n.fileID=n1.fileID and {near(anchor, 'z.shape', 'n.shape')}


where l.removed=0
) z  where rn=1 and rn2=1
order by ps_ord, l_id, obj_id
---------------------------------------------------------------------------------------------
    '''

    return q




#-------------------------------------------------------------------------------------


def get_ps2(mark_line, mark_pts, cols):
    '''
    Дает участки ПТС
    '''

    obj_par = ''
    if len(cols) > 0:
        obj_par = '  hps.' + ',\n  hps.'.join(cols) + ',\n   '

    
    q = f'''   
---------------------------------------------------------------------------------------------
select 
--hps.pipeSectionID as id,
mark_line.pts as id,
mark_line.ord,
-- десктоп 921fc9e: строка на трубу с её узлами (раньше — участок ПТС от узла до узла)
l.nodeID1,
l.nodeID2,
mark_line.ord AS ps_ord,

l.externalSignLineID,

{obj_par}

hps.tubingTypeID,
hps.tubeTypeID,
case when l.externalSignLineID in (1, 2, 4) then hps.diameterExternal else 0 end diamP,
case when l.externalSignLineID in (1, 3, 5) then hps.diameterExternal else  0 end diamO,

case when l.externalSignLineID in (1, 2, 4) then hps.wallThickness else 0 end tolP,
case when l.externalSignLineID in (1, 3, 5) then hps.wallThickness else 0 end tolO,

case when l.externalSignLineID in (1, 2, 4) then hps.pipeSectLength else 0 end lenP,
case when l.externalSignLineID in (1, 3, 5) then hps.pipeSectLength else 0 end lenO,

case when l.externalSignLineID in (1, 2, 4) then hps.pipeSectLength*power(hps.diameterInternal/1000, 2)*pi() else 0 end vP,
case when l.externalSignLineID in (1, 3, 5) then hps.pipeSectLength*power(hps.diameterInternal/1000, 2)*pi() else  0 end vO


from linesobj l
JOIN heatPipeSections hps on hps.lineID=l.id
join (values {mark_line}) mark_line(ord, id, napr, pts) on mark_line.id=l.id
--join (values {mark_pts}) mark_pts(ord, id, nodeID1, nodeID2) on mark_pts.id=mark_line.pts
where l.removed=0
    
---------------------------------------------------------------------------------------------
'''
    
    return q


#-------------------------------------------------------------------------------------

def group_ps1(q1, cols, gr_obj=set()):
    
#    gr_obj = gr_obj_par.split(',')

    gr_obj_par = ''

    if len(gr_obj) > 0:
        gr_obj_par = ',\n   z.' + ',\n  z.'.join(gr_obj)

    if len(cols) > 0:
#        cols = obj_par.split(',')

        param = ''
        param_gr = ''

        for col in cols:
#            print(col)
            if col.find(' ') != -1:
                pass
#                param += f',\n    {col}'
            elif col in gr_obj:
#                print('!!!')
#                exit(0)
                param += f',\n    z.{col}'
            else:
#                if col.find('cnt_') == 0:
                    param += f',\n    sum(z.{col}) as {col}'
#                else:
#                    param += f',\n    max(z.{col}) as {col}'
    
    q = f'''
---------------------------------------------------------------------------------------------
select ps_id, 
n_id,
ps_ord,
z.nodeID1,
z.nodeID2,

ROW_NUMBER() OVER (PARTITION BY ps_ord ORDER by ps_id) AS ps_rn
{param}

from (
{q1}
) z
group by 
    ps_id, ps_ord, 
    z.nodeID1,
    z.nodeID2,
    n_id 
    {gr_obj_par}
---------------------------------------------------------------------------------------------
    '''

    return q;


#-------------------------------------------------------------------------------------

if __name__ == "__main__":

#    mark_line = '(1, 6363,0),(2, 6366,1),(3, 6371,1),(4, 6372,1),(5, 6378,0),(6, 6316,1),(7, 6368,1),(8, 6369,1),(9, 6414,1),(10, 6370,1),(11, 6317,1),(12, 6345,1),(13, 6344,1),(14, 6343,1),(15, 6342,1),(16, 6339,0),(17, 6341,1),(18, 6367,1),(19, 3218669,0),(20, 6340,1),(21, 6264,1),(22, 6360,1),(23, 6361,1),(24, 6362,1),(25, 6364,1),(26, 6246,0),(27, 3218670,1),(28, 3218671,1),(29, 6265,0),(30, 6309,0),(31, 6249,1),(32, 6415,1),(33, 6416,1),(34, 6263,0),(35, 6359,1),(36, 6261,0),(37, 6262,1),(38, 6248,1),(39, 6258,0),(40, 6260,1),(41, 6237,1),(42, 6397,1),(43, 6347,1),(44, 6245,1),(45, 6244,1),(46, 6253,1),(47, 6348,1),(48, 6346,1),(49, 6254,1),(50, 6255,1),(51, 6256,1),(52, 6243,1),(53, 6238,1),(54, 6252,1),(55, 6349,1),(56, 6350,1),(57, 6358,1),(58, 6387,1),(59, 6251,1),(60, 6257,1),(61, 6403,0),(62, 6404,0),(63, 6250,1),(64, 6239,1),(65, 6240,1),(66, 6200,1),(67, 6201,1),(68, 6202,1),(69, 6351,1),(70, 6356,1),(71, 6241,1),(72, 6242,1),(73, 6357,1),(74, 6352,1),(75, 6353,1),(76, 6354,1),(77, 6355,1),(78, 6247,0),(79, 6259,0),(80, 33636190,0),(81, 33636619,1),(82, 33636100,1),(83, 33636244,1),(84, 33636047,1),(85, 33636091,1),(86, 33636392,1),(87, 33636192,1),(88, 33636038,1),(89, 33636440,1),(90, 33636101,1),(91, 33636603,1),(92, 33636037,1),(93, 33636058,1),(94, 33636489,1),(95, 33636386,1),(96, 33636700,1),(97, 33636531,1),(98, 33636090,1),(99, 33636439,1),(100, 33636143,0),(101, 33636193,1),(102, 33636096,1),(103, 33636191,1),(104, 33636488,1),(105, 33636605,1),(106, 33636530,1),(107, 33636298,1),(108, 33636299,1),(109, 33636526,1),(110, 33636346,1),(111, 33636215,1),(112, 33636254,1),(113, 33636266,1),(114, 33636351,1),(115, 33636153,1),(116, 33636300,1),(117, 33636309,1),(118, 33636048,1),(119, 33636049,1),(120, 33636712,1),(121, 33636347,1),(122, 33636604,1),(123, 33636426,0),(124, 33636699,0),(125, 33636427,0),(126, 33636203,0),(127, 33636046,0),(128, 33636695,0),(129, 33636523,0),(130, 33636522,0),(131, 33636443,1),(132, 33636385,0),(133, 33636609,0),(134, 33636475,0),(135, 33636477,1),(136, 33636476,0),(137, 33636702,0),(138, 33636103,0),(139, 33636430,1),(140, 33636142,0),(141, 33636689,1),(142, 33636297,1),(143, 33636384,1),(144, 33636474,1),(145, 33636701,1),(146, 33636521,1),(147, 33636393,1),(148, 33636625,1),(149, 33636243,1),(150, 33636102,1),(151, 33636490,1),(152, 33636614,1),(153, 33636532,1),(154, 33636624,1),(155, 33636615,1),(156, 33636438,1),(157, 33636054,0),(158, 33636711,1)'
#    mark_line = '(1, 183111,0),(2, 183820,1),(3, 183821,1),(4, 183533,0),(5, 183350,1),(6, 186544,0),(7, 183105,0),(8, 183351,1),(9, 183352,1),(10, 183688,1),(11, 183353,1),(12, 183535,0),(13, 183186,1),(14, 183187,1),(15, 183349,0),(16, 183110,1)'

#    q = get_f2_2_q(mark_line)

#    q = node_name_sw('qq', 'node1', 'node2')
#    print(q)
    pass

