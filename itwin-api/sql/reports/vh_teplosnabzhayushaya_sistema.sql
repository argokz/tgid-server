-- gid6 excel2/sql2/Теплоснабжающая система.sql (шаблон gst, лист 1). Без фрагмента: heatsystem общая.
-- В исходнике пропущена запятая после t_vnew (t_vnew уходил в колонку tx), и колонки
-- съезжали относительно шаблона; здесь порядок колонок совпадает с шапкой gst.xls:
-- H конец/начало сезона, I/J холодная вода, K/L грунт, M/N наружный воздух, O утечки.
SELECT 'ТС' AS ts,
       hs.name, hs.nasel_point, sz.name AS season, hs.year,
       hs.t_or, hs.t_vr, hs.t_vnew,
       hs.tx, hs.tx_leto,
       hs.tg_god, hs.tg_god_leto,
       hs.tn_god, hs.tn_god_leto,
       hs.a
  FROM heatsystem hs
  LEFT JOIN seasons sz ON sz.id = hs.seasonid
 ORDER BY hs.id
