-- gid6 excel2/sql2/OUT_Дроссельные органы.sql: результаты расчёта дросселирования (шаблон G_DR, лист 2)
-- $1: фрагмент, $2: расчёт
SELECT ec.name AS kod, n.externalnodename AS uzel,
       d.b3, d.cxema,
       COALESCE(d.otoplz, 0) + COALESCE(d.otopln, 0) AS otopl,
       COALESCE(d.ventil, 0) + COALESCE(d.kondiz, 0) AS vent,
       COALESCE(d.gvpr, 0) + COALESCE(d.gvsm, 0) + COALESCE(d.gvps, 0) + COALESCE(d.gvpw, 0) AS gvz,
       d.gvop,
       d.gvoo,
       0 AS zero0,
       d.b4, d.b5, d.b6,
       d.diam_p, d.diam_o,
       d.b7, d.b8, d.b9, d.b11,
       d.b12, d.b13, d.b14, d.b15, d.b16, d.b17,
       d.b18, d.b19, d.b20, d.b21, d.b22, d.b23,
       d.b27, d.b28, d.b29, d.b30, d.b31, d.b32, d.b33, d.b34, d.b35, d.b36, d.b37, d.b38, d.b39, d.b40,
       d.b41, d.balans
  FROM dr_out d
  JOIN nodes n ON n.id = d.nodeid
  JOIN externalcodes ec ON ec.id = n.externalcodeid
 WHERE n.fileid = $1 AND d.calculationid = $2 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id
