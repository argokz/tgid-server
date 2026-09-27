-- gid6 excel2/sql2/OUT_Задвижки_ТП.sql: задвижки тепловых пунктов, типы узлов 7..11 (шаблон G_ZD, лист 6)
-- $1: фрагмент, $2: расчёт
SELECT t.*
  FROM ({{out_zadvizhki}}) t
 WHERE t._ni_type IN (7, 8, 9, 10, 11)
 ORDER BY t.kod_p, t.uzel_p, t.kod1, t.uzel1, t._line_id
