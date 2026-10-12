-- SRID 9998 — местная система базы (как в схеме десктопа sety/1/full_tgid.sql).
-- Координаты nodes/linesobj этой базы — в системе Астаны (9995), а 9998 был описан как Алматы,
-- поэтому ST_Transform(..., 4326) уводил объекты под Алматы.
-- Как было до правки: H:\tgid-backups\2026-10-09_astana\spatial_ref_sys_before.csv.
UPDATE spatial_ref_sys d
   SET srtext = replace(s.srtext, 'PROJCS["Astana"', 'PROJCS["Astana (local 9998)"'),
       proj4text = '+proj=tmerc +lat_0=0 +lon_0=72 +k=1 +x_0=40406 +y_0=-5671186 +ellps=krass +towgs84=24,-121,-76,0,0,0,0 +units=m +no_defs'
  FROM spatial_ref_sys s
 WHERE d.srid = 9998 AND s.srid = 9995;
