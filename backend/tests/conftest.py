import contextlib
import hashlib
import os
import importlib
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"
REAL_DATABASE = APP_DIR / "epl_logistics.db"

# Establish a safe baseline before pytest imports test modules during collection.
# Individual fixtures may replace this URL with a narrower per-test database.
_ORIGINAL_DATABASE_ENV = {
    name: os.environ.get(name)
    for name in ("DATABASE_MODE", "DATABASE_URL", "EPL_ENV_FILE")
}
_COLLECTION_DATABASE = Path(tempfile.gettempdir()) / (
    f"epl-pytest-collection-{os.getpid()}.sqlite3"
)
os.environ["DATABASE_MODE"] = "sqlite"
os.environ["DATABASE_URL"] = f"sqlite:///{_COLLECTION_DATABASE.as_posix()}"
os.environ["EPL_ENV_FILE"] = str(_COLLECTION_DATABASE.with_suffix(".env.disabled"))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _database_fingerprint(path):
    if not path.exists():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        counts = {
            name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for (name,) in tables
            if name != "sqlite_sequence"
        }
    return (path.stat().st_mtime_ns, path.stat().st_size, digest, counts)


# Token dùng chung cho các test tự dựng TestClient. Xác thực giờ là
# mặc định-chặn (xem app/auth_middleware.py), nên test nào không đi qua fixture
# app_client phải tự gửi bearer token này.
API_TEST_TOKEN = "pytest-api-token"

API_TEST_HEADERS = {"Authorization": f"Bearer {API_TEST_TOKEN}"}


def bao_gia_hop_le(**ghi_de):
    """Payload mot bao gia HOP LE — dung cho moi bai kiem tao bao gia.

    Chu du an da chot: bao gia LO hoac HET HAN thi khong duoc duyet. Truoc do
    cac bai kiem tao bao gia RONG (khong han hieu luc, khong gia thanh, khong
    cuoc thu) roi duyet — va duyet duoc, vi duong duyet khong kiem gi. Sau khi
    bit lo hong do thi mot bao gia rong khong con duyet duoc, va muoi bon bai
    kiem do vi DU LIEU THU khong hop le chu khong vi ma nguon sai.

    Ham nay de mot cho: lan sau doi luat duyet thi sua mot cho, khong sua muoi
    bon tep. Bai kiem nao co y thu bao gia SAI thi tu ghi de tung truong —
    `bao_gia_hop_le(valid_to="2020-01-01")` cho bao gia het han chang han.

    Han hieu luc dat theo NGAY HOM NAY cong ba muoi: dat mot ngay co dinh thi
    bo kiem se do vao dung ngay do va khong ai hieu vi sao.
    """
    import datetime as _dt
    from zoneinfo import ZoneInfo as _Zone
    hom_nay = _dt.datetime.now(_Zone("Asia/Ho_Chi_Minh")).date()
    payload = {
        "id": "QT-T1",
        "customer_id": "CUS-T1",
        "route_id": "RT-T1",
        "valid_to": (hom_nay + _dt.timedelta(days=30)).isoformat(),
        "total_cost": 2_000_000,
        "selling_price": 3_000_000,
    }
    payload.update(ghi_de)
    return payload


def seed_open_accounting_period(db, period_id="TEST-OPEN-PERIOD"):
    """Tạo một kỳ kế toán đang mở, bao trùm rộng.

    Hạch toán AR, AP và settlement đều đòi một kỳ kế toán đang mở bao trùm thời
    điểm ghi sổ, nên mọi luồng test đi tới bước lập hóa đơn đều cần gọi hàm này.
    Trước đây riêng đường AR không kiểm, nên client có thể ghi doanh thu lùi vào
    một kỳ đã đóng.
    """
    import datetime as _dt
    import importlib as _importlib

    models = _importlib.import_module("models")
    year = _dt.datetime.now(_dt.timezone.utc).year
    db.merge(models.AccountingPeriod(
        id=period_id,
        starts_at=_dt.datetime(year - 2, 1, 1),
        ends_at=_dt.datetime(year + 2, 12, 31, 23, 59, 59),
        status="open",
    ))
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def configure_api_test_token():
    """Cấp một token API cố định cho cả phiên test."""
    baseline = os.environ.get("EPL_TMS_API_TOKEN")
    os.environ["EPL_TMS_API_TOKEN"] = API_TEST_TOKEN
    yield API_TEST_TOKEN
    if baseline is None:
        os.environ.pop("EPL_TMS_API_TOKEN", None)
    else:
        os.environ["EPL_TMS_API_TOKEN"] = baseline


@pytest.fixture(scope="session", autouse=True)
def isolate_application_database(tmp_path_factory):
    before = _database_fingerprint(REAL_DATABASE)
    test_database = tmp_path_factory.mktemp("database") / "suite.sqlite3"
    url_pg = _url_kiem_postgres()
    _bao_dam_csdl_kiem_ton_tai(url_pg)
    if url_pg:
        # Chế độ PostgreSQL: nền của cả phiên là một schema riêng, để bài kiểm
        # nào KHÔNG đi qua `app_client` cũng không rơi về SQLite một cách lặng
        # lẽ — rơi về SQLite là trả lời sai câu hỏi người chạy đặt ra.
        schema = "t_phien_%d" % os.getpid()
        _tao_schema(url_pg, schema)
        # Schema nền cũng phải có `schema_migrations`: những bài kiểm tự dựng
        # `TestClient` (không đi qua `app_client`) chạy trên schema này, và
        # đường khởi động của máy chủ đọc bảng đó — thiếu nó thì tám bài
        # `test_app_liveness` đỏ với `relation "schema_migrations" does not
        # exist`, một lời báo không nói gì về điều chúng đang kiểm.
        _ghi_nhan_moc(url_pg, schema)
        os.environ["DATABASE_MODE"] = "postgres"
        os.environ["DATABASE_URL"] = _dat_schema(url_pg, schema)
        print("[bộ kiểm] Chạy trên PostgreSQL, schema nền: %s" % schema)
    # Không còn nhánh `else` đặt DATABASE_MODE=sqlite: `_url_kiem_postgres()`
    # dừng cả phiên thay vì trả None, nên nhánh đó không bao giờ tới được.
    yield test_database
    if url_pg:
        _bo_schema(url_pg, "t_phien_%d" % os.getpid())
    assert _database_fingerprint(REAL_DATABASE) == before, (
        "Tests changed the real application database"
    )
    for name, value in _ORIGINAL_DATABASE_ENV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


