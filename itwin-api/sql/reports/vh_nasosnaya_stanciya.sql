-- gid6 excel2/sql2/Насосная станция.sql (шаблон gnc)
-- $1: фрагмент
SELECT n.id,
       n.externalnodename AS kod, ec.name AS uzel, es.name AS pr,
       n.geomarknodearea AS geod_z, n.geomarktoptube AS geodz, n.displaysign AS podp,
       n.calcpressflow AS pp_fact, n.calcpressret AS po_fact, n.archivechangedate AS date_archives, n.memo AS memo,
       n.nodename AS "Наименование", n.scheme AS "Схема", n.gpscoords AS "GPS координаты",
       n.inventnumber AS "Инвентарный номер", n.belongmagistralsite AS "Принадлежность участку МС",
       n.belongdistsite AS "Принадлежность РС", n.pipelinesign AS "Признак трубопровода",
       n.belonghn AS "Принадлежность тепловым сетям",
       ps.heighttubemark AS "Высотная отметка оси трубы", ps.heightareamark AS "Высотная отметка местности",
       ps.state AS sost
  FROM pumpstations ps
  JOIN nodes n ON n.id = ps.nodeid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN externalsigns es ON es.id = n.externalsignid
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
