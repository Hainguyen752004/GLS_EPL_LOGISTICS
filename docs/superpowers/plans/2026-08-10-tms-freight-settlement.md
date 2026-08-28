# TMS Core 5 Freight Settlement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng sub-ledger chi phí vận tải, AP, payment và settlement chính xác bằng Decimal, nối Journal hiện có mà không phá AR.

**Architecture:** Domain chia thành bốn service biên rõ: money/master policy, actual cost, AP posting, settlement/payment. Tất cả mutation dùng row lock/version/idempotency/audit trong một transaction; migration `007` nâng JournalBatch thành nguồn đa loại và validate schema trước readiness.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL production, SQLite test cô lập, Decimal, pytest.

---

## Chunk 1: Money policy và Actual Cost

### Task 1: Money/master models và calculator

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_money.py`
- Create: `backend/tests/test_tms_freight_finance.py`

- [ ] RED tests cho `CurrencyDefinition`, `CurrencyRateHistory`, `TaxCode`, `FinanceControlConfig`; missing config trả navigation target Master Data.
- [ ] RED tests Decimal `Numeric(24,6)`, minor units 0/2/3, `ROUND_HALF_UP`, inclusive/exclusive/exempt tax, multi-rate và deterministic residual allocation.
- [ ] Chạy `python -m pytest backend/tests/test_tms_freight_finance.py -k "money or master" -q`; expected FAIL do model/service chưa tồn tại.
- [ ] Cài pure functions `quantize_currency`, `calculate_charge_line`, `allocate_rounding_residual`, `to_functional`; từ chối bool/float/NaN/Infinity.
- [ ] GREEN cùng lệnh; ghi RED/GREEN checkpoint.

### Task 2: Actual cost state machine và GPS variance

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_cost_service.py`
- Modify: `backend/tests/test_tms_freight_finance.py`

- [ ] RED tests cho `FreightActualCost`, `FreightChargeItem`, `FreightCostDocument`; một active cost/FO, draft edit-only, delivered-only, version và audit/IP.
- [ ] RED tests Haversine sắp `event_time, recorded_at, id`, bỏ điểm trùng, thiếu điểm, planned=0 và Decimal km.
- [ ] RED tests submit/approve, carrier từ awarded tender/internal configured carrier, active/tax snapshot, SOD fail-closed và missing master navigation.
- [ ] Chạy `python -m pytest backend/tests/test_tms_freight_finance.py -k "cost or distance" -q`; expected FAIL theo mã domain.
- [ ] Cài service với row lock, server totals, immutable sau submit, CAS version và AuditLog.
- [ ] GREEN; rollback test chứng minh cost/items/docs/audit/status nguyên tử.

## Chunk 2: AP và Journal đa nguồn

### Task 3: AP lifecycle và vendor invariants

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_ap_service.py`
- Modify: `backend/tests/test_tms_freight_finance.py`

- [ ] RED tests AP create-from-approved-cost snapshot, normalized vendor invoice uniqueness/carrier, one active AP/cost, line/header currency consistency.
- [ ] RED tests submit/approve/post permission matrix, SOD, closed period, missing tax/FX/account mapping, version/idempotency replay.
- [ ] RED tests AP reversal: posted/no active payment only, one reversal, no reversal cycle, cost reversal prohibited while AP active.
- [ ] Chạy `python -m pytest backend/tests/test_tms_freight_finance.py -k "ap or reversal" -q`; expected FAIL.
- [ ] Cài state machine, locks, DB-last-defense conflict translation và audit.
- [ ] GREEN focused.

### Task 4: Journal source evolution và balanced posting

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_journal_service.py`
- Modify: `backend/tests/test_tms_freight_finance.py`

- [ ] RED tests JournalBatch `source_type/source_id`, AR backward compatibility, unique source, AP expense/input-tax/AP entries, debit=credit functional.
- [ ] RED tests exactly-once post, concurrent post and injected failure rollback AP/batch/lines/audit/idempotency.
- [ ] Chạy RED `python -m pytest backend/tests/test_tms_freight_finance.py -k journal -q`; expected FAIL vì journal hiện chỉ nhận AR.
- [ ] Cài posting pure builder + transactional persist; source-specific account mapping and open period.
- [ ] Chạy `python -m pytest backend/tests/test_tms_freight_finance.py -k journal -q`; expected PASS.

## Chunk 3: Settlement, payment và API

