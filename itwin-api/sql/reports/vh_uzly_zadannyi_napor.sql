-- gid6 excel2/sql2/Узлы с заданным напором.sql (шаблон gzn)
-- $1: фрагмент
SELECT n.id,
       ec.name AS kod, n.externalnodename AS uzel,
       spn.pressflow AS h_p, spn.pressret AS h_o, spn.kod_m, spn.uzel_m
  FROM setpressnodes spn
  JOIN nodes n ON n.id = spn.nodeid
  JOIN externalcodes ec ON ec.id = n.externalcodeid
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
