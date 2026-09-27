-- gid6 excel2/sql2/Дроссели.sql: дроссельные устройства реальных потребителей (шаблон gpt, лист 2 / G_DR, лист 1)
-- $1: фрагмент
SELECT 'ДР' AS dr,
       ec.name AS kod, n.externalnodename AS uzel,
       rc.name AS name_building,
       rc.schemenum AS cxema,
       rc.parallheaterscountindep AS a19_co,
       rc.mixfactcoeff AS uf,
       rc.calcthrustloshs AS a7,
       rc.calcthrustlosah AS a8,
       rc.calcthrustlosac AS a9,
       rc.calcthrustlosflow AS a10,
       rc.calcthrustlosflowcirc AS a11,
       rc.calcthrustinwdo AS a12,
       tss.name AS a13,
       rc.diameterelevnozzle AS a14,
       rc.diameterthrotdiaph AS a15,
       tcs.name AS a17,
       rc.parallheaterscount1 AS a18, rc.parallheaterscount2 AS a19,
       rc.calcthrustlosheaters1 AS a22, rc.calcthrustlosheaters2 AS a23,
       pdvil.name AS pr_per_pd, rc.setpdonregulator AS p_per_pd
  FROM realconsumers rc
  JOIN nodes n ON n.id = rc.nodeid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN pdvalveinstalllocs pdvil ON pdvil.id = rc.pdvalveinstalllocid
  LEFT JOIN temperaturechartsigns tcs ON tcs.id = rc.temperchartsignid
  LEFT JOIN throtstagesigns tss ON tss.id = rc.throtstagesignid
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
