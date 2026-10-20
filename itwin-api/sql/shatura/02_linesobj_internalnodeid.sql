-- Шатура: у linesobj нет колонки internalnodeid (в Алматы и Астане есть). Конвертер десктопа этой
-- версии её не создаёт, а API и веб отличают по ней участки внутренних схем от основной сети:
-- без неё данные привязки трассы (topology/snap-data), отключения, расчётные выборки падают
-- с «столбец l.internalnodeid не существует».
-- Участок внутренней схемы — тот, чей начальный узел в схеме (nodes.internalnodeid = узел-владелец).
-- Новые участки (десктоп, веб) заполняются триггером от начального узла. Идемпотентно.

ALTER TABLE linesobj ADD COLUMN IF NOT EXISTS internalnodeid integer;

UPDATE linesobj l
   SET internalnodeid = n.internalnodeid
  FROM nodes n
 WHERE n.id = l.nodeid1
   AND l.internalnodeid IS DISTINCT FROM n.internalnodeid
   AND n.internalnodeid IS NOT NULL
   AND l.internalnodeid IS NULL;

CREATE INDEX IF NOT EXISTS linesobj_internalnodeid_idx ON linesobj (internalnodeid);

CREATE OR REPLACE FUNCTION tg_linesobj_internalnodeid() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.internalnodeid IS NULL AND NEW.nodeid1 IS NOT NULL THEN
    SELECT n.internalnodeid INTO NEW.internalnodeid FROM nodes n WHERE n.id = NEW.nodeid1;
  END IF;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS linesobj_internalnodeid ON linesobj;
CREATE TRIGGER linesobj_internalnodeid
  BEFORE INSERT OR UPDATE OF nodeid1 ON linesobj
  FOR EACH ROW EXECUTE FUNCTION tg_linesobj_internalnodeid();
