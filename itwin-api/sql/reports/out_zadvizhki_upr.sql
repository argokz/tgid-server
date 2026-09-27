-- gid6 excel2/sql2/OUT_Задвижки_Упр.sql: управляющие задвижки (шаблон G_ZD, лист 3)
-- $1: фрагмент, $2: расчёт
SELECT t.*
  FROM ({{out_zadvizhki}}) t
 WHERE t.name_zd = 'Управляющая'
 ORDER BY t.kod_p, t.uzel_p, t.kod1, t.uzel1, t._line_id
