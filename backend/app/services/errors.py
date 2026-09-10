from fastapi import HTTPException


MASTER_DATA_TARGETS = {
    "customer": "master-data/customers",
    "route": "master-data/routes",
    "vehicle": "master-data/vehicles",
    # Thieu khoa nay thi `missing_master("vehicle_type", ...)` no KeyError -> 500,
    # trong khi y dinh la 422 kem dieu huong toi man Loai xe.
    "vehicle_type": "master-data/vehicle-types",
    "driver": "master-data/drivers",
    "location": "master-data/locations",
    "carrier": "master-data/carriers",
    "chart_of_accounts": "master-data/chart-of-accounts",
}


class DomainError(Exception):
    def __init__(self, code, message, status_code=400, navigation_targets=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.navigation_targets = navigation_targets or []


def conflict(code, message, navigation_targets=None):
    return DomainError(code, message, 409, navigation_targets)


def raise_http(error):
    raise HTTPException(
        status_code=error.status_code,
        detail={
            "code": error.code,
            "message": error.message,
            "navigation_targets": error.navigation_targets,
        },
    )


def missing_master(entity, label):
    return DomainError(
        f"MISSING_{entity.upper()}",
        f"Thiếu {label}. Vui lòng vào Master Data để cấu hình trước khi tiếp tục luồng.",
        422,
        [MASTER_DATA_TARGETS[entity]],
    )
