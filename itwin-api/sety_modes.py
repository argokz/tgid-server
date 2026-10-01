"""Режимы запуска sety так, как их собирает десктоп gid8 (gidview/gidr_calc.cpp).

* plan («Плановый…», getDoItDr + ui/Param1Dialog): воркер добавляет -dross
  (в sety это g_is_avar=False). Потребители — нагрузки, опционально -tg, теплопотери,
  дроссельные органы (-dross_yes), -iter, -trtp.
* emergency («Фактический…», getDoIt + ui/Param2Dialog; в коде помечен «Фактический /
  Аварийный»): -dross НЕ передаётся → g_is_avar=True. sety не читает realConsumers/
  generalizedConsumers как нагрузки, а моделирует гидравлические тракты потребителей
  (дроссели, элеваторы, отопительные приборы) — детализированно или эквивалентно (-a);
  результаты по потребителям пишет out_PT_OUT2/out_PT_OUT3, dr_out переносится на расчёт.
  Отдельного списка «отключаемых элементов» у десктопа нет: аварийное состояние сети
  задаётся текущим состоянием объектов в БД (задвижки и т.п.).
* «по списку» (onDoItListDr / onDoItList): тот же набор флагов для каждого выбранного
  фрагмента, фрагменты считаются по очереди (десктоп пишет .bat построчно).

Строка аргументов собирается только из типизированной модели и дополнительно проходит
белый список воркера (worker.validate_sety_params).
"""

from __future__ import annotations

import re
import shlex
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_LIST_FRAGMENTS = 50

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _num(value: float) -> str:
    """Число без лишних нулей (-25.0 → -25), как QString::arg у десктопа."""
    return f"{value:g}"


class SetyRunRequest(BaseModel):
    mode: Literal["plan", "emergency"] = "plan"
    fragment_ids: list[int] = Field(..., min_length=1, max_length=MAX_LIST_FRAGMENTS)
    name: Optional[str] = Field(None, max_length=200)
    tn: float = Field(-32, ge=-60, le=50, description="Температура наружного воздуха, °C")

    # «Настройка» (ui/ParamDialog): формула сопротивлений и плотности — общие для режимов
    sopr: int = Field(0, ge=0, le=4, description="0 ТГид, 1 Альтшуль, 2 Никурадзе, 3 Шифринсон, 4 Колбрук-Уайт")
    ro_p: float = Field(0.975, gt=0, le=2)
    ro_o: float = Field(0.975, gt=0, le=2)
    ro_temp: bool = False

    char_sety: bool = False       # Количественные характеристики сети
    mag_fragment: bool = False    # Магистральный фрагмент
    use_kv: bool = True           # С учётом коэффициентов вариации (иначе -no_kv)
    veter: bool = False           # Учитывать ветер
    avtomat: bool = False         # Расчёт автоматизированных потребителей

    # Только плановый (Param1Dialog)
    tg: bool = False              # Расходы по температурному графику (иначе по удельным)
    teplopoter: bool = True       # С учётом тепловых потерь (при tg)
    uf_calc: bool = False         # С учётом рассчитанных коэффициентов смешения
    save_uf_new: bool = False     # Запись коэффициентов смешения (при tg)
    teplovyd: bool = True         # С учётом внутренних тепловыделений
    dross_yes: bool = False       # Расчёт дроссельных органов и запись сопротивлений
    save_po: bool = False         # Запись нагрузок и потерь в обобщённый потребитель
    utechki: bool = False         # Учёт нормируемых утечек
    trtp: int = Field(0, ge=0, le=2, description="tн расчёта теплопотерь: 0 расчётная, 1 среднесезонная, 2 текущая")
    iter: int = Field(20, ge=1, le=1000, description="Итераций для расчёта регуляторов")

    # Только аварийный/фактический (Param2Dialog)
    consumer_resistance: Literal["detailed", "equivalent"] = "equivalent"  # -a при equivalent
    leto: bool = False            # Летний режим
    save_leto: bool = False       # Запись летних сопротивлений в обобщённый потребитель

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if _CONTROL_CHARS.search(value):
            raise ValueError("Наименование расчёта не должно содержать управляющих символов")
        if value.startswith("-"):
            raise ValueError("Наименование расчёта не может начинаться с «-»")  # argparse примет за флаг
        return value or None

    @field_validator("fragment_ids")
    @classmethod
    def _unique_fragments(cls, value: list[int]) -> list[int]:
        if any(v < 1 for v in value):
            raise ValueError("Номер фрагмента должен быть положительным")
        if len(set(value)) != len(value):
            raise ValueError("Фрагменты в списке не должны повторяться")
        return value

    @model_validator(mode="after")
    def _mode_consistency(self) -> "SetyRunRequest":
        if self.mode == "plan":
            wrong = [f for f in ("leto", "save_leto") if getattr(self, f)]
            if wrong:
                raise ValueError(f"Только для аварийного (фактического) режима: {', '.join(wrong)}")
            if not self.tg and (self.save_uf_new or not self.teplopoter):
                raise ValueError("Теплопотери и запись коэффициентов смешения — только при расчёте по температурному графику")
        else:
            wrong = [f for f in ("tg", "uf_calc", "save_uf_new", "dross_yes", "save_po", "utechki")
                     if getattr(self, f)]
            if wrong:
                raise ValueError(f"Только для планового режима: {', '.join(wrong)}")
            if not self.teplovyd:
                raise ValueError("Только для планового режима: teplovyd")
            if self.save_leto and not self.leto:
                raise ValueError("Запись летних сопротивлений доступна только в летнем режиме")
            if self.leto and self.consumer_resistance == "equivalent":
                # Param2Dialog: летний режим переключает на детализированное сопротивление
                raise ValueError("Летний режим считается только с детализированным сопротивлением потребителей")
        return self

    @property
    def is_list(self) -> bool:
        return len(self.fragment_ids) > 1

    @property
    def dross(self) -> bool:
        return self.mode == "plan"