# =========================================================== chạy trên PostgreSQL

#: Cơ sở dữ liệu của bộ kiểm. **PostgreSQL là mặc định**, không cần đặt gì:
#: `_url_kiem_postgres()` tự suy ra `<tên cơ sở dữ liệu thật>_pytest` từ `.env`.
#: Đặt biến này chỉ để trỏ sang một chỗ khác:
#:
#:     EPL_TEST_DATABASE_URL=postgresql+psycopg2://sa:***@192.168.1.89:1437/epl_logistics_pytest
#:
#: VÌ SAO KHÔNG CÒN SQLITE. Bộ kiểm trước đây dựng SQLite tạm từ `models.py`,
#: nên nó KHÔNG kiểm được PostgreSQL — và ba lỗi nặng đã lọt qua đúng vì thế:
#: ràng buộc trạng thái báo giá thiếu bốn giá trị (gửi khách / khách chấp nhận /
#: khách từ chối / tách DO đều vỡ trên cơ sở dữ liệu thật), PostgreSQL cưỡng chế
#: khoá ngoại mà SQLite thì không, và kiểu cột thời gian khai không nhất quán
#: làm khung giờ chuyến lệch bảy giờ. **Cả ba đều XANH trong bộ kiểm.**
#:
#: Nguyên nhân gốc của cả ba là một: SQLite trong dự án được DỰNG LẠI từ
#: `models.py` nên luôn có ràng buộc mới nhất, còn PostgreSQL thì NÂNG CẤP TỪNG
#: BƯỚC nên schema có thể trôi khỏi mô hình. Một bộ kiểm chạy trên bản dựng lại
#: không thể thấy sự trôi đó.
#:
#: Chủ dự án đã chốt: ngưng SQLite hoàn toàn, kể cả trong bộ kiểm.
ENV_URL_KIEM = "EPL_TEST_DATABASE_URL"


def _url_kiem_mac_dinh():
    """Suy ra URL kiểm từ `.env`: cùng máy chủ, cơ sở dữ liệu `<thật>_pytest`.

    VÌ SAO SUY RA THAY VÌ BẮT ĐẶT BIẾN. Bắt đặt biến thì ai quên là bộ kiểm lặng
    lẽ chạy sang chỗ khác — mà chỗ khác trước đây chính là SQLite, tức đúng cái
    đang phải bỏ. Suy ra thì không có đường nào chạy trên SQLite nữa.

    Cách suy ra này thoả CẢ HAI chốt an toàn ở `_url_kiem_postgres()`: tên có
    chứa `pytest`, và nó khác tên trong `.env` vì có thêm hậu tố.
    """
    tep = BACKEND_DIR.parent / ".env"
    if not tep.is_file():
        return ""
    for dong in tep.read_text(encoding="utf-8", errors="replace").splitlines():
        if not dong.strip().startswith("DATABASE_URL="):
            continue
        goc = dong.split("=", 1)[1].split("#")[0].strip()
        if not goc.startswith("postgresql"):
            return ""
        # Mật khẩu có ký tự đặc biệt (`@`, `/`, `#`) phải được mã hoá — cùng một
        # phép với máy chủ (`config.chuan_hoa_database_url`), để bộ kiểm và máy
        # chủ đọc ra cùng một địa chỉ.
        from config import chuan_hoa_database_url
        goc = chuan_hoa_database_url(goc)
        than, _, truy_van = goc.partition("?")
        than = than.rstrip("/")
        if "/" not in than:
            return ""
        dau, _, ten = than.rpartition("/")
        return "%s/%s_pytest%s%s" % (dau, ten, "?" if truy_van else "", truy_van)
    return ""


def _url_kiem_postgres():
    """URL PostgreSQL để chạy bộ kiểm. PostgreSQL là đường DUY NHẤT.

    HAI CHỐT AN TOÀN, và cả hai đều là chốt cứng chứ không phải lời nhắc:

      1. Tên cơ sở dữ liệu PHẢI chứa `test` hoặc `pytest`. Bộ kiểm xoá và dựng
         lại schema liên tục; trỏ nó vào một cơ sở dữ liệu vận hành là mất dữ
         liệu thật, và không có lệnh hoàn tác nào cho việc đó.
      2. PHẢI KHÁC cơ sở dữ liệu trong `.env`. Chốt thứ nhất một mình không đủ:
         nếu có ngày ai đặt tên cơ sở dữ liệu thật là `epl_test` thì chốt đó cho
         qua.

    Vi phạm thì DỪNG CẢ PHIÊN thay vì bỏ qua và lặng lẽ chạy trên SQLite —
    người chạy đã nói rõ họ muốn kiểm trên PostgreSQL, chạy sang chỗ khác mà
    không nói là trả về một kết quả không đúng câu hỏi họ đặt.
    """
    url = (os.environ.get(ENV_URL_KIEM) or "").strip() or _url_kiem_mac_dinh()
    if not url:
        # Không suy ra được (không có `.env`, hoặc `.env` không trỏ PostgreSQL).
        # DỪNG thay vì lùi về SQLite: lùi lặng lẽ là trả về một kết quả không
        # đúng câu hỏi người chạy đặt, và đó chính là cách ba lỗi kia lọt qua.
        raise pytest.UsageError(
            "không xác định được cơ sở dữ liệu PostgreSQL cho bộ kiểm. Đặt %s, "
            "hoặc để `.env` có DATABASE_URL trỏ PostgreSQL để tự suy ra "
            "`<tên>_pytest`. Bộ kiểm KHÔNG còn đường chạy trên SQLite."
            % ENV_URL_KIEM)
    ten = url.rstrip("/").split("/")[-1].split("?")[0]
    if "test" not in ten.lower():
        raise pytest.UsageError(
            "%s trỏ vào cơ sở dữ liệu %r — tên phải chứa 'test'. Bộ kiểm xoá và "
            "dựng lại schema liên tục, nên nó chỉ được chạy trên một cơ sở dữ "
            "liệu dành riêng cho việc kiểm." % (ENV_URL_KIEM, ten))
    that = _ten_csdl_that()
    if that and ten.lower() == that.lower():
        raise pytest.UsageError(
            "%s trỏ vào ĐÚNG cơ sở dữ liệu vận hành trong .env (%r). Không chạy."
            % (ENV_URL_KIEM, that))
    return url


