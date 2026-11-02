"""
HỆ THỐNG QUẢN LÝ HÃNG VẬN TẢI HÀNH KHÁCH ĐƯỜNG DÀI
Tkinter + MySQL — toàn bộ SQL (bảng, trigger, view, dữ liệu mẫu, báo cáo) được nhúng trong file này.

Cài đặt:   pip install mysql-connector-python
Chạy:      python vantai_app.py
Lần đầu chạy, ứng dụng tự tạo CSDL, bảng, trigger, view và (tùy chọn) nạp dữ liệu mẫu.
Cần một MySQL 8.0.16+ đang chạy; tài khoản cần quyền CREATE DATABASE / TRIGGER.
"""
import csv
import datetime as dt
import json
import math
import os
import random
import re
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import mysql.connector

# ================================================================ CẤU HÌNH KẾT NỐI
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vantai_config.json")
DB = dict(host="localhost", port=3306, user="root", password="", database="vantai")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                DB.update(json.load(f))
        except (OSError, ValueError):
            pass
    for k in DB:
        v = os.environ.get("VANTAI_DB_" + k.upper())
        if v:
            DB[k] = int(v) if k == "port" else v


def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)


def run(sql, params=None, fetch=True):
    cn = mysql.connector.connect(**DB)
    try:
        cur = cn.cursor()
        cur.execute(sql, params or ())
        if fetch:
            return [d[0] for d in cur.description], cur.fetchall()
        cn.commit()
    finally:
        cn.close()


def server_connect():

    return mysql.connector.connect(**{k: v for k, v in DB.items() if k != "database"})



