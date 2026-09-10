"""Chốt chặn môi trường cho các script nạp dữ liệu demo.

Các script seed chạy vào *bất kỳ* DATABASE_URL nào đang cấu hình — tức Postgres
production theo mặc định — rồi ``db.merge()`` các bản ghi ID cố định
(``CUS-001``, ``INV-2026-001`` trạng thái Posted, kèm bút toán GL). ``merge`` là
upsert, nên khách hàng thật trùng ID bị ghi đè im lặng và bút toán giả rơi vào
sổ cái. Đây là rủi ro vận hành chứ không cần ai tấn công: một lần gõ
``python seed_db.py`` với ``.env`` production là đủ.

(Công cụ ``data_cleanup.py`` chạy trên SQLite đã xoá 10/09 — dự án chỉ dùng PostgreSQL.) Nguyên tắc: (bắt buộc
``--approved-sha256`` của manifest, backup và verify restore trước khi xóa);
module này mang cùng tinh thần sang phía nạp dữ liệu.
"""

import os
import sys


CONFIRM_FLAG = "--i-know-this-is-not-production"
CONFIRM_ENV = "EPL_ALLOW_DEMO_SEED"


class UnsafeSeedTargetError(RuntimeError):
    """Từ chối nạp dữ liệu demo vào một đích không an toàn."""


def _confirmed(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if CONFIRM_FLAG in argv:
        return True
    return os.getenv(CONFIRM_ENV, "").strip().lower() in {"1", "true", "yes"}


def assert_demo_seed_allowed(argv=None):
    """Bật lỗi nếu việc nạp dữ liệu demo có thể chạm vào dữ liệu thật.

    Hai lớp: chế độ postgres bị chặn cứng, và mọi đích khác vẫn cần xác nhận
    tường minh — vì một file SQLite cũng có thể là dữ liệu thật của ai đó.
    """
    mode = os.getenv("DATABASE_MODE", "").strip().lower()
    url = os.getenv("DATABASE_URL", "").strip()
    looks_like_postgres = mode == "postgres" or url.startswith(
        ("postgresql:", "postgresql+", "postgres:")
    )

    if looks_like_postgres:
        raise UnsafeSeedTargetError(
            "Từ chối nạp dữ liệu demo vào PostgreSQL. Các script seed dùng "
            "db.merge() trên những ID cố định (CUS-001, INV-2026-001, bút toán "
            "GL), nên chúng sẽ ghi đè dữ liệu thật và thêm bút toán giả vào sổ "
            "cái. Hãy trỏ DATABASE_MODE=sqlite vào một file dùng một lần rồi "
            "chạy lại."
        )

    if not _confirmed(argv):
        raise UnsafeSeedTargetError(
            "Việc nạp dữ liệu demo cần xác nhận tường minh vì nó ghi đè các ID "
            f"cố định. Chạy lại kèm {CONFIRM_FLAG}, hoặc đặt {CONFIRM_ENV}=1. "
            f"Đích hiện tại: DATABASE_MODE={mode or '(chưa đặt)'} "
            f"DATABASE_URL={url or '(chưa đặt)'}"
        )
