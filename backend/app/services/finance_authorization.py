import json

from models import Role, User
from services.errors import DomainError


def _principal_id(principal):
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        for key in ("id", "sub", "username"):
            value = principal.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("id", "sub", "username"):
        value = getattr(principal, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise DomainError("AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập để sử dụng nghiệp vụ tài chính.", 401)


def resolve_finance_context(db, principal, required_permissions=frozenset()):
    actor = _principal_id(principal)
    user = db.get(User, actor)
    if user is None:
        user = db.query(User).filter(User.username == actor).first()
    if user is None or not user.role_id:
        raise DomainError("FINANCE_PERMISSION_DENIED", "Người dùng chưa được phân quyền tài chính.", 403)
    role = db.get(Role, user.role_id)
    if role is None or not role.permissions:
        raise DomainError("FINANCE_PERMISSION_DENIED", "Vai trò chưa được cấu hình quyền tài chính.", 403)
    try:
        permissions = json.loads(role.permissions)
    except (TypeError, json.JSONDecodeError):
        raise DomainError("FINANCE_PERMISSION_INVALID", "Cấu hình quyền tài chính không hợp lệ.", 403) from None
    if not isinstance(permissions, list) or not all(isinstance(item, str) and item for item in permissions):
        raise DomainError("FINANCE_PERMISSION_INVALID", "Cấu hình quyền tài chính không hợp lệ.", 403)
    permission_set = set(permissions)
    missing = set(required_permissions) - permission_set
    if missing:
        raise DomainError("FINANCE_PERMISSION_DENIED", "Bạn không có quyền thực hiện nghiệp vụ tài chính này.", 403)
    return actor, permission_set