SCHEMA = [
    """
CREATE TABLE XE (
  MaXe INT AUTO_INCREMENT PRIMARY KEY,
  BienSo VARCHAR(15) NOT NULL UNIQUE,
  MauXe VARCHAR(30),
  HangSX VARCHAR(50),
  DoiXe INT,
  Model VARCHAR(50),
  SoGhe INT NOT NULL CHECK (SoGhe > 2),
  NgayDuaVaoSD DATE NOT NULL,            -- Số năm sử dụng = TIMESTAMPDIFF(YEAR, NgayDuaVaoSD, CURDATE())
  NgayBaoDuongCuoi DATE NOT NULL
)
""",
    """
CREATE TABLE TAIXE (
  MaTX INT AUTO_INCREMENT PRIMARY KEY,
  HoTen VARCHAR(100) NOT NULL,
  CMT VARCHAR(12) NOT NULL UNIQUE,
  SoBangLai VARCHAR(15) NOT NULL UNIQUE,
  LoaiBangLai VARCHAR(5) NOT NULL,       -- D, E, FC...
  DiaChi VARCHAR(200),
  NgaySinh DATE,
  NgayVaoLam DATE NOT NULL               -- Thâm niên = TIMESTAMPDIFF(YEAR, NgayVaoLam, CURDATE())
)
""",
    """
CREATE TABLE HESO_DOPHUCTAP (
  DoPhucTap INT PRIMARY KEY CHECK (DoPhucTap IN (1,2,3)),
  HeSoLuong DECIMAL(4,2) NOT NULL,
  HeSoKm    DECIMAL(4,2) NOT NULL
)
""",
    """
INSERT INTO HESO_DOPHUCTAP VALUES (1,1.0,1.0),(2,1.3,1.2),(3,1.6,1.5)
""",
    """
CREATE TABLE CAUHINH (
  Ten VARCHAR(50) PRIMARY KEY,
  GiaTri DECIMAL(15,2) NOT NULL
)
""",
    """
INSERT INTO CAUHINH VALUES
 ('LUONG_PHUXE_CB',300000),
 ('CHU_KY_BAO_DUONG',360),
 ('KM_MOI_NGAY_TRU',100),
 ('NGUONG_SAP_BAO_DUONG',30)
""",
    """
CREATE TABLE TUYEN (
  MaTuyen INT AUTO_INCREMENT PRIMARY KEY,
  DiemDau VARCHAR(100) NOT NULL,
  DiemCuoi VARCHAR(100) NOT NULL,
  DoDai DECIMAL(8,2) NOT NULL CHECK (DoDai > 0),   -- km
  DoPhucTap INT NOT NULL,
  ThoiGianDuKien INT NOT NULL,                      -- phút
  FOREIGN KEY (DoPhucTap) REFERENCES HESO_DOPHUCTAP(DoPhucTap)
)
""",
    """
CREATE TABLE CHUYEN (
  MaChuyen INT AUTO_INCREMENT PRIMARY KEY,
  MaTuyen INT NOT NULL,
  MaXe INT NOT NULL,
  MaLaiXe INT NOT NULL,
  MaPhuXe INT NOT NULL,
  GioKhoiHanh DATETIME NOT NULL,
  GioDenDuKien DATETIME NOT NULL,
  GiaVe DECIMAL(12,0) NOT NULL CHECK (GiaVe >= 0),
  SoKhach INT NOT NULL DEFAULT 0 CHECK (SoKhach >= 0),   -- được trigger cập nhật từ VE
  TrangThai ENUM('ChuaKhoiHanh','DangChay','HoanThanh','Huy') NOT NULL DEFAULT 'ChuaKhoiHanh',
  FOREIGN KEY (MaTuyen)  REFERENCES TUYEN(MaTuyen),
  FOREIGN KEY (MaXe)     REFERENCES XE(MaXe),
  FOREIGN KEY (MaLaiXe)  REFERENCES TAIXE(MaTX),
  FOREIGN KEY (MaPhuXe)  REFERENCES TAIXE(MaTX),
  CHECK (MaLaiXe <> MaPhuXe),
  CHECK (GioDenDuKien > GioKhoiHanh)
)
""",
    """
CREATE INDEX idx_chuyen_tuyen_gio ON CHUYEN(MaTuyen, GioKhoiHanh)
""",
    """
CREATE INDEX idx_chuyen_xe        ON CHUYEN(MaXe, GioKhoiHanh)
""",
    """
CREATE TABLE KHACHHANG (
  MaKH INT AUTO_INCREMENT PRIMARY KEY,
  HoTen VARCHAR(100) NOT NULL,
  SDT VARCHAR(15) NOT NULL UNIQUE,
  Email VARCHAR(100)
)
""",
    """
CREATE TABLE VE (
  MaVe INT AUTO_INCREMENT PRIMARY KEY,
  MaChuyen INT NOT NULL,
  MaKH INT NOT NULL,
  SoGhe INT NOT NULL,                    -- số ghế ngồi, từ 1 đến (SoGhe xe - 2)
  NgayDat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  GiaBan DECIMAL(12,0) NOT NULL,
  TrangThai ENUM('ConHieuLuc','DaSuDung','DaHuy') NOT NULL DEFAULT 'ConHieuLuc',
  FOREIGN KEY (MaChuyen) REFERENCES CHUYEN(MaChuyen),
  FOREIGN KEY (MaKH)     REFERENCES KHACHHANG(MaKH),
  UNIQUE (MaChuyen, SoGhe)
)
""",
    """
CREATE INDEX idx_ve_kh_ngay ON VE(MaKH, NgayDat)
""",
    """
CREATE TABLE CHIPHI_CHUYEN (
  MaCP INT AUTO_INCREMENT PRIMARY KEY,
  MaChuyen INT NOT NULL,
  LoaiChiPhi ENUM('NhienLieu','CauDuong','BenBai','Khac') NOT NULL,
  SoTien DECIMAL(12,0) NOT NULL,
  FOREIGN KEY (MaChuyen) REFERENCES CHUYEN(MaChuyen)
)
""",
    """
CREATE TABLE BAODUONG_LS (
  MaBD INT AUTO_INCREMENT PRIMARY KEY,
  MaXe INT NOT NULL,
  NgayBaoDuong DATE NOT NULL,
  ChiPhi DECIMAL(12,0),
  GhiChu VARCHAR(200),
  FOREIGN KEY (MaXe) REFERENCES XE(MaXe)
)
""",
    """
CREATE TRIGGER trg_ve_bi BEFORE INSERT ON VE FOR EACH ROW
BEGIN
  DECLARE v_cap INT; DECLARE v_cnt INT;
  SELECT x.SoGhe - 2 INTO v_cap FROM CHUYEN c JOIN XE x ON x.MaXe = c.MaXe WHERE c.MaChuyen = NEW.MaChuyen;
  SELECT COUNT(*) INTO v_cnt FROM VE WHERE MaChuyen = NEW.MaChuyen AND TrangThai <> 'DaHuy';
  IF NEW.SoGhe < 1 OR NEW.SoGhe > v_cap THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'So ghe khong hop le';
  END IF;
  IF NEW.TrangThai <> 'DaHuy' AND v_cnt >= v_cap THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chuyen xe da het cho (SoGhe - 2)';
  END IF;
END
""",
    """
CREATE TRIGGER trg_ve_ai AFTER INSERT ON VE FOR EACH ROW
  UPDATE CHUYEN SET SoKhach = (SELECT COUNT(*) FROM VE WHERE MaChuyen = NEW.MaChuyen AND TrangThai <> 'DaHuy')
  WHERE MaChuyen = NEW.MaChuyen
""",
    """
CREATE TRIGGER trg_ve_au AFTER UPDATE ON VE FOR EACH ROW
  UPDATE CHUYEN SET SoKhach = (SELECT COUNT(*) FROM VE WHERE MaChuyen = NEW.MaChuyen AND TrangThai <> 'DaHuy')
  WHERE MaChuyen = NEW.MaChuyen
""",
    """
CREATE TRIGGER trg_chuyen_bi BEFORE INSERT ON CHUYEN FOR EACH ROW
BEGIN
  DECLARE v_ghe INT;
  SELECT SoGhe INTO v_ghe FROM XE WHERE MaXe = NEW.MaXe;
  IF NEW.SoKhach > v_ghe - 2 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'So khach vuot qua SoGhe - 2';
  END IF;
  IF EXISTS (SELECT 1 FROM CHUYEN c WHERE c.TrangThai <> 'Huy'
             AND (c.MaXe = NEW.MaXe OR c.MaLaiXe IN (NEW.MaLaiXe,NEW.MaPhuXe) OR c.MaPhuXe IN (NEW.MaLaiXe,NEW.MaPhuXe))
             AND c.GioKhoiHanh < NEW.GioDenDuKien AND c.GioDenDuKien > NEW.GioKhoiHanh) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Xe hoac tai xe trung lich';
  END IF;
END
""",
    """
CREATE TRIGGER trg_chuyen_bu BEFORE UPDATE ON CHUYEN FOR EACH ROW
BEGIN
  DECLARE v_ghe INT;
  SELECT SoGhe INTO v_ghe FROM XE WHERE MaXe = NEW.MaXe;
  IF NEW.SoKhach > v_ghe - 2 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'So khach vuot qua SoGhe - 2';
  END IF;
END
""",
    """
CREATE TRIGGER trg_bd_ai AFTER INSERT ON BAODUONG_LS FOR EACH ROW
  UPDATE XE SET NgayBaoDuongCuoi = NEW.NgayBaoDuong WHERE MaXe = NEW.MaXe
""",
    """
CREATE VIEW VW_CHUYEN_GHE AS
SELECT c.MaChuyen, c.MaTuyen, c.MaXe, c.GioKhoiHanh, c.TrangThai, c.SoKhach,
       x.SoGhe - 2 AS SucChua,
       x.SoGhe - 2 - c.SoKhach AS GheTrong,
       ROUND(c.SoKhach / (x.SoGhe - 2) * 100, 1) AS TyLeLapDay
FROM CHUYEN c JOIN XE x ON x.MaXe = c.MaXe
""",
    """
CREATE VIEW VW_BAODUONG AS
SELECT t.*,
       t.ChuKy - FLOOR(t.KmQuyDoi / t.KmTru) AS NgayConLai,
       DATE_ADD(t.NgayBaoDuongCuoi, INTERVAL (t.ChuKy - FLOOR(t.KmQuyDoi / t.KmTru)) DAY) AS NgayBaoDuongTiep
FROM (
  SELECT x.MaXe, x.BienSo, x.NgayBaoDuongCuoi,
         COALESCE(SUM(r.DoDai * h.HeSoKm), 0) AS KmQuyDoi,
         (SELECT GiaTri FROM CAUHINH WHERE Ten = 'CHU_KY_BAO_DUONG') AS ChuKy,
         (SELECT GiaTri FROM CAUHINH WHERE Ten = 'KM_MOI_NGAY_TRU') AS KmTru
  FROM XE x
  LEFT JOIN CHUYEN c ON c.MaXe = x.MaXe AND c.TrangThai = 'HoanThanh' AND c.GioKhoiHanh >= x.NgayBaoDuongCuoi
  LEFT JOIN TUYEN r ON r.MaTuyen = c.MaTuyen
  LEFT JOIN HESO_DOPHUCTAP h ON h.DoPhucTap = r.DoPhucTap
  GROUP BY x.MaXe, x.BienSo, x.NgayBaoDuongCuoi
) t
""",
]


