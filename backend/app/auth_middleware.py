"""Xác thực mặc định-chặn cho toàn bộ API.

Trước đây middleware này chỉ *gán* principal rồi để mỗi handler tự gọi
``_require_api_principal``. Cách opt-in đó bỏ sót 95 trên 105 endpoint ghi dữ
liệu, nên việc gác quyền được chuyển vào đây: mọi đường dẫn đều phải có
principal, trừ danh sách công khai tường minh bên dưới.
"""

import hmac
import os

from starlette.responses import JSONResponse

# Đường dẫn công khai, khớp tuyệt đối.
_PUBLIC_EXACT = frozenset(
    {
        "/",                     # vỏ frontend (không còn chứa token, xem main.py)
        "/favicon.ico",
        "/test-runner",          # trang HTML tĩnh, không thực thi gì
        "/kich-ban-test",
        "/api/health",           # probe nông cho load balancer
        "/api/health/database",  # probe sâu cho readiness
    }
)

# Đường dẫn công khai theo tiền tố.
_PUBLIC_PREFIXES = (
    "/static/",
    "/api/parking-qr/",  # luồng quét QR ở bãi, công khai theo thiết kế
    # Ảnh xe và tài xế đã upload. BẮT BUỘC phải công khai: giao diện hiển thị
    # chúng bằng <img src="/uploads/...">, và thẻ <img> không gửi được header
    # Authorization — lớp bọc fetch trong frontend/js/api-auth.js không chạm
    # tới nó. Bỏ đường này ra khỏi danh sách công khai làm MỌI ảnh biến thành
    # 401, tức ảnh trống trên toàn bộ màn hình đội xe.
    #
    # Điều này an toàn vì đường đọc đã tự phòng thủ, không dựa vào xác thực:
    # nó chặn path traversal (kiểm relative_to sau resolve), chỉ nhận đúng hai
    # thành phần đường dẫn, và chỉ phục vụ các thư mục trong danh sách cho
    # phép ("vehicles", "drivers"). Tên tệp lưu trên đĩa là uuid4 nên không
    # đoán hay dò tuần tự được.
    "/uploads/",
)

# Tài liệu API chỉ mở khi được bật tường minh (xem main.py).
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"})


def _is_public(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True  # preflight CORS không mang được Authorization
    if path in _PUBLIC_EXACT:
        return True
    if path in _DOCS_PATHS:
        return _docs_enabled()
    return path.startswith(_PUBLIC_PREFIXES)


def _docs_enabled() -> bool:
    return os.getenv("EPL_ENABLE_DOCS", "").strip().lower() in {"1", "true", "yes"}


def _unauthorized() -> JSONResponse:
    """Giữ đúng khuôn phong bì lỗi của ứng dụng.

    Middleware nằm ngoài tầm với của các exception handler đã đăng ký, nên
    phong bì phải được dựng tay tại đây thay vì raise HTTPException.
    """
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Vui lòng đăng nhập.",
                "fields": [],
                "links": [],
            },
            "detail": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Vui lòng đăng nhập.",
            },
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


async def tms_bearer_auth(request, call_next):
    """Gán principal từ bearer token, rồi chặn mọi đường dẫn không công khai."""
    if not getattr(request.state, "principal", None):
        configured = os.getenv("EPL_TMS_API_TOKEN", "").strip()
        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        if (
            configured
            and separator
            and scheme.lower() == "bearer"
            and hmac.compare_digest(supplied, configured)
        ):
            request.state.principal = os.getenv("EPL_TMS_API_PRINCIPAL", "tms-api").strip() or "tms-api"

    if not getattr(request.state, "principal", None) and not _is_public(
        request.url.path, request.method.upper()
    ):
        return _unauthorized()

    return await call_next(request)
