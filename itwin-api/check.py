import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT')
)
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='linesobj';")
print("linesobj:", [c[0] for c in cur.fetchall()])
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='nodes';")
print("nodes:", [c[0] for c in cur.fetchall()])