def _has_table(name):
    try:
        return bool(run("SHOW TABLES LIKE %s", (name,))[1])
    except mysql.connector.Error:
        return False


def schema_ready():
    """Đã khởi tạo xong: câu lệnh cuối cùng của SCHEMA (view VW_BAODUONG) đã tồn tại."""
    return _has_table("VW_BAODUONG")


def schema_partial():
    """Khởi tạo dở dang: có bảng XE nhưng chưa đủ cấu trúc."""
    return _has_table("XE") and not schema_ready()


def create_schema(drop=False):
    cn = server_connect()
    try:
        cur = cn.cursor()
        name = DB["database"]
        if drop:
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4")
        cur.execute(f"USE `{name}`")
        for stmt in SCHEMA:
            cur.execute(stmt)
        cn.commit()
    finally:
        cn.close()


# ================================================================ DỮ LIỆU MẪU
ROUTES = [  # MaTuyen, DiemDau, DiemCuoi, DoDai(km), DoPhucTap, ThoiGianDuKien(phút), GiaVe
    (1, "Hà Nội", "Hải Phòng", 120, 1, 150, 120000),
    (2, "Hà Nội", "Hạ Long", 155, 1, 180, 150000),
    (3, "Hà Nội", "Vinh", 300, 2, 330, 250000),
    (4, "Hà Nội", "Sa Pa", 320, 3, 360, 300000),
    (5, "Hà Nội", "Điện Biên", 470, 3, 600, 380000),
    (6, "Hà Nội", "Đà Nẵng", 770, 2, 840, 450000),
]
VEHICLES = [  # MaXe, BienSo, Mau, Hang, Doi, Model, SoGhe, NgaySD, bảo dưỡng cách đây (ngày)
    (1, "29B-123.45", "Trắng", "Hyundai", 2021, "Universe", 45, dt.date(2021, 3, 15), 400),   # quá hạn
    (2, "30F-678.90", "Xanh", "Thaco", 2022, "Mobihome", 35, dt.date(2022, 6, 10), 200),      # sắp đến hạn
    (3, "29B-246.80", "Đỏ", "Samco", 2020, "Felix", 29, dt.date(2020, 9, 1), 60),
    (4, "29B-135.79", "Đen", "Ford", 2023, "Transit", 16, dt.date(2023, 2, 20), 100),
    (5, "30E-112.33", "Vàng", "Hyundai", 2019, "County", 29, dt.date(2019, 4, 20), 390),      # quá hạn
    (6, "29B-998.77", "Bạc", "Thaco", 2024, "Universe", 45, dt.date(2024, 1, 12), 20),
]
DRIVER_NAMES = ["Nguyễn Văn Hùng", "Trần Quốc Bảo", "Lê Minh Tuấn", "Phạm Đức Anh", "Hoàng Văn Nam", "Vũ Thanh Sơn",
                "Đặng Quang Huy", "Bùi Văn Long", "Đỗ Mạnh Cường", "Ngô Xuân Trường", "Dương Văn Khoa", "Lý Hải Đăng"]
LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô"]
MID = ["Văn", "Thị", "Minh", "Thanh", "Quốc", "Ngọc", "Hữu", "Thu"]
FIRST_N = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Hiếu", "Lan", "Linh", "Mai", "Nam", "Phúc", "Quân", "Thảo", "Trang", "Vy"]
ADDR = ["Cầu Giấy, Hà Nội", "Thanh Xuân, Hà Nội", "Hà Đông, Hà Nội", "Long Biên, Hà Nội", "Đống Đa, Hà Nội", "Nam Từ Liêm, Hà Nội"]


