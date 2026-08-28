# EPL Transport Revenue And Expense Reporting Design

## Goal

Build a database-backed reporting module that reproduces every business field in EPL's monthly transport revenue spreadsheet, adds management charts, and turns the supplied expense form into a controlled Trip/DO expense-voucher workflow.

## Reporting Grain

One revenue row represents one completed Delivery Order allocation on a Transport Trip. The row joins the DO, Trip, Freight Order, SO, customer, route, vehicle, driver, POD closeout, AR invoice, approved Actual Cost, and currency snapshots. A DO without a completed delivery or posted AR invoice remains visible as an exception but is excluded from recognized revenue totals.

## User Experience

The existing Reporting view becomes a three-tab operational module:

1. `Tong quan`: period and dimension filters, KPI strip, revenue/cost/profit trend, customer/route bar chart, and cargo/currency distribution chart.
2. `Doanh thu theo chuyen`: a dense export-oriented table containing all EPL spreadsheet columns, sticky identity columns, responsive overflow, and a row detail drawer linked to source records.
3. `Phieu chi phi`: voucher worklist and editor linked to a Trip/DO. Header fields are auto-filled from master and workflow data; fuel and other expenses are stored as FreightChargeItem rows; documents use FreightCostDocument; submit and approve use the existing Actual Cost state machine.

On small screens, KPI and charts stack, tables become horizontally scrollable, and the voucher editor uses a single-column form. No viewport scaling transform is used.

## Revenue Fields

The API returns: sequence number, departure date, dispatch order number, recognition date, invoice number, origin, destination, carrier/agency company, driver, tractor plate, trailer plate, vehicle code, customer, cargo type, trip count, unit of measure, weight in tonnes, transaction currency/rate, unit price and total in LAK/THB/USD/CNY, source transaction total, and note.

Fields unavailable in the current model are explicit `null`/empty values and appear in a `missing_fields` array. They must never be silently invented. Trailer plate is initially read from vehicle metadata when available and remains blank otherwise.

## Expense Voucher

The voucher is a presentation and workflow projection over FreightActualCost rather than a competing ledger. New voucher metadata stores voucher number/date, vehicle manager, payment method, contract number, machine-number notes, checked-by identity, and business note. It has a one-to-one link to the active Actual Cost record.

Line groups:

- Fuel: quantity in litres, unit price, tax, amount.
- Other expenses: service, purchase, repair/maintenance, toll, loading/unloading, and other.

State transitions:

`draft -> submitted -> approved -> AP invoice/settlement posting`

Only draft vouchers can be edited or deleted. Submit validates Trip/DO, vehicle, driver, currency, at least one positive line, and document rules. Approve uses finance authorization and optimistic version checks. Every command requires an idempotency key and writes an audit record.

## Money Rules

- Recognized revenue is the posted AR invoice total, backed by the final DO closeout.
- Cost is the active approved Actual Cost total.
- Profit equals recognized revenue minus approved cost.
- Margin percentage equals profit divided by recognized revenue.
- Conversions use dated CurrencyRateHistory snapshots. Historical rows never use the current rate retroactively.
- Missing exchange rates produce an exception flag and no fabricated conversion.

## API

- `GET /api/tms/reporting/transport-revenue`: filtered rows, totals, chart series, and data-quality exceptions.
- `GET /api/tms/reporting/transport-revenue/export.csv`: UTF-8 CSV with the EPL column order, usable by Excel.
- `GET /api/tms/reporting/expense-vouchers`: voucher worklist.
- `GET /api/tms/reporting/expense-vouchers/{id}`: printable voucher detail.
- `PUT /api/tms/reporting/trips/{trip_id}/expense-voucher`: create/update draft metadata and cost lines atomically through the Actual Cost service.

Existing Actual Cost submit/approve/document APIs remain authoritative for transitions and attachments.

## Error Handling And Verification

The frontend only displays success after the API commits. Failed commands retain form values. Tests cover report joins, recognition rules, currency conversion, voucher persistence, transition guards, export columns, frontend API wiring, charts, responsive table behavior, and Vietnamese source encoding.
