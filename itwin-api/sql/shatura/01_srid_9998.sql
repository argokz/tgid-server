-- SRID 9998 — местная система базы (как в схеме десктопа sety/1/full_tgid.sql).
-- Координаты nodes/linesobj базы Шатуры — Web Mercator (EPSG:3857: x ≈ 4,40 млн, y ≈ 7,47 млн м —
-- 39,54° в. д., 55,55° с. ш.), а 9998 описан как Алматы, поэтому ST_Transform(..., 4326) уводил
-- объекты в Тихий океан. Откат: описание Алматы — sql/astana нет, взять из almatygid (srid 9998).
UPDATE spatial_ref_sys d
   SET srtext = replace(s.srtext, 'PROJCS["WGS 84 / Pseudo-Mercator"', 'PROJCS["Shatura (local 9998 = EPSG:3857)"'),
       proj4text = s.proj4text
  FROM spatial_ref_sys s
 WHERE d.srid = 9998 AND s.srid = 3857;