### Task 5: Settlement/payment accounting

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_settlement_service.py`
- Modify: `backend/tests/test_tms_freight_finance.py`

- [ ] RED tests settlement amounts denominated AP currency, payment same currency, overpayment, partial/paid transitions, payment permission/version/idempotency.
- [ ] RED tests payment Journal `Dr AP / Cr Bank|Cash`, realized FX gain/loss, closed period, void/reversal và AP reversal blocked while payment active.
- [ ] RED two-session same/different key and simultaneous payment; exactly one payment/audit/journal.
- [ ] Assert công thức từng partial payment: `ap_functional_portion = quantize(payment_amount * ap_rate)`, `payment_functional = quantize(payment_amount * payment_rate)`, `realized_fx = ap_functional_portion - payment_functional`; số dương post FX gain credit, số âm post FX loss debit với absolute amount. Phân bổ minor-unit residual vào payment cuối; settlement amounts luôn AP currency.
- [ ] Assert DB checks `payment.amount>0`, `paid_amount>=0`, `paid_amount<=approved_amount`, `remaining_amount=approved_amount-paid_amount`; unique `reversal_of_payment_id`, cấm reversal-of-reversal.
- [ ] Chạy RED `python -m pytest backend/tests/test_tms_freight_finance.py -k "settlement or payment" -q`; expected FAIL trước khi cài service.
- [ ] Cài row locks + CAS + unique defenses; atomic payment/status/journal/audit/idempotency.
- [ ] GREEN cùng lệnh và rollback tests.

### Task 6: Authenticated bounded APIs

**Files:**
- Create: `backend/app/routes/tms_finance_routes.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/auth_middleware.py`
- Create: `backend/app/services/finance_authorization.py`
- Modify: `backend/tests/test_tms_freight_finance.py`

- [ ] RED API contract tests list/get/create/edit draft/submit/approve/reverse cost; create/submit/approve/post/reverse AP; create/payment/void settlement; dashboard.
- [ ] RED auth/role/SOD fail-closed, bounded schemas, `Idempotency-Key`, Vietnamese 401/403/409/422, secret-safe logs; assert no DELETE submitted financial headers.
- [ ] RED permission resolver: bearer principal string tra `User.username|id`, lấy Role.permissions JSON array allowlist; malformed/missing user/role/JSON fail 403. Không nhận permission từ header/token payload. Test exact matrix create/approve/post/payment/read và SOD.
- [ ] Chạy RED `python -m pytest backend/tests/test_tms_freight_finance.py -k "api or auth or permission" -q`; expected FAIL trước khi include router/resolver.
- [ ] Cài router riêng `/api/tms/finance`; include đúng một lần, response `{message,data}` và dependency principal/permissions.
- [ ] Chạy `python -m pytest backend/tests/test_tms_freight_finance.py backend/tests/test_route_uniqueness.py -q`; expected PASS.

## Chunk 4: Migration 007 và verification

### Task 7: PostgreSQL/SQLite migration

**Files:**
- Create: `backend/app/migrations/v007_tms_freight_settlement.py`
- Modify: `backend/app/migrations/runner.py`
- Modify: `backend/app/routes/health_routes.py`
- Create: `backend/tests/test_migration_v007_freight_settlement.py`
- Modify: `backend/tests/test_migration_v001.py`
- Modify: `backend/tests/test_database_readiness.py`

- [ ] RED migration tests bảng/cột/types/nullability/default/PK/FK/check/partial unique/index; Journal backfill v001-v006 populated; head/readiness `007`.
- [ ] RED schema drift per invariant, repeat-run, injected failure no marker, rollback guard populated AP/payment/journal.
- [ ] RED scoped idempotency migration: rebuild `idempotency_records` thêm `actor,method,path,key,request_hash,response_json,status,created_at`, PK/unique `(actor,method,path,key)`; backfill legacy rows actor=`legacy`, method=`LEGACY`, path=operation, key=idempotency_key; bảo toàn response/hash.
- [ ] RED JournalBatch rebuild/copy: `invoice_id` nullable, backfill `source_type='ar_invoice',source_id=invoice_id`, drop old unique invoice-only, add unique `(source_type,source_id)` và source check. JournalLine thêm `transaction_amount Numeric(24,6)`, `transaction_currency`, `exchange_rate Numeric(18,8)`, `functional_debit/credit Numeric(24,6)`; backfill từ debit/credit/currency/rate và giữ các cột cũ tương thích.
- [ ] Chạy RED `python -m pytest backend/tests/test_migration_v007_freight_settlement.py backend/tests/test_migration_v001.py backend/tests/test_database_readiness.py -q`; expected FAIL vì v007 chưa tồn tại.
- [ ] Cài upgrade/validation/rollback dependency-safe cho SQLite và PostgreSQL; authorized rollback khôi phục AR-only Journal khi không còn AP data.
- [ ] Runner gọi `pre_rollback_validate(connection,dialect,restore_from)` của từng migration trước DDL. v007 từ chối rollback nếu có cost/AP/settlement/payment/AP-source journal; PostgreSQL refusal phải xảy ra trước DROP/ALTER và giữ marker/schema. `restore_from` là authorization/reference được audit trong CLI output, không phải đường dẫn được tự động đọc.
- [ ] Chạy `python -m pytest backend/tests/test_migration_v007_freight_settlement.py backend/tests/test_migration_v001.py backend/tests/test_database_readiness.py -q`.
- [ ] Chạy offline `python -m migrations.runner upgrade --database-url postgresql://not-connected/epl --dry-run` từ `backend/app`; không mở kết nối.

