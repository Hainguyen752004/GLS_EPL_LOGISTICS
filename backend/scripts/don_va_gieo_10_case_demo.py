# -*- coding: utf-8 -*-
"""DỌN dữ liệu sai và GIEO 10 case demo đi trọn luồng A→Z.

CHẠY QUA API THẬT, không ghi thẳng vào bảng (trừ bước dọn). Đó là điểm quan
trọng nhất của tệp này: mỗi case demo phải đi qua ĐÚNG những cửa mà người dùng
thật đi qua — duyệt báo giá, tách lệnh, kiểm hạn đăng kiểm, kiểm ca trực, kiểm
POD, kiểm kỳ kế toán. Dữ liệu gieo bằng câu INSERT sẽ trông đúng trên màn hình
nhưng không chứng minh được gì, và nó là loại dữ liệu vỡ ngay khi ai đó bấm nút
tiếp theo trong buổi demo.

BỐN PHẦN

  1. DỌN — xoá toàn bộ dữ liệu giao dịch và những bản ghi thử nghiệm `AZ-*`.
     Giữ nguyên dữ liệu gốc `DEMO-*` (khách, tuyến, loại xe, xe, tài xế) và
     nhật ký kiểm toán.
  2. CHUẨN LẠI DỮ LIỆU GỐC — đây cũng là dọn dữ liệu sai: đội xe đang có ba
     cách viết trạng thái ("active", "Sẵn sàng", "Đang vận chuyển") mà điều
     phối chỉ nhận đúng một, và bốn xe có hạn bảo dưỡng đã quá hạn. Xe như vậy
     không điều phối được, nên chúng là dữ liệu sai chứ không phải dữ liệu cũ.
  3. GIEO 10 CASE, mỗi case dừng ở một chặng khác nhau của luồng, để mọi màn
     hình đều có thứ để xem: ba case xong hẳn (báo cáo doanh thu có số), hai
     case đang giao (màn Theo dõi có xe chạy), hai case chờ điều phối (màn Điều
     phối có hàng đợi), một chờ khách, một chờ duyệt nội bộ, một bản nháp.
  4. GHI LẠI — in ra bảng dữ liệu luồng và ghi vào
     `docs/du-lieu-luong-demo.md` để mở ra là biết case nào ở đâu.

CÁCH CHẠY

    EPL_ENV_FILE=/duong/den/.env.sqlite python scripts/don_va_gieo_10_case_demo.py

Máy chủ phải đang chạy ở `http://127.0.0.1:8011` (đổi bằng biến `EPL_GOC`).
"""

import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

GOC = os.environ.get("EPL_GOC", "http://127.0.0.1:8011")
VN = timezone(timedelta(hours=7))
DAU = uuid.uuid4().hex[:8]

THU_MUC_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
DUONG_DB = os.path.join(THU_MUC_APP, "epl_sqlite_lam_viec.db")

DEM = {"xanh": 0, "do": 0}
LOI = []
SO_KE = []


# ================================================ chạy được trên CẢ HAI cơ sở dữ liệu

#: Đường tới cơ sở dữ liệu mà MÁY CHỦ đang dùng, đọc từ cùng một `.env`.
#:
#: VÌ SAO KHÔNG ĐÓNG CỨNG VÀO SQLITE NỮA. Bản trước mở thẳng
#: `epl_sqlite_lam_viec.db` bằng `sqlite3`, nên nó chỉ dọn và chuẩn hoá được
#: SQLite — mà PostgreSQL mới là cơ sở dữ liệu chuẩn của dự án. Hệ quả: khi
#: PostgreSQL tới được, bộ dữ liệu demo trên đó vẫn là bộ CŨ (5 báo giá ở
#: `approved` theo luồng đã bỏ) và không có cách nào gieo lại ngoài việc viết
#: một bản thứ hai của tệp lệnh này — tức hai bản sẽ trôi khỏi nhau.
#:
#: Nay tệp lệnh đọc `DATABASE_URL` giống hệt máy chủ, nên nó luôn dọn ĐÚNG cơ
#: sở dữ liệu mà máy chủ đang ghi vào. Chọn cơ sở dữ liệu nào là việc của
#: `EPL_ENV_FILE`, không phải việc của tệp lệnh.
def _duong_csdl():
    from dotenv import load_dotenv
    tep_env = os.environ.get("EPL_ENV_FILE") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    load_dotenv(tep_env)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Không đọc được DATABASE_URL từ %s" % tep_env)
    return url


class KetNoi:
    """Một kết nối dùng được y như `sqlite3`, nhưng chạy trên cả PostgreSQL.

    Lớp bọc này giữ nguyên API của `sqlite3` (`execute(sql, tuple)` trả về thứ
    có `.fetchone()`, cộng `commit()` và `close()`) để hai mươi chỗ gọi trong
    tệp này không phải sửa. Đổi cả hai mươi chỗ sang SQLAlchemy là hai mươi cơ
    hội gõ sai một câu SQL xoá dữ liệu.

    Nó dịch dấu `?` sang tham số có tên, vì `psycopg2` không hiểu `?`.
    """

    def __init__(self, url):
        from sqlalchemy import create_engine
        self.url = url
        self.postgres = url.startswith("postgres")
        self._may = create_engine(url)
        self._kn = self._may.connect()

    def execute(self, sql, tham=()):
        from sqlalchemy import text
        if tham:
            goi = {}
            ra = []
            i = 0
            for k in sql:
                if k == "?":
                    ra.append(":p%d" % i)
                    goi["p%d" % i] = tham[i]
                    i += 1
                else:
                    ra.append(k)
            if i != len(tham):
                raise ValueError("số dấu ? (%d) khác số tham số (%d): %s" % (i, len(tham), sql))
            return self._kn.execute(text("".join(ra)), goi)
        return self._kn.execute(text(sql))

    def commit(self):
        self._kn.commit()

    def close(self):
        try:
            self._kn.close()
        finally:
            self._may.dispose()


def ket_noi():
    return KetNoi(_duong_csdl())


def co_bang(c, ten):
    """Bảng có tồn tại không — hỏi đúng theo từng loại cơ sở dữ liệu.

    Bản trước hỏi `sqlite_master`, và trên PostgreSQL câu đó ném lỗi
    `UndefinedTable` chứ không trả về rỗng — nên mọi phép kiểm sau nó cũng vỡ
    theo (PostgreSQL huỷ cả giao dịch khi một câu lỗi).
    """
    if c.postgres:
        return bool(list(c.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = ?", (ten,))))
    return bool(list(c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (ten,))))


def dat_hoac_thay(c, bang, cac_cot, gia_tri):
    """`INSERT OR REPLACE` của SQLite, viết lại cho cả PostgreSQL.

    PostgreSQL không có `INSERT OR REPLACE`; câu tương đương là
    `ON CONFLICT (<khoá chính>) DO UPDATE SET ...`. Cột đầu trong `cac_cot`
    được coi là khoá chính — đúng với hai bảng dùng hàm này (`roles`, `users`).
    """
    cot = ", ".join('"%s"' % x for x in cac_cot)
    cho = ", ".join("?" for _ in cac_cot)
    if not c.postgres:
        c.execute('INSERT OR REPLACE INTO "%s" (%s) VALUES (%s)' % (bang, cot, cho), gia_tri)
        return
    dat = ", ".join('"%s" = EXCLUDED."%s"' % (x, x) for x in cac_cot[1:])
    c.execute('INSERT INTO "%s" (%s) VALUES (%s) ON CONFLICT ("%s") DO UPDATE SET %s'
              % (bang, cot, cho, cac_cot[0], dat), gia_tri)


# ======================================================================= hạ tầng

def goi(duong, than=None, cach="GET", dau=None):
    tieu_de = {"Content-Type": "application/json"}
    if dau:
        tieu_de["Idempotency-Key"] = dau
    yc = urllib.request.Request(
        GOC + duong,
        data=json.dumps(than, ensure_ascii=False).encode("utf-8") if than is not None else None,
        method=cach, headers=tieu_de)
    try:
        with urllib.request.urlopen(yc, timeout=120) as tra:
            return tra.status, json.loads(tra.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"detail": raw[:400]}
    except Exception as e:                                        # noqa: BLE001
        return 0, {"detail": "%s: %s" % (type(e).__name__, e)}


def dang(duong, truong, cac_tep, dau=None):
    """Gửi biểu mẫu multipart bằng thư viện chuẩn (không cần gói ngoài)."""
    bien = "----EPL" + uuid.uuid4().hex
    phan = []
    for k, v in truong.items():
        phan.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                     % (bien, k, v)).encode("utf-8"))
    for ten, (ten_tep, kieu, noi) in cac_tep.items():
        phan.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                     "Content-Type: %s\r\n\r\n" % (bien, ten, ten_tep, kieu)).encode("utf-8"))
        phan.append(noi)
        phan.append(b"\r\n")
    phan.append(("--%s--\r\n" % bien).encode("utf-8"))
    than = b"".join(phan)
    tieu_de = {"Content-Type": "multipart/form-data; boundary=%s" % bien,
               "Content-Length": str(len(than))}
    if dau:
        tieu_de["Idempotency-Key"] = dau
    yc = urllib.request.Request(GOC + duong, data=than, method="POST", headers=tieu_de)
    try:
        with urllib.request.urlopen(yc, timeout=180) as tra:
            return tra.status, json.loads(tra.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"detail": raw[:400]}


def chu(g):
    if not isinstance(g, dict):
        return str(g)[:260]
    for lay in (lambda: g["message"], lambda: g["error"]["message"],
                lambda: g["detail"]["message"], lambda: g["detail"]):
        try:
            v = lay()
            if isinstance(v, str) and v.strip():
                return v.strip()[:260]
        except (KeyError, TypeError):
            continue
    return json.dumps(g, ensure_ascii=False)[:260]


