import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_DIR / ".env"
API_BASE = os.getenv("EPL_API_BASE", "http://127.0.0.1:8001")

IDS = {
    "quotation": "LIVE-QT-20260822-001",
    "sales_order": "LIVE-SO-20260822-001",
    "delivery_order": "LIVE-DO-20260822-001",
    "trip": "LIVE-TRIP-20260822-001",
}


def read_env(name):
    if not ENV_FILE.exists():
        return ""
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip()
    return ""


TOKEN = os.getenv("EPL_TMS_API_TOKEN") or read_env("EPL_TMS_API_TOKEN")


def api(method, path, payload=None, extra_headers=None):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }
    if extra_headers:
        headers.update(extra_headers)
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc


def find_record(path, record_id):
    _, payload = api("GET", path)
    rows = payload.get("items") or payload.get("data") or []
    return next((row for row in rows if row.get("id") == record_id), None)


def main():
    if not TOKEN:
        raise RuntimeError("EPL_TMS_API_TOKEN is missing")

    existing = find_record(
        "/api/delivery-orders?page=1&page_size=200", IDS["delivery_order"]
    )
    pickup_start = "2026-08-23T08:00:00+07:00"
    pickup_end = "2026-08-23T09:00:00+07:00"
    delivery_start = "2026-08-23T13:00:00+07:00"
    delivery_end = "2026-08-23T15:00:00+07:00"

    quotation = find_record("/api/quotations?page=1&page_size=200", IDS["quotation"])
    if not quotation:
        api("POST", "/api/quotations", {
            "id": IDS["quotation"],
            "customer_id": "DEMO-CUS-SGNFOOD",
            "route_id": "DEMO-RT-VSIP2A-CATLAI",
            "origin": "Kho VSIP II-A, Bình Dương",
            "destination": "Cảng Cát Lái, TP. Thủ Đức",
            "pickup_window_start": pickup_start,
            "pickup_window_end": pickup_end,
            "delivery_window_start": delivery_start,
            "delivery_window_end": delivery_end,
            "weight_kg": 7200,
            "pallet_count": 15,
            "volume_m3": 21,
            "cargo_type": "Hàng thực phẩm khô đóng pallet",
            "packaging_spec": "15 pallet quấn màng PE, có seal",
            "total_cost": 3150000,
            "selling_price": 5200000,
        })
        api("PUT", f"/api/quotations/{IDS['quotation']}/approve", {})
    elif (quotation.get("canonical_status") or "").lower() != "approved":
        api("PUT", f"/api/quotations/{IDS['quotation']}/approve", {})

    sales_order = find_record("/api/sales-orders?page=1&page_size=200", IDS["sales_order"])
    if not sales_order:
        api("POST", "/api/sales-orders", {
            "id": IDS["sales_order"],
            "quotation_id": IDS["quotation"],
        })
        api("PUT", f"/api/sales-orders/{IDS['sales_order']}/confirm", {})
    elif (sales_order.get("canonical_status") or "").lower() != "confirmed":
        api("PUT", f"/api/sales-orders/{IDS['sales_order']}/confirm", {})

    if not existing:
        api("POST", "/api/delivery-orders", {
            "id": IDS["delivery_order"],
            "so_id": IDS["sales_order"],
            "route_id": "DEMO-RT-VSIP2A-CATLAI",
            "origin": "Kho VSIP II-A, Bình Dương",
            "destination": "Cảng Cát Lái, TP. Thủ Đức",
            "pickup_window_start": pickup_start,
            "pickup_window_end": pickup_end,
            "delivery_window_start": delivery_start,
            "delivery_window_end": delivery_end,
            "weight_kg": 7200,
            "pallet_count": 15,
        })

    trip = find_record("/api/tms/trips?page=1&page_size=200", IDS["trip"])
    if not trip:
        _, trip_payload = api(
            "POST",
            "/api/tms/trips/from-delivery-orders",
            {
            "id": IDS["trip"],
            "do_ids": [IDS["delivery_order"]],
            "trip_type": "one_way",
            "planned_departure_at": pickup_start,
            "avg_speed_kmh": "45",
            "dwell_minutes": 45,
            "stop_plan": [{
                "sequence_no": 1,
                "stop_name": "Cổng giao nhận Cảng Cát Lái",
                "receiver_name": "Trần Quốc Huy",
                "receiver_phone": "0912112340",
                "delivery_note": "Giao đủ 15 pallet, kiểm seal và ký biên bản POD.",
            }],
            },
            {"Idempotency-Key": "live-trip-20260822-001"},
        )
        trip = trip_payload["data"]

    if str(trip.get("status") or "").lower() not in {"dispatched", "in_transit"}:
        api("POST", "/api/drivers", {
            "id": "DEMO-DRV-002",
            "name": "Lê Hoàng Nam",
            "role": "Lái xe chính",
            "license_type": "Hạng FC",
            "phone": "0938667771",
            "assigned_vehicle": "DEMO-61H-112.34",
            "shift": "Ca ngày (06:00 - 18:00)",
            "status": "🟢 Rảnh (Sẵn sàng)",
        })
        api("PUT", f"/api/tms/trips/{IDS['trip']}/dispatch", {
            "vehicle_id": "DEMO-61H-112.34",
            "driver_id": "DEMO-DRV-002",
            "expected_version": trip["version"],
            "assignment_start": "2026-08-23T08:00:00Z",
            "assignment_end": "2026-08-23T15:00:00Z",
        })

    _, tracking = api("GET", f"/api/tracking/{IDS['delivery_order']}")
    print(json.dumps({
        "message": "Live A-Z workflow created through HTTP APIs",
        **IDS,
        "status": tracking.get("status"),
        "vehicle_id": tracking.get("vehicle_id"),
        "driver_id": tracking.get("driver_id"),
        "selling_price_vnd": 5200000,
        "receiver_name": "Trần Quốc Huy",
        "receiver_phone": "0912112340",
        "next_action": "Open Hoàn tất giao hàng and submit POD",
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