def _ten_csdl_that():
    """Tên cơ sở dữ liệu trong `.env` — để bảo đảm bộ kiểm không trỏ vào nó."""
    tep = BACKEND_DIR.parent / ".env"
    if not tep.is_file():
        return None
    for dong in tep.read_text(encoding="utf-8", errors="replace").splitlines():
        if dong.strip().startswith("DATABASE_URL="):
            gia_tri = dong.split("=", 1)[1].strip()
            return gia_tri.rstrip("/").split("/")[-1].split("?")[0]
    return None


def _dat_schema(url, schema):
    """Trỏ mọi kết nối của ứng dụng vào đúng một schema, qua `EPL_DB_SEARCH_PATH`.

    Mỗi bài kiểm được một schema RIÊNG thay vì một cơ sở dữ liệu riêng: tạo một
    cơ sở dữ liệu cho mỗi bài kiểm mất vài giây một bài, còn tạo schema thì tính
    bằng phần nghìn giây.

    KHÔNG đặt `?options=-csearch_path=...` trong URL. `database.py` truyền
    `connect_args={"options": ...}` cho pool kết nối, và `connect_args` GHI ĐÈ
    tham số trong URL — nên cách đó bị bỏ lặng lẽ, và bộ kiểm ghi vào `public`
    trong khi tưởng mình đang ở schema riêng. Đã mất một lượt tìm vì chuyện đó.
    """
    os.environ["EPL_DB_SEARCH_PATH"] = schema
    return url


def _may_quan_tri(url):
    from sqlalchemy import create_engine
    return create_engine(url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)


def _bao_dam_csdl_kiem_ton_tai(url):
    """Tạo cơ sở dữ liệu `<thật>_pytest` trên máy chủ nếu chưa có.

    VÌ SAO. Khi chủ dự án chuyển PostgreSQL sang máy chủ mới và đưa `.env` mới,
    bộ kiểm suy ra `<tên>_pytest` — nhưng cơ sở dữ liệu đó chưa tồn tại ở máy
    mới, và lỗi hiện ra là `database "…_pytest" does not exist` ở bài kiểm đầu
    tiên, không nói gì về việc phải làm. Tạo nó ở đây, một lần, bằng chính tài
    khoản trong `.env` (nối vào `postgres` để chạy CREATE DATABASE). Không có
    quyền tạo thì dừng cả phiên với lời chỉ rõ câu SQL cần người quản trị chạy.
    """
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import OperationalError

    u = make_url(url)
    ten = u.database
    try:
        may = _may_quan_tri(url)
        with may.connect() as c:
            c.execute(text("SELECT 1"))
        may.dispose()
        return
    except OperationalError as loi:
        if "does not exist" not in str(loi) and "không tồn tại" not in str(loi):
            raise
    quan_tri = _may_quan_tri(u.set(database="postgres").render_as_string(hide_password=False))
    try:
        with quan_tri.connect() as c:
            c.execute(text('CREATE DATABASE "%s"' % ten))
        print("[bộ kiểm] Đã tạo cơ sở dữ liệu kiểm %s trên máy chủ mới." % ten)
    except Exception as loi:  # noqa: BLE001
        raise pytest.UsageError(
            "Cơ sở dữ liệu kiểm %r chưa có và không tự tạo được (%s). Nhờ người "
            "quản trị chạy: CREATE DATABASE \"%s\";" % (ten, str(loi)[:120], ten))
    finally:
        quan_tri.dispose()


def _tao_schema(url, schema):
    from sqlalchemy import text
    may = _may_quan_tri(url)
    try:
        with may.connect() as c:
            c.execute(text('DROP SCHEMA IF EXISTS "%s" CASCADE' % schema))
            c.execute(text('CREATE SCHEMA "%s"' % schema))
    finally:
        may.dispose()


def _ghi_nhan_moc(url, schema):
    """Ghi nhận ĐỦ mốc nâng cấp cho một schema vừa dựng từ `models.py`.

    Nói đúng sự thật: schema dựng bằng `create_all` chính là schema của mốc
    cuối. Ghi thiếu thì máy chủ tưởng cần nâng cấp; không ghi gì thì đường khởi
    động của nó không chạy được.
    """
    from sqlalchemy import text
    from migrations.runner import MIGRATIONS
    may = _may_quan_tri(_dat_schema_url(url, schema))
    try:
        with may.connect() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations ("
                           " version TEXT PRIMARY KEY,"
                           " applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
            for m in MIGRATIONS:
                c.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"
                               " ON CONFLICT (version) DO NOTHING"), {"v": m.VERSION})
    finally:
        may.dispose()


def _dat_schema_url(url, schema):
    """Như `_dat_schema` nhưng gắn vào URL, dùng cho những kết nối KHÔNG đi qua
    `database.py` (nên không đọc `EPL_DB_SEARCH_PATH`)."""
    noi = "&" if "?" in url else "?"
    return "%s%soptions=-csearch_path%%3D%s" % (url, noi, schema)


