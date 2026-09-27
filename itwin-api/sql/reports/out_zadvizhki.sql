-- gid6 excel2/sql2/OUT_Задвижки1.sql: результаты расчёта по задвижкам внутренних схем (шаблон G_ZD, лист 2).
-- Колонки с «_» служебные: в Excel не пишутся, по ним фильтруют варианты
-- (out_zadvizhki_upr / _sekc / _ns / _tp).
-- $1: фрагмент, $2: расчёт
SELECT eci.name AS kod_p, ni.externalnodename AS uzel_p,
       esi.name AS pr_p,
       '' AS name_soder,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE z.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2,
       n2.externalnodename AS uzel2,
       CASE z.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       z.a8 AS name_soder_zd,
       d.dispatcherswitch AS name_zd,
       das.name AS sost,
       d.partdempopen,
       z.a9,
       z.a10, z.a11, z.a12, z.a13, z.a14, z.a15,
       ni.id AS _ni_id,
       ni.nodetypeid AS _ni_type,
       l.id AS _line_id
  FROM zd_out z
  JOIN linesobj l ON l.id = z.lineid
  JOIN dampers d ON d.lineid = l.id
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  JOIN externalsignline esl ON esl.id = z.externalsignlineid
  JOIN nodes ni ON ni.id = n1.internalnodeid
  JOIN damperarmaturestates das ON das.id = d.damperarmaturestateid
  JOIN externalcodes eci ON eci.id = ni.externalcodeid
  JOIN externalsigns esi ON esi.id = ni.externalsignid
 WHERE n1.fileid = $1 AND z.calculationid = $2 AND l.removed = 0
 ORDER BY eci.name, ni.externalnodename, ec1.name, n1.externalnodename, l.id, z.externalsignlineid
