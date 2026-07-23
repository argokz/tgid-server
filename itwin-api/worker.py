import os
import sys
import subprocess
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

@celery_app.task(bind=True, name="run_sety_calculation")
def run_sety_calculation(self, params: str, request_id: str = None):
    if not request_id:
        request_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

    server = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    port = os.getenv("DB_PORT")
    password = os.getenv("DB_PASSWORD")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ww_path = os.path.join(base_dir, "sety", "ww.py")
    out_file_path = os.path.join(base_dir, "sety", f"out_{request_id}.txt")
    log_file_path = os.path.join(base_dir, f"ww_output_{request_id}.log")
    
    cmd = [
        sys.executable, ww_path,
        "-type_of_net", "1",
        "-server", server,
        "-database", database,
        "-user", user,
        "-port", port,
        "-password", password,
        "-rdbms", "postgreSQL",
        "-out_file", out_file_path,
        "-color",
        "-dross",
    ]
    
    # Safely split parameters and add to command
    cmd += shlex.split(params)
    
    cmd_str = ' '.join([f'"{c}"' if ' ' in c else c for c in cmd])
    logger.info(f"Task {self.request.id} executing command: {cmd_str}")
    
    try:
        # We can update state so that frontend can see "PROGRESS" instead of just "PENDING"
        self.update_state(state='PROGRESS', meta={'message': 'Расчет запущен', 'request_id': request_id})
        
        # Run process synchronously in this worker thread (which is fine for Celery)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Write output to log
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write(result.stdout)
            
        return {
            "status": "success",
            "message": "Расчет окончен",
            "output": result.stdout,
            "request_id": request_id
        }
        
    except subprocess.CalledProcessError as e:
        error_message = e.stderr if e.stderr else "Неизвестная ошибка"
        logger.error(f"Ошибка запуска ww.py: {error_message}")
        return {
            "status": "error",
            "message": "Ошибка при выполнении расчета",
            "output": e.stdout,
            "error": error_message,
            "request_id": request_id
        }
        
    finally:
        # Clean up temporary output files to prevent disk leak
        try:
            if os.path.exists(out_file_path):
                os.remove(out_file_path)
            # You might want to keep the log file or remove it. Leaving it matching previous main.py behavior.
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
        except Exception as e:
            logger.error(f"Ошибка при удалении временных файлов: {str(e)}")