def _bo_schema(url, schema):
    from sqlalchemy import text
    may = _may_quan_tri(url)
    try:
        with may.connect() as c:
            c.execute(text('DROP SCHEMA IF EXISTS "%s" CASCADE' % schema))
    except Exception:
        # Dọn dẹp thất bại thì KHÔNG được làm bài kiểm đỏ theo: kết quả của bài
        # kiểm đã có rồi. Schema sót lại chỉ tốn chỗ trong một cơ sở dữ liệu
        # dành riêng cho việc kiểm.
        pass
    finally:
        may.dispose()


@pytest.fixture
def may_kiem(tmp_path):
    """XƯỞNG tạo engine PostgreSQL cho một bài kiểm, mỗi lần gọi một schema riêng.

    Đây là thứ thay cho `create_engine(f"sqlite:///{tmp_path}/...")` mà hai mươi
    chỗ trong mười bốn tệp kiểm từng tự dựng. Cách dùng giữ nguyên đúng hình
    dạng cũ, nên thân fixture của các tệp đó không phải viết lại:

        @pytest.fixture
        def db_session(may_kiem):
            engine = may_kiem()
            Base.metadata.create_all(engine)
            ...

    VÌ SAO LÀ XƯỞNG chứ không phải một engine sẵn: vài bài kiểm cần HAI cơ sở
    dữ liệu độc lập cùng lúc — ví dụ bài kiểm ghi đồng thời từ hai luồng, hay
    bài so hai bản schema. Mỗi lần gọi cho một schema mới, và cả nhóm được xoá
    một lượt lúc bài kiểm xong.

    VÌ SAO SCHEMA chứ không phải cơ sở dữ liệu riêng: tạo một cơ sở dữ liệu mất
    vài giây mỗi bài kiểm, tạo một schema tính bằng phần nghìn giây. Tên schema
    lấy từ `tmp_path` nên nó gắn với đúng bài kiểm đang chạy — schema sót lại
    sau một lần dừng giữa đường vẫn truy được về bài nào.
    """
    from sqlalchemy import create_engine

    url = _url_kiem_postgres()
    goc = "t_%s" % hashlib.sha1(str(tmp_path).encode("utf-8")).hexdigest()[:14]
    da_tao = []

    def tao(**ghi_de):
        schema = goc if not da_tao else "%s_%d" % (goc, len(da_tao))
        _tao_schema(url, schema)
        _ghi_nhan_moc(url, schema)
        da_tao.append(schema)
        # HAI tham số phiên, và cả hai đều phải đặt Ở ĐÂY vì engine này KHÔNG
        # đi qua `database.py` nên nó không nhận gì từ đó:
        #
        #   · `search_path` — đặt sai chỗ là bài kiểm ghi vào `public` trong khi
        #     tưởng mình ở schema riêng. Đã mất một lượt tìm vì chuyện đó.
        #   · `timezone=UTC` — BẮT BUỘC, không phải cho gọn. Vài cột khai
        #     `DateTime(timezone=True)`; ghi một mốc TRẦN vào cột `timestamptz`
        #     thì PostgreSQL diễn giải nó theo múi giờ của PHIÊN. Máy chủ này
        #     mặc định Asia/Ho_Chi_Minh, nên cùng một mốc `datetime(2026,8,11,7)`
        #     do bài kiểm ghi vào và do `database.py` (đã khoá UTC) đọc ra lệch
        #     nhau BẢY GIỜ — và lệch im lặng, chỉ lộ ra ở một cửa chặn giờ giấc
        #     nào đó nói "chưa có lịch làm việc bao phủ".
        return create_engine(
            url, pool_pre_ping=True,
            connect_args={"options": "-c search_path=%s -c timezone=UTC" % schema},
            **ghi_de)

    try:
        yield tao
    finally:
        for schema in da_tao:
            _bo_schema(url, schema)


class _KetNoiPG:
    """Bọc một kết nối PostgreSQL sao cho dùng được y như `sqlite3`.

    Giữ nguyên khuôn `execute(sql, tuple)` với dấu `?`, để mười hai chỗ gọi
    trong tám tệp kiểm không phải viết lại theo hai cú pháp khác nhau.
    """

    def __init__(self, url, schema):
        from sqlalchemy import create_engine
        self._may = create_engine(url, isolation_level="AUTOCOMMIT",
                                  connect_args={"options": "-c search_path=%s" % schema})
        self._kn = self._may.connect()

    def execute(self, sql, tham=()):
        from sqlalchemy import text
        if not tham:
            return self._kn.execute(text(sql))
        goi, ra, i = {}, [], 0
        for k in sql:
            if k == "?":
                ra.append(":p%d" % i)
                goi["p%d" % i] = tham[i]
                i += 1
            else:
                ra.append(k)
        return self._kn.execute(text("".join(ra)), goi)

    def executemany(self, sql, cac_tham):
        """`sqlite3` có hàm này, nên bọc phải có nốt.

        Không gộp thành một câu nhiều VALUES: giữ một câu cho mỗi bộ tham số thì
        hành vi giống `sqlite3` (kể cả khi một bộ vi phạm ràng buộc), và ở quy
        mô của bộ kiểm thì chênh lệch tốc độ không đáng kể.
        """
        kq = None
        for tham in cac_tham:
            kq = self.execute(sql, tham)
        return kq

    def commit(self):
        pass          # AUTOCOMMIT

    def close(self):
        try:
            self._kn.close()
        finally:
            self._may.dispose()


