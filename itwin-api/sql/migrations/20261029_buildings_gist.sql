-- 29.10.2026: пространственные индексы слоёв зданий. Тайл зданий (martin tgid_mvt_zdaniya_2, GeoServer,
-- запекание PMTiles) ищет контуры по shape && охват тайла; без GiST — полный проход по таблице
-- (в Алматы 187 тыс. контуров, 0,15–0,6 с на тайл). Только добавление индекса: десктоп его не замечает.
-- Таблицы зданий есть не в каждой базе — индекс создаётся там, где есть таблица с колонкой shape.
-- Откат: DROP INDEX zdaniya_2_shape_gist; DROP INDEX zdaniya_tu_shape_gist;
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['zdaniya_2', 'zdaniya_tu'] LOOP
        IF EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = t AND column_name = 'shape')
           AND NOT EXISTS (SELECT 1 FROM pg_indexes
                            WHERE schemaname = 'public' AND tablename = t AND indexdef ILIKE '%USING gist (shape)%') THEN
            EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON public.%I USING gist (shape)', t || '_shape_gist', t);
        END IF;
    END LOOP;
END
$$;
