import hmac
import os


async def tms_bearer_auth(request, call_next):
    """Populate a trusted principal only for a configured, constant-time token match."""
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
    return await call_next(request)