def du_lieu(g):
    if isinstance(g, list):
        return g
    return (g or {}).get("data", g) or {}


def kiem(ten, dieu_kien, ghi=""):
    if dieu_kien:
        DEM["xanh"] += 1
        print("   [OK ] %s%s" % (ten, (" — " + ghi) if ghi else ""))
    else:
        DEM["do"] += 1
        LOI.append(ten + ((" — " + ghi) if ghi else ""))
        print("   [LỖI] %s%s" % (ten, (" — " + ghi) if ghi else ""))
    return bool(dieu_kien)


def tien(x):
    try:
        return "{:,.0f}".format(float(x or 0)).replace(",", ".")
    except (TypeError, ValueError):
        return str(x)


def M(phut):
    """Mốc cách bây giờ `phut` phút, kèm múi giờ +07:00.

    Cả bộ dữ liệu neo vào HIỆN TẠI chứ không vào một ngày cố định: máy chủ chặn
    sự kiện vận tải ở tương lai xa, và một chuyến "đang giao" của tuần sau thì
    màn Theo dõi không hiện. Chạy lại tệp này ngày nào cũng ra một bộ dữ liệu
    đúng ngày đó.
    """
    return (datetime.now(VN) + timedelta(minutes=phut)).replace(
        second=0, microsecond=0).isoformat()


def ngay(cong=0):
    return (datetime.now(VN) + timedelta(days=cong)).date().isoformat()


def de(s):
    print()
    print("=" * 78)
    print(s)
    print("=" * 78)


# =============================================================== 1. DỌN DỮ LIỆU

#: Bảng giao dịch, XOÁ THEO THỨ TỰ NÀY — con trước, cha sau.
#:
#: Thứ tự không phải để làm vừa lòng ràng buộc khoá ngoại (SQLite chỉ bật kiểm
#: khi có PRAGMA), mà để nếu dừng giữa đường thì không còn dòng con trỏ vào một
#: cha đã mất — một bản ghi mồ côi khó tìm hơn một bảng rỗng.
BANG_GIAO_DICH = [
    "journal_lines", "journal_batches", "ar_invoices",
    "delivery_order_charge_adjustments", "delivery_order_closeouts",
    "delivery_pod_documents", "delivery_pod_records",
    "freight_charge_items", "freight_actual_costs",
    "parking_events", "parking_labels", "parking_list_items", "parking_lists",
    "transport_events", "vehicle_tracking",
    "trip_delivery_orders", "transport_trip_legs",
    "resource_assignments", "transport_trips",
    "freight_order_legacy_links", "freight_orders",
    "delivery_order_details", "delivery_orders",
    "sales_order_lines", "sales_order_documents", "sales_orders",
    "quotation_attachments", "quotation_items", "quotation_versions", "quotations",
    "epl_expense_vouchers", "vehicle_maintenance_requests",
    "idempotency_records",
    # CA TRUC cung xoa han roi gieo lai. Bo demo cu co ca 8 tieng, ma dieu phoi
    # doi lich bao phu TOAN BO thoi gian chuyen — mot chuyen di va ve dai hon
    # tam tieng, nen nhung ca do lam moi lenh dieu phoi bi tu choi. Do la du
    # lieu khong di duoc luong, khong phai du lieu cu.
    "driver_shift_assignments",
]

def thu_tu_xoa(c, cac_bang):
    """Sắp lại thứ tự xoá theo KHOÁ NGOẠI THẬT của cơ sở dữ liệu: con trước, cha sau.

    VÌ SAO CẦN. PostgreSQL **cưỡng chế khoá ngoại**, SQLite trong dự án này thì
    không (mặc định SQLite không bật, và bộ nâng cấp còn chủ động
    `PRAGMA foreign_keys=OFF`). Nên một thứ tự xoá viết bằng tay chạy trơn trên
    SQLite hoàn toàn có thể vỡ trên PostgreSQL — và đã vỡ thật:

        ForeignKeyViolation: update or delete on table "freight_actual_costs"
        violates foreign key constraint "epl_expense_vouchers_cost_id_fkey"
        DETAIL: Key (id)=(DEMO-COST-2026-003) is still referenced from
                table "epl_expense_vouchers".

    Danh sách viết tay để `epl_expense_vouchers` ở gần cuối, sau
    `freight_actual_costs` mà nó trỏ vào.

    Không sửa bằng cách đổi chỗ hai dòng trong danh sách: lần sau thêm một bảng
    mới là lại vỡ, và người sửa lúc đó phải tự dựng lại cây phụ thuộc trong đầu.
    Thay vào đó ĐỌC quan hệ thật từ siêu dữ liệu và sắp thứ tự (sắp topo). Danh
    sách viết tay vẫn được tôn trọng làm thứ tự ưu tiên giữa các bảng không phụ
    thuộc nhau, nên hành vi trên SQLite không đổi.
    """
    from sqlalchemy import inspect as _inspect
    tt = _inspect(c._may)
    trong_ds = list(cac_bang)
    tap = set(trong_ds)
    # cha[b] = các bảng mà `b` TRỎ VÀO (phải xoá `b` trước chúng)
    cha = {}
    for b in trong_ds:
        try:
            cha[b] = {k["referred_table"] for k in tt.get_foreign_keys(b)
                      if k.get("referred_table") in tap and k.get("referred_table") != b}
        except Exception:
            cha[b] = set()

    ra, con_lai = [], list(trong_ds)
    while con_lai:
        # Bảng nào KHÔNG còn bảng nào trong `con_lai` trỏ vào nó thì xoá được ngay.
        duoc = [b for b in con_lai
                if not any(b in cha[x] for x in con_lai if x != b)]
        if not duoc:
            # Vòng phụ thuộc (khoá ngoại vòng tròn). Giữ nguyên thứ tự còn lại
            # và để lỗi lộ ra kèm tên bảng, thay vì lặp vô hạn.
            ra.extend(con_lai)
            break
        for b in duoc:
            ra.append(b)
            con_lai.remove(b)
    return ra


#: Bảng dữ liệu gốc — chỉ xoá những dòng THỬ NGHIỆM `AZ-*`, giữ phần `DEMO-*`.
BANG_GOC_CAN_LOC = [
    ("driver_qualifications", "driver_id"),
    ("cost_formulas", "id"),
    ("vehicles", "id"),
    ("drivers", "id"),
    ("routes", "id"),
    ("vehicle_types", "id"),
    ("customers", "id"),
]


#: Nơi đặt bản sao PostgreSQL. Đã có trong `.gitignore` — tệp dump chứa dữ liệu
#: thật của khách hàng, chuyến và tiền, nên không bao giờ được chốt vào git.
THU_MUC_SAO_LUU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backups")

#: `pg_dump` không có trong PATH trên máy này; bản cài PostgreSQL 18 để nó ở đây.
PG_DUMP = [
    "pg_dump",
    r"C:/Program Files/PostgreSQL/18/bin/pg_dump.exe",
    r"C:/Program Files/PostgreSQL/17/bin/pg_dump.exe",
    r"C:/Program Files/PostgreSQL/16/bin/pg_dump.exe",
]


