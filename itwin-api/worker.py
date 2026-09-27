import os
import sys
import subprocess
import re
import shlex
import uuid
import time
import logging
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Setup Redis URL using environment variables
redis_addr = os.getenv('REDIS_ADDR', '127.0.0.1:6379')
redis_password = os.getenv('REDIS_PASSWORD', '').strip()

if redis_password:
    redis_url = f"redis://:{redis_password}@{redis_addr}/0"
else:
    redis_url = f"redis://{redis_addr}/0"

celery_app = Celery(
    "itwin_tasks",
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Almaty',
    enable_utc=True,
)

logger = logging.getLogger(__name__)

# Флаги подключения и вывода задаёт сам воркер; из пользовательских параметров
# их принимать нельзя (argparse берёт последнее значение — переопределили бы БД/файл).
# -copy_calc/-database2 копируют результат в другую БД — тоже только сервер.
RESERVED_SETY_FLAGS = {
    "-type_of_net", "-server", "-database", "-user", "-port", "-password", "-rdbms", "-out_file",
    "-copy_calc", "-database2",
}

# Белый список флагов sety/config.py, которые можно передать из клиента. Сравнение точное:
# argparse принимает сокращения (-databas → -database), поэтому чёрного списка мало.
ALLOWED_SETY_FLAGS = frozenset({
    "-fileID", "-name", "-time", "-user_gid", "-Tn", "-iter", "-tp_metod", "-trtp",
    "-sopr", "-roP", "-roO", "-ro_temp", "-GWS", "-GWS2",
    "-a", "-dross", "-dross_yes", "-avtomat_yes", "-tg", "-char_sety", "-no_balans",
    "-no_teplovyd", "-no_teplopoter", "-uf_calc", "-save_uf_new", "-veter",
    "-save_po", "-save_po_yes", "-zulu_zn0", "-zulu_utechki", "-zulu_utechki_sm",
    "-ZULU", "-ZN0", "-leto", "-no_current", "-is_dop", "-fakt", "-no_out", "-plan",
    "-no_kv", "-mag_fragment", "-color",
})

_NUMBER_RE = re.compile(r"^-\d+(\.\d+)?$")


def validate_sety_params(params: str) -> list[str]:
    """Разбирает строку параметров sety; ValueError для зарезервированных и неизвестных флагов."""
    try:
        tokens = shlex.split(params or "")
    except ValueError as exc:
        raise ValueError(f"Не удалось разобрать параметры расчёта: {exc}") from exc
    for token in tokens:
        if not token.startswith("-") or _NUMBER_RE.match(token):
            continue  # значение флага (в т.ч. отрицательное число: -Tn -25)
        raw = token.split("=", 1)[0]
        flag = raw.lower()
        if flag.startswith("--"):
            flag = flag[1:]
        if flag in RESERVED_SETY_FLAGS:
            raise ValueError(f"Параметр {flag} задаётся сервером и не может быть передан в расчёт")
        if raw not in ALLOWED_SETY_FLAGS:
            raise ValueError(f"Неизвестный параметр расчёта: {raw}")
    return tokens


def _sety_base_cmd(out_file_path: str, dross: bool) -> list[str]:
    cmd = [
        sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sety", "ww.py"),
        "-type_of_net", "1",
        "-server", os.getenv("DB_HOST"),
        "-database", os.getenv("DB_NAME"),
        "-user", os.getenv("DB_USER"),
        "-port", os.getenv("DB_PORT"),
        "-password", os.getenv("DB_PASSWORD"),
        "-rdbms", "postgreSQL",
        "-out_file", out_file_path,
        "-color",
    ]
    # Десктоп (gid8 gidr_calc.cpp): плановый режим (getDoItDr) передаёт -dross, фактический/
    # аварийный (getDoIt) — нет; в sety это g_is_avar (store_false).
    if dross:
        cmd.append("-dross")
    return cmd


