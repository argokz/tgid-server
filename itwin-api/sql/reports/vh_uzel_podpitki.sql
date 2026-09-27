-- gid6 excel2/sql2/Узел подпитки.sql (шаблон gup)
-- $1: фрагмент
SELECT n.id,
       ec.name AS kod, n.externalnodename AS uzel, es.name AS pr,
       rn.diameterinternal AS diam, rn.refillexpend AS r_p, rn.wdo AS r_v, rn.refillloss AS r_ut,
       rn.watervolup AS urov_v, rn.watervoldown AS urov_n, rn.watervolupset AS urov_z,
       rn.potscount AS kol, rn.potssumvol AS v_sum, rn.potworkingsign AS prz_r,
       rn.chargeexpend AS r_z, rn.dischargeexpend AS r_r, rn.setpressret AS napor, n.fileid
  FROM refillnodes rn
  JOIN nodes n ON n.id = rn.nodeid
  JOIN externalcodes ec ON ec.id = n.externalcodeid
  JOIN externalsigns es ON es.id = n.externalsignid
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
