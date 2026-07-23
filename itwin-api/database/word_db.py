async def get_defect_info(conn, defect_id: int) -> dict:
    sql = """
    SELECT 
        d.id,
        d.data_osmotra,
        tpov.name as tip_povrezhdenia,
        d.tsentrPovrezhdenia as tsentr_povrezhdenia,
        d.shirinaPovrezhdenia as shirina_povrezhdenia,
        d.vysotaPovrezhdenia as vysota_povrezhdenia,
        sostNP.name as sost_naruzhnoy,
        d.rasstoyanieDoPovrezhdeniyaNachKamery as rasstoyanie,
        d.data_nachala_remonta as vremya_nachala_rabot,
        d.data_zaversheniya_remonta as vremya_okonchaniya_rabot,
        es.name as povrezhdennyi_truboprovod
    FROM defect d
    LEFT JOIN tipPovrezhdenia tpov ON tpov.id = d.tipPovrezhdeniaID
    LEFT JOIN sostNaruzhnoiPoverkhnosti sostNP ON sostNP.id = d.sostNaruzhnoiPoverkhnostiID
    LEFT JOIN externalSigns es ON es.id = d.priznak_truboprovoda
    WHERE d.id = $1
    """
    row = await conn.fetchrow(sql, defect_id)
    return dict(row) if row else {}
