import threading
import time
from scheduler import AutomationScheduler
from api_server import app
import uvicorn

def run_scheduler():
    """스케줄러 실행"""
    scheduler = AutomationScheduler()
    scheduler.start(run_immediately=True)
    
    # 계속 실행
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()

def run_api():
    """API 서버 실행"""
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STARTING STOCK SELECTION AGENT")
    print("="*60)
    print("\n1. API Server: http://localhost:8002")
    print("2. Scheduler: Running in background (hourly)")
    print("\nPress Ctrl+C to stop all services\n")
    print("="*60 + "\n")
    
    # 스케줄러를 별도 스레드로 실행
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # API 서버 실행 (메인 스레드)
    try:
        run_api()
    except KeyboardInterrupt:
        print("\n👋 Shutting down all services...\n")