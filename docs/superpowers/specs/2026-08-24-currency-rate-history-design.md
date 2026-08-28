# Currency Rate Current And History Design

## Goal

Prevent locale-formatted exchange rates from being misread and clearly separate approved, proposed, and previous rates.

## Design

- Parse both Vietnamese (`26.173,50`) and international (`26,173.50`) numeric formats through one shared frontend utility.
- Keep `currencies` as the approved operational snapshot.
- Persist approved daily snapshots in `currency_rate_history` using `APPROVED_UI`; retain the immediately preceding same-day value as `PREVIOUS_UI`.
- Return a summary endpoint containing current, previous, change amount, change percentage, source, and history.
- A provider refresh remains a proposal. Only `Lưu tỷ giá mới` changes approved rates and history.
- Each currency card labels the editable proposal, approved current value, previous value, and increase/decrease. A compact history table provides audit context.

## Failure Rules

- Reject zero, negative, missing, or ambiguous invalid values atomically.
- Never partially save a subset of currencies.
- Provider failures retain approved values and history.
- Display the correct Baht symbol `฿`.

## Verification

- Unit-test locale parsing and conversion.
- API-test current/previous history and atomic validation.
- UI-contract-test current/reference/previous labels and history rendering.
