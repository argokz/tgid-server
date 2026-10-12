-- 10.10.2026: слой GeoServer AstanaGIS:uzel отмечает узлы с внутренней схемой (знак камеры десктопа),
-- для этого в каждом тайле ищутся узлы схемы по nodes.internalnodeid. Откат: DROP INDEX nodes_internalnodeid_idx;
CREATE INDEX IF NOT EXISTS nodes_internalnodeid_idx ON public.nodes USING btree (internalnodeid) WHERE internalnodeid IS NOT NULL;
