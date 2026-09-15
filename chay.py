"""Chạy bản demo Packing List: python chay.py

Mở http://127.0.0.1:8042 là dùng được ngay.
"""
import os
import sys

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(GOC, "backend", "app"))

import uvicorn
from config import CONG

if __name__ == "__main__":
    print(f"Packing List Demo -> http://127.0.0.1:{CONG}")
    uvicorn.run("main:app", host="0.0.0.0", port=CONG, reload=False)