@contextlib.contextmanager
def ket_noi_du_lieu(database_file):
    """Mở kết nối tới CƠ SỞ DỮ LIỆU MÀ BÀI KIỂM ĐANG THỰC SỰ CHẠY TRÊN.

    VÌ SAO PHẢI CÓ HÀM NÀY. Mười hai chỗ trong tám tệp kiểm mở thẳng
    `sqlite3.connect(database_file)` để soi hoặc sửa dữ liệu — kiểm nhật ký
    kiểm toán, đặt lại số pallet, và những việc không có đường API. Cách đó
    đóng cứng bộ kiểm vào SQLite: chạy trên PostgreSQL thì `database_file` trỏ
    vào một tệp KHÔNG TỒN TẠI, `sqlite3` lặng lẽ tạo ra nó rỗng, và bài kiểm
    đọc được đúng không có gì — rồi đỏ với một lời báo không liên quan tới
    nguyên nhân.

    Hàm này trả về kết nối tới đúng chỗ máy chủ đang ghi vào.

    KHÔNG CÒN ĐƯỜNG LÙI VỀ SQLITE. Bản trước có nhánh `sqlite3.connect(...)` khi
    chưa bật chế độ PostgreSQL. Nhánh đó giờ vừa CHẾT (PostgreSQL là mặc định,
    `_url_kiem_postgres()` dừng cả phiên nếu không xác định được) vừa GÂY NHẦM:
    ai đọc vào sẽ tưởng SQLite vẫn là một chế độ được hỗ trợ. `database_file`
    giữ lại trong chữ ký để mười hai chỗ gọi không phải sửa.
    """
    url = _url_kiem_postgres()
    schema = os.environ.get("EPL_DB_SEARCH_PATH")
    if not schema:
        raise RuntimeError("đang ở chế độ PostgreSQL mà không có EPL_DB_SEARCH_PATH — "
                           "fixture `app_client` chưa chạy?")
    kn = _KetNoiPG(url, schema)
    try:
        yield kn
    finally:
        kn.close()


#: Những bài kiểm CHỈ nói về đường SQLite. Chúng không sai — chúng khẳng định
#: đúng cái mà chế độ PostgreSQL cố tình thay đổi (`DATABASE_MODE == "sqlite"`,
#: một tệp cơ sở dữ liệu riêng cho mỗi yêu cầu HTTP). Chạy chúng trong chế độ
#: PostgreSQL rồi báo đỏ là báo sai: chúng vẫn đúng ở chế độ mặc định.
#: RỖNG, và nên giữ rỗng.
#:
#: Hai bài từng nằm đây đã được xử lý đúng cách thay vì bỏ qua vĩnh viễn:
#:
#:   · `test_engine_dung_duoc_o_che_do_sqlite` — ĐÃ BỎ. Lý do tồn tại nó tự
#:     khai là "bộ kiểm và CI dùng nhánh SQLite", và lý do đó không còn.
#:   · `test_http_database_requests_are_isolated` — ĐÃ VIẾT LẠI. Ý định của nó
#:     (một yêu cầu HTTP không được đụng cơ sở dữ liệu thật) vẫn đúng; chỉ phép
#:     đo là lạc hậu, nên nay nó kiểm SCHEMA riêng thay vì TỆP riêng.
#:
#: VÌ SAO KHÔNG ĐỂ CHÚNG TRONG DANH SÁCH BỎ QUA. PostgreSQL giờ là mặc định, nên
#: một bài trong danh sách này sẽ bị bỏ qua ở MỌI lần chạy — tức nó không còn
#: kiểm gì nữa, mà vẫn nằm đó trông như đang được kiểm. Đó là dạng che lỗi tệ
#: nhất: bộ kiểm xanh và không ai biết một phép chốt đã ngừng chạy.
CHI_SQLITE = set()


def cung_thoi_diem(a, b):
    """Hai mốc thời gian có chỉ cùng một THỜI ĐIỂM không — bất kể múi giờ.

    VÌ SAO CẦN. Một số cột khai `DateTime(timezone=True)`, nên PostgreSQL trả về
    mốc CÓ múi giờ còn SQLite trả về mốc TRẦN. Bài kiểm nào so trực tiếp hai mốc
    đó sẽ đúng ở một chế độ và sai ở chế độ kia — và cách "sửa" dễ nhất là
    `.replace(tzinfo=None)`, tức so GIỜ ĐỒNG HỒ chứ không so thời điểm. Cách đó
    che đúng loại lỗi lệch múi giờ đã làm khung giờ chuyến sai bảy giờ.

    Mốc trần được coi là UTC, đúng quy ước lưu trữ của dự án.
    """
    import datetime as _dt

    def _utc(x):
        if x is None:
            return None
        return (x.replace(tzinfo=_dt.timezone.utc) if x.tzinfo is None
                else x.astimezone(_dt.timezone.utc))

    return _utc(a) == _utc(b)


def _remove_app_modules():
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            Path(module_file).resolve().relative_to(APP_DIR.resolve())
        except (OSError, ValueError):
            continue
        sys.modules.pop(name, None)


