from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
import os, dotenv, json, pathlib
from backup_core import backup_all

dotenv.load_dotenv()
app = FastAPI(title="Pancake Safe Backup")

from fastapi.responses import FileResponse

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

def job_backup():
    chat_token = os.getenv("PANCAKE_CHAT_TOKEN")
    pos_key = os.getenv("PANCAKE_POS_API_KEY")
    if not chat_token:
        print("[JOB] Chưa có token, bỏ qua")
        return
    try:
        print("[JOB] Bắt đầu backup tự động mỗi 1 phút...")
        filename, count = backup_all(chat_token, pos_key)
        print(f"[JOB] Xong {count} khách, file {filename}")
    except Exception as e:
        print(f"[JOB] Lỗi backup: {e}")

# Chạy ngay khi khởi động
@app.on_event("startup")
def start_scheduler():
    interval_min = int(os.getenv("BACKUP_INTERVAL_MINUTES", "1"))
    scheduler.add_job(job_backup, 'interval', minutes=interval_min, id='backup_job', replace_existing=True)
    scheduler.start()
    print(f"Đã bật tự động backup mỗi {interval_min} phút")
    # Chạy thử 1 lần khi start
    job_backup()

@app.get("/api/status")
def status():
    latest_json = pathlib.Path("backup_latest.json")
    count = 0
    last_time = None
    if latest_json.exists():
        try:
            data = json.loads(latest_json.read_text(encoding="utf-8"))
            count = len(data)
            if data:
                last_time = data[0].get('thoi_gian_backup')
        except:
            pass
    return {"total_customers": count, "last_backup": last_time, "interval_minutes": os.getenv("BACKUP_INTERVAL_MINUTES","1")}

@app.get("/api/customers")
def customers():
    latest_json = pathlib.Path("backup_latest.json")
    if not latest_json.exists():
        return []
    try:
        return json.loads(latest_json.read_text(encoding="utf-8"))
    except:
        return []

@app.post("/api/backup-now")
def backup_now():
    chat_token = os.getenv("PANCAKE_CHAT_TOKEN")
    pos_key = os.getenv("PANCAKE_POS_API_KEY")
    if not chat_token:
        return {"error": "Chưa cấu hình PANCAKE_CHAT_TOKEN"}
    filename, count = backup_all(chat_token, pos_key)
    return {"ok": True, "file": filename, "count": count}

# Serve frontend - bản sáng y hệt Pancake
if pathlib.Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    index = pathlib.Path("static/index.html")
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Pancake Safe API đang chạy. Vào /docs để xem API"}

# Serve file Excel mới nhất
@app.get("/api/download-excel")
def download_excel():
    from fastapi.responses import FileResponse
    p = pathlib.Path("backup_latest.xlsx")
    if p.exists():
        return FileResponse(str(p), filename="backup_latest.xlsx")
    return {"error": "Chưa có file backup"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
