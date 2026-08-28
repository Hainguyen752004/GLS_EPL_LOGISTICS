# Parking List / Packing List Design

## Goal

Add a real database-backed Parking List feature linked to the existing SO/DO workflow. The feature creates printable package labels and a detailed packing list, each with a stable QR code and auditable operational status.

## Scope

- Generate one versioned Parking List for a Delivery Order (DO).
- Reuse DO/SO data for shipment header fields.
- Reuse `DeliveryOrderDetail` rows for item-level packing data.
- Store package/box labels separately because one DO can contain multiple boxes.
- Print a compact label and a detailed Packing List.
- Scan a QR code to open the correct DO/package record.
- Record authenticated, idempotent status updates and scan history.

## Source Of Truth

DO supplies customer, route, origin, destination, pickup/delivery windows, package totals and shipment status. SO and `DeliveryOrderDetail` supply the commercial order and item rows. The system must block generation when required DO/SO/item data is missing; it must never invent barcode, SKU, item description, weight or cube values.

## Data Model

### `parking_lists`

One active version per DO. Fields include id, do_id, so_id, trip_id, version, customer/store identifiers, route/wave/gate, box_count, total_pieces, total_weight_kg, total_cube_m3, status, generated_at, generated_by, updated_at and updated_by. Unique active version is enforced per DO.

### `parking_list_items`

Rows copied from the source DO/SO detail at generation time: parking_list_id, source_detail_id, barcode, item_id_laos, item_id_thai, sku, description, case_qty, piece_qty, uom, weight_kg, cube_m3 and note. Source values remain traceable.

### `parking_labels`

One row per package: parking_list_id, package_no, package_total, qr_token, label_status, printed_at, printed_by and reprint_count. `qr_token` is opaque and unique; QR payload is a same-origin scan URL containing only the token.

### `parking_events`

Audit trail: parking_list_id, label_id, event_type, event_time, actor, note and idempotency key. Events are append-only.

## Statuses

`draft -> ready -> parked -> gate_in -> loaded -> dispatched -> delivered -> cancelled`.

Only valid forward transitions are allowed, with an explicit cancellation path. Repeating the same request with the same idempotency key returns the original result without duplicating an event.

## API Surface

- `POST /api/parking-lists/from-do/{do_id}`: generate or return the active version.
- `GET /api/parking-lists`: paginated search/filter by date, DO, SO, customer, route and status.
- `GET /api/parking-lists/{id}`: detail with header, item rows, labels and event history.
- `GET /api/parking-lists/{id}/label`: printable compact labels.
- `GET /api/parking-lists/{id}/packing-list`: printable detailed manifest.
- `GET /api/parking-qr/{token}`: read-only token lookup.
- `POST /api/parking-lists/{id}/status`: authenticated status transition.

Mutation endpoints require the existing authenticated principal and `Idempotency-Key` contract. Cross-DO tokens, missing source rows, invalid transitions and cancelled records return domain errors.

## UI

Add a separate `Parking List` page under operations. The first viewport contains a search field, date/status filters, result count and a compact table. Selecting a row opens a fixed-width detail drawer with shipment header, package cards, item table, event history, `In nhãn`, `In Packing List` and status actions. The page is responsive without rendering the entire data set at once.

The label mirrors the reference: company/RDC, store/customer, route, wave, gate, package number, item/package totals, weight, cube and QR. The detailed document contains the full item table and totals. Missing optional fields are shown as `-`; missing required fields block printing and explain what must be completed.

## Testing

Backend tests cover source lineage, one active version per DO, QR uniqueness, pagination, status transitions, idempotency, authorization, cross-DO isolation and missing-data validation. Frontend tests cover search, detail drawer, print actions, empty/error states and responsive layout. Existing SO/DO/POD tests must remain green.

