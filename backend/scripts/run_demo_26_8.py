"""Create and complete the demo_26_8 workflow through the live HTTP API."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
BASE = os.getenv("EPL_API_BASE", "http://127.0.0.1:8001")


def env(name):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return os.getenv(name, "")


TOKEN = os.getenv("EPL_TMS_API_TOKEN") or env("EPL_TMS_API_TOKEN")
IDS = {
    "route_outbound": "demo_26_8-OUTBOUND-ROUTE",
    "route_return": "demo_26_8-RETURN-ROUTE",
    "formula": "demo_26_8-COST-FORMULA",
    "quotation": "demo_26_8-QT",
    "sales_order": "demo_26_8-SO",
    "delivery_order": "demo_26_8-DO",
    "trip": "demo_26_8-TRIP",
    "cost": "demo_26_8-ACTUAL-COST",
    "voucher": "demo_26_8-EXPENSE-VOUCHER",
}


def call(method, path, payload=None, headers=None, files=None):
    request_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }
    request_headers.update(headers or {})
    body = None
    if files is not None:
        boundary = "----EPLDemo268Boundary"
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        chunks = []
        fields = payload or {}
        for name, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"), b"\r\n",
            ])
        for name, (filename, content, mime) in files.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {mime}\r\n\r\n".encode(), content, b"\r\n",
            ])
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
    elif payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(BASE + path, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc


def rows(path):
    _, data = call("GET", path)
    if isinstance(data, list):
        return data
    return data.get("items") or data.get("data") or []


def existing(path, identity):
    return next((item for item in rows(path) if item.get("id") == identity), None)


def ensure_master_data():
    vehicles = rows("/api/vehicles?page=1&page_size=200")
    drivers = rows("/api/drivers?page=1&page_size=200")
    routes = rows("/api/routes?page=1&page_size=200")
    vehicle = next(item for item in vehicles if item["id"] == "DEMO-61H-112.34")
    driver = next(item for item in drivers if item["id"] == "DEMO-DRV-002")
    co_driver = next(item for item in drivers if item["id"] == "DEMO-DRV-003")
    route = next(item for item in routes if item["id"] == "DEMO-RT-VSIP2A-CATLAI")
    outbound_route = existing("/api/routes?page=1&page_size=200", IDS["route_outbound"])
    if not outbound_route:
        _, route_response = call("POST", "/api/routes", {
            "id": IDS["route_outbound"],
            "name": "Kho VSIP II-A - Vanh dai 3 - Cang Cat Lai (demo_26_8)",
            "distance_km": 44.7,
            "segments_json": json.dumps([
                {"origin": "Kho VSIP II-A, Binh Duong", "destination": "Vanh dai 3", "distance_km": 18.2},
                {"origin": "Vanh dai 3", "destination": "Cang Cat Lai, TP. Thu Duc", "distance_km": 26.5},
            ]),
        })
        outbound_route = route_response.get("data") or route_response
    if not existing("/api/routes?page=1&page_size=200", IDS["route_return"]):
        call("POST", "/api/routes", {
            "id": IDS["route_return"],
            "name": "Cang Cat Lai - Kho VSIP II-A (Chieu ve)",
            "distance_km": 44,
            "segments_json": json.dumps([
                {"origin": "Cang Cat Lai, TP. Thu Duc", "destination": "Kho VSIP II-A, Binh Duong", "distance_km": 44},
            ]),
        })
    return vehicle, driver, co_driver, outbound_route


def main():
    if not TOKEN:
        raise RuntimeError("EPL_TMS_API_TOKEN is missing")
    vehicle, driver, co_driver, route = ensure_master_data()
    pickup_start = "2026-08-26T08:00:00+07:00"
    pickup_end = "2026-08-26T09:00:00+07:00"
    delivery_start = "2026-08-26T13:00:00+07:00"
    delivery_end = "2026-08-26T15:00:00+07:00"

    if not existing("/api/quotations?page=1&page_size=200", IDS["quotation"]):
        call("POST", "/api/quotations", {
            "id": IDS["quotation"], "customer_id": "DEMO-CUS-SGNFOOD", "route_id": route["id"],
            "origin": "Kho VSIP II-A, Binh Duong", "destination": "Cang Cat Lai, TP. Thu Duc",
            "pickup_window_start": pickup_start, "pickup_window_end": pickup_end,
            "delivery_window_start": delivery_start, "delivery_window_end": delivery_end,
            "weight_kg": 8500, "pallet_count": 18, "volume_m3": 24,
            "cargo_type": "Hang thuc pham kho dong pallet",
            "packaging_spec": "18 pallet quan mang PE, co seal",
            "fuel_cost": 550000, "driver_cost": 500000, "toll_fee": 300000,
            "total_cost": 1350000, "selling_price": 3600000,
            "valid_to": "2026-09-26",
        })
    quotation = existing("/api/quotations?page=1&page_size=200", IDS["quotation"])
    if (quotation.get("canonical_status") or "").lower() != "approved":
        call("PUT", f"/api/quotations/{IDS['quotation']}/approve", {})

    if not existing("/api/sales-orders?page=1&page_size=200", IDS["sales_order"]):
        call("POST", "/api/sales-orders", {
            "id": IDS["sales_order"], "quotation_id": IDS["quotation"], "route_id": route["id"],
            "origin": "Kho VSIP II-A, Binh Duong", "destination": "Cang Cat Lai, TP. Thu Duc",
            "pickup_window_start": pickup_start, "pickup_window_end": pickup_end,
            "delivery_window_start": delivery_start, "delivery_window_end": delivery_end,
            "weight_kg": 8500, "pallet_count": 18, "volume_m3": 24,
            "total_amount": 3600000, "currency_code": "VND",
            "packaging_spec": "18 pallet quan mang PE, co seal", "order_date": "2026-08-26",
        })
    sales_order = existing("/api/sales-orders?page=1&page_size=200", IDS["sales_order"])
    if (sales_order.get("canonical_status") or "").lower() != "confirmed":
        call("PUT", f"/api/sales-orders/{IDS['sales_order']}/confirm", {})

    if not existing("/api/delivery-orders?page=1&page_size=200", IDS["delivery_order"]):
        call("POST", "/api/delivery-orders", {
            "id": IDS["delivery_order"], "so_id": IDS["sales_order"], "route_id": route["id"],
            "origin": "Kho VSIP II-A, Binh Duong", "destination": "Cang Cat Lai, TP. Thu Duc",
            "pickup_window_start": pickup_start, "pickup_window_end": pickup_end,
            "delivery_window_start": delivery_start, "delivery_window_end": delivery_end,
            "pickup_date": "2026-08-26T00:00:00+07:00", "delivery_date": "2026-08-26T00:00:00+07:00",
            "weight_kg": 8500, "pallet_count": 18,
        })
    else:
        current_do = existing("/api/delivery-orders?page=1&page_size=200", IDS["delivery_order"])
        if current_do.get("route_id") != route["id"] and current_do.get("canonical_status") == "pending":
            call("PUT", f"/api/delivery-orders/{IDS['delivery_order']}", {"route_id": route["id"]})

    trip = existing("/api/tms/trips?page=1&page_size=200", IDS["trip"])
    if not trip:
        _, response = call("POST", "/api/tms/trips/from-delivery-orders", {
            "id": IDS["trip"], "do_ids": [IDS["delivery_order"]], "trip_type": "round_trip",
            "planned_departure_at": pickup_start, "avg_speed_kmh": "45", "dwell_minutes": 60,
            "stop_plan": [{"sequence_no": 1, "stop_name": "Cong giao nhan Cang Cat Lai",
                           "receiver_name": "Nguyen Van An", "receiver_phone": "0908123456",
                           "delivery_note": "Giao du 8.500 kg, 18 pallet, kiem seal va ky POD.",
                           "dwell_minutes": 60}],
        }, {"Idempotency-Key": "demo_26_8-create-trip"})
        trip = response["data"]

    if not any(leg.get("leg_type") == "empty_return" for leg in trip.get("legs", [])):
        return_segment = {"origin": "Cang Cat Lai, TP. Thu Duc", "destination": "Kho VSIP II-A, Binh Duong", "distance_km": 44}
        call("POST", f"/api/tms/trips/{IDS['trip']}/legs", {
            "expected_version": trip["version"], "id": f"{IDS['trip']}-RETURN-001", "do_id": None,
            "sequence_no": len(trip.get("legs", [])) + 1, "leg_type": "empty_return",
            "origin": return_segment["origin"], "destination": return_segment["destination"],
            "distance_km": 44, "avg_speed_kmh": 45, "dwell_minutes": 30,
            "planned_departure_at": None, "stop_name": "Xe quay ve Kho VSIP II-A",
            "receiver_name": None, "receiver_phone": None, "delivery_note": "Chay rong ve diem goc theo Route Master chieu ve.",
        }, {"Idempotency-Key": "demo_26_8-add-return"})
        trip = existing("/api/tms/trips?page=1&page_size=200", IDS["trip"])

    if trip.get("status") not in {"dispatched", "in_transit", "completed"}:
        call("PUT", f"/api/tms/trips/{IDS['trip']}/dispatch", {
            "vehicle_id": vehicle["id"], "driver_id": driver["id"], "co_driver_id": co_driver["id"],
            "expected_version": trip["version"],
            # The live SQLite database stores workflow windows as local wall-clock values.
            # Use the same wall-clock values with Z for this API call so the real dispatch
            # validator compares the intended 08:00-15:00 operating window.
            "assignment_start": "2026-08-26T08:00:00Z", "assignment_end": "2026-08-26T15:00:00Z",
        })

    trip = call("GET", f"/api/tms/trips/{IDS['trip']}")[1]["data"]
    delivery_legs = [leg for leg in trip["legs"] if leg.get("leg_type") == "delivery" and leg.get("do_id") == IDS["delivery_order"]]
    pod_entries = []
    uploads = {}
    for index, leg in enumerate(delivery_legs, 1):
        pod_field = f"pod_file_{index}"
        signature_field = f"signature_file_{index}"
        pod_entries.append({
            "leg_id": leg["id"], "vehicle_id": vehicle["id"], "stop_no": index,
            "location_text": leg.get("destination") or "Cang Cat Lai, TP. Thu Duc",
            "receiver_name": "Nguyen Van An", "receiver_phone": "0908123456",
            "delivery_time": "2026-08-26T14:00:00+07:00", "delivery_result": "delivered_full",
            "cargo_condition": "Nguyen niem phong, khong mop vo",
            "file_field": pod_field, "signature_file_field": signature_field,
            "note": "POD demo_26_8 day du nguoi nhan, thoi gian va chu ky.",
        })
        uploads[pod_field] = (f"demo_26_8-pod-{index}.png", b"demo_26_8-pod", "image/png")
        uploads[signature_field] = (f"demo_26_8-signature-{index}.png", b"demo_26_8-signature", "image/png")
    current_do = existing("/api/delivery-orders?page=1&page_size=200", IDS["delivery_order"])
    if current_do.get("canonical_status") != "delivered":
        call("POST", f"/api/delivery-orders/{IDS['delivery_order']}/complete-delivery",
             {"payload": json.dumps({"trip_id": IDS["trip"], "currency_code": "VND", "pod_entries": pod_entries,
                                      "charge_adjustments": [
                                          {"name": "Phi cho boc do", "original_amount": 0, "actual_amount": 350000},
                                          {"name": "Phi cau duong bo sung", "original_amount": 0, "actual_amount": 120000},
                                      ]})},
             {"Idempotency-Key": "demo_26_8-complete-delivery"}, uploads)

    trip = call("GET", f"/api/tms/trips/{IDS['trip']}")[1]["data"]
    if trip.get("status") in {"dispatched", "in_transit"}:
        call("POST", f"/api/tms/trips/{IDS['trip']}/complete-return", {
            "expected_version": trip["version"],
            "actual_return_at": "2026-08-26T11:30:00+07:00",
        }, {"Idempotency-Key": "demo_26_8-complete-return"})

    cost_payload = {"id": IDS["cost"], "currency_code": "VND", "lines": [
        {"id": f"{IDS['cost']}-FUEL", "name": "Nhien lieu dau diesel", "original_amount": 0, "actual_amount": 550000, "note": "Theo 88 km ca di va quay ve"},
        {"id": f"{IDS['cost']}-DRIVER", "name": "Phu cap tai xe va phu xe", "original_amount": 0, "actual_amount": 500000},
        {"id": f"{IDS['cost']}-TOLL", "name": "Phi cau duong", "original_amount": 0, "actual_amount": 300000},
        {"id": f"{IDS['cost']}-WAREHOUSE", "name": "Phi bai va luu kho", "original_amount": 0, "actual_amount": 200000},
    ]}
    if not existing("/api/tms/finance/costs?page=1&page_size=200", IDS["cost"]):
        call("PUT", f"/api/tms/finance/trips/{IDS['trip']}/actual-cost", cost_payload, {"Idempotency-Key": "demo_26_8-actual-cost"})
    saved_cost = call("GET", f"/api/tms/finance/costs/{IDS['cost']}")[1]["data"]
    if saved_cost.get("status") == "draft":
        call("POST", f"/api/tms/finance/costs/{IDS['cost']}/submit",
             {"expected_version": saved_cost["version"]}, {"Idempotency-Key": "demo_26_8-submit-cost"})
        saved_cost = call("GET", f"/api/tms/finance/costs/{IDS['cost']}")[1]["data"]
    if saved_cost.get("status") == "submitted":
        call("POST", f"/api/tms/finance/costs/{IDS['cost']}/approve",
             {"expected_version": saved_cost["version"]}, {"Idempotency-Key": "demo_26_8-approve-cost"})

    if not existing("/api/tms/reporting/expense-vouchers", IDS["voucher"]):
        call("PUT", f"/api/tms/reporting/trips/{IDS['trip']}/expense-voucher", {
            **cost_payload, "voucher_no": IDS["voucher"], "voucher_date": "2026-08-26", "do_id": IDS["delivery_order"],
            "vehicle_manager": "Bo phan dieu phoi EPL", "payment_method": "cash", "contract_no": "demo_26_8",
            "machine_numbers": "ENG-DEMO-61H-112.34; CHS-DEMO-61H-112.34", "checked_by": "Quan ly van tai EPL",
            "note": "Phieu chi phi day du cho chuyen demo_26_8.",
        }, {"Idempotency-Key": "demo_26_8-expense-voucher"})

    report = call("GET", "/api/tms/reporting/transport-revenue?date_from=2026-08-26&date_to=2026-08-26&currency_code=VND")[1]["data"]
    trip_final = call("GET", f"/api/tms/trips/{IDS['trip']}")[1]["data"]
    do_final = existing("/api/delivery-orders?page=1&page_size=200", IDS["delivery_order"]) or {}
    cost_final = call("GET", f"/api/tms/finance/trips/{IDS['trip']}/actual-cost")[1]["data"]
    print(json.dumps({"workflow": IDS, "master_data": {"route": route["id"], "return_route": IDS["route_return"],
        "vehicle": vehicle["id"], "driver": driver["id"], "co_driver": co_driver["id"], "formula": IDS["formula"]},
        "result": {"do_status": do_final.get("canonical_status"), "trip_status": trip_final.get("status"),
                   "trip_departure": trip_final.get("planned_departure_at"), "trip_arrival": trip_final.get("planned_arrival_at"),
                   "trip_return": trip_final.get("planned_return_at"), "selling_price_vnd": 3600000,
                   "customer_surcharge_vnd": 470000, "final_price_vnd": 4070000,
                   "actual_cost_vnd": cost_final.get("total_amount"), "actual_cost_status": cost_final.get("status"),
                   "report_rows": len(report.get("rows", []))}},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
