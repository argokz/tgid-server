
def getPts(id, type, fragments):
    q = f"""
    
    SELECT
    distinct
    t.tblName,
    t.beginNode,
    t.endNode,
    t.externalID,
    t.armatureType,
    t.designType,
    t.constructionType,
    t.material,
    t.diametr,
    1 as 'count_obj',
    t.orderID,
    t.externalID2,
    t.purposeType,
    IIF( t.min_node1 < t.min_node2, t.beginNode, t.endNode) as pavilion,
    t.id as 'id_obj',
    t.pipeSectionID,
    t.externalLineStr,
    t.ms,
    t.rs
    FROM (
        SELECT
            IIF (n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ',n1.externalNodeName, n1.nodeName) as 'beginNode',
            IIF (n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ',n2.externalNodeName, n2.nodeName) as 'endNode',
            l.shape.STDistance(obj.shape.STPointN(1)) as length,
            MIN(l.shape.STDistance(obj.shape.STPointN(1))) OVER(PARTITION BY obj.id ) AS min_len,
            MIN(obj.shape.STPointN(1).STDistance(n1.shape)) OVER(PARTITION BY obj.id ) AS min_node1,
            MIN(obj.shape.STPointN(1).STDistance(n2.shape)) OVER(PARTITION BY obj.id ) AS min_node2,
            srt.orderID,
            obj.tblName,
            l.externalSignLineID as 'externalID',
            obj.priznak_truboprovoda as 'externalID2',
            arm_t.name as 'armatureType',
            des_t.name as 'designType',
            con_t.name as 'constructionType',
            mat_t.name as 'material',
            pur_t.name as 'purposeType',
            --n2.nodeName as 'pavilion',
            --nn.nodeName as 'pavilion',
            obj.diametr,
            obj.id,
            hps.magistralSite as 'ms',
            hps.distSite as 'rs',
            pss.id AS pipeSectionID,
            el.name as 'externalLineStr'
        FROM vtPtsAll obj
        LEFT JOIN linesobj l ON l.shape.STDistance(obj.shape.STPointN(1)) < 0.3
        LEFT JOIN externalSignLine el ON el.id = obj.priznak_truboprovoda
        LEFT JOIN heatPipeSections hps ON hps.lineID=l.id
        LEFT JOIN pipeSections pss ON pss.id=hps.pipeSectionID
        LEFT JOIN sortLinesForUchastok srt ON hps.pipeSectionID = srt.pipeSectionID
        LEFT JOIN purposeTypes pur_t ON pur_t.id = obj.purposeTypesID
        LEFT JOIN armatureTypes arm_t ON arm_t.id = obj.armatureTypesID
        LEFT JOIN designTypes des_t ON des_t.id = obj.designTypesID
        LEFT JOIN constructionTypes con_t ON con_t.id = obj.constructionTypesID
        LEFT JOIN materialTypes mat_t ON mat_t.id = obj.materialTypesID
        LEFT JOIN nodes n1 ON n1.id = pss.nodeID1
        LEFT JOIN nodes n2 ON n2.id = pss.nodeID2
        left join externalCodes ec1 ON ec1.id = n1.externalCodeID
        left join externalCodes ec2 ON ec2.id = n2.externalCodeID
        --LEFT JOIN nodes nn ON nn.shape.STDistance(obj.shape.STPointN(1)) < 3
        WHERE NOT l.shape.STDistance(obj.shape.STPointN(1)) IS NULL and n1.fileID in (select value from fn_split_string({fragments}, ',') )
        AND ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) )
        and (
            ({type} = 'ms' and hps.magistralSite = {id})
            or ({type} = 'rs' and hps.distSite = {id})
            or ({type} = 'pipe' and pss.id = {id})
            or ({type} = 'all')
            or ({type} = 'obj' and obj.id = {id}) )
        and l.externalSignLineID is not NULL
    ) as t
where   t.length = t.min_len
"""

    return q