def build_sety_args(req: SetyRunRequest, user_gid: str) -> list[str]:
    """Флаги sety без подключения/-fileID/-dross (их добавляет воркер)."""
    args: list[str] = []
    if req.name:
        args += ["-name", req.name]
    args += ["-Tn", _num(req.tn)]
    args += ["-sopr", str(req.sopr), "-roP", _num(req.ro_p), "-roO", _num(req.ro_o)]
    if req.ro_temp:
        args.append("-ro_temp")

    if req.mode == "plan":
        # getDoItDr: "-iter N -dross -Tn T -tp_metod M -trtp K" + флаги. M — индекс
        # combo_Metod, где у десктопа один пункт «нормы» → всегда 0 (умолчание sety — 1).
        args += ["-iter", str(req.iter), "-tp_metod", "0", "-trtp", str(req.trtp)]
        if req.dross_yes:
            args.append("-dross_yes")
        if req.avtomat:
            args.append("-avtomat_yes")
        if req.utechki:
            args.append("-zulu_utechki")
        if req.char_sety:
            args.append("-char_sety")
        if not req.teplovyd:
            args.append("-no_teplovyd")
        if req.uf_calc:
            args.append("-uf_calc")
        if req.tg:
            args.append("-tg")
            if not req.teplopoter:
                args.append("-no_teplopoter")
            if req.save_uf_new:
                args.append("-save_uf_new")
        if req.mag_fragment:
            args.append("-mag_fragment")
        if req.veter:
            args.append("-veter")
        if req.save_po:
            args.append("-save_po")
    else:
        # getDoIt: "-Tn T -GWS 1 -GWS2 1" + флаги (GWS в десктопе зашиты единицами)
        args += ["-GWS", "1", "-GWS2", "1"]
        if req.avtomat:
            args.append("-avtomat_yes")
        if req.char_sety:
            args.append("-char_sety")
        if req.veter:
            args.append("-veter")
        if req.consumer_resistance == "equivalent":
            args.append("-a")
        if req.leto:
            args.append("-leto")
        if req.save_leto:
            args.append("-save_po")
        if req.mag_fragment:
            args.append("-mag_fragment")

    if not req.use_kv:
        args.append("-no_kv")
    author = (user_gid or "").lstrip("-").strip()
    if author:
        args += ["-user_gid", author]  # автор расчёта — пользователь из токена, не из запроса
    return args


def args_to_params(args: list[str]) -> str:
    """Список аргументов → строка для Celery-задачи (воркер разбирает её shlex.split)."""
    return shlex.join(args)


def tn_range_error(tn: float, t_or: Optional[float], t_vnew: Optional[float], leto: bool) -> Optional[str]:
    """Проверка sety (w.py) до постановки в очередь: Tн в [t_or; t_vnew] из «Системы теплоснабжения».

    sety берёт первую строку heatSystem и при Tн вне диапазона завершается с ошибкой
    (летний режим не проверяется). Десктоп не ограничивает ввод — sety так же отказывает,
    а умолчание формы (-32) — из QSettings; у Алматы расчётная -25, поэтому ловим заранее.
    """
    if leto or t_or is None or t_vnew is None:
        return None
    if t_or <= tn <= t_vnew:
        return None
    return (
        f"Температура наружного воздуха должна быть от {_num(t_or)} до {_num(t_vnew)} °C "
        "(расчётная для отопления и конца отопительного периода, «Система теплоснабжения»)"
    )
