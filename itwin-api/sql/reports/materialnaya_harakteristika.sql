-- gid6 excel2/sql2/Материальная характеристика.sql: материальная характеристика и ёмкость участков.
-- В десктопе нет ни шаблона, ни пункта меню (.lst); шапка берётся из каталога.
-- $1: фрагмент
SELECT pssf.name AS pipesectionstate,
       ec1.name AS externalcode1,
       n1.externalnodename AS externalnodename1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS externalsignline1,
       ec2.name AS externalcode2,
       n2.externalnodename AS externalnodename2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS externalsignline2,
       tt.name AS tubingtype,
       EXTRACT(YEAR FROM hps.firstpicdatehp)::int AS firstpicdatehp,
       hps.picdatecapital,
       hps.diameterexternal,
       hps.pipesectlength,
       CASE WHEN hps.tubingtypeid IN (4) AND l.externalsignlineid IN (1, 2, 4)
            THEN hps.pipesectlength * hps.diameterinternal / 1000 ELSE 0 END AS matcharflow,
       CASE WHEN hps.tubingtypeid IN (4) AND l.externalsignlineid IN (1, 3, 4)
            THEN hps.pipesectlength * hps.diameterinternal / 1000 ELSE 0 END AS matcharret,
       CASE WHEN hps.tubingtypeid NOT IN (4) THEN hps.pipesectlength * hps.diameterinternal / 1000 ELSE 0 END
         * CASE WHEN l.externalsignlineid IN (1) THEN 2 ELSE 1 END AS matcharunder,
       hps.pipesectlength * power(hps.diameterinternal / 1000, 2) * pi() / 4
         * CASE WHEN l.externalsignlineid IN (1) THEN 2 ELSE 1 END AS capacity,
       org.name AS organization
  FROM heatpipesections hps
  JOIN linesobj l ON l.id = hps.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  LEFT JOIN pipesectionsstates pssf ON pssf.id = hps.pipesectstateidflow
  LEFT JOIN tubingtypes tt ON tt.id = hps.tubingtypeid
  LEFT JOIN organizations org ON org.id = l.organizationid
 WHERE n1.fileid = $1 AND n1.internalnodeid IS NULL AND l.removed = 0
 ORDER BY ec1.name, n1.externalnodename, l.id
