"""
인증관리 에이전트 실행 스크립트
"""
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)