@pytest.fixture
def app_client(tmp_path):
    from fastapi.testclient import TestClient

    real_before = _database_fingerprint(REAL_DATABASE)
    database_file = tmp_path / "http.sqlite3"
    baseline = {
        name: os.environ.get(name)
        for name in ("DATABASE_MODE", "DATABASE_URL", "EPL_ENV_FILE")
    }
    url_pg = _url_kiem_postgres()
    schema = None
    if url_pg:
        # Mỗi bài kiểm một SCHEMA riêng trong cùng một cơ sở dữ liệu dành cho
        # việc kiểm. Tên lấy từ `tmp_path` nên nó gắn với đúng bài kiểm đang
        # chạy — schema sót lại sau một lần dừng giữa đường vẫn truy được về
        # bài nào.
        schema = "t_%s" % hashlib.sha1(str(tmp_path).encode("utf-8")).hexdigest()[:16]
        _tao_schema(url_pg, schema)
        os.environ["DATABASE_MODE"] = "postgres"
        os.environ["DATABASE_URL"] = _dat_schema(url_pg, schema)
    # Không còn nhánh `else` dựng một tệp SQLite: máy chủ kiểm luôn chạy trên
    # PostgreSQL. `database_file` chỉ còn dùng làm chỗ neo tên, không ai mở nó.
    os.environ["EPL_ENV_FILE"] = str(tmp_path / "no-env-file")
    _remove_app_modules()

    database_module = importlib.import_module("database")
    if url_pg:
        # `create_all` dựng schema TỪ `models.py`, tức đúng bằng mốc cuối. Nhưng
        # nó không tạo `schema_migrations`, và máy chủ kiểm bảng đó lúc khởi
        # động (`Database startup failed` / `relation "schema_migrations" does
        # not exist`).
        #
        # Ghi nhận ĐỦ mốc là nói đúng sự thật ở đây: schema vừa dựng chính là
        # schema của mốc cuối. Ghi thiếu thì máy chủ tưởng cần nâng cấp; không
        # ghi gì thì nó không khởi động được.
        #
        # Trên SQLite bước này không cần: đường khởi động cho qua khi chưa có
        # bảng, vì một tệp SQLite mới là chuyện bình thường.
        from sqlalchemy import text as _text
        from migrations.runner import MIGRATIONS as _MIGRATIONS
        database_module.Base.metadata.create_all(bind=database_module.engine)
        with database_module.engine.begin() as _c:
            _c.execute(_text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version TEXT PRIMARY KEY,"
                " applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
            for _m in _MIGRATIONS:
                _c.execute(_text("INSERT INTO schema_migrations(version) VALUES (:v)"
                                 " ON CONFLICT (version) DO NOTHING"), {"v": _m.VERSION})
    main_module = importlib.import_module("main")
    database_module.Base.metadata.create_all(bind=database_module.engine)

    @main_module.app.middleware("http")
    async def inject_test_principal(request, call_next):
        principal = request.headers.get("X-Test-Principal")
        request.state.principal = principal or "test-user"
        return await call_next(request)

    def override_get_db():
        session = database_module.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    main_module.app.dependency_overrides[database_module.get_db] = override_get_db
    try:
        with TestClient(main_module.app) as client:
            yield client, database_file, real_before
    finally:
        main_module.app.dependency_overrides.clear()
        database_module.engine.dispose()
        _remove_app_modules()
        if schema and url_pg:
            os.environ.pop("EPL_DB_SEARCH_PATH", None)
            _bo_schema(url_pg, schema)
        for name, value in baseline.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def san_sang_dieu_phoi(client, do_id, vehicle_id="VEH-T1", driver_id="DRV-T1"):
    """Cho xe, tài xế và lệnh đi qua ĐỦ cửa điều phối, đúng như người vận hành làm.

    VÌ SAO CÓ HÀM NÀY. `PUT /api/delivery-orders/{id}/dispatch` từng là đường
    tắt: không kiểm hạn pháp lý xe, bằng lái, ca làm việc, Packing List. Nhiều
    bài kiểm dùng nó để đưa một DO sang `in_transit` rồi kiểm việc khác (xoá,
    nhật ký, POD). Khi đường đó có đủ cửa như điều phối chuyến, những bài kiểm
    ấy phải chuẩn bị dữ liệu như thật — và làm ở MỘT chỗ, không lặp trong sáu
    tệp. Mốc thời gian phủ rộng (2025–2028) vì vài bài cố ý điều phối ở một ngày
    cố định trong quá khứ.
    """
    import datetime as _dt
    import importlib as _importlib

    database = _importlib.import_module("database")
    models = _importlib.import_module("models")
    with database.SessionLocal() as db:
        xe = db.get(models.Vehicle, vehicle_id)
        if xe is not None:
            xe.inspection_exp = "2028-12-31"
            xe.insurance_date = "2028-12-31"
            xe.maintenance_date = "2028-12-31"
        tx = db.get(models.Driver, driver_id)
        if tx is not None and not str(tx.license_type or "").strip():
            tx.license_type = "FC"
        hang = (tx.license_type if tx is not None else None) or "FC"
        db.commit()

    # Goi lan hai cho CUNG tai xe (bai kiem dieu hai DO chung mot xe/tai xe) thi
    # bang lai va ca da co: 409 trung lap khong phai loi o day.
    r = client.post("/api/tms/driver-qualifications", json={
        "driver_id": driver_id, "license_type": hang,
        "valid_from": "2025-01-01", "valid_to": "2028-12-31", "status": "active",
    })
    assert r.status_code in (200, 201, 409), r.text
    r = client.post("/api/tms/scheduling/driver-shifts", json={
        "id": f"SHIFT-SAN-SANG-{driver_id}", "driver_id": driver_id,
        "shift_type": "custom", "availability_kind": "work",
        "shift_start": "2025-01-01T00:00:00+00:00", "shift_end": "2028-12-31T00:00:00+00:00",
        "status": "confirmed",
    })
    assert r.status_code in (200, 201, 409), r.text

    quet_du_kien(client, do_id)
    return do_id


def dieu_phoi_qua_chuyen(client, do_id, vehicle_id="VEH-T1", driver_id="DRV-T1",
                         ma_trip=None, khung_gio=None, dau=None):
    """Điều phối một lệnh giao hàng QUA CHUYẾN — đường duy nhất còn lại.

    VÌ SAO CÓ HÀM NÀY. `PUT /api/delivery-orders/{id}/dispatch` từng là đường
    tắt: nó đưa lệnh sang `in_transit` mà không lập chuyến, nên lệnh đó không
    nộp được POD, không huỷ được, và xe cùng tổ lái bị giữ vĩnh viễn vì mọi
    đường giải phóng đều đi qua chuyến. Đường ghi đó đã đóng.

    Nhiều bài kiểm dùng điều phối chỉ để ĐẶT một lệnh vào trạng thái đang chạy
    rồi kiểm việc khác (xoá, nhật ký, POD, khoá bản nháp). Hàm này làm đúng ba
    bước người vận hành làm, ở MỘT chỗ, để mười bảy chỗ gọi không phải lặp lại:

      1. cho lệnh đủ khung giờ lấy và giao (bước lập chuyến đòi cả bốn mốc),
      2. lập chuyến một chiều từ lệnh đó,
      3. điều phối chuyến — xe, tổ lái, phân công, chặng.

    Trả về mã chuyến, để bài kiểm nào cần huỷ hoặc đóng chuyến thì có sẵn.
    """
    import datetime as _dt
    import importlib as _importlib

    database = _importlib.import_module("database")
    models = _importlib.import_module("models")

    dau_khung, cuoi = khung_gio or (
        _dt.datetime(2026, 8, 12, 1, 0, tzinfo=_dt.timezone.utc),
        _dt.datetime(2026, 8, 12, 13, 0, tzinfo=_dt.timezone.utc),
    )
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        assert do is not None, f"khong thay lenh giao hang {do_id}"
        # TUYEN PHAI CO CHANG THAT. Vai tep kiem tu dung du lieu goc rieng va de
        # `segments_json` rong; buoc lap chuyen doc chang de sinh ETA nen no tu
        # choi tuyen rong. Va ra o day mot lan, thay vi sua tung tep.
        tuyen = db.get(models.Route, do.route_id) if do.route_id else None
        if tuyen is not None:
            import json as _json
            try:
                cac_chang = _json.loads(tuyen.segments_json or "[]")
            except (TypeError, ValueError):
                cac_chang = []
            if not isinstance(cac_chang, list) or not cac_chang:
                km = float(tuyen.distance_km or 0) or 10
                tuyen.distance_km = km
                tuyen.segments_json = _json.dumps([{
                    "origin": getattr(tuyen, "origin", None) or "Kho A",
                    "destination": getattr(tuyen, "destination", None) or "Cảng B",
                    "distance_km": km,
                }], ensure_ascii=False)
        do.pickup_window_start = dau_khung
        do.pickup_window_end = dau_khung + _dt.timedelta(hours=3)
        do.delivery_window_start = dau_khung + _dt.timedelta(hours=3)
        do.delivery_window_end = cuoi
        db.commit()

    san_sang_dieu_phoi(client, do_id, vehicle_id, driver_id)

    ma_trip = ma_trip or f"TRIP-{do_id}"
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": ma_trip, "do_ids": [do_id], "trip_type": "one_way",
        "planned_departure_at": dau_khung.isoformat(), "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={**API_TEST_HEADERS, **(dau or {}),
                "Idempotency-Key": f"lap-trip-{ma_trip}"})
    assert r.status_code in (200, 201), r.text
    phien_ban = int((r.json().get("data") or {}).get("version") or 1)

    r = client.put(f"/api/tms/trips/{ma_trip}/dispatch", json={
        "vehicle_id": vehicle_id, "driver_id": driver_id, "co_driver_id": None,
        "expected_version": phien_ban,
        "assignment_start": dau_khung.isoformat(), "assignment_end": cuoi.isoformat(),
    }, headers={**API_TEST_HEADERS, **(dau or {})})
    assert r.status_code == 200, r.text
    return ma_trip


