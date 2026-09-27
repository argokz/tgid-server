-- gid6 excel2/sql2/Узлы.sql: узлы расчётных схем без нагрузки (шаблон gus)
-- $1: фрагмент
SELECT n.id,
       ec.name AS kod,
       n.externalnodename AS uzel,
       es.name AS pr,
       n.geomarknodearea AS geod_zemli,
       n.geomarktoptube AS geodz,
       nt.name AS name_typ
  FROM nodes n
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN externalsigns es ON es.id = n.externalsignid
  LEFT JOIN nodetypes nt ON nt.id = n.nodetypeid
 WHERE n.fileid = $1 AND n.internalnodeid IS NULL AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