def _masked(cmd: list[str]) -> str:
    safe = ['***' if i > 0 and cmd[i - 1] == '-password' else c for i, c in enumerate(cmd)]
    return ' '.join([f'"{c}"' if ' ' in c else c for c in safe])


def _run_one(cmd: list[str], request_id: str, label: str) -> dict:
    """Один запуск ww.py; out_file и лог — временные, удаляются после расчёта."""
    out_file_path = cmd[cmd.index("-out_file") + 1]
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"ww_output_{request_id}_{label}.log")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write(result.stdout)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        error_message = e.stderr if e.stderr else "Неизвестная ошибка"
        logger.error(f"Ошибка запуска ww.py: {error_message}")
        return {"status": "error", "output": e.stdout, "error": error_message}
    finally:
        try:
            if os.path.exists(out_file_path):
                os.remove(out_file_path)
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
        except Exception as e:
            logger.error(f"Ошибка при удалении временных файлов: {str(e)}")


@celery_app.task(bind=True, name="run_sety_calculation")
def run_sety_calculation(self, params: str, request_id: str = None, dross: bool = True,
                         file_ids: list[int] | None = None):
    """Расчёт sety.

    params   — пользовательские флаги (белый список, см. validate_sety_params);
    dross    — True: плановый режим (-dross), False: фактический/аварийный (без -dross);
    file_ids — «по списку»: фрагменты считаются по очереди тем же набором флагов
               (десктоп onDoItList/onDoItListDr пишет .bat по строке на фрагмент);
               тогда -fileID в params недопустим.
    """
    if not request_id:
        request_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

    user_tokens = validate_sety_params(params)
    if not dross and "-dross" in user_tokens:
        raise ValueError("Флаг -dross несовместим с аварийным (фактическим) режимом")
    if file_ids is not None:
        if "-fileID" in user_tokens:
            raise ValueError("Для расчёта по списку -fileID задаётся списком фрагментов")
        targets = [int(f) for f in file_ids]
    else:
        targets = [None]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    runs = []
    for idx, file_id in enumerate(targets, start=1):
        label = str(file_id) if file_id is not None else "0"
        out_file_path = os.path.join(base_dir, "sety", f"out_{request_id}_{label}.txt")
        cmd = _sety_base_cmd(out_file_path, dross) + user_tokens
        if file_id is not None:
            cmd += ["-fileID", str(file_id)]
        logger.info(f"Task {self.request.id} executing command: {_masked(cmd)}")
        self.update_state(state='PROGRESS', meta={
            'message': 'Расчет запущен' if len(targets) == 1 else f'Расчет фрагмента {file_id} ({idx}/{len(targets)})',
            'request_id': request_id,
            'current': idx,
            'total': len(targets),
        })
        run = _run_one(cmd, request_id, label)
        run["file_id"] = file_id
        runs.append(run)

    if file_ids is None:
        run = runs[0]
        response = {
            "status": run["status"],
            "message": "Расчет окончен" if run["status"] == "success" else "Ошибка при выполнении расчета",
            "output": run.get("output"),
            "request_id": request_id,
        }
        if run["status"] != "success":
            response["error"] = run.get("error")
        return response

    ok = sum(1 for r in runs if r["status"] == "success")
    status = "success" if ok == len(runs) else ("error" if ok == 0 else "partial")
    output = "\n".join(
        f"==== Фрагмент {r['file_id']}: {'успешно' if r['status'] == 'success' else 'ошибка'} ====\n{r.get('output') or ''}"
        for r in runs
    )
    response = {
        "status": status,
        "message": f"Расчет по списку окончен: успешно {ok} из {len(runs)}",
        "output": output,
        "request_id": request_id,
        "runs": runs,
    }
    errors = [f"Фрагмент {r['file_id']}: {r.get('error')}" for r in runs if r["status"] != "success"]
    if errors:
        response["error"] = "\n".join(errors)
    return response
