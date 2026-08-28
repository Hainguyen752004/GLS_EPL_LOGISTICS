# Driver Shift And Vehicle Turnaround Design

## Decision

Implement scheduling option 3 in `Master Data > Quản lý Tài xế & Sắp Ca`:

- Schedule a driver into a shift first.
- Assigning a vehicle is optional during shift planning.
- Dispatch remains the final resource lock before departure.
- Move the seven-day vehicle plan into this module as `Lịch xe 7 ngày`.

## Source Of Truth

- Route geometry and configured distance come from Route Master.
- Ordered stops, dwell time and planned/actual timestamps come from Trip legs.
- Live speed comes from the latest valid GPS event when available.
- Fallback speed priority is assigned vehicle average, vehicle type average, then Trip-leg average.
- A return forecast is valid only when the Trip has a configured backhaul or empty-return leg.

## Availability Model

For an outbound Trip from A to B:

1. `available_at_destination` is the final delivery arrival plus final stop dwell/unload time.
2. The vehicle is available at B for a compatible backhaul after that timestamp.
3. If no backhaul is assigned and an empty-return leg exists, `available_at_origin` is the arrival of that return leg.
4. Scheduling a vehicle before either applicable availability timestamp is rejected.
5. Missing return route data produces `RETURN_ROUTE_REQUIRED`; the system does not invent a distance.

## Scheduling Rules

- Driver shifts cannot overlap for the same driver.
- Vehicle assignments cannot overlap for the same vehicle.
- A vehicle cannot be assigned before its previous Trip availability timestamp.
- A backhaul starts at the previous Trip destination and must link a return DO.
- An empty return is used only when no backhaul has been assigned.
- Drag-and-drop is a UI gesture only; persistence occurs through the scheduling API and is confirmed by reloading the saved record.

## UI

- Left rail: searchable driver list and a button to open the full driver profile.
- Center: week calendar with morning, afternoon and night shift rows.
- Right inspector: selected shift, optional `Gán kèm xe`, vehicle selection and warnings.
- Tabs: `Lịch tài xế`, `Lịch xe 7 ngày`, `Cảnh báo`.
- Desktop supports drag-and-drop. Touch devices support tap driver, then tap a calendar slot.
- Vehicle timeline distinguishes outbound, available at B, backhaul and empty return.

## API

- `GET /api/tms/scheduling/driver-shifts?start=&end=`
- `POST /api/tms/scheduling/driver-shifts`
- `PUT /api/tms/scheduling/driver-shifts/{shift_id}`
- `DELETE /api/tms/scheduling/driver-shifts/{shift_id}`
- `GET /api/tms/scheduling/vehicle-availability?start=&end=`

All commands write an audit record and return the saved database representation.
