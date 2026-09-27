-- gid6 excel2/sql2/OUT_Задвижки_НС.sql: задвижки насосных станций (шаблон G_ZD, лист 5)
-- $1: фрагмент, $2: расчёт
SELECT t.*
  FROM ({{out_zadvizhki}}) t
 WHERE EXISTS (SELECT 1 FROM pumpstations ps WHERE ps.nodeid = t._ni_id)
 ORDER BY t.kod_p, t.uzel_p, t.kod1, t.uzel1, t._line_id
