"""Generate Vietnamese database and API reference documents from runtime metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1] / "app"
ROOT_DIR = APP_DIR.parents[1]
DOCS_DIR = ROOT_DIR / "docs"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app  # noqa: E402
from models import Base  # noqa: E402


TABLE_PURPOSES = {
    "currency_definitions": "Danh muc tien te va ty gia van hanh hien tai.",
    "currency_rate_history": "Lich su thay doi ty gia de doi chieu va audit.",
    "tax_codes": "Danh muc ma thue dung cho hoa don va but toan.",
    "finance_control_config": "Cau hinh kiem soat nghiep vu tai chinh.",
    "vehicles": "Ho so tung xe, thong so ky thuat va trang thai van hanh.",
    "vehicle_maintenance_requests": "Phieu yeu cau sua chua, thay the va bao duong xe.",
    "vehicle_maintenance_cost_lines": "Chi tiet chi phi cua tung phieu sua chua/bao duong.",
    "vehicle_types": "Danh muc loai xe va gioi han tai trong, pallet, the tich.",
    "drivers": "Ho so tai xe, phu xe, bang lai va trang thai nguon luc.",
    "driver_shift_assignments": "Ca lam viec, lich nghi va chuyen da khoa cua nhan su.",
    "routes": "Tuyen van tai nguon dung de tao bao gia va Trip.",
    "locations": "Danh muc kho, bai, cong va diem giao/nhan.",
    "customers": "Ho so khach hang va thong tin lien he.",
    "quotations": "Phan dau bao gia van tai cho khach hang.",
    "quotation_details": "Hang muc va so lieu chi tiet cua bao gia.",
    "sales_orders": "Don ban hang duoc tao tu bao gia da duyet.",
    "delivery_orders": "Lenh giao hang va cua so lay/giao hang.",
    "delivery_order_details": "Danh sach hang hoa cua tung lenh giao hang.",
    "parking_lists": "Ho so gom kien hang sinh tu DO/SO de quan ly vao bai va boc hang.",
    "parking_list_items": "Dong hang hoa duoc phan bo vao Parking List.",
    "parking_labels": "Tem QR duy nhat cho tung kien hang.",
    "parking_events": "Lich su quet QR va chuyen trang thai Parking List.",
    "transport_trips": "Chuyen van tai thuc te lien ket DO/FO va ke hoach quay dau.",
    "trip_delivery_orders": "Bang lien ket nhieu-nhieu giua Trip va DO.",
    "transport_trip_legs": "Cac chang giao, backhaul hoac chay rong cua Trip.",
    "freight_orders": "Lenh van tai chuan dung cho lap ke hoach va tai chinh.",
    "freight_units": "Don vi hang van tai duoc gom tu nhu cau.",
    "freight_order_units": "Lien ket Freight Order voi cac don vi hang.",
    "transport_demands": "Nhu cau van tai dau vao truoc khi tao Freight Unit/Order.",
    "resource_assignments": "Phan cong xe, tai xe va nguon luc cho lenh van tai.",
    "transport_events": "Su kien tracking, check-in, pickup, arrival va POD.",
    "transport_event_documents": "Chung tu dinh kem theo su kien van tai.",
    "vehicle_tracking": "Du lieu vi tri/toc do GPS cua xe.",
    "pod": "Ban ghi POD tuong thich voi luong cu.",
    "delivery_pod_records": "Thong tin giao nhan va chu ky theo diem giao.",
    "delivery_pod_documents": "Tep anh/PDF POD cua tung diem giao.",
    "delivery_order_closeouts": "Ket qua chot gia cuoi sau khi giao hang.",
    "delivery_order_charge_adjustments": "Cac khoan tang/giam gia khi chot DO.",
    "ar_invoices": "Hoa don phai thu sinh tu DO da giao.",
    "ap_invoices": "Hoa don phai tra cho nha cung cap/carrier.",
    "ap_invoice_lines": "Chi tiet hang muc tren hoa don phai tra.",
    "freight_actual_costs": "Chi phi van hanh thuc te cua Freight Order/Trip.",
    "freight_charge_items": "Dong chi phi chi tiet cua ho so chi phi thuc te.",
    "freight_cost_documents": "Chung tu dinh kem cho chi phi van tai.",
    "freight_settlements": "Ho so doi soat cac khoan phai tra.",
    "settlement_payments": "Cac lan thanh toan cua mot ho so doi soat.",
    "epl_expense_vouchers": "Phieu chi phi EPL lien ket Trip va Actual Cost.",
    "shipment_costs": "Chi phi chuyen hang cua luong nghiep vu cu.",
    "gl_transactions": "But toan so cai phat sinh tu hoa don va nghiep vu tai chinh.",
    "journal_batches": "Lo but toan de kiem soat ghi so.",
    "journal_lines": "Dong no/co cua tung lo but toan.",
    "chart_of_accounts": "He thong tai khoan ke toan.",
    "accounting_periods": "Ky ke toan va trang thai mo/khoa so.",
    "account_mappings": "Anh xa nghiep vu sang tai khoan ke toan.",
    "price_lists": "Bang gia dich vu theo doi tuong ap dung.",
    "cost_formulas": "Cong thuc va cau thanh chi phi theo loai xe/tien te.",
    "currencies": "Danh muc tien te cua luong du lieu goc.",
    "items": "Danh muc hang hoa.",
    "uoms": "Danh muc don vi tinh.",
    "carriers": "Danh muc nha van chuyen thue ngoai.",
    "tenders": "Dot moi thau van tai.",
    "tender_offers": "Bao gia cua carrier trong mot dot thau.",
    "driver_qualifications": "Bang cap/chung chi va dieu kien cua tai xe.",
    "warehouse_appointments": "Lich hen kho cho lay/giao hang.",
    "incidents": "Su co phat sinh trong qua trinh van chuyen.",
    "audit_logs": "Nhat ky thao tac phuc vu truy vet.",
    "roles": "Danh muc vai tro phan quyen.",
    "users": "Tai khoan nguoi dung he thong.",
    "idempotency_records": "Khoa chong tao trung khi goi lai API.",
    "migration_quarantine": "Du lieu khong hop le duoc cach ly khi migration.",
    "freight_order_legacy_links": "Lien ket Freight Order voi ma ho so he thong cu.",
}


TAG_VI = {
    "default": "API ung dung chung",
    "TMS Core Planning": "Lap ke hoach va dieu phoi van tai",
    "TMS Finance": "Chi phi, cong no va doi soat",
    "TMS Reporting": "Bao cao van tai",
}


def humanize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def table_purpose(name: str) -> str:
    return TABLE_PURPOSES.get(name, f"Luu tru du lieu nghiep vu {humanize(name)}.")


def format_default(column: Any) -> str:
    default = column.default or column.server_default
    if default is None:
        return "-"
    value = getattr(default, "arg", default)
    return str(value).replace("\n", " ")


def generate_database_doc() -> str:
    tables = sorted(Base.metadata.tables.values(), key=lambda item: item.name)
    lines = [
        "# Tài liệu cơ sở dữ liệu EPL Logistics",
        "",
        "> Tài liệu này được sinh từ SQLAlchemy metadata của ứng dụng. Hệ thống production sử dụng PostgreSQL qua `DATABASE_URL`.",
        "",
        f"Tổng số bảng: **{len(tables)}**.",
        "",
        "## Quy ước",
        "",
        "- `PK`: khóa chính.",
        "- `FK`: khóa ngoại theo định dạng `bảng.cột`.",
        "- `Bắt buộc`: cột không chấp nhận NULL.",
        "- Dữ liệu thực tế phải được thay đổi qua service/API, không sửa trực tiếp trong PostgreSQL nếu không có quy trình migration.",
        "",
        "## Danh sách bảng",
        "",
    ]
    for table in tables:
        lines.append(f"- [`{table.name}`](#{table.name.replace('_', '-')}) - {table_purpose(table.name)}")
    for table in tables:
        lines.extend(["", f"## `{table.name}`", "", table_purpose(table.name), ""])
        lines.append("| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |")
        lines.append("|---|---|---|---|---|")
        for column in table.columns:
            constraints = []
            if column.primary_key:
                constraints.append("PK")
            if not column.nullable:
                constraints.append("Bắt buộc")
            if column.unique:
                constraints.append("Unique")
            foreign_keys = sorted(str(fk.target_fullname) for fk in column.foreign_keys)
            constraints.extend(f"FK -> `{fk}`" for fk in foreign_keys)
            desc = f"Trường {humanize(column.name)} của bảng `{table.name}`."
            lines.append(
                f"| `{column.name}` | `{column.type}` | {'; '.join(constraints) or '-'} | "
                f"`{format_default(column)}` | {desc} |"
            )
        indexes = sorted(index.name for index in table.indexes if index.name)
        if indexes:
            lines.extend(["", f"Chỉ mục: {', '.join(f'`{name}`' for name in indexes)}."])
    lines.extend(["", "---", "", "Tái sinh tài liệu: `python backend/scripts/generate_system_docs.py` (chạy theo hướng dẫn trong `docs/README.md`).", ""])
    return "\n".join(lines)


def resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    current: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        current = current.get(part, {}) if isinstance(current, dict) else {}
    return current if isinstance(current, dict) else {}


def expanded_schema(schema: dict[str, Any], openapi: dict[str, Any]) -> dict[str, Any]:
    """Resolve a local OpenAPI reference while preserving inline metadata."""
    if "$ref" not in schema:
        return schema
    resolved = resolve_ref(openapi, schema["$ref"])
    return {**resolved, **{key: value for key, value in schema.items() if key != "$ref"}}


def schema_type(schema: dict[str, Any], openapi: dict[str, Any]) -> str:
    schema = expanded_schema(schema, openapi)
    if "enum" in schema:
        return " | ".join(str(value) for value in schema["enum"])
    if schema.get("type") == "array":
        return f"array<{schema_type(schema.get('items', {}), openapi)}>"
    for union_key in ("anyOf", "oneOf"):
        if union_key in schema:
            values = [schema_type(item, openapi) for item in schema[union_key]]
            return " | ".join(dict.fromkeys(values))
    return schema.get("type") or schema.get("format") or "object"


def append_body_fields(lines: list[str], schema: dict[str, Any], openapi: dict[str, Any]) -> None:
    root = expanded_schema(schema, openapi)
    if root.get("type") == "array":
        root = expanded_schema(root.get("items", {}), openapi)
    properties = root.get("properties", {})
    if not properties:
        return
    required = set(root.get("required", []))
    lines.extend([
        "",
        "| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |",
        "|---|---|---:|---|---|",
    ])
    for name, field_schema in properties.items():
        field_schema = expanded_schema(field_schema, openapi)
        default = field_schema.get("default", "-")
        description = field_schema.get("description") or field_schema.get("title") or "Trường dữ liệu nghiệp vụ."
        lines.append(
            f"| `{name}` | `{schema_type(field_schema, openapi)}` | "
            f"{'Có' if name in required else 'Không'} | `{default}` | {description} |"
        )


def schema_label(schema: dict[str, Any], openapi: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if schema.get("type") == "array":
        return f"Danh sach {schema_label(schema.get('items', {}), openapi)}"
    return schema.get("title") or schema.get("type") or "object"


def api_purpose(method: str, path: str, summary: str | None) -> str:
    if summary and not re.match(r"^(Get|Post|Put|Delete|Patch) ", summary):
        return summary
    resource = humanize(path.strip("/").replace("api/", ""))
    verbs = {
        "get": "Doc/tra cuu",
        "post": "Tao moi hoac thuc hien hanh dong tren",
        "put": "Cap nhat",
        "patch": "Cap nhat mot phan",
        "delete": "Xoa/huy",
    }
    return f"{verbs.get(method, method.upper())} {resource}."


def generate_api_doc() -> str:
    openapi = app.openapi()
    endpoints = []
    for path, path_item in sorted(openapi.get("paths", {}).items()):
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation:
                endpoints.append((path, method, operation))
    lines = [
        "# Tài liệu API EPL Logistics",
        "",
        "> Tài liệu này được sinh trực tiếp từ OpenAPI của FastAPI đang chạy. Swagger UI: `/docs`; OpenAPI JSON: `/openapi.json`.",
        "",
        f"Tổng số endpoint: **{len(endpoints)}**.",
        "",
        "## Xác thực và quy ước",
        "",
        "- API nghiệp vụ được bảo vệ bằng token cấu hình tại `EPL_TMS_API_TOKEN`; không đưa token vào URL hoặc source code.",
        "- Gửi `Content-Type: application/json` cho request JSON.",
        "- Thời gian dùng ISO 8601 và kèm múi giờ khi có thể.",
        "- Lỗi nghiệp vụ trả HTTP 4xx với thông điệp `detail`; lỗi hệ thống trả HTTP 5xx.",
        "- Không đưa `.env`, token, chữ ký hoặc POD nhạy cảm vào log/repository.",
        "",
        "## Mục lục theo nhóm",
        "",
    ]
    grouped: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    for endpoint in endpoints:
        tag = (endpoint[2].get("tags") or ["default"])[0]
        grouped.setdefault(tag, []).append(endpoint)
    for tag, items in grouped.items():
            lines.append(f"- **{TAG_VI.get(tag, tag)}**: {len(items)} endpoint.")
    for tag, items in grouped.items():
        lines.extend(["", f"## {TAG_VI.get(tag, tag)}", ""])
        for path, method, operation in items:
            title = f"{method.upper()} {path}"
            lines.extend([f"### `{title}`", "", api_purpose(method, path, operation.get("summary")), ""])
            lines.append(f"- **Operation ID:** `{operation.get('operationId', '-')}`")
            lines.append(f"- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.")
            parameters = operation.get("parameters", [])
            if parameters:
                lines.extend(["", "**Tham số**", "", "| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |", "|---|---|---:|---|---|"])
                for parameter in parameters:
                    schema = parameter.get("schema", {})
                    lines.append(
                        f"| `{parameter.get('name')}` | `{parameter.get('in')}` | "
                        f"{'Có' if parameter.get('required') else 'Không'} | `{schema_type(schema, openapi)}` | "
                        f"{parameter.get('description') or 'Tham số nghiệp vụ.'} |"
                    )
            request_body = operation.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                media_type, media = next(iter(content.items()), ("application/json", {}))
                body_schema = media.get("schema", {})
                lines.extend([
                    "",
                    "**Request body**",
                    "",
                    f"- Content-Type: `{media_type}`.",
                    f"- Schema: `{schema_label(body_schema, openapi)}`.",
                    f"- Bắt buộc: {'Có' if request_body.get('required') else 'Không'}.",
                ])
                append_body_fields(lines, body_schema, openapi)
            responses = operation.get("responses", {})
            lines.extend(["", "**Phản hồi**", "", "| HTTP | Ý nghĩa | Schema |", "|---:|---|---|"])
            for code, response in responses.items():
                content = response.get("content", {})
                _, media = next(iter(content.items()), ("", {}))
                lines.append(
                    f"| `{code}` | {response.get('description', 'Phan hoi API.')} | "
                    f"`{schema_label(media.get('schema', {}), openapi) if media else '-'}` |"
                )
            lines.append("")
    lines.extend(["---", "", "Tái sinh tài liệu: `python backend/scripts/generate_system_docs.py` (chạy theo hướng dẫn trong `docs/README.md`).", ""])
    return "\n".join(lines)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    database_doc = generate_database_doc()
    api_doc = generate_api_doc()
    (DOCS_DIR / "DATABASE_SCHEMA_VI.md").write_text(database_doc, encoding="utf-8")
    (DOCS_DIR / "API_REFERENCE_VI.md").write_text(api_doc, encoding="utf-8")
    summary = {
        "tables": len(Base.metadata.tables),
        "api_endpoints": sum(
            1
            for path_item in app.openapi().get("paths", {}).values()
            for method in ("get", "post", "put", "patch", "delete")
            if method in path_item
        ),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