def sao_luu_truoc_khi_xoa(c):
    """Sao lưu ĐÚNG THEO LOẠI cơ sở dữ liệu, và KHÔNG xoá nếu chưa sao lưu được.

    SQLite thì sao lưu là sao chép một tệp. PostgreSQL thì phải `pg_dump` —
    bản trước sao chép `epl_sqlite_lam_viec.db` bất kể máy chủ đang dùng gì,
    nên chạy trên PostgreSQL là xoá dữ liệu thật mà bản sao lại là một tệp
    SQLite không liên quan.

    Trả về đường dẫn bản sao, hoặc `None` nếu không sao lưu được — và người gọi
    PHẢI dừng khi nhận `None`. Xoá dữ liệu thật mà không có đường về là việc
    không được làm dù tệp lệnh có tiện đến đâu.
    """
    import shutil as _sh
    import subprocess
    import urllib.parse as _up

    if not c.postgres:
        if not os.path.isfile(DUONG_DB):
            kiem("tìm thấy tệp cơ sở dữ liệu", False, DUONG_DB)
            return None
        ban_sao = "%s.truoc-khi-don-%s.bak" % (
            DUONG_DB, datetime.now().strftime("%Y%m%d-%H%M%S"))
        _sh.copy2(DUONG_DB, ban_sao)
        return ban_sao

    p = _up.urlparse(c.url.replace("postgresql+psycopg2://", "postgresql://"))
    csdl = (p.path or "/").lstrip("/")
    cong_cu = next((x for x in PG_DUMP if _sh.which(x) or os.path.isfile(x)), None)
    if not cong_cu:
        kiem("tìm thấy pg_dump để sao lưu PostgreSQL", False,
             "đã thử: " + ", ".join(PG_DUMP))
        return None
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    ban_sao = os.path.join(THU_MUC_SAO_LUU, "postgres-%s-truoc-khi-don-%s.dump" % (
        csdl, datetime.now().strftime("%Y%m%d-%H%M%S")))
    kq = subprocess.run(
        [cong_cu, "-h", p.hostname or "localhost", "-p", str(p.port or 5432),
         "-U", _up.unquote(p.username or ""), "-d", csdl, "-Fc", "-f", ban_sao],
        env=dict(os.environ, PGPASSWORD=_up.unquote(p.password or "")),
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if kq.returncode:
        kiem("pg_dump chạy được", False, (kq.stderr or "")[:200])
        return None
    return ban_sao


def don_du_lieu():
    de("1. DỌN DỮ LIỆU SAI VÀ DỮ LIỆU THỬ NGHIỆM")
    c = ket_noi()
    print("   Cơ sở dữ liệu: %s" % ("PostgreSQL" if c.postgres else "SQLite"))

    # SAO LƯU TRƯỚC KHI XOÁ. Một bản sao vài trăm KB rẻ hơn vô cùng so với việc
    # dựng lại cả bộ dữ liệu demo lúc 2 giờ sáng.
    ban_sao = sao_luu_truoc_khi_xoa(c)
    if not ban_sao:
        c.close()
        print("   KHÔNG XOÁ GÌ — chưa sao lưu được thì không được xoá.")
        return False
    print("   Đã sao lưu:", ban_sao)

    try:
        tong_xoa = 0
        print("   -- Xoá dữ liệu giao dịch")
        for t in thu_tu_xoa(c, BANG_GIAO_DICH):
            if not co_bang(c, t):
                continue
            n = c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
            if n:
                c.execute('DELETE FROM "%s"' % t)
                tong_xoa += n
                print("      %-40s xoá %5d dòng" % (t, n))
        print("   -- Xoá bản ghi thử nghiệm AZ-*")
        for t, cot in BANG_GOC_CAN_LOC:
            if not co_bang(c, t):
                continue
            n = c.execute('SELECT COUNT(*) FROM "%s" WHERE "%s" LIKE ?' % (t, cot),
                          ("AZ-%",)).fetchone()[0]
            if n:
                c.execute('DELETE FROM "%s" WHERE "%s" LIKE ?' % (t, cot), ("AZ-%",))
                tong_xoa += n
                print("      %-40s xoá %5d dòng" % (t, n))
        # Địa điểm do bài soi sinh ra: giữ những điểm CÓ toạ độ (chúng dùng được
        # cho tuyến thật), xoá những dòng rỗng không ai tham chiếu.
        if co_bang(c, "locations"):
            n = c.execute("SELECT COUNT(*) FROM locations WHERE id LIKE 'LOC-%' "
                          "AND (latitude IS NULL OR longitude IS NULL)").fetchone()[0]
            if n:
                c.execute("DELETE FROM locations WHERE id LIKE 'LOC-%' "
                          "AND (latitude IS NULL OR longitude IS NULL)")
                tong_xoa += n
                print("      %-40s xoá %5d dòng (địa điểm rỗng toạ độ)" % ("locations", n))
        c.commit()
        kiem("dọn xong", True, "tổng %d dòng đã xoá" % tong_xoa)
        return True
    finally:
        c.close()


def chuan_lai_du_lieu_goc():
    """Sửa những chỗ dữ liệu gốc KHÔNG ĐI ĐƯỢC LUỒNG.

    Ba thứ, và cả ba đều là dữ liệu sai chứ không phải dữ liệu cũ:

      · TRẠNG THÁI XE viết ba kiểu. Điều phối chỉ nhận đúng "Sẵn sàng"
        (`READY_VEHICLE`), nên bảy xe ghi "active" là bảy xe không điều phối
        được — mà nhìn màn hình thì chúng vẫn xanh.
      · HẠN BẢO DƯỠNG đã quá. Bốn xe có hạn bảo dưỡng từ đầu năm, và cửa kiểm
        `_require_legal_vehicle` chặn đúng. Đẩy hạn về tương lai cho bộ demo.
      · TRẠNG THÁI TÀI XẾ. Sau những lần thử nghiệm, một số tài xế còn mắc ở
        "đang chạy" cho những chuyến đã bị xoá.
    """
    de("2. CHUẨN LẠI DỮ LIỆU GỐC CHO ĐÚNG LUỒNG")
    c = ket_noi()
    try:
        n = c.execute("SELECT COUNT(*) FROM vehicles WHERE status <> 'Sẵn sàng'").fetchone()[0]
        c.execute("UPDATE vehicles SET status = 'Sẵn sàng'")
        print("   Trạng thái xe: đưa %d xe về 'Sẵn sàng' (điều phối chỉ nhận chuỗi này)" % n)

        han_xa, han_gan = ngay(400), ngay(120)
        n = c.execute("SELECT COUNT(*) FROM vehicles WHERE maintenance_date < ? "
                      "OR maintenance_date IS NULL", (ngay(0),)).fetchone()[0]
        c.execute("UPDATE vehicles SET inspection_exp = ?, insurance_date = ?, "
                  "maintenance_date = ?", (han_xa, han_xa, han_gan))
        print("   Ba hạn pháp lý: đặt lại cho mọi xe (%d xe đang quá hạn bảo dưỡng)" % n)

        # CỘT `vehicles.type` PHẢI GIỮ MÃ LOẠI XE, không giữ tên.
        #
        # Hai xe đang ghi "Container 20FT" — tên hiển thị — thay vì
        # `DEMO-VT-20FT`. Mọi phép tra loại xe đi theo mã, nên hai xe đó không
        # khớp loại nào: điều phối không so được năng lực, và giá thành không
        # tìm được công thức.
        for r in list(c.execute("SELECT id, name FROM vehicle_types")):
            c.execute("UPDATE vehicles SET type = ? WHERE type = ?", (r[0], r[1]))
        print("   Cột loại xe của đội xe: đưa tên hiển thị về mã loại xe")

        # NGƯỜI DUYỆT CHI PHÍ — một người thứ hai, và cố ý KHÔNG có quyền tạo.
        #
        # Quy tắc bốn mắt của bảng chi phí thực: người vận hành trình, trưởng
        # phòng tài chính duyệt, và máy chủ chặn người tạo tự duyệt bảng của
        # mình. Bộ dữ liệu chỉ có MỘT người dùng (`demo-dispatcher`) nên không
        # ai duyệt được, và báo cáo doanh thu hiện lãi gộp 100% — con số đầu
        # tiên người xem demo nhìn vào, và nó sai.
        #
        # Vai của người này KHÔNG có `finance_creator`: một người duyệt mà cũng
        # tạo được thì quy tắc bốn mắt chỉ còn là một dòng chữ.
        #
        # Đây là dữ liệu PHÂN QUYỀN, tức việc của hệ thống cha cấp tài khoản —
        # không có đường API nào trong module này để tạo, nên ghi thẳng bảng.
        dat_hoac_thay(c, "roles", ("id", "permissions"),
                      ("DEMO-TMS-FINANCE-APPROVER",
                       '["finance_read", "finance_approver", "finance_poster"]'))
        dat_hoac_thay(c, "users", ("id", "username", "role_id"),
                      ("truong-phong-tai-chinh", "truong-phong-tai-chinh",
                       "DEMO-TMS-FINANCE-APPROVER"))
        print("   Người duyệt chi phí: truong-phong-tai-chinh (không có quyền tạo)")

        n = c.execute("SELECT COUNT(*) FROM drivers WHERE status <> '🟢 Rảnh (Sẵn sàng)'").fetchone()[0]
        c.execute("UPDATE drivers SET status = '🟢 Rảnh (Sẵn sàng)', assigned_vehicle = 'Chưa gán'")
        print("   Trạng thái tài xế: giải phóng %d người còn mắc ở chuyến đã xoá" % n)
        c.commit()
        kiem("chuẩn lại dữ liệu gốc", True, "")
    finally:
        c.close()

    # KỲ KẾ TOÁN phải MỞ cho hôm nay, nếu không thì không phát hành hoá đơn được
    # và ba case "hoàn tất" sẽ dừng ở bước cuối.
    ma, g = goi("/api/master-data/accounting-periods", {
        "id": "KY-%s" % datetime.now(VN).strftime("%Y-%m"),
        "name": "Kỳ %s" % datetime.now(VN).strftime("%m/%Y"),
        "starts_at": datetime.now(VN).replace(day=1, hour=0, minute=0, second=0,
                                              microsecond=0).isoformat(),
        "ends_at": (datetime.now(VN).replace(day=1) + timedelta(days=62)).replace(
            hour=23, minute=59, second=59, microsecond=0).isoformat(),
        "status": "open",
    }, "POST")
    print("   Kỳ kế toán tháng này:", ma, chu(g)[:120])

    # BẰNG LÁI và CA TRỰC cho tổ lái sẽ dùng.
    ma, g = goi("/api/drivers")
    ds_tx = du_lieu(g)
    ds_tx = ds_tx if isinstance(ds_tx, list) else (ds_tx.get("items") or [])
    chinh = [x for x in ds_tx if "chính" in str(x.get("role") or "")]
    phu = [x for x in ds_tx if "hụ xe" in str(x.get("role") or "")]
    so_bl = so_ca = 0
    for x in chinh + phu:
        m, _ = goi("/api/tms/driver-qualifications", {
            "driver_id": x["id"], "license_type": x.get("license_type") or "Hạng FC",
            "valid_from": ngay(-400), "valid_to": ngay(400), "status": "active",
        }, "POST")
        so_bl += 1 if m in (200, 201) else 0
        # Ca trực phủ RỘNG: từ 12 giờ trước tới 3 ngày sau. Điều phối đòi lịch
        # bao phủ TOÀN BỘ thời gian chuyến, nên một ca 8 tiếng không phủ nổi
        # một chuyến khứ hồi có chặng về.
        for i, (bd, kt) in enumerate(((-720, 720), (720, 2880), (2880, 5040)), start=1):
            m, _ = goi("/api/tms/scheduling/driver-shifts", {
                "id": "SHIFT-DEMO-%s-%d" % (x["id"], i),
                "driver_id": x["id"], "shift_type": "custom", "availability_kind": "work",
                "shift_start": M(bd), "shift_end": M(kt),
                "work_location": x.get("depot_code") or "Bãi trung tâm",
                "status": "confirmed", "notes": "Ca của bộ dữ liệu demo",
            }, "POST")
            so_ca += 1 if m in (200, 201) else 0
    kiem("bằng lái và ca trực cho tổ lái", so_bl >= len(chinh) and so_ca > 0,
         "%d bằng lái · %d ca · %d lái chính · %d phụ xe"
         % (so_bl, so_ca, len(chinh), len(phu)))
    return chinh, phu


def chuan_lai_tuyen():
    """Bảo đảm mọi tuyến demo có km và toạ độ — nếu không thì bản đồ trắng."""
    print("   -- Toạ độ điểm của các tuyến")
    ma, g = goi("/api/routes")
    ds = du_lieu(g)
    thieu = []
    for r in (ds if isinstance(ds, list) else []):
        for t in (r.get("diem_thieu_toa_do") or []):
            if t not in thieu:
                thieu.append(t)
    if not thieu:
        kiem("mọi điểm của tuyến đều có toạ độ", True, "%d tuyến" % len(ds))
        return
    # Khai TAY cho những điểm dịch vụ ngoài không biết. Đây là đường chốt cuối,
    # và nó chỉ dùng được vì mỗi đầu chặng đều đã có một dòng trong bảng địa
    # điểm (xem `toa_do_diem.bao_dam_dia_diem`).
    ma, g = goi("/api/locations/coordinates")
    d = du_lieu(g)
    theo_ten = {x["name"]: x for x in (d.get("dia_diem") or [])}
    da = 0
    for ten in thieu:
        x = theo_ten.get(ten)
        if x and x.get("latitude") is None and ten in TOA_DO_BO_SUNG:
            la, lo = TOA_DO_BO_SUNG[ten]
            m, _ = goi("/api/locations/%s/coordinates" % urllib.parse.quote(x["id"]),
                       {"latitude": la, "longitude": lo}, "PUT")
            da += 1 if m == 200 else 0
    kiem("khai tay toạ độ cho điểm còn thiếu", True,
         "%d/%d điểm đã khai · còn thiếu: %s"
         % (da, len(thieu), [t for t in thieu if t not in TOA_DO_BO_SUNG]))


def nap_hinh_duong_bo():
    """Lấy và LƯU hình đường bộ thật cho từng tuyến, trước buổi demo.

    Đường `GET /api/routes` cố ý KHÔNG gọi ra ngoài — một tuyến bốn điểm là sáu
    lượt tra toạ độ, và làm vậy mỗi lần mở màn Dữ liệu gốc thì màn đó chờ mấy
    chục giây. Đường `/geo` thì được phép, và nó GHI LẠI hình vào tuyến.

    Nạp trước ở đây có hai cái được: buổi demo mở bản đồ là thấy ngay, và nó
    vẫn thấy KỂ CẢ KHI MẤT MẠNG — đúng tình huống đã từng làm bản đồ trắng.
    """
    print("   -- Nạp sẵn hình đường bộ thật cho từng tuyến")
    ma, g = goi("/api/routes")
    ds = du_lieu(g)
    xong = 0
    for r in (ds if isinstance(ds, list) else []):
        ma, g = goi("/api/routes/%s/geo" % urllib.parse.quote(str(r.get("id"))))
        d = du_lieu(g)
        if d.get("duong_bo"):
            xong += 1
            print("      %-30s %4d điểm hình · %s km đường bộ · nguồn %s"
                  % (r.get("id"), len(d.get("duong_bo") or []),
                     d.get("km_duong_bo"), d.get("nguon_duong_bo")))
        else:
            print("      %-30s CHƯA VẼ ĐƯỢC — thiếu toạ độ: %s"
                  % (r.get("id"), d.get("diem_thieu_toa_do")))
    kiem("tuyến đã có hình đường bộ lưu sẵn", xong > 0,
         "%d/%d tuyến" % (xong, len(ds if isinstance(ds, list) else [])))


#: Toạ độ khai tay cho những điểm nội bộ mà dịch vụ tra toạ độ không biết.
#: Đây là BẢNG MỒI, và nó được ghi vào bảng địa điểm ngay lần đầu dùng — không
#: phải một hằng số vĩnh viễn trong mã.
TOA_DO_BO_SUNG = {
    "Bãi Sóng Thần": (10.8894, 106.7294),
    "KCN Sóng Thần 1, Dĩ An": (10.8894, 106.7294),
    "Vành đai 3": (10.8769, 106.7734),
    "KCN Amata": (10.9458, 106.8671),
    "Kho Long An": (10.6086, 106.4692),
    "Kho Long An, Bến Lức": (10.6086, 106.4692),
    "Cảng Cái Mép": (10.5303, 107.0302),
    "Cảng Cái Mép, Bà Rịa": (10.5303, 107.0302),
    "Kho VSIP II-A, Bình Dương": (11.0497, 106.7428),
    "Cảng Cát Lái, TP. Thủ Đức": (10.7567, 106.7828),
}


# ============================================================== 3. MƯỜI CASE

#: Mười case, mỗi case DỪNG Ở MỘT CHẶNG KHÁC NHAU của luồng.
#:
#: VÌ SAO KHÔNG GIEO CẢ MƯỜI CASE Ở TRẠNG THÁI "XONG": một bộ dữ liệu toàn
#: chuyến đã đóng làm màn Điều phối trống, màn Theo dõi trống, và hàng đợi "cần
#: xử lý" trống — tức ba màn của người vận hành không có gì để xem. Buổi demo
#: cần thấy cả đường ống, không chỉ cái đuôi.
#:
#: `chang` nhận: nhap · cho_duyet · cho_khach · da_tach · dang_giao · xong
CASE = [
    {"ma": "C01", "chang": "xong", "khach": "DEMO-CUS-NIDEC",
     "tuyen": "DEMO-RT-VSIP2A-CATLAI", "loai_xe": "DEMO-VT-TRACTOR40",
     "kg": 24000, "m3": 58, "don_vi": "per_trip", "he_so_gia": 1.45,
     "hang": [("Linh kiện motor điện", 2, "40'", "xếp 2 lớp, tránh ẩm")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 40'",
     "chuyen_thang": 26, "nguoi_nhan": "Cổng B · Phạm T. Nga · 0912345678"},

    {"ma": "C02", "chang": "xong", "khach": "DEMO-CUS-SGNFOOD",
     "tuyen": "DEMO-RT-SONGTHAN-CATLAI", "loai_xe": "DEMO-VT-20FT",
     "kg": 22000, "m3": 30, "don_vi": "per_trip", "he_so_gia": 1.5,
     "hang": [("Gạo đóng bao 50kg", 2, "20'", "kê pallet, không xếp chồng")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 20'",
     "chuyen_thang": 40, "nguoi_nhan": "Cổng A · Trần V. Long · 0908111222"},

    {"ma": "C03", "chang": "xong", "khach": "DEMO-CUS-POUYUEN",
     "tuyen": "DEMO-RT-LONGAN-CAIMEP", "loai_xe": "DEMO-VT-TRACTOR40",
     "kg": 26000, "m3": 62, "don_vi": "per_tonne", "he_so_gia": 1.42,
     "hang": [("Giày xuất khẩu", 2, "40'", "hàng dễ móp, chèn kỹ")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 40'",
     "chuyen_thang": 18, "nguoi_nhan": "Cổng CM3 · Lê T. Hoa · 0933444555"},

    {"ma": "C04", "chang": "dang_giao", "khach": "DEMO-CUS-COLGATE",
     "tuyen": "DEMO-RT-VSIP2A-CAIMEP", "loai_xe": "DEMO-VT-TRACTOR20",
     "kg": 20000, "m3": 30, "don_vi": "per_trip", "he_so_gia": 1.48,
     "hang": [("Kem đánh răng thùng carton", 2, "20'", "không xếp chồng quá 2 lớp")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 20'",
     "chuyen_thang": 22, "nguoi_nhan": "Cổng CM1 · Vũ M. Tuấn · 0977888999"},

    {"ma": "C05", "chang": "dang_giao", "khach": "DEMO-CUS-UNILEVER",
     "tuyen": "DEMO-RT-CATLAI-AMATA", "loai_xe": "DEMO-VT-TRUCK15",
     "kg": 14000, "m3": 55, "don_vi": "per_trip", "he_so_gia": 1.52,
     "hang": [("Bột giặt đóng thùng", 2, "Kiện", "hàng nhập, giao nội bộ KCN")],
     "loai_hang": "Hàng khô", "quy_cach": "Hàng rời, đổ ben — cân tại kho",
     "chuyen_thang": 30, "nguoi_nhan": "Kho A2 · Đỗ V. Hùng · 0966555444"},

    {"ma": "C06", "chang": "da_tach", "khach": "DEMO-CUS-NIDEC",
     "tuyen": "DEMO-RT-SONGTHAN-CATLAI", "loai_xe": "DEMO-VT-20FT",
     "kg": 21000, "m3": 30, "don_vi": "per_trip", "he_so_gia": 1.47,
     "hang": [("Linh kiện motor điện", 3, "20'", "giao ba chuyến trong ngày")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 20'",
     "chuyen_thang": 36, "nguoi_nhan": "Cổng B · Phạm T. Nga · 0912345678"},

    {"ma": "C07", "chang": "da_tach", "khach": "DEMO-CUS-SGNFOOD",
     "tuyen": "DEMO-RT-VSIP2A-CATLAI", "loai_xe": "DEMO-VT-TRUCK10",
     "kg": 9500, "m3": 40, "don_vi": "per_tonne", "he_so_gia": 1.55,
     "hang": [("Thực phẩm khô đóng thùng", 2, "Kiện", "giao trước 16:00")],
     "loai_hang": "Hàng khô", "quy_cach": "Thùng carton trên pallet",
     "chuyen_thang": 24, "nguoi_nhan": "Cổng A · Trần V. Long · 0908111222"},

    {"ma": "C08", "chang": "cho_khach", "khach": "DEMO-CUS-COLGATE",
     "tuyen": "DEMO-RT-CATLAI-AMATA", "loai_xe": "DEMO-VT-TRUCK15",
     "kg": 13000, "m3": 52, "don_vi": "per_trip", "he_so_gia": 1.5,
     "hang": [("Kem đánh răng thùng carton", 2, "Kiện", "")],
     "loai_hang": "Hàng khô", "quy_cach": "Thùng carton trên pallet",
     "chuyen_thang": 20, "nguoi_nhan": "Kho A2 · Đỗ V. Hùng · 0966555444"},

    # BIÊN MỎNG CÓ CHỦ Ý — để buổi demo thấy được cửa duyệt nội bộ. Hệ số 1.10
    # cho biên ~9%, dưới ngưỡng 15% nhưng VẪN TRÊN giá thành: báo giá lỗ thì bị
    # chặn hẳn, không vào được trạng thái chờ duyệt.
    {"ma": "C09", "chang": "cho_duyet", "khach": "DEMO-CUS-POUYUEN",
     "tuyen": "DEMO-RT-LONGAN-CAIMEP", "loai_xe": "DEMO-VT-TRACTOR40",
     "kg": 25000, "m3": 60, "don_vi": "per_trip", "he_so_gia": 1.10,
     "hang": [("Giày xuất khẩu", 2, "40'", "khách ép giá, cần trưởng phòng duyệt")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 40'",
     "chuyen_thang": 12, "nguoi_nhan": "Cổng CM3 · Lê T. Hoa · 0933444555"},

    {"ma": "C10", "chang": "nhap", "khach": "DEMO-CUS-UNILEVER",
     "tuyen": "DEMO-RT-VSIP2A-CAIMEP", "loai_xe": "DEMO-VT-TRACTOR20",
     "kg": 19000, "m3": 32, "don_vi": "per_trip", "he_so_gia": 1.5,
     "hang": [("Hàng nhập khẩu", 2, "20'", "chờ khách chốt khung giờ")],
     "loai_hang": "Hàng khô", "quy_cach": "Container nguyên khối 20'",
     "chuyen_thang": 16, "nguoi_nhan": ""},
]

PNG_POD = b"\x89PNG\r\n\x1a\n" + b"POD-DEMO" + b"\x00" * 48
PNG_KY = b"\x89PNG\r\n\x1a\n" + b"CHU-KY-DEMO" + b"\x33" * 48
PDF_HD = (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n"
          b"trailer<</Root 1 0 R>>\n%%EOF\n")


def gia_thanh_cua(c):
    ma, g = goi("/api/quotations/price-preview", {
        "route_id": c["tuyen"], "vehicle_type_id": c["loai_xe"],
        "weight_kg": c["kg"], "customer_id": c["khach"],
    }, "POST")
    d = du_lieu(g)
    if not d.get("tinh_duoc"):
        return None, d.get("viec_con_thieu") or [chu(g)]
    return d, None


def don_gia_tu_gia_thanh(c, gia_thanh):
    """Đơn giá theo ĐƠN VỊ CỦA KHÁCH, suy từ giá thành và hệ số của case.

    Không viết cứng con số: giá thành phụ thuộc công thức loại xe và số km
    đường bộ thật, nên một đơn giá viết cứng sẽ cho ra biên khác hẳn khi ai đó
    sửa giá dầu ở màn Dữ liệu gốc — và case "biên mỏng" sẽ không còn mỏng.
    """
    cuoc_chuyen = gia_thanh * c["he_so_gia"]
    if c["don_vi"] == "per_tonne":
        tan = max(0.001, c["kg"] / 1000.0)
        return round(cuoc_chuyen / tan, -2), cuoc_chuyen
    return round(cuoc_chuyen, -3), cuoc_chuyen


def chon_xe(cac_xe, c):
    """Xe hợp với case: đúng loại xe, và đủ tải cùng đủ thể tích.

    Ưu tiên xe CÙNG LOẠI với loại xe đã khai trên báo giá — giá thành của case
    tính theo công thức của loại đó, nên điều một xe loại khác đi làm con số
    quyết toán không còn khớp báo giá. Không có xe cùng loại thì lấy xe đủ năng
    lực, và nói ra ở sổ kê.
    """
    def du_suc(x):
        try:
            tai = float(x.get("weight_capacity") or 0)
            the_tich = float(x.get("volume_capacity_m3") or 0)
        except (TypeError, ValueError):
            return False
        return tai >= c["kg"] and (the_tich <= 0 or the_tich >= c["m3"])

    cung_loai = [x for x in cac_xe
                 if str(x.get("type") or "") == c["loai_xe"] and du_suc(x)]
    if cung_loai:
        return cung_loai[0]
    du = [x for x in cac_xe if du_suc(x)]
    if du:
        return sorted(du, key=lambda x: float(x.get("weight_capacity") or 0))[0]
    return None


def gieo_mot_case(c, tx_chinh, tx_phu, cac_xe, dem_xe):
    """Gieo một case và đưa nó tới đúng chặng đã khai. Trả về bản ghi sổ kê."""
    print()
    print("-- %s · %s · %s · dừng ở: %s" % (c["ma"], c["khach"], c["tuyen"], c["chang"]))
    so = {"ma": c["ma"], "chang_dich": c["chang"], "khach": c["khach"],
          "tuyen": c["tuyen"], "loai_xe": c["loai_xe"]}

    xt, thieu = gia_thanh_cua(c)
    if xt is None:
        kiem("%s tính được giá thành" % c["ma"], False, str(thieu))
        return so
    gia_thanh = float(xt["gia_thanh"])
    don_gia, cuoc_chuyen = don_gia_tu_gia_thanh(c, gia_thanh)
    so["gia_thanh"] = gia_thanh
    so["km"] = xt.get("km")

    # --- Báo giá, khai ĐẦY ĐỦ mọi trường của bản thiết kế -------------------
    than = {
        "customer_id": c["khach"], "route_id": c["tuyen"],
        "vehicle_type_id": c["loai_xe"],
        "pickup_window_start": M(-240), "pickup_window_end": M(-30),
        "delivery_window_start": M(0), "delivery_window_end": M(420),
        "weight_kg": c["kg"], "volume_m3": c["m3"],
        "pallet_count": 0, "cargo_type": c["loai_hang"],
        "cargo_value": 0, "packaging_spec": c["quy_cach"],
        "temperature_requirement": "",
        "stacking": "Không xếp chồng" if "không xếp" in (c["hang"][0][3] or "").lower()
                    else "Tối đa 2 lớp",
        "sealing": "Có · ghi số seal khi lấy hàng"
                   if "nguyên khối" in c["quy_cach"] else "Không",
        "recipient_contact": c["nguoi_nhan"],
        "valid_to": ngay(45),
        "price_basis": c["don_vi"], "unit_price": don_gia,
        "min_qty_per_trip": round(c["kg"] / 1000.0 * 0.9, 1)
                            if c["don_vi"] == "per_tonne" else 0,
        "total_cost": gia_thanh, "currency_code": "VND", "fx_rate": 1,
        "payment_terms": "30 ngày sau hoá đơn", "waiting_surcharge": 200000,
        "sales_rep": "tran.anh", "trips_per_month": c["chuyen_thang"],
        "notes_customer": "Giá chưa gồm VAT. Phụ phí lưu bãi tính theo thực tế.",
        "notes_ops": c["hang"][0][3] or "Gọi người nhận trước 30 phút.",
        "notes_internal": "Dữ liệu demo — case %s." % c["ma"],
    }
    ma, g = goi("/api/quotations", than, "POST")
    qid = du_lieu(g).get("id")
    if not kiem("%s tạo báo giá" % c["ma"], bool(qid), "%s · %s" % (ma, chu(g))):
        return so
    so["bao_gia"] = qid

    ma, g = goi("/api/quotations/%s/items" % qid, {"items": [
        {"line_no": i + 1, "name": t, "quantity": sl, "uom": dv, "note": gc}
        for i, (t, sl, dv, gc) in enumerate(c["hang"])
    ]}, "PUT")
    kiem("%s bảng hàng hoá" % c["ma"], ma == 200, chu(g))

    dang("/api/quotations/%s/attachments" % qid,
         {"doc_type": "Hợp đồng", "note": "Hợp đồng khung 2026"},
         {"file": ("hop-dong-%s.pdf" % c["ma"], "application/pdf", PDF_HD)})

    ma, g = goi("/api/quotations/%s/detail" % qid)
    q = du_lieu(g)
    so["cuoc"] = q.get("selling_price")
    so["bien"] = q.get("bien")
    so["so_do_du_kien"] = q.get("so_do_du_kien")
    print("      giá thành %s · cước %s · biên %s%% · %s DO dự kiến"
          % (tien(gia_thanh), tien(q.get("selling_price")),
             round((q.get("bien") or 0) * 100, 1), q.get("so_do_du_kien")))

    if c["chang"] == "nhap":
        so["trang_thai"] = q.get("canonical_status")
        return so

    # --- Gửi khách ----------------------------------------------------------
    ma, g = goi("/api/quotations/%s/send" % qid, {}, "POST")
    d = du_lieu(g)
    kiem("%s gửi khách" % c["ma"], ma == 200,
         "trạng thái %s · %s" % (d.get("canonical_status"), chu(g)[:110]))
    so["ma_khach_thay"] = d.get("quote_no")

    if c["chang"] == "cho_duyet":
        so["trang_thai"] = d.get("canonical_status")
        kiem("%s biên mỏng thì vào CHỜ DUYỆT NỘI BỘ" % c["ma"],
             d.get("canonical_status") == "pending_approval",
             "trạng thái: %s" % d.get("canonical_status"))
        return so
    if c["chang"] == "cho_khach":
        so["trang_thai"] = d.get("canonical_status")
        return so

    # --- Khách chấp nhận, rồi tách DO ---------------------------------------
    ma, g = goi("/api/quotations/%s/accept" % qid, {}, "POST")
    kiem("%s khách chấp nhận" % c["ma"], ma == 200, chu(g)[:110])

    n_do = int(so.get("so_do_du_kien") or 1)
    # SỐ NIÊM PHONG cho hàng nguyên khối — nó là một chốt xuất bến, không phải
    # một ô cho đẹp: bước điều phối chặn xe chở hàng nguyên cont mà không có số
    # seal, vì đó là bằng chứng duy nhất cho biết hàng không bị mở trên đường.
    co_seal = "nguyên khối" in c["quy_cach"]
    dong = [{"pickup_at": M(-240 + i * 45), "due_at": M(300 + i * 45),
             "seal_no": ("SL-%s-%s-%02d" % (DAU[:4].upper(), c["ma"], i + 1)
                         if co_seal else ""),
             "driver_note": c["hang"][0][3] or "Mang phiếu giao hàng"}
            for i in range(n_do)]
    ma, g = goi("/api/quotations/%s/split" % qid, {"dos": dong}, "POST")
    d = du_lieu(g)
    ds_do = d.get("do_ids") or []
    kiem("%s tách %d DO" % (c["ma"], n_do), ma == 200 and len(ds_do) == n_do,
         "%s · giá khoá %s đ/chuyến" % (ds_do, tien(d.get("gia_moi_chuyen"))))
    so["do"] = ds_do
    so["gia_khoa"] = d.get("gia_moi_chuyen")

    if c["chang"] == "da_tach" or not ds_do:
        so["trang_thai"] = "split"
        return so

    # --- Lập Trip và điều phối ---------------------------------------------
    # CHON XE PHU HOP, khong chon vong tron.
    #
    # Buoc dieu phoi kiem nang luc xe so voi tong tai trong va the tich cua ca
    # chuyen ("vuot nang luc xe: tai trong 24.000/10.000 kg"), va no kiem dung.
    # Chon vong tron nghia la mot chuyen 24 tan roi vao mot xe 10 tan, va case
    # do dung ngay o buoc dieu phoi.
    xe = chon_xe(cac_xe, c)
    if xe is None:
        kiem("%s có xe phù hợp" % c["ma"], False,
             "cần loại %s, tải >= %s kg, thể tích >= %s m³"
             % (c["loai_xe"], c["kg"], c["m3"]))
        so["trang_thai"] = "split"
        return so
    tx = tx_chinh[dem_xe[0] % len(tx_chinh)]
    px = tx_phu[dem_xe[0] % len(tx_phu)] if tx_phu else None
    dem_xe[0] += 1

    ma_trip = "TRIP-%s-%s" % (DAU.upper(), c["ma"])
    ma, g = goi("/api/tms/trips/from-delivery-orders", {
        # MỘT DO MỘT CHUYẾN — đúng luật của bản thiết kế: "1 DO = 1 cont (hoặc
        # 1 xe) = 1 chuyến".
        #
        # Gộp hai DO vào một chuyến còn làm vỡ bước nộp POD trên tuyến MỘT
        # CHẶNG: tuyến một chặng sinh đúng một chặng giao, chặng đó thuộc một
        # DO, và DO còn lại không có chặng nào để gắn POD nên không hoàn tất
        # được. Đã dò thấy khi gieo: "Phải nộp POD cho đúng tất cả chặng giao
        # của DO".
        #
        # DO còn lại của báo giá ở lại hàng đợi `pending` — và đó cũng là thứ
        # màn Điều phối cần có để xem.
        "id": ma_trip, "do_ids": ds_do[:1], "trip_type": "one_way",
        "planned_departure_at": M(-240), "avg_speed_kmh": 42,
        "dwell_minutes": 30, "return_purpose": "none",
    }, "POST", dau="gieo-trip-%s-%s" % (DAU, c["ma"]))
    d = du_lieu(g)
    if not kiem("%s lập Trip" % c["ma"], ma in (200, 201), "%s · %s" % (ma, chu(g))):
        so["trang_thai"] = "split"
        return so
    so["trip"] = ma_trip
    so["lenh_van_chuyen"] = d.get("freight_order_id")
    pb = int(d.get("version") or 1)

    ma, g = goi("/api/tms/trips/%s/dispatch" % ma_trip, {
        "vehicle_id": xe["id"], "driver_id": tx["id"],
        "co_driver_id": (px or {}).get("id"),
        "expected_version": pb,
        "assignment_start": M(-240), "assignment_end": M(420),
    }, "PUT")
    d = du_lieu(g)
    kiem("%s điều phối xe %s + tổ lái" % (c["ma"], xe["id"]), ma == 200,
         "%s · trạng thái chuyến %s" % (chu(g)[:90], d.get("status")))
    so["xe"] = xe["id"]
    so["tai_xe"] = tx["id"]
    so["phu_xe"] = (px or {}).get("id")

    # --- Mốc thực thi -------------------------------------------------------
    ma_fo = so.get("lenh_van_chuyen")
    if ma_fo:
        ma, g = goi("/api/tms/freight-orders")
        ds_fo = du_lieu(g)
        ds_fo = ds_fo if isinstance(ds_fo, list) else (ds_fo.get("items") or [])
        pbv = int(next((x.get("version") for x in ds_fo if x.get("id") == ma_fo), 1) or 1)
        MOC = [("check_in", "Xe vào cổng lấy hàng", -235),
               ("pickup", "Đã nhận hàng và niêm phong", -205),
               ("departure", "Xuất bến", -190)]
        if c["chang"] == "xong":
            MOC += [("arrival", "Đã đến điểm giao", -70),
                    ("unloading", "Đang hạ hàng", -50)]
        so_moc = 0
        for i, (loai, ghi, phut) in enumerate(MOC, start=1):
            ma, g = goi("/api/tms/freight-orders/%s/events" % ma_fo, {
                "event_type": loai, "expected_version": pbv,
                "event_time": M(phut), "note": ghi,
                "location_text": ghi, "documents": [],
                "source": "manual", "vehicle_id": xe["id"], "driver_id": tx["id"],
            }, "POST", dau="gieo-ev-%s-%s-%d" % (DAU, c["ma"], i))
            if ma in (200, 201):
                so_moc += 1
                d = du_lieu(g)
                pbv = int(d.get("order_version") or d.get("version") or pbv + 1)
            else:
                print("      mốc %s lỗi: %s %s" % (loai, ma, chu(g)[:120]))
                break
        kiem("%s ghi %d mốc thực thi" % (c["ma"], len(MOC)), so_moc == len(MOC),
             "%d/%d" % (so_moc, len(MOC)))
        so["so_moc"] = so_moc

    if c["chang"] == "dang_giao":
        so["trang_thai"] = "in_transit"
        return so

    # --- Hoàn tất giao hàng cho MỌI DO của chuyến ---------------------------
    ma, g = goi("/api/tms/trips/%s" % ma_trip)
    tr = du_lieu(g)
    cac_chang = tr.get("legs") or tr.get("trip_legs") or []
    xong = 0
    for md in ds_do[:1]:
        chang_cua_do = [l for l in cac_chang
                        if str(l.get("leg_type")) == "delivery"
                        and str(l.get("do_id") or "") == md]
        if not chang_cua_do:
            chang_cua_do = [l for l in cac_chang if str(l.get("leg_type")) == "delivery"]
        if not chang_cua_do:
            continue
        goi_pod = {
            "trip_id": ma_trip, "currency_code": "VND",
            "pod_entries": [{
                "leg_id": str(l.get("id")), "vehicle_id": xe["id"], "stop_no": i + 1,
                "location_text": str(l.get("destination") or "Điểm giao"),
                "receiver_name": (c["nguoi_nhan"].split("·")[1].strip()
                                  if "·" in c["nguoi_nhan"] else "Người nhận"),
                "receiver_phone": (c["nguoi_nhan"].split("·")[-1].strip()
                                   if "·" in c["nguoi_nhan"] else "0900000000"),
                "delivery_time": M(-20), "delivery_result": "delivered_full",
                "cargo_condition": "Nguyên kiện, không hư hỏng",
                "file_field": "pod%d" % (i + 1),
                "signature_file_field": "sig%d" % (i + 1),
                "note": "Giao đủ theo chứng từ",
            } for i, l in enumerate(chang_cua_do)],
            "charge_adjustments": [
                {"name": "Phí cầu đường", "original_amount": "0",
                 "actual_amount": "180000", "note": "Hai trạm BOT"},
            ],
        }
        cac_tep = {}
        for i in range(len(chang_cua_do)):
            cac_tep["pod%d" % (i + 1)] = (
                "pod-%s-%d.png" % (md, i), "image/png", PNG_POD + bytes([i, 1]))
            cac_tep["sig%d" % (i + 1)] = (
                "ky-%s-%d.png" % (md, i), "image/png", PNG_KY + bytes([i, 2]))
        ma, g = dang("/api/delivery-orders/%s/complete-delivery" % md,
                     {"payload": json.dumps(goi_pod, ensure_ascii=False)},
                     cac_tep, dau="gieo-pod-%s-%s" % (DAU, md))
        if ma in (200, 201):
            xong += 1
            so["gia_cuoi"] = (du_lieu(g).get("commercials") or {}).get("final_selling_price")
        else:
            print("      hoàn tất %s lỗi: %s %s" % (md, ma, chu(g)[:150]))
    kiem("%s hoàn tất POD cho DO đầu" % c["ma"], xong == 1,
         "%d/1 · giá cuối %s · DO còn lại ở hàng đợi Điều phối"
         % (xong, tien(so.get("gia_cuoi"))))

    # --- Chi phí thực -------------------------------------------------------
    ma, g = goi("/api/tms/trips/%s" % ma_trip)
    tr = du_lieu(g)
    if tr.get("status") != "completed":
        # Chuyến một chiều không có chặng về, nên nó đóng ngay khi mọi DO có
        # POD. Nếu vẫn chưa đóng thì nói ra chứ không lặng lẽ bỏ bước.
        print("      chuyến chưa hoàn thành (%s) — bỏ bước chi phí thực"
              % tr.get("status"))
        so["trang_thai"] = "delivered"
        return so
    # CHI PHÍ THỰC dựng từ ĐÚNG CÁC CẤU PHẦN của giá thành kế hoạch.
    #
    # Không bịa mấy dòng cho có: cả ý nghĩa của bảng này là ĐỐI SOÁT kế hoạch
    # với thực tế, nên `original_amount` phải là con số công thức đã tính, và
    # `actual_amount` là con số chạy thật. Bịa ba dòng nhỏ làm báo cáo hiện lãi
    # gộp 91% — con số đầu tiên người xem demo nhìn vào, và nó vô lý với một
    # báo giá biên 31%.
    #
    # Biến thiên đặt ở khoản DẦU (vượt 5%): đó là khoản biến động thật của một
    # chuyến — đi lệch vì cấm tải, tắc đường, chạy không tải. Phụ cấp và phí bãi
    # là số khoán nên đúng bằng kế hoạch.
    dong_chi = [d for d in (xt.get("cac_dong") or []) if d.get("loai") == "chi"]
    dong_cp = []
    for d in dong_chi:
        ke_hoach = round(float(d.get("thanh_tien") or 0))
        la_dau = str(d.get("khoa") or "") in ("fuel", "dau", "xang_dau")
        dong_cp.append({
            "name": d.get("nhan") or "Chi phí",
            "original_amount": ke_hoach,
            "actual_amount": round(ke_hoach * 1.05) if la_dau else ke_hoach,
            "note": "Vượt 5% vì đi lệch tuyến cấm tải" if la_dau else "Đúng khoán",
        })
    if not any("cầu đường" in x["name"].lower() or "bot" in x["name"].lower()
               for x in dong_cp):
        dong_cp.append({"name": "Phí cầu đường / BOT", "original_amount": 0,
                        "actual_amount": 180000, "note": "Hai trạm BOT"})
    ma, g = goi("/api/tms/finance/trips/%s/actual-cost" % ma_trip, {
        "currency_code": "VND", "lines": dong_cp,
    }, "PUT", dau="gieo-cost-%s-%s" % (DAU, c["ma"]))
    d = du_lieu(g)
    kiem("%s ghi chi phí thực" % c["ma"], ma == 200,
         "%s · tổng %s" % (chu(g)[:70], tien(d.get("total_amount"))))
    so["chi_phi_thuc"] = d.get("total_amount")

    # TRÌNH VÀ DUYỆT chi phí thực.
    #
    # Báo cáo doanh thu chỉ cộng GIÁ THÀNH ĐÃ DUYỆT, nên một bảng chi phí còn ở
    # bản nháp làm báo cáo hiện lãi gộp 100% — một con số không ai tin được, và
    # nó là con số đầu tiên người xem demo nhìn vào.
    ma_cp = d.get("id")
    if ma_cp:
        # `expected_version` là BẮT BUỘC ở cả hai bước — chốt chống ghi đè khi
        # hai người sửa cùng một bảng chi phí. Phiên bản đọc lại sau mỗi bước
        # vì mỗi bước làm nó tăng.
        pb_cp = int(d.get("version") or 1)
        m1, g1 = goi("/api/tms/finance/costs/%s/submit" % ma_cp,
                     {"expected_version": pb_cp}, "POST",
                     dau="gieo-cp-trinh-%s-%s" % (DAU, c["ma"]))
        pb_cp = int((du_lieu(g1) or {}).get("version") or pb_cp + 1)
        m2, g2 = goi("/api/tms/finance/costs/%s/approve" % ma_cp,
                     {"expected_version": pb_cp}, "POST",
                     dau="gieo-cp-duyet-%s-%s" % (DAU, c["ma"]))
        # DUYỆT LÀ VIỆC CỦA NGƯỜI KHÁC, và đó là chốt đúng.
        #
        # Máy chủ trả 403 "Người tạo không được đồng thời duyệt chi phí" — quy
        # tắc bốn mắt. Bộ gieo chạy dưới MỘT danh tính nên nó chỉ TRÌNH được;
        # bước duyệt phải do một người thứ hai bấm, hoặc chạy
        # `scripts/duyet_chi_phi_bang_nguoi_khac.py`.
        #
        # Nên "trình xong" mới là thành công ở đây. Coi 403 ở bước duyệt là lỗi
        # thì bộ gieo báo đỏ cho một quy tắc đang chạy đúng.
        kiem("%s trình chi phí thực (duyệt là việc của người thứ hai)" % c["ma"],
             m1 == 200, "trình %s · duyệt %s: %s" % (m1, m2, chu(g2)[:90]))
        so["chi_phi_cho_duyet"] = (m1 == 200 and m2 != 200)
    so["trang_thai"] = "completed"
    return so


def gieo_muoi_case(tx_chinh, tx_phu):
    de("3. GIEO 10 CASE DEMO ĐI TRỌN LUỒNG")
    ma, g = goi("/api/vehicles")
    ds_xe = du_lieu(g)
    ds_xe = ds_xe if isinstance(ds_xe, list) else (ds_xe.get("items") or [])
    san_sang = [x for x in ds_xe if str(x.get("status") or "") == "Sẵn sàng"]
    print("   Xe sẵn sàng: %d · lái chính: %d · phụ xe: %d"
          % (len(san_sang), len(tx_chinh), len(tx_phu)))
    if not san_sang or not tx_chinh:
        kiem("có xe và tổ lái để điều phối", False, "")
        return
    dem = [0]
    # Xe cua nhung case DANG GIAO bi giu tới het buoi demo, nen bo chung ra khoi
    # danh sach sau khi dung. Ba case "xong" thi tra xe lai, nhung don gian hon
    # la khong dung lai xe nao trong mot lan gieo.
    da_dung = set()
    # THỨ TỰ CÓ Ý: gieo ba case "xong" TRƯỚC. Điều phối làm xe và tài xế thành
    # "đang chạy", và chỉ bước hoàn tất mới giải phóng họ — nên nếu gieo hai
    # case "đang giao" trước thì hai xe bị giữ và ba case sau không còn xe.
    for c in CASE:
        con_lai = [x for x in san_sang if x["id"] not in da_dung]
        so = gieo_mot_case(c, tx_chinh, tx_phu, con_lai or san_sang, dem)
        if so.get("xe"):
            da_dung.add(so["xe"])
        SO_KE.append(so)


# ================================================== 4. ĐỐI CHIẾU VÀ GHI LẠI

NHAN_CHANG = {
    "draft": "Nháp",
    "pending_approval": "Chờ duyệt nội bộ",
    "sent": "Đã gửi · chờ khách",
    "approved": "Đã gửi · chờ khách",
    "accepted": "Đã chấp nhận",
    "split": "Đã tách DO · chờ điều phối",
    "in_transit": "Đang giao",
    "delivered": "Đã giao · chờ quyết toán",
    "completed": "Hoàn tất",
    "rejected": "Từ chối",
    "expired": "Hết hạn",
}


def doi_chieu():
    de("4. ĐỐI CHIẾU: SỐ LIỆU CÓ VÀO CÁC MÀN VÀ BÁO CÁO KHÔNG")

    ma, g = goi("/api/quotations/summary")
    d = du_lieu(g)
    print("   Dải số liệu báo giá:", json.dumps(d, ensure_ascii=False)[:260])
    kiem("dải số liệu báo giá đọc được", ma == 200)

    ma, g = goi("/api/quotations/board?status=all")
    ds = (du_lieu(g) or {}).get("items") or []
    kiem("bảng báo giá có đủ 10 case", len(ds) >= 10, "%d báo giá" % len(ds))

    ma, g = goi("/api/delivery-orders?page=1&page_size=200")
    dd = du_lieu(g)
    dd = dd.get("items") if isinstance(dd, dict) else dd
    theo_tt = {}
    for x in (dd or []):
        theo_tt[x.get("canonical_status")] = theo_tt.get(x.get("canonical_status"), 0) + 1
    print("   Lệnh giao hàng theo trạng thái:", theo_tt)
    kiem("hàng đợi Điều phối có việc", theo_tt.get("pending", 0) > 0,
         "%d DO chờ xử lý" % theo_tt.get("pending", 0))
    kiem("màn Theo dõi có xe đang chạy", theo_tt.get("in_transit", 0) > 0,
         "%d DO đang vận chuyển" % theo_tt.get("in_transit", 0))
    kiem("có DO đã giao xong", (theo_tt.get("delivered", 0)
                                + theo_tt.get("completed", 0)) > 0,
         "%d DO đã giao" % (theo_tt.get("delivered", 0) + theo_tt.get("completed", 0)))

    ma, g = goi("/api/tms/reporting/transport-revenue")
    d = du_lieu(g)
    dong = (d.get("rows") or []) if isinstance(d, dict) else []
    tong = (d.get("summary") or {}) if isinstance(d, dict) else {}
    ngoai_le = (d.get("exceptions") or []) if isinstance(d, dict) else []
    print("   Báo cáo doanh thu: %d dòng · doanh thu %s · giá thành %s · lãi gộp %s (%s%%)"
          % (len(dong), tien(tong.get("recognized_revenue")),
             tien(tong.get("approved_cost")), tien(tong.get("gross_profit")),
             tong.get("margin_percent")))
    kiem("báo cáo doanh thu có số", len(dong) > 0, "%d dòng" % len(dong))
    kiem("không có ngoại lệ 'đã giao mà chưa ghi sổ hoá đơn'", not ngoai_le,
         "%d ngoại lệ" % len(ngoai_le))

    ma, g = goi("/api/dashboard/stats")
    print("   Bảng điều khiển:", json.dumps(du_lieu(g), ensure_ascii=False)[:260])
    kiem("bảng điều khiển đọc được", ma == 200)

    ma, g = goi("/api/tracking/control-tower")
    d = du_lieu(g)
    ds = (d.get("trips") or d.get("items") or []) if isinstance(d, dict) else (d or [])
    kiem("tháp kiểm soát có chuyến", len(ds) > 0, "%d chuyến" % len(ds))

    ma, g = goi("/api/routes")
    ds_rt = du_lieu(g)
    ve_duoc = [r for r in (ds_rt if isinstance(ds_rt, list) else [])
               if r.get("duong_bo")]
    kiem("tuyến vẽ được sơ đồ lộ trình", len(ve_duoc) > 0,
         "%d/%d tuyến có hình đường bộ"
         % (len(ve_duoc), len(ds_rt if isinstance(ds_rt, list) else [])))


def ghi_so_ke():
    de("5. SỔ KÊ DỮ LIỆU LUỒNG")
    cot = ("%-5s %-11s %-26s %-13s %13s %13s %7s %-9s %-24s")
    print(cot % ("Case", "Chặng", "Khách", "Loại xe", "Giá thành", "Cước/chuyến",
                 "Biên", "Số DO", "Chuyến"))
    print("-" * 132)
    for s in SO_KE:
        print(cot % (
            s.get("ma", ""), NHAN_CHANG.get(s.get("trang_thai"), s.get("chang_dich", ""))[:11],
            (s.get("khach") or "").replace("DEMO-CUS-", "")[:26],
            (s.get("loai_xe") or "").replace("DEMO-VT-", "")[:13],
            tien(s.get("gia_thanh")), tien(s.get("cuoc")),
            ("%.1f%%" % ((s.get("bien") or 0) * 100)) if s.get("bien") is not None else "—",
            "%s DO" % len(s.get("do") or []) if s.get("do") else "—",
            (s.get("trip") or "—")[:24]))

    dong_md = [
        "# Dữ liệu luồng của bộ demo EPL",
        "",
        "Sinh bởi `backend/scripts/don_va_gieo_10_case_demo.py` lúc %s (giờ Việt Nam)."
        % datetime.now(VN).strftime("%d/%m/%Y %H:%M"),
        "",
        "Mười case dừng ở **những chặng khác nhau** của luồng, có chủ ý: một bộ dữ",
        "liệu toàn chuyến đã đóng sẽ làm màn Điều phối, màn Theo dõi và hàng đợi",
        "\"cần xử lý\" trống trơn — tức ba màn của người vận hành không có gì để xem.",
        "",
        "Luồng: **Dữ liệu gốc → Báo giá → khách chấp nhận → Lệnh giao hàng (DO) →",
        "Trip → Điều phối → Mốc thực thi → POD → Hoá đơn → Chi phí thực → Báo cáo.**",
        "Không còn bước Đơn hàng (SO).",
        "",
        "## Mười case",
        "",
        "| Case | Dừng ở | Khách hàng | Tuyến | Loại xe | Giá thành | Cước/chuyến | Biên | DO | Chuyến |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in SO_KE:
        dong_md.append("| %s | %s | %s | %s | %s | %s đ | %s đ | %s | %s | %s |" % (
            s.get("ma", ""),
            NHAN_CHANG.get(s.get("trang_thai"), s.get("chang_dich", "")),
            (s.get("khach") or "").replace("DEMO-CUS-", ""),
            (s.get("tuyen") or "").replace("DEMO-RT-", ""),
            (s.get("loai_xe") or "").replace("DEMO-VT-", ""),
            tien(s.get("gia_thanh")), tien(s.get("cuoc")),
            ("%.1f%%" % ((s.get("bien") or 0) * 100)) if s.get("bien") is not None else "—",
            len(s.get("do") or []) or "—",
            s.get("trip") or "—"))

    dong_md += [
        "",
        "## Mở màn nào để xem case nào",
        "",
        "| Màn hình | Case có dữ liệu | Xem được gì |",
        "|---|---|---|",
        "| Kinh doanh › Báo giá cước | cả 10 | dải 6 số liệu, 6 thẻ trạng thái, bảng 9 cột |",
        "| Báo giá › phiếu chi tiết | C01 (đã tách) · C10 (nháp) | 8 mục, cột phải, thanh đáy đổi nút theo trạng thái |",
        "| Báo giá › chờ duyệt nội bộ | C09 | biên dưới ngưỡng thì nút chính thành \"Gửi duyệt nội bộ\" |",
        "| Lệnh giao hàng › cần xử lý | C06 · C07 | hàng đợi DO chờ lập Trip |",
        "| Điều phối và thực thi | C04 · C05 | chuyến đã gán xe và tổ lái |",
        "| Theo dõi và kiểm soát | C04 · C05 | mốc check-in → nhận hàng → xuất bến |",
        "| Hoàn tất giao hàng | C01 · C02 · C03 | POD đã ký, giá cuối, phụ phí |",
        "| Kế toán › hoá đơn | C01 · C02 · C03 | hoá đơn đã ghi sổ, bút toán 131/511 |",
        "| Báo cáo doanh thu | C01 · C02 · C03 | doanh thu, giá thành, lãi gộp theo chuyến |",
        "| Dữ liệu gốc › Tuyến đường | 5 tuyến DEMO | sơ đồ lộ trình vẽ bằng đường bộ thật |",
        "",
        "## Ba điều cần biết khi demo",
        "",
        "1. **Mốc thời gian neo vào lúc chạy tệp này.** Các chuyến \"đang giao\" có",
        "   mốc xuất bến khoảng ba giờ trước, nên chúng hiện trên màn Theo dõi. Chạy",
        "   lại tệp vào ngày khác thì bộ dữ liệu tự dịch theo ngày đó.",
        "2. **Giá không viết cứng.** Đơn giá của từng case suy ra từ giá thành thật",
        "   (công thức loại xe × số km đường bộ) nhân một hệ số. Sửa giá dầu ở màn",
        "   Dữ liệu gốc rồi chạy lại là cả mười case đổi theo.",
        "3. **C09 cố ý biên mỏng** (~9%) để thấy cửa duyệt nội bộ. Nó VẪN TRÊN giá",
        "   thành — báo giá lỗ bị chặn hẳn, không vào được trạng thái chờ duyệt.",
        "",
        "## Chạy lại bộ dữ liệu — HAI BƯỚC, hai người",
        "",
        "```",
        "python scripts/don_va_gieo_10_case_demo.py       # người vận hành",
        "python scripts/duyet_chi_phi_bang_nguoi_khac.py  # trưởng phòng tài chính",
        "```",
        "",
        "Bước hai là một tệp riêng vì **quy tắc bốn mắt**: bảng chi phí thực đi qua",
        "hai tay — người vận hành trình, trưởng phòng duyệt — và máy chủ chặn người",
        "tạo tự duyệt bảng của mình. Bộ gieo chạy dưới một danh tính nên nó chỉ",
        "trình được; nếu bỏ bước hai thì báo cáo doanh thu chỉ cộng phần chi phí",
        "*vượt kế hoạch* đã duyệt, không cộng giá thành kế hoạch, và lãi gộp hiện",
        "cao giả tạo.",
        "",
        "Đây cũng là một thứ đáng cho người xem thấy: hệ thống không cho một người",
        "vừa nhập vừa xác nhận con số của chính mình.",
        "",
        "## Ba con số của báo cáo doanh thu",
        "",
        "Báo cáo hiện **ba** cột chi phí, không gộp thành một:",
        "",
        "| Cột | Nghĩa |",
        "|---|---|",
        "| Giá thành kế hoạch | công thức loại xe × số km đường bộ, đúng con số màn Báo giá hiện |",
        "| Chênh lệch đã duyệt | phần chi phí thực vượt kế hoạch, đã qua trưởng phòng |",
        "| Giá thành | tổng hai cột trên — mẫu số của lãi gộp |",
        "",
        "Gộp thành một cột thì người đọc không biết chuyến vượt kế hoạch bao nhiêu,",
        "mà đó chính là câu hỏi của người quản lý đội xe.",
        "",
    ]
    duong_md = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs", "du-lieu-luong-demo.md")
    try:
        os.makedirs(os.path.dirname(duong_md), exist_ok=True)
        io.open(duong_md, "w", encoding="utf-8", newline="\n").write("\n".join(dong_md))
        print()
        print("   Đã ghi sổ kê vào:", duong_md)
    except OSError as e:
        print("   Không ghi được tệp sổ kê:", e)


# ================================================================== CỬA VÀO

def main():
    de("DỌN DỮ LIỆU SAI VÀ GIEO 10 CASE DEMO ĐI TRỌN LUỒNG A→Z")
    print("   Máy chủ:", GOC)
    # In DUONG THAT, khong in duong SQLite dong cung: tep lenh nay chay tren
    # ca hai co so du lieu, va biet no dang xoa cai nao la dieu dau tien
    # nguoi chay can thay.
    _u = _duong_csdl()
    print("   Cơ sở dữ liệu:", _u.split("@")[0].split("//")[0] + "//***:***@" + _u.split("@")[1]
          if "@" in _u else _u)
    ma, g = goi("/api/health/database")
    print("   Engine đang chạy:", json.dumps(du_lieu(g), ensure_ascii=False))
    if ma != 200:
        print("   MÁY CHỦ CHƯA SẴN SÀNG — dừng lại.")
        return 1

    if not don_du_lieu():
        return 1
    tx_chinh, tx_phu = chuan_lai_du_lieu_goc()
    chuan_lai_tuyen()
    # GỌI Ở ĐÂY, không gọi trong `chuan_lai_tuyen`: hàm đó trả về sớm khi không
    # thiếu toạ độ nào, nên một lời gọi đặt ở cuối nó sẽ không bao giờ chạy —
    # đúng lỗi vừa mắc, và nó im lặng chứ không báo gì.
    nap_hinh_duong_bo()
    gieo_muoi_case(tx_chinh, tx_phu)
    doi_chieu()
    ghi_so_ke()

    de("TỔNG KẾT")
    print("   OK: %d    LỖI: %d" % (DEM["xanh"], DEM["do"]))
    if LOI:
        print()
        print("   CÁC BƯỚC LỖI:")
        for x in LOI:
            print("     ·", x)
    return 0 if not LOI else 2


if __name__ == "__main__":
    sys.exit(main())
