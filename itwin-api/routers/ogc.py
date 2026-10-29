"""OGC API — Features (часть 1, Core + GeoJSON) поверх слоёв сети: /api/ogc/…

Подключение в QGIS: «Слой → Добавить слой → WFS / OGC API — Features», адрес <API>/api/ogc,
аутентификация — заголовок Authorization: Bearer <токен> (роль «просмотр»). Подробно:
database/ogc_features.py.
"""

from typing import Annotated, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from auth import AuthUser, require_roles
from database.connect import acquire_conn
from database.ogc_features import COLLECTIONS, DEFAULT_LIMIT, MAX_LIMIT, get_item, get_items, parse_bbox

router = APIRouter(tags=["ogc-features"])

Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
GEOJSON = "application/geo+json"
CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
CONFORMANCE = [
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30",
]
# Охват сети для метаданных коллекций: считается один раз на процесс
_extent: dict[str, list[float]] = {}


def _base(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/ogc"


def _link(href: str, rel: str, type_: str = "application/json", title: Optional[str] = None) -> dict:
    link = {"href": href, "rel": rel, "type": type_}
    if title:
        link["title"] = title
    return link


async def _network_extent() -> list[float]:
    if "bbox" not in _extent:
        async with acquire_conn() as conn:
            # без 0,1 % крайних точек: узлы с нулевыми координатами десктопа уводят охват в океан
            row = await conn.fetchrow(
                """SELECT percentile_disc(0.001) WITHIN GROUP (ORDER BY ST_X(p)) x1,
                          percentile_disc(0.001) WITHIN GROUP (ORDER BY ST_Y(p)) y1,
                          percentile_disc(0.999) WITHIN GROUP (ORDER BY ST_X(p)) x2,
                          percentile_disc(0.999) WITHIN GROUP (ORDER BY ST_Y(p)) y2
                     FROM (SELECT ST_Transform(shape, 4326) p FROM nodes
                            WHERE shape IS NOT NULL AND COALESCE(removed, 0) = 0) t""")
        _extent["bbox"] = [row["x1"], row["y1"], row["x2"], row["y2"]] if row and row["x1"] is not None \
            else [-180.0, -90.0, 180.0, 90.0]
    return _extent["bbox"]


def _collection_meta(base: str, cid: str, bbox: list[float]) -> dict:
    c = COLLECTIONS[cid]
    return {
        "id": cid,
        "title": c.title,
        "description": c.description,
        "itemType": "feature",
        "crs": [CRS84],
        "extent": {"spatial": {"bbox": [bbox], "crs": CRS84}},
        "links": [
            _link(f"{base}/collections/{cid}", "self"),
            _link(f"{base}/collections/{cid}/items", "items", GEOJSON, c.title),
        ],
    }


def _collection_or_404(cid: str) -> None:
    if cid not in COLLECTIONS:
        raise HTTPException(status_code=404, detail=f"Коллекции {cid!r} нет: {', '.join(COLLECTIONS)}")


@router.get("/api/ogc")
async def ogc_landing(request: Request, _: Viewer):
    """Стартовая страница OGC API — Features."""
    base = _base(request)
    return {
        "title": "ТГИД — слои инженерной сети",
        "description": "Участки, узлы, потребители, источники и задвижки теплосети города (OGC API — Features, GeoJSON, WGS84)",
        "links": [
            _link(base, "self"),
            _link(f"{base}/conformance", "conformance"),
            _link(f"{base}/collections", "data"),
            _link(str(request.base_url).rstrip("/") + "/openapi.json", "service-desc", "application/vnd.oai.openapi+json;version=3.0"),
        ],
    }


@router.get("/api/ogc/conformance")
async def ogc_conformance(_: Viewer):
    return {"conformsTo": CONFORMANCE}


@router.get("/api/ogc/collections")
async def ogc_collections(request: Request, _: Viewer):
    base = _base(request)
    bbox = await _network_extent()
    return {
        "links": [_link(f"{base}/collections", "self")],
        "collections": [_collection_meta(base, cid, bbox) for cid in COLLECTIONS],
    }


@router.get("/api/ogc/collections/{collection_id}")
async def ogc_collection(request: Request, collection_id: str, _: Viewer):
    _collection_or_404(collection_id)
    return _collection_meta(_base(request), collection_id, await _network_extent())


@router.get("/api/ogc/collections/{collection_id}/items")
async def ogc_items(
    request: Request,
    collection_id: str,
    _: Viewer,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    bbox: Optional[str] = Query(None, description="minLon,minLat,maxLon,maxLat (CRS84)"),
    fileid: Optional[int] = Query(None, ge=1, description="Фрагмент сети"),
):
    """Объекты коллекции (GeoJSON FeatureCollection); next — следующая страница."""
    _collection_or_404(collection_id)
    try:
        box = parse_bbox(bbox)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    async with acquire_conn() as conn:
        features = await get_items(conn, collection_id, bbox=box, fileid=fileid, limit=limit, offset=offset)
    url = f"{_base(request)}/collections/{collection_id}/items"
    query = {k: v for k, v in (("bbox", bbox), ("fileid", fileid)) if v is not None}
    links = [_link(f"{url}?{urlencode({**query, 'limit': limit, 'offset': offset})}", "self", GEOJSON)]
    if len(features) == limit:
        links.append(_link(f"{url}?{urlencode({**query, 'limit': limit, 'offset': offset + limit})}", "next", GEOJSON))
    if offset > 0:
        links.append(_link(f"{url}?{urlencode({**query, 'limit': limit, 'offset': max(0, offset - limit)})}", "prev", GEOJSON))
    return JSONResponse(
        {"type": "FeatureCollection", "numberReturned": len(features), "features": features, "links": links},
        media_type=GEOJSON,
    )


@router.get("/api/ogc/collections/{collection_id}/items/{feature_id}")
async def ogc_item(request: Request, collection_id: str, _: Viewer, feature_id: Annotated[int, Path(ge=1)]):
    _collection_or_404(collection_id)
    async with acquire_conn() as conn:
        feature = await get_item(conn, collection_id, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"Объекта {feature_id} в коллекции {collection_id} нет")
    url = f"{_base(request)}/collections/{collection_id}"
    feature["links"] = [_link(f"{url}/items/{feature_id}", "self", GEOJSON), _link(url, "collection")]
    return JSONResponse(feature, media_type=GEOJSON)
