"""Bo ket noi Postgres phai vua voi may chu, va khong duoc chiem cho vinh vien.

Do duoc tren Postgres that cua du an (192.168.1.89:1437):

    max_connections                : 100
    superuser_reserved_connections : 3
    -> con 97 cho cho ung dung

Ban truoc moi tien trinh uvicorn xin duoc toi 30 ket noi (pool_size 10 +
max_overflow 20). Ba tien trinh la 90/97; cong pgAdmin (4-5 ket noi) la HET
cho, va luc het cho Postgres tra:

    FATAL: remaining connection slots are reserved for roles with the SUPERUSER

Ung dung bien cai do thanh 500, va giao dien hien "Nap that bai ..." o MOI man
hinh — nut bam khong an gi vi moi loi goi API deu that bai. Do dung la hien
tuong da phai di truy.

Con te hon: da do thay 30 ket noi nam o trang thai `idle in transaction` suot
14 phut lien, thuoc mot tien trinh con da mat cha. Postgres KHONG tu thu hoi
chung — no cho tin hieu TCP keepalive, ma mac dinh cua he dieu hanh la hang
gio. Trong luc do 30 cho bi chiem, va giao dich mo con giu snapshot nen VACUUM
khong don duoc dong cu, bang phinh dan.

Hai chot o day chan ca hai chuyen do. Bai kiem chay tren SQLite nen no doc
CAU HINH chu khong noi voi Postgres; phan doi thoai that voi Postgres da duoc
thu tay va ghi lai trong `git log`.
"""
import importlib
import os
import re

import pytest


NGUON = os.path.join(os.path.dirname(__file__), '..', 'app', 'database.py')


@pytest.fixture(scope='module')
def nguon_database():
    with open(NGUON, encoding='utf-8-sig') as f:
        return f.read()


def _mac_dinh(nguon, ten):
    """Gia tri mac dinh cua mot bien moi truong trong database.py."""
    m = re.search(r'os\.getenv\(\s*"' + re.escape(ten) + r'"\s*,\s*"([^"]+)"\s*\)',
                  nguon)
    assert m, 'khong thay %s trong database.py' % ten
    return m.group(1)


def test_bo_ket_noi_vua_voi_may_chu_thuc(nguon_database):
    """Mot tien trinh khong duoc xin qua nhieu so voi 97 cho cua may chu."""
    pool = int(_mac_dinh(nguon_database, 'EPL_DB_POOL_SIZE'))
    overflow = int(_mac_dinh(nguon_database, 'EPL_DB_MAX_OVERFLOW'))
    toi_da = pool + overflow

    # 97 cho, va thuc te co the co ca may chu web, script demo va pgAdmin cung
    # chay. Ba tien trinh khong duoc vuot nua so cho.
    assert toi_da * 3 <= 97 // 2 + 15, (
        'mot tien trinh xin toi %d ket noi; ba tien trinh la %d trong 97 cho'
        % (toi_da, toi_da * 3))
    assert toi_da >= 10, (
        'nhung cung khong duoc qua chat: da do 60 yeu cau song song, can it '
        'nhat 10 ket noi. Dang la %d' % toi_da)


def test_ket_noi_bo_roi_giua_giao_dich_phai_tu_bi_thu_hoi(nguon_database):
    """Phai dat `idle_in_transaction_session_timeout` cho moi phien."""
    assert 'idle_in_transaction_session_timeout' in nguon_database, (
        'thieu chot nay thi mot tien trinh con mat cha se chiem cho ket noi '
        'hang gio — da do duoc 30 cho bi chiem 14 phut lien')

    ms = int(_mac_dinh(nguon_database, 'EPL_DB_IDLE_TX_TIMEOUT_MS'))
    # Du dai de khong cat ngang mot giao dich that dang cho I/O, du ngan de
    # khong de cho bi chiem lau.
    assert 15000 <= ms <= 300000, 'timeout %d ms khong hop ly' % ms

    # Phai truyen qua `options` cua libpq, va nam trong connect_args de moi
    # ket noi MOI cung nhan duoc — dat bang mot cau SET sau khi ket noi thi
    # ket noi lay tu be se khong co.
    m = re.search(r'connect_args\s*=\s*\{(.*?)\n            \}',
                  nguon_database, re.S)
    assert m, 'khong doc duoc connect_args'
    assert 'idle_in_transaction_session_timeout' in m.group(1), (
        'chot phai nam trong connect_args de ap cho MOI ket noi moi')


def test_van_cho_ghi_de_bang_bien_moi_truong(nguon_database):
    """May chu that o noi khac co the co max_connections khac — phai doi duoc."""
    for ten in ('EPL_DB_POOL_SIZE', 'EPL_DB_MAX_OVERFLOW',
                'EPL_DB_IDLE_TX_TIMEOUT_MS', 'EPL_DB_POOL_TIMEOUT',
                'EPL_DB_CONNECT_TIMEOUT'):
        assert 'os.getenv("%s"' % ten in nguon_database, (
            '%s phai doc duoc tu bien moi truong' % ten)


def test_pre_ping_con_bat(nguon_database):
    """Chot thu hoi chi an toan khi CON `pool_pre_ping`.

    Postgres thu hoi mot ket noi dang nam trong be thi lan sau lay ra no da
    chet. `pool_pre_ping` thu mot cau truoc khi dua ra, thay chet thi thay
    ket noi moi — nen nguoi dung khong thay loi nao. Go no di thi chot thu hoi
    lai tro thanh nguon sinh loi.
    """
    assert 'pool_pre_ping=True' in nguon_database

# `test_engine_dung_duoc_o_che_do_sqlite` DA BO.
#
# Bai do chot rang mot moc moi khong lam vo nhanh SQLite cua `database.py`, va
# ly do no tu khai la: *"bo kiem va CI dung nhanh do"*. Ly do do khong con —
# bo kiem gio chay tren PostgreSQL, va chu du an da chot ngung SQLite hoan
# toan. No cung khong con CHAY duoc: no dat `DATABASE_MODE=sqlite` roi nap lai
# `database`, ma `DATABASE_URL` luc do la URL PostgreSQL nen `_sqlite_url()`
# nem loi ngay.
#
# Phan `options=-c ...` ma no canh giu (cu phap libpq, SQLite khong hieu) van
# nam trong nhanh postgres va van duoc chot boi cac bai con lai trong tep nay.
# Khi nao bo han nhanh SQLite khoi `database.py` / `config.py` thi cho nay
# khong con gi phai noi nua.
