"""ТУ balance summary by heat source (gid6 excel2/tu/tu.sql → PG)."""

from __future__ import annotations

from typing import Any, Optional

import asyncpg


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


async def get_technical_condition_balance(
    conn: asyncpg.Connection,
    *,
    year: Optional[int] = None,
) -> dict[str, Any]:
    """Свод по источникам: мощность источника + договорная + прирост ТУ + баланс.

    Эталон: gid6/gidr/excel2/tu/tu.sql.
    Стыковка котловых с `prisoedinennaya_nagruzka_istochnikov` — по `p.id2 = k.id`.
    """
    if year is None:
        year = await conn.fetchval(
            """
            SELECT EXTRACT(YEAR FROM data_vydachi_tu)::int
              FROM tehnicheskie_usloviya
             WHERE data_vydachi_tu IS NOT NULL
             ORDER BY data_vydachi_tu DESC
             LIMIT 1
            """
        )
    if year is None:
        return {"year": None, "capacity_year": None, "items": [], "totals": {}}

    capacity_year = await conn.fetchval(
        """
        SELECT god FROM prisoedinennaya_nagruzka_istochnikov
         WHERE god IS NOT NULL
         ORDER BY CASE WHEN god = $1 THEN 0 ELSE 1 END, god DESC
         LIMIT 1
        """,
        year,
    )

    rows = await conn.fetch(
        """
        WITH tu AS (
            SELECT
                COALESCE(NULLIF(BTRIM(istochnik), ''), '(без источника)') AS heat_source,
                COUNT(*)::int AS tu_count,
                COALESCE(SUM(prirost_nagruzki), 0)::float AS load_increase_total,
                COALESCE(SUM(v_tom_chisle_prirost_otoplenie), 0)::float AS heating_increase,
                COALESCE(SUM(v_tom_chisle_prirost_ventilyatsiya), 0)::float AS ventilation_increase,
                COALESCE(SUM(v_tom_chisle_prirost_gvs_maks), 0)::float AS gvs_max_increase,
                COALESCE(SUM(teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch), 0)::float
                    AS admitted_total,
                COALESCE(SUM(v_tom_chisle_otoplenie_po_aktu), 0)::float AS admitted_heating,
                COALESCE(SUM(v_tom_chisle_ventilyatsiya_po_aktu), 0)::float AS admitted_ventilation,
                COALESCE(SUM(v_tom_chisle_gvs_maks_po_aktu), 0)::float AS admitted_gvs_max
              FROM tehnicheskie_usloviya
             WHERE EXTRACT(YEAR FROM data_vydachi_tu)::int = $1
             GROUP BY 1
        ),
        nagr AS (
            SELECT
                COALESCE(NULLIF(BTRIM(heat_source), ''), '(без источника)') AS heat_source,
                SUM(q_ot)::float AS contract_heating,
                SUM(q_v)::float AS contract_ventilation,
                SUM(q_gvs)::float AS contract_gvs,
                SUM(q_ot + q_v + q_gvs)::float AS contract_total
              FROM (
                SELECT
                    istochnik_tepla AS heat_source,
                    COALESCE(nagruzka__otoplenie_, 0) AS q_ot,
                    COALESCE(nagruzka__ventilyatsiya_, 0) AS q_v,
                    COALESCE(nagruzka__gvs_, 0) AS q_gvs
                  FROM organizatsii
                UNION ALL
                SELECT
                    istochnik_tepla,
                    COALESCE(nagruzka_otoplenie, 0),
                    0,
                    COALESCE(nagruzka_gvs, 0)
                  FROM zhile
              ) raw
             GROUP BY 1
        ),
        ist AS (
            SELECT
                COALESCE(NULLIF(BTRIM(k.naimenovanie), ''), '(без источника)') AS heat_source,
                COALESCE(p.raspolagaemaya_moschnost_summarnaya, k.raspologaemaya_moschnost, 0)::float
                    AS available_power,
                COALESCE(p.prisoedinennaya_moschnost_otoplenie, k.otoplenie_istochnik, 0)::float
                    AS source_heating,
                COALESCE(p.prisoedinennaya_moschnost_ventilyatsiya, k.ventilyatsiya_istochnik, 0)::float
                    AS source_ventilation,
                COALESCE(p.prisoedinennaya_moschnost_gvs_maksimalnaya, k.gvs_istochnik, 0)::float
                    AS source_gvs,
                COALESCE(p.normativnye_teplovye_poteri, k.normativnye_teplovye_poteri, 0)::float
                    AS normative_losses,
                COALESCE(
                    p.ustanovlennaya_moschnost,
                    k.ustanovlennaya_moschnost,
                    COALESCE(p.prisoedinennaya_moschnost_otoplenie, k.otoplenie_istochnik, 0)
                    + COALESCE(p.prisoedinennaya_moschnost_ventilyatsiya, k.ventilyatsiya_istochnik, 0)
                    + COALESCE(p.prisoedinennaya_moschnost_gvs_maksimalnaya, k.gvs_istochnik, 0)
                )::float AS installed_power
              FROM kotelnye k
              LEFT JOIN prisoedinennaya_nagruzka_istochnikov p
                     ON p.id2 = k.id
                    AND ($2::int IS NOT NULL AND p.god = $2)
        ),
        keys AS (
            SELECT heat_source FROM tu
            UNION
            SELECT heat_source FROM ist
            UNION
            SELECT heat_source FROM nagr
        )
        SELECT
            k.heat_source,
            COALESCE(t.tu_count, 0)::int AS tu_count,
            COALESCE(i.installed_power, 0)::float AS installed_power,
            COALESCE(i.source_heating, 0)::float AS source_heating,
            COALESCE(i.source_ventilation, 0)::float AS source_ventilation,
            COALESCE(i.source_gvs, 0)::float AS source_gvs,
            COALESCE(i.available_power, 0)::float AS available_power,
            COALESCE(i.normative_losses, 0)::float AS normative_losses,
            COALESCE(n.contract_heating, 0)::float AS contract_heating,
            COALESCE(n.contract_ventilation, 0)::float AS contract_ventilation,
            COALESCE(n.contract_gvs, 0)::float AS contract_gvs,
            COALESCE(n.contract_total, 0)::float AS contract_total,
            COALESCE(t.heating_increase, 0)::float AS heating_increase,
            COALESCE(t.ventilation_increase, 0)::float AS ventilation_increase,
            COALESCE(t.gvs_max_increase, 0)::float AS gvs_max_increase,
            COALESCE(t.load_increase_total, 0)::float AS load_increase_total,
            COALESCE(t.admitted_heating, 0)::float AS admitted_heating,
            COALESCE(t.admitted_ventilation, 0)::float AS admitted_ventilation,
            COALESCE(t.admitted_gvs_max, 0)::float AS admitted_gvs_max,
            COALESCE(t.admitted_total, 0)::float AS admitted_total
          FROM keys k
          LEFT JOIN tu t ON t.heat_source = k.heat_source
          LEFT JOIN ist i ON i.heat_source = k.heat_source
          LEFT JOIN nagr n ON n.heat_source = k.heat_source
         ORDER BY k.heat_source
        """,
        year,
        capacity_year,
    )

    items: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        # Баланс по присоединённой нагрузке (как в tu.sql, без /1e6 — в PG уже Гкал/ч)
        d["balance_connected"] = (
            _f(d["available_power"])
            - _f(d["source_heating"])
            - _f(d["source_ventilation"])
            - _f(d["source_gvs"])
            - _f(d["normative_losses"])
            - _f(d["contract_total"])
        )
        # Баланс по присоединённой и перспективной (ТУ прирост)
        d["balance_with_prospective"] = (
            _f(d["available_power"])
            - _f(d["source_heating"])
            - _f(d["source_ventilation"])
            - _f(d["source_gvs"])
            - _f(d["normative_losses"])
            - _f(d["contract_total"])
            - _f(d["load_increase_total"])
        )
        items.append(d)

    # Источники без ТУ/мощности не шумим: оставляем строки с хоть какими-то данными
    items = [
        i
        for i in items
        if i["tu_count"]
        or i["available_power"]
        or i["contract_total"]
        or i["installed_power"]
        or i["load_increase_total"]
    ]

    keys = [
        "tu_count",
        "installed_power",
        "source_heating",
        "source_ventilation",
        "source_gvs",
        "available_power",
        "normative_losses",
        "contract_heating",
        "contract_ventilation",
        "contract_gvs",
        "contract_total",
        "heating_increase",
        "ventilation_increase",
        "gvs_max_increase",
        "load_increase_total",
        "admitted_heating",
        "admitted_ventilation",
        "admitted_gvs_max",
        "admitted_total",
        "balance_connected",
        "balance_with_prospective",
    ]
    totals = {k: sum(_f(i.get(k)) for i in items) for k in keys}
    totals["tu_count"] = int(totals["tu_count"])

    return {
        "year": year,
        "capacity_year": capacity_year,
        "items": items,
        "totals": totals,
        "notes": (
            None
            if capacity_year == year
            else (
                f"Мощности источников взяты за {capacity_year} "
                f"(в prisoedinennaya_nagruzka_istochnikov нет года {year})"
                if capacity_year
                else "Нет строк в prisoedinennaya_nagruzka_istochnikov — только ТУ/договорная"
            )
        ),
    }
