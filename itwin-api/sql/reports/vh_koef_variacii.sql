-- gid6 excel2/sql2/Коэффициенты вариации.sql (шаблон gkv)
-- $1: фрагмент (varcoefficients.fileid)
SELECT id,
       kodkv, kvpot, otoplz, otopln, ventil, kondiz, txz, txop, txoo, gvz, gvop,
       gvoo, ut, cher, diam
  FROM varcoefficients
 WHERE fileid = $1
 ORDER BY kodkv, id
