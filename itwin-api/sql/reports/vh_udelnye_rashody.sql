-- gid6 excel2/sql2/Удельные расходы.sql (шаблон gur)
-- $1: фрагмент (specexpends.fileid)
SELECT id,
       specexpendid AS kodur,
       calchldep AS otoplz,
       calchlindep AS otopln,
       calchlventil AS ventil,
       calcexpendhwopen AS gvo,
       circhlosopen AS rez,
       avghlgvscloseparall AS gvpr,
       avghlgvsclosemix AS gvsm,
       avghlgvscloseconseq AS gvps,
       avghlgvsclosepreon AS gvpw,
       avghlgvsclosesummer AS gvz_leto,
       avghlgvsopensummer AS gvo_leto,
       hsourcecode AS kod_ist
  FROM specexpends
 WHERE fileid = $1
 ORDER BY specexpendid, id