def build_seed(now):
    """Sinh dữ liệu mẫu thuần Python (không chạm CSDL): không trùng lịch, không vượt SoGhe - 2."""
    rnd = random.Random(2026)
    today = now.date()
    seats = {v[0]: v[6] for v in VEHICLES}
    route = {r[0]: r for r in ROUTES}

    drivers = []
    for i, name in enumerate(DRIVER_NAMES, 1):
        drivers.append((i, name, f"001{i:02d}{rnd.randrange(10**7):07d}", f"7{i:02d}{rnd.randrange(10**8):08d}",
                        rnd.choice(["D", "E", "FD"]), rnd.choice(ADDR),
                        dt.date(rnd.randint(1975, 1995), rnd.randint(1, 12), rnd.randint(1, 28)),
                        dt.date(rnd.randint(2008, 2023), rnd.randint(1, 12), rnd.randint(1, 28))))

    customers, phones = [], set()
    for i in range(1, 41):
        while True:
            phone = f"09{rnd.randrange(10**8):08d}"
            if phone not in phones:
                phones.add(phone)
                break
        name = f"{rnd.choice(LAST)} {rnd.choice(MID)} {rnd.choice(FIRST_N)}"
        customers.append((i, name, phone, f"kh{i:02d}@example.com"))
    weights = [(41 - i) ** 1.5 for i in range(1, 41)]   # một số khách mua nhiều hơn hẳn

    trips, tickets, costs = [], {}, []
    mc = 1
    for d in range(0, 32):                      # 25 ngày trước đến 6 ngày sau
        day = today - dt.timedelta(days=25) + dt.timedelta(days=d)
        off = d % 12
        perm = [x[0] for x in drivers[off:] + drivers[:off]]
        for k in range(6):
            if rnd.random() < 0.12:
                continue
            r = route[ROUTES[(k + d) % len(ROUTES)][0]]
            depart = dt.datetime.combine(day, dt.time(5 + k, rnd.choice([0, 30])))
            arrive = depart + dt.timedelta(minutes=r[5])
            xe = k + 1
            cap = seats[xe] - 2
            if arrive < now:
                status = "HoanThanh"
            elif depart <= now:
                status = "DangChay"
            else:
                status = "ChuaKhoiHanh"
            n_cancel = rnd.randint(0, 2)
            if status == "ChuaKhoiHanh":
                x = rnd.random()
                if x < 0.18:
                    n_act, n_cancel = cap, 0                                  # hết vé
                elif x < 0.45:
                    n_act = min(cap, math.ceil(cap * rnd.uniform(0.82, 0.97)))  # > 80%
                elif x < 0.55:
                    n_act = max(1, int(cap * rnd.uniform(0.05, 0.25)))          # vắng khách
                else:
                    n_act = int(cap * rnd.uniform(0.3, 0.75))
            else:
                n_act = int(cap * rnd.uniform(0.35, 0.95))
            n_total = min(cap, n_act + n_cancel)
            n_act = min(n_act, n_total)
            trips.append((mc, r[0], xe, perm[k], perm[k + 6], depart, arrive, r[6], 0, status))

            seat_list = rnd.sample(range(1, cap + 1), n_total)
            rows = []
            for j, seat in enumerate(seat_list):
                cancelled = j >= n_act
                ve_status = "DaHuy" if cancelled else ("ConHieuLuc" if status == "ChuaKhoiHanh" else "DaSuDung")
                booked = min(now - dt.timedelta(minutes=rnd.randint(1, 600)),
                             depart - dt.timedelta(days=rnd.randint(1, 14), hours=rnd.randint(0, 20)))
                rows.append((mc, rnd.choices(range(1, 41), weights)[0], seat, booked, r[6], ve_status))
            tickets[mc] = rows

            if status == "HoanThanh":
                costs.append((mc, "NhienLieu", int(r[3] * 3500 // 1000 * 1000)))
                costs.append((mc, "CauDuong", rnd.choice([0, 60000, 120000, 180000])))
                costs.append((mc, "BenBai", 150000))
            mc += 1

    maint = []
    for v in VEHICLES:
        last = today - dt.timedelta(days=v[8])
        maint.append((v[0], last - dt.timedelta(days=330), 2500000, "Bảo dưỡng định kỳ"))
        maint.append((v[0], last, 3200000, "Bảo dưỡng định kỳ"))
    vehicles = [(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], today - dt.timedelta(days=v[8])) for v in VEHICLES]
    return dict(routes=[r[:6] for r in ROUTES], vehicles=vehicles, drivers=drivers, customers=customers,
                trips=trips, tickets=tickets, costs=costs, maint=maint)


def seed(progress=None):
    """Nạp dữ liệu mẫu vào CSDL (trigger vẫn chạy nên số khách tự đồng bộ)."""
    data = build_seed(dt.datetime.now())
    cn = mysql.connector.connect(**DB)
    try:
        cur = cn.cursor()
        cur.executemany("INSERT INTO TUYEN (MaTuyen,DiemDau,DiemCuoi,DoDai,DoPhucTap,ThoiGianDuKien) VALUES (%s,%s,%s,%s,%s,%s)", data["routes"])
        cur.executemany("INSERT INTO XE (MaXe,BienSo,MauXe,HangSX,DoiXe,Model,SoGhe,NgayDuaVaoSD,NgayBaoDuongCuoi) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", data["vehicles"])
        cur.executemany("INSERT INTO TAIXE (MaTX,HoTen,CMT,SoBangLai,LoaiBangLai,DiaChi,NgaySinh,NgayVaoLam) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", data["drivers"])
        cur.executemany("INSERT INTO KHACHHANG (MaKH,HoTen,SDT,Email) VALUES (%s,%s,%s,%s)", data["customers"])
        cur.executemany("INSERT INTO BAODUONG_LS (MaXe,NgayBaoDuong,ChiPhi,GhiChu) VALUES (%s,%s,%s,%s)", data["maint"])
        cn.commit()
        total = len(data["trips"])
        for i, t in enumerate(data["trips"], 1):
            cur.execute("INSERT INTO CHUYEN (MaChuyen,MaTuyen,MaXe,MaLaiXe,MaPhuXe,GioKhoiHanh,GioDenDuKien,GiaVe,SoKhach,TrangThai) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", t)
            cur.executemany("INSERT INTO VE (MaChuyen,MaKH,SoGhe,NgayDat,GiaBan,TrangThai) VALUES (%s,%s,%s,%s,%s,%s)", data["tickets"][t[0]])
            if i % 20 == 0:
                cn.commit()
            if progress:
                progress(i, total)
        cur.executemany("INSERT INTO CHIPHI_CHUYEN (MaChuyen,LoaiChiPhi,SoTien) VALUES (%s,%s,%s)", data["costs"])
        cn.commit()
    finally:
        cn.close()


def cli_init(wait=90):
    """Chế độ không giao diện (python vantai_app.py --init): chờ MySQL, tạo CSDL, nạp dữ liệu mẫu nếu còn trống.
    Đặt VANTAI_SEED=0 để bỏ qua bước nạp dữ liệu mẫu."""
    for _ in range(wait):
        try:
            server_connect().close()
            break
        except mysql.connector.Error as e:
            print("Đang chờ MySQL…", e, flush=True)
            time.sleep(2)
    else:
        raise SystemExit("Không kết nối được MySQL")
    if not schema_ready():
        print("Tạo CSDL, bảng, trigger, view…", flush=True)
        create_schema(drop=schema_partial())
    if os.environ.get("VANTAI_SEED", "1") != "0" and run("SELECT COUNT(*) FROM XE")[1][0][0] == 0:
        print("Nạp dữ liệu mẫu…", flush=True)
        seed(lambda i, t: print(f"  chuyến {i}/{t}", flush=True) if i % 50 == 0 else None)
    print("CSDL sẵn sàng.", flush=True)


# ================================================================ GIAO DIỆN: TIỆN ÍCH


def txt(x):
    if isinstance(x, (bytes, bytearray)):
        return x.decode()
    return "" if x is None else str(x)


def make_tree(parent, columns):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
    for c in columns:
        tree.heading(c, text=c)
        tree.column(c, width=110, anchor="w")
    vs = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hs = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vs.grid(row=0, column=1, sticky="ns")
    hs.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return frame, tree


def fill_tree(tree, columns, rows):
    tree.delete(*tree.get_children())
    tree["columns"] = columns
    for c in columns:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="w")
    for r in rows:
        tree.insert("", "end", values=[txt(v) for v in r])


# ---------------------------------------------------------------- Tab CRUD
class TableTab(ttk.Frame):
    """Tab quản lý một bảng: xem / thêm / sửa / xóa (tự sinh form từ cấu trúc bảng)."""

    def __init__(self, master, table):
        super().__init__(master)
        self.table = table
        _, info = run(f"SHOW COLUMNS FROM {table}")
        self.cols = [txt(r[0]) for r in info]
        self.pk = self.cols[0]
        self.fields = [r for r in info if "auto_increment" not in txt(r[5])]

        form = ttk.LabelFrame(self, text=f"Thông tin - {table}")
        form.pack(fill="x", padx=8, pady=6)
        self.widgets = {}
        for i, r in enumerate(self.fields):
            name, typ = txt(r[0]), txt(r[1])
            ttk.Label(form, text=name).grid(row=i // 3, column=(i % 3) * 2, padx=4, pady=3, sticky="e")
            if typ.startswith("enum"):
                w = ttk.Combobox(form, values=re.findall(r"'([^']*)'", typ), state="readonly", width=22)
            else:
                w = ttk.Entry(form, width=25)
            w.grid(row=i // 3, column=(i % 3) * 2 + 1, padx=4, pady=3, sticky="w")
            self.widgets[name] = w
        ttk.Label(form, text="Ngày: YYYY-MM-DD | Giờ: YYYY-MM-DD HH:MM:SS",
                  foreground="gray").grid(columnspan=6, pady=2)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8)
        for text, cmd in [("Thêm", self.add), ("Sửa", self.update),
                          ("Xóa", self.delete), ("Làm mới", self.refresh)]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3)

        frame, self.tree = make_tree(self, self.cols)
        frame.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.refresh()

    def values(self):
        out = []
        for r in self.fields:
            v = self.widgets[txt(r[0])].get().strip()
            out.append(v if v != "" else None)
        return out

    def refresh(self):
        try:
            cols, rows = run(f"SELECT * FROM {self.table} ORDER BY {self.pk} DESC LIMIT 500")
            fill_tree(self.tree, cols, rows)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        row = dict(zip(self.cols, self.tree.item(sel[0], "values")))
        for r in self.fields:
            name = txt(r[0])
            w = self.widgets[name]
            if isinstance(w, ttk.Combobox):
                w.set(row[name])
            else:
                w.delete(0, "end")
                w.insert(0, row[name] if row[name] != "None" else "")

    def exec(self, sql, params):
        try:
            run(sql, params, fetch=False)
            self.refresh()
        except Exception as e:  # lỗi từ trigger/CHECK/FK hiển thị ở đây
            messagebox.showerror("Không thực hiện được", str(e))

    def add(self):
        names = ",".join(txt(r[0]) for r in self.fields)
        ph = ",".join(["%s"] * len(self.fields))
        self.exec(f"INSERT INTO {self.table} ({names}) VALUES ({ph})", self.values())

    def update(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Sửa", "Hãy chọn một dòng.")
        pkv = self.tree.item(sel[0], "values")[0]
        sets = ",".join(f"{txt(r[0])}=%s" for r in self.fields)
        self.exec(f"UPDATE {self.table} SET {sets} WHERE {self.pk}=%s", self.values() + [pkv])

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Xóa", "Hãy chọn một dòng.")
        if messagebox.askyesno("Xóa", "Xóa bản ghi đã chọn?"):
            self.exec(f"DELETE FROM {self.table} WHERE {self.pk}=%s",
                      [self.tree.item(sel[0], "values")[0]])


# ---------------------------------------------------------------- Báo cáo
TODAY = dt.date.today()
FIRST = TODAY.replace(day=1)

P_RANGE = [("tu", "Từ ngày", FIRST.isoformat()), ("den", "Đến ngày", TODAY.isoformat())]

REPORTS = [
    ("1. Lương lái xe / phụ xe trong tháng (đến hiện tại)", """
        SELECT t.MaTX, t.HoTen,
               COUNT(c.MaChuyen) AS SoChuyen,
               COALESCE(SUM((SELECT GiaTri FROM CAUHINH WHERE Ten='LUONG_PHUXE_CB')
                            * h.HeSoLuong * IF(c.MaLaiXe=t.MaTX,2,1)),0) AS LuongThang
        FROM TAIXE t
        LEFT JOIN CHUYEN c ON (c.MaLaiXe=t.MaTX OR c.MaPhuXe=t.MaTX)
             AND c.TrangThai='HoanThanh'
             AND c.GioKhoiHanh >= DATE_SUB(CURDATE(), INTERVAL DAYOFMONTH(CURDATE())-1 DAY)
             AND c.GioKhoiHanh <= NOW()
        LEFT JOIN TUYEN r ON r.MaTuyen=c.MaTuyen
        LEFT JOIN HESO_DOPHUCTAP h ON h.DoPhucTap=r.DoPhucTap
        GROUP BY t.MaTX, t.HoTen ORDER BY LuongThang DESC""", []),

    ("2. Doanh thu từng xe theo khoảng ngày", """
        SELECT x.MaXe, x.BienSo, COUNT(c.MaChuyen) AS SoChuyen,
               COALESCE(SUM(c.SoKhach),0) AS TongKhach,
               COALESCE(SUM(c.SoKhach*c.GiaVe),0) AS DoanhThu
        FROM XE x LEFT JOIN CHUYEN c ON c.MaXe=x.MaXe AND c.TrangThai='HoanThanh'
             AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s
        GROUP BY x.MaXe, x.BienSo ORDER BY DoanhThu DESC""", P_RANGE),

    ("3a. Xe + ngày bảo dưỡng tiếp theo", """
        SELECT MaXe, BienSo, NgayBaoDuongCuoi, ROUND(KmQuyDoi,1) AS KmQuyDoi,
               NgayConLai, NgayBaoDuongTiep
        FROM VW_BAODUONG WHERE NgayBaoDuongTiep >= CURDATE() ORDER BY NgayBaoDuongTiep""", []),

    ("3b. Xe QUÁ HẠN bảo dưỡng", """
        SELECT MaXe, BienSo, NgayBaoDuongTiep, DATEDIFF(CURDATE(), NgayBaoDuongTiep) AS SoNgayQuaHan
        FROM VW_BAODUONG WHERE NgayBaoDuongTiep < CURDATE() ORDER BY NgayBaoDuongTiep""", []),

    ("4a. Chuyến còn dưới 10 ghế trống", """
        SELECT * FROM VW_CHUYEN_GHE
        WHERE TrangThai='ChuaKhoiHanh' AND GheTrong BETWEEN 1 AND 9 ORDER BY GheTrong""", []),

    ("4b. Chuyến đã bán trên 80% ghế", """
        SELECT * FROM VW_CHUYEN_GHE
        WHERE TrangThai='ChuaKhoiHanh' AND TyLeLapDay > 80 ORDER BY TyLeLapDay DESC""", []),

    ("4c. Chuyến đã hết vé", """
        SELECT * FROM VW_CHUYEN_GHE WHERE TrangThai='ChuaKhoiHanh' AND GheTrong = 0""", []),

    ("4d. Chuyến ghế trống lớn / nhỏ hơn mức", """
        SELECT *, IF(GheTrong > %(muc)s,'Nhiều chỗ trống','Sắp hết chỗ') AS CanhBao
        FROM VW_CHUYEN_GHE
        WHERE TrangThai='ChuaKhoiHanh' AND GheTrong <> %(muc)s ORDER BY GheTrong""",
     [("muc", "Mức ghế trống", "15")]),

    ("5. Xe sắp đến hạn bảo dưỡng (tăng dần)", """
        SELECT MaXe, BienSo, NgayBaoDuongTiep, NgayConLai FROM VW_BAODUONG
        WHERE NgayBaoDuongTiep BETWEEN CURDATE()
              AND DATE_ADD(CURDATE(), INTERVAL %(ngay)s DAY)
        ORDER BY NgayBaoDuongTiep ASC""", [("ngay", "Trong vòng (ngày)", "30")]),

    ("6. Lịch trình các chuyến của một tuyến", """
        SELECT c.MaChuyen, CONCAT(r.DiemDau,' - ',r.DiemCuoi) AS TuyenDuong,
               CONCAT(x.HangSX,' ',x.Model) AS XeSuDung, x.BienSo,
               l.HoTen AS LaiXe, p.HoTen AS PhuXe,
               c.GioKhoiHanh, c.GioDenDuKien,
               x.SoGhe-2-c.SoKhach AS GheConTrong, c.TrangThai
        FROM CHUYEN c JOIN TUYEN r ON r.MaTuyen=c.MaTuyen JOIN XE x ON x.MaXe=c.MaXe
             JOIN TAIXE l ON l.MaTX=c.MaLaiXe JOIN TAIXE p ON p.MaTX=c.MaPhuXe
        WHERE c.MaTuyen=%(tuyen)s ORDER BY c.GioKhoiHanh ASC""",
     [("tuyen", "Mã tuyến", "1")]),

    ("7. Khách mua nhiều vé nhất trong tháng", """
        SELECT k.MaKH, k.HoTen, k.SDT, COUNT(*) AS SoVe, SUM(v.GiaBan) AS TongTien
        FROM VE v JOIN KHACHHANG k ON k.MaKH=v.MaKH
        WHERE v.TrangThai<>'DaHuy' AND v.NgayDat >= %(thang)s
              AND v.NgayDat < DATE_ADD(%(thang)s, INTERVAL 1 MONTH)
        GROUP BY k.MaKH, k.HoTen, k.SDT ORDER BY SoVe DESC""",
     [("thang", "Tháng (YYYY-MM-01)", FIRST.isoformat())]),

    ("8a. Thống kê vé theo tháng", """
        SELECT CONCAT(YEAR(NgayDat),'-',LPAD(MONTH(NgayDat),2,'0')) AS Thang,
               COUNT(*) AS TongVeBan, SUM(TrangThai='DaSuDung') AS DaSuDung,
               SUM(TrangThai='DaHuy') AS DaHuy, SUM(TrangThai='ConHieuLuc') AS ConHieuLuc,
               SUM(IF(TrangThai<>'DaHuy',GiaBan,0)) AS DoanhThu
        FROM VE GROUP BY Thang ORDER BY Thang""", []),

    ("8b. Thống kê vé theo tuyến", """
        SELECT r.MaTuyen, CONCAT(r.DiemDau,' - ',r.DiemCuoi) AS Tuyen,
               COUNT(v.MaVe) AS TongVeBan, COALESCE(SUM(v.TrangThai='DaSuDung'),0) AS DaSuDung,
               COALESCE(SUM(v.TrangThai='DaHuy'),0) AS DaHuy,
               COALESCE(SUM(v.TrangThai='ConHieuLuc'),0) AS ConHieuLuc,
               COALESCE(SUM(IF(v.TrangThai<>'DaHuy',v.GiaBan,0)),0) AS DoanhThu
        FROM TUYEN r LEFT JOIN CHUYEN c ON c.MaTuyen=r.MaTuyen
             LEFT JOIN VE v ON v.MaChuyen=c.MaChuyen
        GROUP BY r.MaTuyen, Tuyen ORDER BY DoanhThu DESC""", []),

    ("9. Hiệu quả hoạt động từng tuyến", """
        SELECT t.*, t.DoanhThu - t.ChiPhi AS LoiNhuan FROM (
          SELECT r.MaTuyen, CONCAT(r.DiemDau,' - ',r.DiemCuoi) AS Tuyen,
            (SELECT COUNT(*) FROM CHUYEN c WHERE c.MaTuyen=r.MaTuyen AND c.TrangThai='HoanThanh'
               AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s) AS TongChuyen,
            (SELECT COUNT(*) FROM VE v JOIN CHUYEN c ON c.MaChuyen=v.MaChuyen
              WHERE c.MaTuyen=r.MaTuyen AND v.TrangThai<>'DaHuy'
               AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s) AS TongVeBan,
            (SELECT COALESCE(SUM(c.SoKhach*c.GiaVe),0) FROM CHUYEN c
              WHERE c.MaTuyen=r.MaTuyen AND c.TrangThai='HoanThanh'
               AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s) AS DoanhThu,
            (SELECT COALESCE(SUM(cp.SoTien),0) FROM CHIPHI_CHUYEN cp JOIN CHUYEN c ON c.MaChuyen=cp.MaChuyen
              WHERE c.MaTuyen=r.MaTuyen AND c.TrangThai='HoanThanh'
               AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s)
            + (SELECT COUNT(*) FROM CHUYEN c WHERE c.MaTuyen=r.MaTuyen AND c.TrangThai='HoanThanh'
               AND DATE(c.GioKhoiHanh) BETWEEN %(tu)s AND %(den)s)
              * 3 * h.HeSoLuong * (SELECT GiaTri FROM CAUHINH WHERE Ten='LUONG_PHUXE_CB') AS ChiPhi
          FROM TUYEN r JOIN HESO_DOPHUCTAP h ON h.DoPhucTap=r.DoPhucTap
        ) t ORDER BY DoanhThu DESC""", P_RANGE),
]


class ReportTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Báo cáo:").pack(side="left")
        self.cb = ttk.Combobox(top, values=[r[0] for r in REPORTS], state="readonly", width=55)
        self.cb.current(0)
        self.cb.pack(side="left", padx=6)
        self.cb.bind("<<ComboboxSelected>>", self.build_params)
        ttk.Button(top, text="Chạy", command=self.run_report).pack(side="left", padx=3)
        ttk.Button(top, text="Xuất CSV", command=self.export).pack(side="left", padx=3)

        self.pframe = ttk.Frame(self)
        self.pframe.pack(fill="x", padx=8)
        self.entries = {}
        frame, self.tree = make_tree(self, [])
        frame.pack(fill="both", expand=True, padx=8, pady=6)
        self.build_params()

    def build_params(self, _=None):
        for w in self.pframe.winfo_children():
            w.destroy()
        self.entries = {}
        for key, label, default in REPORTS[self.cb.current()][2]:
            ttk.Label(self.pframe, text=label).pack(side="left", padx=4)
            e = ttk.Entry(self.pframe, width=16)
            e.insert(0, default)
            e.pack(side="left", padx=4)
            self.entries[key] = e

    def run_report(self):
        sql = REPORTS[self.cb.current()][1]
        params = {k: e.get().strip() for k, e in self.entries.items()}
        try:
            cols, rows = run(sql, params)
            fill_tree(self.tree, cols, rows)
        except Exception as e:
            messagebox.showerror("Lỗi truy vấn", str(e))

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(self.tree["columns"])
            for iid in self.tree.get_children():
                w.writerow(self.tree.item(iid, "values"))
        messagebox.showinfo("Xuất CSV", "Đã lưu: " + path)



# ================================================================ GIAO DIỆN: HỆ THỐNG
class ConnDialog(tk.Toplevel):
    """Hộp thoại cấu hình kết nối MySQL."""

    FIELDS = [("host", "Máy chủ"), ("port", "Cổng"), ("user", "Tài khoản"), ("password", "Mật khẩu"), ("database", "Tên CSDL")]

    def __init__(self, master, msg=""):
        super().__init__(master)
        self.title("Cấu hình kết nối MySQL")
        self.resizable(False, False)
        self.transient(master)
        self.ok = False
        self.vars = {}
        r = 0
        if msg:
            ttk.Label(self, text=msg, foreground="red", wraplength=340, justify="left").grid(row=r, columnspan=2, padx=10, pady=8)
            r += 1
        for key, label in self.FIELDS:
            ttk.Label(self, text=label).grid(row=r, column=0, padx=10, pady=4, sticky="e")
            v = tk.StringVar(value=str(DB[key]))
            ttk.Entry(self, textvariable=v, width=28, show="*" if key == "password" else "").grid(row=r, column=1, padx=10, pady=4)
            self.vars[key] = v
            r += 1
        ttk.Button(self, text="Lưu & kết nối", command=self.save).grid(row=r, columnspan=2, pady=10)
        self.grab_set()

    def save(self):
        for k, v in self.vars.items():
            DB[k] = int(v.get()) if k == "port" else v.get().strip()
        save_config()
        self.ok = True
        self.destroy()


class Progress(tk.Toplevel):
    def __init__(self, master, text):
        super().__init__(master)
        self.title("Đang xử lý")
        self.transient(master)
        ttk.Label(self, text=text).pack(padx=20, pady=(14, 6))
        self.bar = ttk.Progressbar(self, length=320, maximum=100)
        self.bar.pack(padx=20, pady=(0, 14))
        self.update()

    def step(self, i, total):
        self.bar["value"] = i * 100 / total
        self.update()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quản lý Hãng vận tải hành khách đường dài")
        self.geometry("1200x720")
        menu = tk.Menu(self)
        sysm = tk.Menu(menu, tearoff=0)
        sysm.add_command(label="Cấu hình kết nối…", command=self.change_config)
        sysm.add_separator()
        sysm.add_command(label="Khởi tạo lại CSDL (xóa toàn bộ)…", command=self.reset_db)
        sysm.add_command(label="Nạp dữ liệu mẫu…", command=self.do_seed)
        sysm.add_command(label="Xem SQL khởi tạo…", command=self.show_sql)
        sysm.add_separator()
        sysm.add_command(label="Làm mới giao diện", command=self.build_tabs)
        sysm.add_command(label="Thoát", command=self.destroy)
        menu.add_cascade(label="Hệ thống", menu=sysm)
        self.config(menu=menu)
        self.status = ttk.Label(self, anchor="w", relief="sunken")
        self.status.pack(side="bottom", fill="x")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.after(100, self.startup)

    # ---- khởi động & thiết lập
    def ensure_server(self):
        msg = ""
        while True:
            try:
                server_connect().close()
                return True
            except mysql.connector.Error as e:
                msg = f"Không kết nối được máy chủ MySQL:\n{e}"
            d = ConnDialog(self, msg)
            self.wait_window(d)
            if not d.ok:
                return False

    def startup(self):
        if not self.ensure_server():
            self.status.config(text="Chưa kết nối được máy chủ MySQL (menu Hệ thống → Cấu hình kết nối)")
            return
        if not schema_ready():
            partial = schema_partial()
            q = (f"CSDL '{DB['database']}' đang khởi tạo dở dang.\nXóa và tạo lại toàn bộ?" if partial
                 else f"Chưa có CSDL '{DB['database']}'.\nTạo CSDL, bảng, trigger và view ngay bây giờ?")
            if not messagebox.askyesno("Khởi tạo hệ thống", q):
                return
            self.init_db(partial)
        self.build_tabs()

    def init_db(self, drop):
        try:
            create_schema(drop)
        except mysql.connector.Error as e:
            messagebox.showerror("Lỗi khởi tạo", str(e))
            return False
        if messagebox.askyesno("Dữ liệu mẫu", "Đã tạo xong cấu trúc CSDL.\nNạp dữ liệu mẫu để chạy thử?"):
            self.do_seed(confirm=False)
        return True

    def reset_db(self):
        if messagebox.askyesno("Khởi tạo lại", "Thao tác này XÓA TOÀN BỘ dữ liệu hiện có.\nTiếp tục?", icon="warning"):
            if self.ensure_server() and self.init_db(True):
                self.build_tabs()

    def do_seed(self, confirm=True):
        try:
            if schema_ready() and run("SELECT COUNT(*) FROM XE")[1][0][0] > 0:
                messagebox.showinfo("Dữ liệu mẫu", "CSDL đã có dữ liệu. Hãy dùng 'Khởi tạo lại CSDL' để nạp lại từ đầu.")
                return
            if confirm and not messagebox.askyesno("Dữ liệu mẫu", "Nạp dữ liệu mẫu vào CSDL?"):
                return
            p = Progress(self, "Đang nạp dữ liệu mẫu (chuyến xe, vé, chi phí, bảo dưỡng)…")
            try:
                seed(p.step)
            finally:
                p.destroy()
            messagebox.showinfo("Dữ liệu mẫu", "Đã nạp xong dữ liệu mẫu.")
            self.build_tabs()
        except mysql.connector.Error as e:
            messagebox.showerror("Lỗi nạp dữ liệu", str(e))

    def change_config(self):
        d = ConnDialog(self)
        self.wait_window(d)
        if d.ok:
            self.startup()

    def show_sql(self):
        w = tk.Toplevel(self)
        w.title("SQL khởi tạo CSDL (nhúng trong ứng dụng)")
        t = tk.Text(w, width=130, height=40, font=("Consolas", 10))
        t.insert("1.0", ";\n\n".join(s.strip() for s in SCHEMA) + ";")
        t.config(state="disabled")
        t.pack(fill="both", expand=True)

    def build_tabs(self):
        for t in self.nb.tabs():
            self.nb.forget(t)
        try:
            for title, table in [("Chuyến xe", "CHUYEN"), ("Vé", "VE"), ("Khách hàng", "KHACHHANG"),
                                 ("Xe", "XE"), ("Tài xế", "TAIXE"), ("Tuyến", "TUYEN"),
                                 ("Chi phí chuyến", "CHIPHI_CHUYEN"), ("Lịch sử bảo dưỡng", "BAODUONG_LS"),
                                 ("Hệ số tuyến", "HESO_DOPHUCTAP"), ("Cấu hình", "CAUHINH")]:
                self.nb.add(TableTab(self.nb, table), text=title)
            self.nb.add(ReportTab(self.nb), text="BÁO CÁO / THỐNG KÊ")
            self.nb.select(self.nb.tabs()[-1])
            self.status.config(text=f" Đã kết nối {DB['user']}@{DB['host']}:{DB['port']}/{DB['database']}")
        except mysql.connector.Error as e:
            messagebox.showerror("Lỗi", str(e))


if __name__ == "__main__":
    load_config()
    if "--init" in sys.argv:
        cli_init()
    else:
        App().mainloop()
