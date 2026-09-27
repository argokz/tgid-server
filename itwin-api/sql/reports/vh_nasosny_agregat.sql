-- gid6 excel2/sql2/Насосный агрегат.sql (шаблон gns). В десктопе запрос брал строки из NS_OUT
-- (результаты расчёта) и не совпадал с колонками входного шаблона; здесь колонки шаблона
-- заполняются из исходной таблицы pumps. Станция: внутренний узел, в схеме которого стоит насос.
-- $1: фрагмент
SELECT p.id,
       eci.name AS kod_p, ni.externalnodename AS uzel_p, ni.nodename AS name_p, esi.name AS pr_p,
       p.number AS nomer,
       st.name AS sost,
       ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       p.thrust AS napor,
       p.r0, p.r1, p.r2,
       sp.h_min, sp.q_min, sp.h_max, sp.q_max,
       p.parallagregcount AS kol,
       sp.tip_nas,
       hs.sourcename
  FROM pumps p
  JOIN linesobj l ON l.id = p.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON eci.id = ni.externalcodeid
  LEFT JOIN externalsigns esi ON esi.id = ni.externalsignid
  LEFT JOIN states st ON st.id = p.stateid
  LEFT JOIN standardpumps sp ON sp.id = p.standardpumpid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, p.number, p.id
