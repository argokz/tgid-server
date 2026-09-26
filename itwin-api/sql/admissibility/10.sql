SELECT *
FROM (
WITH base AS (
  SELECT
      l.id,
      'Участок ' || ec1.name || ' ' || n1.externalnodename || ' '  || '-' || ec2.name || ' ' || n2.externalnodename AS "Наименование участка",
      hps.diameterCondit AS d_mm,

      utP.a10 AS v_pod,           -- скорость подача, м/с
      utO.a10 AS v_obr,           -- скорость обратка, м/с
      utP.a14 AS dp_pod_mmperm,   -- потери подача, мм вод. ст./м
      utO.a14 AS dp_obr_mmperm    -- потери обратка, мм вод. ст./м

  FROM linesobj l
  JOIN heatpipesections hps ON hps.lineID = l.id
  JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.removed = 0
  JOIN nodes n2 ON n2.id = l.nodeid2 AND n2.removed = 0

  LEFT JOIN (
      SELECT c.fileID, MAX(c.id) AS cid
      FROM CALCULATION c
      LEFT JOIN fragments fr ON fr.id = c.fileID
      GROUP BY c.fileID
  ) calc ON calc.fileID = n1.fileID

  LEFT JOIN UT_OUT utP ON utP.lineID = l.id AND utP.calculationID = calc.cid AND utP.externalSignLineID = 2
  LEFT JOIN UT_OUT utO ON utO.lineID = l.id AND utO.calculationID = calc.cid AND utO.externalSignLineID = 3
  LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  WHERE l.removed = 0
    AND n1.fileID = $1
    AND utP.id IS NOT NULL
    AND utO.id IS NOT NULL
),
t AS (
  SELECT
      id,
      "Наименование участка",
      d_mm,
      v_pod,
      v_obr,
      dp_pod_mmperm,
      dp_obr_mmperm,

      /* Нормы скорости как текст */
      CASE
        WHEN d_mm > 300               THEN '1.0–2.5'
        WHEN d_mm BETWEEN 100 AND 300 THEN '1.2–3.0'
        ELSE                               '1.5–3.5'
      END AS norm_v_pod,
      CASE
        WHEN d_mm > 300               THEN '0.8–2.0'
        WHEN d_mm BETWEEN 100 AND 300 THEN '1.0–2.5'
        ELSE                               '1.5–3.5'
      END AS norm_v_obr,

      /* Численные границы нормы скорости для удобства сравнений */
      CASE
        WHEN d_mm > 300               THEN 1.0
        WHEN d_mm BETWEEN 100 AND 300 THEN 1.2
        ELSE                               1.5
      END AS vmin_pod,
      CASE
        WHEN d_mm > 300               THEN 2.5
        WHEN d_mm BETWEEN 100 AND 300 THEN 3.0
        ELSE                               3.5
      END AS vmax_pod,

      CASE
        WHEN d_mm > 300               THEN 0.8
        WHEN d_mm BETWEEN 100 AND 300 THEN 1.0
        ELSE                               1.5
      END AS vmin_obr,
      CASE
        WHEN d_mm > 300               THEN 2.0
        WHEN d_mm BETWEEN 100 AND 300 THEN 2.5
        ELSE                               3.5
      END AS vmax_obr
  FROM base
),
final AS (
  SELECT
      id,
      "Наименование участка",
      d_mm AS "Диаметр, мм",

      v_pod AS "Скорость потока (подача), м/с",
      v_obr AS "Скорость потока (обратка), м/с",

      /* Ориентиры по скорости (текст) */
      norm_v_pod AS "Рекоменд. скорость (подача), м/с",
      norm_v_obr AS "Рекоменд. скорость (обратка), м/с",

      /* Анализ скорости (подача) */
      CASE
        WHEN v_pod < vmin_pod THEN 'Ниже рекомендуемого диапазона'
        WHEN v_pod > vmax_pod THEN 'Выше рекомендуемого диапазона'
        ELSE                        'В пределах нормы'
      END AS "Анализ скорости (подача)",

      /* Анализ скорости (обратка) */
      CASE
        WHEN v_obr < vmin_obr THEN 'Ниже рекомендуемого диапазона'
        WHEN v_obr > vmax_obr THEN 'Выше рекомендуемого диапазона'
        ELSE                        'В пределах нормы'
      END AS "Анализ скорости (обратка)",

      dp_pod_mmperm AS "Потери (подача), мм.вод.ст./м",
      dp_obr_mmperm AS "Потери (обратка), мм.вод.ст./м",

      /* Норма потерь справочно */
      '8–10 (при V∈[1.5;3.5])' AS "Допуст. потери (мм.вод.ст./м)",

      /* Анализ потерь (подача): завязан на скорость */
      CASE
        WHEN v_pod < 1.5 THEN 'Ниже рекомендуемого диапазона'
        WHEN v_pod > 3.5 THEN 'Выше рекомендуемого диапазона'
        ELSE
          CASE
            WHEN dp_pod_mmperm < 8  THEN 'Ниже рекомендуемого диапазона'
            WHEN dp_pod_mmperm > 10 THEN 'Выше рекомендуемого диапазона'
            ELSE                        'В пределах нормы'
          END
      END AS "Анализ потерь (подача)",

      /* Анализ потерь (обратка): завязан на скорость */
      CASE
        WHEN v_obr < 1.5 THEN 'Ниже рекомендуемого диапазона'
        WHEN v_obr > 3.5 THEN 'Выше рекомендуемого диапазона'
        ELSE
          CASE
            WHEN dp_obr_mmperm < 8  THEN 'Ниже рекомендуемого диапазона'
            WHEN dp_obr_mmperm > 10 THEN 'Выше рекомендуемого диапазона'
            ELSE                        'В пределах нормы'
          END
      END AS "Анализ потерь (обратка)"
  FROM t
)
SELECT *
FROM final
WHERE
  /* показываем строки, где есть хотя бы одно отклонение */
  ('В пределах нормы' NOT IN ("Анализ скорости (подача)", "Анализ скорости (обратка)")
   OR 'В пределах нормы' NOT IN ("Анализ потерь (подача)", "Анализ потерь (обратка)"))
ORDER BY id
) src
