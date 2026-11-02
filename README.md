# Hệ thống quản lý hãng vận tải hành khách đường dài

Ứng dụng Python (Tkinter) + MySQL. Toàn bộ SQL (bảng, trigger, view, dữ liệu mẫu, báo cáo) nhúng trong `vantai_app.py`.

## Chạy nhanh bằng Docker

```bash
docker compose up --build
```

Mở trình duyệt: <http://localhost:6080/vnc.html?autoconnect=true&resize=scale>

Lần đầu chạy, hệ thống tự tạo CSDL `vantai` và nạp dữ liệu mẫu (≈ 170 chuyến, 3.500 vé; mất vài chục giây).
Dữ liệu được lưu trong volume `dbdata`. Xóa sạch: `docker compose down -v`.

## Chạy không dùng Docker

```bash
pip install -r requirements.txt
python vantai_app.py          # cần MySQL 8.0.16+; app hỏi thông tin kết nối ở lần đầu
```

Biến môi trường: `VANTAI_DB_HOST`, `VANTAI_DB_PORT`, `VANTAI_DB_USER`, `VANTAI_DB_PASSWORD`, `VANTAI_DB_DATABASE`, `VANTAI_SEED=0` (bỏ qua dữ liệu mẫu).

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `vantai_app.py` | Ứng dụng + SQL nhúng + dữ liệu mẫu |
| `Dockerfile`, `docker-compose.yml`, `docker/entrypoint.sh` | Đóng gói (app + MySQL + noVNC) |
| `docs/` | Sơ đồ E-R, lược đồ quan hệ, báo cáo Word, bản SQL tham khảo |
| `.github/workflows/docker.yml` | CI build & đẩy image lên GHCR |

