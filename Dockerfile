# Trang điều xe EPL Lào — một ảnh Docker: FastAPI (API /api) + giao diện tĩnh (/), một tiến trình uvicorn.
# Dựng:  docker compose build        Chạy: docker compose up -d        (xem deploy/linux/HUONG_DAN_HOST_LINUX_DOCKER.md)
FROM python:3.10-slim

# Giờ Lào: ngày lập phiếu, ngày ký nhận, kỳ tháng tính theo giờ máy (UTC+7)
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Vientiane EPL_LAO_TEP=/data/tep
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY deploy/linux/requirements.lock.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY backend ./backend
COPY frontend ./frontend

# ảnh / hợp đồng đính kèm (/data/tep) và nhật ký (/app/logs) nằm ở volume — giữ qua mỗi lần cập nhật ảnh
RUN useradd --system --uid 10001 epl && mkdir -p /data/tep /app/logs && chown -R epl /data/tep /app/logs
USER epl

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)" || exit 1
# MỘT tiến trình: trang có luồng tự đồng bộ nền (5 phút) — nhiều worker là chạy trùng
CMD ["python", "-X", "utf8", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--no-access-log", "--proxy-headers", "--forwarded-allow-ips=*"]
