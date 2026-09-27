-- gid6 excel2/sql2/Расчетные схемы.sql (шаблон gst, лист 3)
-- $1: фрагмент (externalcodes.fileid)
SELECT pc.id,
       pc.name AS "Наименование",
       '' AS "Наименование2",
       ot.name AS "Объект РС",
       ec.name AS "Принадлежность магистрали",
       hs.name AS "Источник тепла",
       pc.responsibleperson AS "Ответственный"
  FROM externalcodes pc
  LEFT JOIN heatsources hs ON hs.id = pc.heatsourceid
  LEFT JOIN objecttypes ot ON ot.id = pc.objectid
  LEFT JOIN externalcodes ec ON ec.id = pc.belongmagistral
 WHERE pc.fileid = $1
 ORDER BY pc.name, pc.id