def quet_du_kien(client, do_id):
    """Hàng đếm theo kiện thì phải có Packing List quét đủ kiện lên xe (3 bước quét)."""
    import importlib as _importlib
    database = _importlib.import_module("database")
    models = _importlib.import_module("models")
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        quy_cach = str(getattr(do, "packaging_spec", "") or "").lower() if do else ""
    if do is not None and "nguyên khối" not in quy_cach and "rời" not in quy_cach:
        r = client.post(f"/api/parking-lists/auto-from-do/{do_id}", json={"list_count": 1})
        assert r.status_code in (200, 201), r.text
        goi = r.json()
        ds = goi.get("data") if isinstance(goi, dict) else goi
        ds = ds if isinstance(ds, list) else (ds.get("items") or ds.get("lists") or [ds])
        for phieu in ds:
            nhan = phieu.get("labels") or []
            for buoc in ("yard_arrival", "gate_entry", "load_package"):
                for nh in nhan:
                    r = client.post(f"/api/parking-qr/{nh['qr_token']}/scan",
                                    json={"action": buoc, "note": "bài kiểm"})
                    assert r.status_code in (200, 201), r.text
    return do_id


@pytest.fixture
def workflow_builder(app_client):
    client, _, _ = app_client

    # Bộ dựng này chạy luồng nghiệp vụ tới bước lập hóa đơn, và hạch toán đòi
    # một kỳ kế toán đang mở, nên cấu hình tài chính hợp lệ thuộc về nó.
    import importlib as _importlib
    _database = _importlib.import_module("database")
    with _database.SessionLocal() as _db:
        seed_open_accounting_period(_db)

    class Builder:
        def customer(self, id="CUS-T1"):
            assert client.post("/api/customers", json={"id": id, "name": "Khách Test"}).status_code in (200, 201)
            return id

        def route(self, id="RT-T1"):
            # TUYEN THU PHAI CO CHANG THAT.
            #
            # `segments_json: "[]"` la du lieu goc KHONG HOP LE: buoc lap chuyen
            # doc chang de sinh ETA va tu choi tuyen rong bang
            # ROUTE_SEGMENTS_INVALID. De rong thi moi bai kiem di qua duong lap
            # chuyen deu do vi DU LIEU THU sai, khong phai vi ma sai.
            assert client.post("/api/routes", json={
                "id": id, "name": "Tuyến Test", "distance_km": 10,
                "segments_json": '[{"origin": "Kho A", "destination": "Cảng B", "distance_km": 10}]',
            }).status_code in (200, 201)
            return id

        def vehicle(self, id="VEH-T1"):
            assert client.post("/api/vehicles", json={"id": id, "type": "Xe tải", "status": "Sẵn sàng"}).status_code in (200, 201)
            return id

        def driver(self, id="DRV-T1"):
            assert client.post("/api/drivers", json={"id": id, "name": "Tài xế Test", "status": "🟢 Rảnh (Sẵn sàng)"}).status_code in (200, 201)
            return id

        def master_data(self):
            self.customer(); self.route(); self.vehicle(); self.driver()
            return self

        def driver_shift(self, start, end, driver_id="DRV-T1", vehicle_id=None, id="SHIFT-T1"):
            payload = {
                "id": id,
                "driver_id": driver_id,
                "shift_type": "custom",
                "availability_kind": "work",
                "shift_start": start,
                "shift_end": end,
                "status": "planned",
            }
            if vehicle_id:
                payload["vehicle_id"] = vehicle_id
            response = client.post("/api/tms/scheduling/driver-shifts", json=payload)
            assert response.status_code == 200, response.text
            return id

        def san_sang_dieu_phoi(self, do_id, vehicle_id="VEH-T1", driver_id="DRV-T1"):
            """Đưa xe, tài xế và lệnh qua đủ cửa điều phối — xem `san_sang_dieu_phoi`."""
            san_sang_dieu_phoi(client, do_id, vehicle_id, driver_id)
            return do_id

        def dieu_phoi_qua_chuyen(self, do_id, vehicle_id="VEH-T1", driver_id="DRV-T1",
                                 ma_trip=None, khung_gio=None, dau=None):
            """Lập chuyến rồi điều phối — xem `dieu_phoi_qua_chuyen`."""
            return dieu_phoi_qua_chuyen(client, do_id, vehicle_id, driver_id,
                                        ma_trip, khung_gio, dau)

        def quotation(self, id="QT-T1", approve=False, valid_to=None,
                      total_cost=2_000_000, selling_price=3_000_000):
            """Bao gia THU, va no phai la mot bao gia HOP LE.

            Truoc day bo dung nay tao mot bao gia RONG — khong han hieu luc,
            khong gia thanh, khong cuoc thu — roi duyet. Duyet duoc, vi luc do
            duong duyet khong kiem gi ca.

            Chu du an da chot: bao gia LO hoac HET HAN thi khong cho duyet. Nen
            mot bo dung tao bao gia rong roi duyet la bo dung khoa lai dung cai
            lo hong vua duoc bit — va no se do o moi bai kiem dung no, khong phai
            vi bai kiem sai ma vi du lieu thu khong con hop le.

            Han hieu luc mac dinh dat o TUONG LAI theo gio lam viec: dat mot ngay
            co dinh thi bo kiem se do vao dung ngay do, va khong ai hieu vi sao.
            """
            import datetime as _dt
            from zoneinfo import ZoneInfo as _Zone
            if valid_to is None:
                hom_nay = _dt.datetime.now(_Zone("Asia/Ho_Chi_Minh")).date()
                valid_to = (hom_nay + _dt.timedelta(days=30)).isoformat()
            response = client.post("/api/quotations", json={
                "id": id, "customer_id": "CUS-T1", "route_id": "RT-T1",
                "valid_to": valid_to,
                "total_cost": total_cost,
                "selling_price": selling_price,
            }, headers={"X-User-Id": "tester"})
            assert response.status_code == 200, response.text
            if approve:
                tra = client.put(f"/api/quotations/{id}/approve", headers={"X-User-Id": "tester"})
                assert tra.status_code == 200, tra.text
            return id

        def delivery_order(self, id="DO-T1", quotation_id="QT-T1", approve=False, **fields):
            """Lenh giao hang SINH TU BAO GIA — duong duy nhat con lai.

            Buoc Don hang (SO) da truc xuat (10/09). Bao gia -> (duyet neu can) ->
            gui -> khach chap nhan voi MOT dong `id=<id>` => DO mang dung ma bai
            kiem muon. `fields` (khung gio, tuyen, quy cach, seal...) ghi thang len
            DO qua ORM sau khi sinh — tuong ung cac truong POST /api/delivery-orders
            cu tung nhan.
            """
            import datetime as _dt
            import importlib as _importlib
            dau = {"X-User-Id": "tester"}
            chi_tiet = client.get(f"/api/quotations/{quotation_id}/detail", headers=dau)
            assert chi_tiet.status_code == 200, chi_tiet.text
            tt = (chi_tiet.json().get("data") or chi_tiet.json()).get("canonical_status")
            if tt in ("draft", "pending_approval"):
                tra = client.put(f"/api/quotations/{quotation_id}/approve", headers=dau)
                assert tra.status_code == 200, tra.text
                tt = "approved"
            if tt == "approved":
                tra = client.post(f"/api/quotations/{quotation_id}/send", json={}, headers=dau)
                assert tra.status_code == 200, tra.text
            tra = client.post(f"/api/quotations/{quotation_id}/accept",
                              json={"dos": [{"id": id, "quantity": 1}]}, headers=dau)
            assert tra.status_code == 200, tra.text
            goi = tra.json()
            ds = goi.get("do_ids") or (goi.get("data") or {}).get("do_ids") or []
            assert id in ds, ds
            if fields:
                database = _importlib.import_module("database")
                models = _importlib.import_module("models")
                with database.SessionLocal() as db:
                    do = db.get(models.DeliveryOrder, id)
                    for k, v in fields.items():
                        if k in ("pickup_window_start", "pickup_window_end", "delivery_window_start",
                                 "delivery_window_end", "pickup_date", "delivery_date") and isinstance(v, str):
                            v = _dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
                        setattr(do, k, v)
                    db.commit()
            return id

    return Builder()


@pytest.fixture
def import_database():
    def run(extra_env):
        env = os.environ.copy()
        for name, value in extra_env.items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value
        env["PYTHONPATH"] = str(APP_DIR)
        return subprocess.run(
            [sys.executable, "-c", "import database"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    return run
