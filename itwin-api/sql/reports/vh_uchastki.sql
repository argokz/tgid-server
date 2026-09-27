-- gid6 excel2/sql2/Участки.sql: входные данные участков теплопроводов (шаблон gut / G_UT, лист 1)
-- $1: фрагмент (nodes.fileid)
SELECT l.id,
       CASE WHEN hps.pipesectstateidflow = 1 THEN '' ELSE 'закр' END AS key_ut_p,
       CASE WHEN hps.pipesectstateidret = 1 THEN '' ELSE 'закр' END AS key_ut_o,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2,
       n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       s.name AS standard,
       hps.tubescount AS truba,
       hps.pipesectlength AS dlina,
       hps.diameterinternal AS diametr,
       hps.tuberoughness AS scher,
       hps.localressum AS mestnoe,
       hps.locallosesshare AS dolja,
       vcf.kodkv AS kodkvp,
       vcr.kodkv AS kodkvo,
       l.hydrores,
       tt.name AS name_typ,
       hps.wallthickness AS tol,
       hps.heattestscoeff AS kti,
       hs.sourcename,
       org.name AS org_name
  FROM heatpipesections hps
  JOIN linesobj l ON l.id = hps.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  JOIN externalsigns es1 ON es1.id = n1.externalsignid
  JOIN externalsigns es2 ON es2.id = n2.externalsignid
  LEFT JOIN standards s ON s.id = hps.standardid
  LEFT JOIN varcoefficients vcf ON vcf.id = hps.varcoeffidflow
  LEFT JOIN varcoefficients vcr ON vcr.id = hps.varcoeffidret
  LEFT JOIN tubingtypes tt ON tt.id = hps.tubingtypeid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
  LEFT JOIN organizations org ON org.id = l.organizationid
 WHERE n1.fileid = $1 AND n1.internalnodeid IS NULL
   AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY ec1.name, n1.externalnodename, l.id
