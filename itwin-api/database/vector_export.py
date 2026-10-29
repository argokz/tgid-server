"""Запись слоёв в файлы ГИС через GDAL (pyogrio): Shapefile (zip), GeoPackage, FlatGeobuf.

Общая часть выгрузок: сеть фрагментов (database/export_shp.py) и выборка по условиям
(database/network_select.py). GeoPackage — один файл со всеми слоями; FlatGeobuf — файл на слой
(несколько слоёв — zip); Shapefile — zip с .shp/.shx/.dbf/.prj/.cpg на слой. Координаты — WGS 84.
GeoParquet не пишется: в сборке GDAL у pyogrio нет драйвера Parquet, а pyarrow в API не ставили.
"""
from __future__ import annotations

import io
import os
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any

import geopandas as gpd


@dataclass(frozen=True)
class VectorFormat:
    key: str
    title: str
    driver: str
    extension: str
    media_type: str
    # все слои в одном файле (иначе — файл на слой, несколько — в zip)
    multi_layer: bool
    sidecars: tuple[str, ...] = ()


FORMATS: dict[str, VectorFormat] = {f.key: f for f in (
    VectorFormat("gpkg", "GeoPackage", "GPKG", "gpkg", "application/geopackage+sqlite3", True),
    VectorFormat("fgb", "FlatGeobuf", "FlatGeobuf", "fgb", "application/octet-stream", False),
    VectorFormat("shp", "Shapefile (zip)", "ESRI Shapefile", "shp", "application/zip", False,
                 ("shx", "dbf", "prj", "cpg")),
)}


class VectorExportError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def get_format(key: str) -> VectorFormat:
    fmt = FORMATS.get((key or "").lower())
    if fmt is None:
        raise VectorExportError(422, f"Формат — один из: {', '.join(FORMATS)}")
    return fmt


def frame(features: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    """GeoJSON-объекты (WGS 84) → GeoDataFrame; пусто — пустой слой."""
    if not features:
        return gpd.GeoDataFrame()
    gdf = gpd.GeoDataFrame.from_features(features)
    gdf.set_crs(epsg=4326, inplace=True, allow_override=True)
    return gdf


def write_layers(layers: dict[str, gpd.GeoDataFrame], fmt: VectorFormat, base_name: str, *,
                 allow_empty: bool = False) -> tuple[bytes, str, str]:
    """Слои → (содержимое, тип, имя файла). Пустые слои пропускаются; все пустые — 404
    (allow_empty — пустой zip, как прежняя выгрузка SHP)."""
    filled = {name: gdf for name, gdf in layers.items() if not gdf.empty}
    if not filled:
        if allow_empty:
            buf = io.BytesIO()
            zipfile.ZipFile(buf, "w").close()
            return buf.getvalue(), "application/zip", f"{base_name}.zip"
        raise VectorExportError(404, "Нечего выгружать: нет объектов с координатами")
    with tempfile.TemporaryDirectory() as tmpdir:
        if fmt.multi_layer:
            path = os.path.join(tmpdir, f"{base_name}.{fmt.extension}")
            for name, gdf in filled.items():
                gdf.to_file(path, layer=name, driver=fmt.driver, engine="pyogrio")
            with open(path, "rb") as fh:
                return fh.read(), fmt.media_type, f"{base_name}.{fmt.extension}"

        written: list[str] = []
        for name, gdf in filled.items():
            path = os.path.join(tmpdir, f"{name}.{fmt.extension}")
            gdf.to_file(path, driver=fmt.driver, engine="pyogrio")
            written += [f"{name}.{ext}" for ext in (fmt.extension, *fmt.sidecars)
                        if os.path.exists(os.path.join(tmpdir, f"{name}.{ext}"))]
        if len(filled) == 1 and not fmt.sidecars:
            with open(os.path.join(tmpdir, written[0]), "rb") as fh:
                return fh.read(), fmt.media_type, f"{base_name}.{fmt.extension}"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_name in written:
                zf.write(os.path.join(tmpdir, file_name), file_name)
        return buf.getvalue(), "application/zip", f"{base_name}.zip"