### Task 8: Verification cuối

**Files:**
- Modify: checklist tài liệu này.

- [ ] `python -m py_compile backend/app/models.py backend/app/services/tms_money.py backend/app/services/tms_cost_service.py backend/app/services/tms_ap_service.py backend/app/services/tms_journal_service.py backend/app/services/tms_settlement_service.py backend/app/routes/tms_finance_routes.py backend/app/migrations/v007_tms_freight_settlement.py`.
- [ ] `python -m pytest backend/tests/test_tms_freight_finance.py backend/tests/test_migration_v007_freight_settlement.py backend/tests/test_route_uniqueness.py backend/tests/test_database_readiness.py -q`.
- [ ] `python -m pytest backend/tests -q`; chỉ đánh dấu complete khi exit 0.
- [ ] Xác nhận `.env` không đổi và không kết nối PostgreSQL Linux.

## Interfaces bắt buộc

```python
# tms_money.py
def quantize_currency(db, amount: Decimal, currency_code: str) -> Decimal: ...
def calculate_charge_line(db, quantity, unit_price, tax_code, tax_mode) -> dict: ...
def to_functional(db, amount, currency_code, rate_date) -> dict: ...

# tms_cost_service.py
def create_cost(db, freight_order_id, data, key, actor, permissions): ...
def save_charge_item(db, cost_id, data, expected_version, key, actor, permissions): ...
def submit_cost(db, cost_id, expected_version, key, actor, permissions): ...
def approve_cost(db, cost_id, expected_version, key, actor, permissions): ...
def reverse_cost(db, cost_id, data, key, actor, permissions): ...
def save_cost_document(db, cost_id, data, expected_version, key, actor, permissions): ...
def update_cost_document(db, cost_id, document_id, data, expected_version, key, actor, permissions): ...
def delete_draft_charge_item(db, cost_id, item_id, expected_version, key, actor, permissions): ...
def delete_draft_cost_document(db, cost_id, document_id, expected_version, key, actor, permissions): ...

# tms_ap_service.py
def create_ap_from_cost(db, cost_id, data, key, actor, permissions): ...
def transition_ap(db, ap_id, action, expected_version, key, actor, permissions): ...
def reverse_ap(db, ap_id, data, key, actor, permissions): ...

# tms_settlement_service.py
def create_settlement(db, ap_id, data, key, actor, permissions): ...
def post_payment(db, settlement_id, data, key, actor, permissions): ...
def reverse_payment(db, payment_id, data, key, actor, permissions): ...
def get_finance_dashboard(db, filters, actor, permissions): ...
```

Idempotency scope `(actor, method, path, key)` phải được truyền từ router/service context; request hash canonical và response lưu cùng transaction. Permission list resolve từ User/Role; missing config fail closed. Không dùng `eval` từ CostFormula.

## Endpoint inventory và task boundaries

- Cost queries: `GET /costs`, `GET /costs/{id}`, dashboard; commands: create, item POST/PUT/DELETE draft, document POST/PUT/DELETE draft, submit, approve, reverse. Mỗi POST/PUT/DELETE item/document nhận `expected_version`, thực hiện CAS trên cost header và tăng version đúng một lần.
- AP queries: `GET /ap-invoices`, `GET /ap-invoices/{id}`; commands: create-from-cost, submit, approve, post, reverse.
- Settlement queries: `GET /settlements`, `GET /settlements/{id}`; commands: create, payment, payment reverse.
- Header không có DELETE. Item/document DELETE chỉ draft và versioned.

Implementer phải xử lý theo checkpoint nhỏ trong từng Task: (a) models + RED/GREEN pure validation, (b) một transition + RED/GREEN, (c) concurrency/idempotency + RED/GREEN, (d) API. Không viết toàn bộ task rồi mới chạy test.

## Concurrency verification seam

- SQLite: CAS `UPDATE ... WHERE version=:expected`, unique constraint và hai independent sessions/barrier chứng minh một winner; bắt `IntegrityError` bằng savepoint và re-read idempotency.
- PostgreSQL offline: compile query và assert `SELECT ... FOR UPDATE` cho cost/AP/settlement/payment; dry-run assert partial unique/check constraints. Fake transactional connection mô phỏng waiting writer bằng pre-lock miss/post-lock re-read. Không tuyên bố live PostgreSQL contention khi server tắt.
