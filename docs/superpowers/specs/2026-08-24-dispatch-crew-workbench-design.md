# Dispatch Crew Workbench Design

## Goal

Make daily dispatch a real scheduling surface: dispatchers drag a pending DO onto an available vehicle time lane, confirm the main driver, optional co-driver and packaging, then persist the whole assignment atomically.

## Ownership

- Master Data owns driver/co-driver profiles, qualifications, default vehicle and shift planning.
- Dispatch consumes vehicle availability, driver shifts, Trips and pending DOs. It does not edit personnel master records.
- Delivery completion releases every active resource assigned to the completed delivery.

## Dispatch UX

- Left: pending DO queue. A DO card is draggable on desktop and selectable before tapping a lane on touch devices.
- Center: one lane per vehicle for the selected day, including idle vehicles. Existing Trips occupy time blocks; idle ranges remain valid drop targets.
- Right: selected DO/Trip details, capacity comparison, fixed vehicle from the target lane, main driver, optional co-driver and packaging.
- Main-driver choices only include main drivers available for the assignment interval. Co-driver choices only include co-drivers available for the same interval.
- Dropping a DO selects a vehicle and opens the detail panel. Data is not committed until the user confirms dispatch.

## Persistence And Validation

- Delivery Order and Trip keep the selected vehicle, main driver and co-driver identifiers.
- Resource Assignment keeps the co-driver identifier for Trip dispatch.
- Direct DO dispatch persists the legacy DO assignment consistently for records that do not yet have a Trip.
- Backend validates distinct crew members, role, ready status, shift/vehicle compatibility, overlapping DO/Trip assignments, vehicle compliance and capacity.
- Dispatch writes all status changes in one database transaction. Any validation error leaves every record unchanged.
- Completion marks assignments complete and restores the vehicle, main driver and co-driver to ready status only when they have no other active assignment.

## Compatibility

- Existing rows with no co-driver remain valid.
- Existing Vietnamese ready-status variants are recognized, while newly written statuses use one canonical display value.
- A missing shift does not block legacy data; a configured overlapping shift must match the selected vehicle.

## Verification

- Backend API tests cover accepted dispatch payload, crew role validation, duplicate crew, overlap, persistence and release.
- Migration tests cover the added co-driver columns.
- Frontend contract tests cover idle vehicle lanes, drag/drop and touch selection.
- Browser screenshots verify desktop and mobile layout without horizontal page overflow.
