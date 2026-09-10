import os
from dotenv import load_dotenv

# Load only an explicitly selected file or the EPL project-root file.
project_env = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
)
explicit_env = os.getenv("EPL_ENV_FILE", "").strip()
env_paths = [explicit_env] if explicit_env else [project_env]

for env_p in env_paths:
    if os.path.exists(env_p):
        load_dotenv(env_p)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_GT", "")
DATABASE_MODE = os.getenv("DATABASE_MODE", "").strip().lower()
if DATABASE_MODE not in {"postgres", "sqlite"}:
    raise ValueError("DATABASE_MODE must be either 'postgres' or 'sqlite'")

def chuan_hoa_database_url(url):
    """Mã hoá ký tự đặc biệt trong mật khẩu của một URL cơ sở dữ liệu.

    LỖI ĐÃ GẶP THẬT khi chủ dự án chuyển PostgreSQL sang máy chủ mới: mật khẩu
    mới có ký tự `@`, và một URL kiểu `postgresql://sa:P@ssw0rd@example.invalid/db`
    bị bộ phân tích cắt ở dấu `@` ĐẦU TIÊN — host thành `ssw0rd@example.invalid`,
    và lỗi báo ra là "could not translate host name", không nói gì về mật khẩu.

    (Ví dụ ở đây dùng `example.invalid` có chủ ý: địa chỉ máy chủ thật chỉ nằm
    trong `.env`, không lặp lại vào mã nguồn.)
    Chuẩn đúng là `P%40ssw0rd`, nhưng ai đổi mật khẩu trong `.env` cũng không
    nhớ điều đó, và `.env` là tệp không nên phải "biết" quy tắc mã hoá URL.

    Cách làm: phần giữa `://` và dấu `@` CUỐI CÙNG là `user:password`; mật khẩu
    là mọi thứ sau dấu `:` đầu tiên của phần đó. Mã hoá mật khẩu bằng
    `quote(..., safe="")` — đã mã hoá rồi (`%40`) thì giải mã trước để không mã
    hoá hai lần. URL không có `@` hay không có `://` thì trả nguyên.
    """
    from urllib.parse import quote, unquote
    if not url or "://" not in url or "@" not in url:
        return url
    dau, _, phan_con = url.partition("://")
    xac_thuc, _, may = phan_con.rpartition("@")
    if not xac_thuc:
        return url
    nguoi, co_mk, mat_khau = xac_thuc.partition(":")
    if not co_mk:
        return url
    return "%s://%s:%s@%s" % (dau, nguoi, quote(unquote(mat_khau), safe=""), may)


raw_db_url = os.getenv("DATABASE_URL", "").split("#")[0].strip()
DATABASE_URL = chuan_hoa_database_url(raw_db_url)
