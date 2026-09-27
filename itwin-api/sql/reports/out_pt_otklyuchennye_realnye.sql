-- gid6 excel2/sql2/OUT_PT_Отключенные_реальные.sql: то же, только реальные потребители
-- (шаблон G_DR, лист 3). В исходнике колонки съехали (fileID и «ec.name uzel»); здесь колонки
-- совпадают с шапкой листа, как у OUT_PT_Отключенные.
-- $1: фрагмент, $2: расчёт
SELECT t.*
  FROM ({{out_pt_otklyuchennye}}) t
 WHERE t.prizn = ' '
 ORDER BY t.kod, t.uzel, t.id
