-- gid6 excel2/sql2/OUT_Задвижки_Секц.sql: секционирующие задвижки (шаблон G_ZD, лист 4)
-- $1: фрагмент, $2: расчёт
SELECT t.*
  FROM ({{out_zadvizhki}}) t
 WHERE t.name_zd = 'Секционирующая'
 ORDER BY t.kod_p, t.uzel_p, t.kod1, t.uzel1, t._line_id
