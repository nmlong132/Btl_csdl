FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    PATH=/opt/venv/bin:$PATH \
    VANTAI_DB_HOST=db

# Tkinter + màn hình ảo (Xvfb) + VNC + noVNC => dùng ứng dụng ngay trên trình duyệt
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-tk \
        xvfb x11vnc novnc websockify \
        fonts-dejavu-core fonts-liberation \
    && ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/venv
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vantai_app.py .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 6080
ENTRYPOINT ["/entrypoint.sh"]
