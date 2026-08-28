const assert = require('assert');
const cockpit = require('../js/tms-cockpit-utils.js');

const baseTrip = {
  id: 'TRIP-26-8',
  status: 'in_transit',
  trip_type: 'round_trip',
  vehicle_id: 'XE-001',
  driver_id: 'DRV-001',
  planned_arrival_at: '2026-08-26T11:28:00+07:00',
  planned_return_at: '2026-08-26T15:30:00+07:00',
  legs: [
    { sequence_no: 1, leg_type: 'delivery', origin: 'Kho A', destination: 'Điểm B', distance_km: 100, avg_speed_kmh: 50, status: 'completed', actual_arrival_at: '2026-08-26T10:00:00+07:00' },
    { sequence_no: 2, leg_type: 'empty_return', origin: 'Điểm B', destination: 'Kho A', distance_km: 100, avg_speed_kmh: 50, status: 'planned' }
  ]
};

assert.strictEqual(typeof cockpit.getTripJourneyPresentation, 'function');
const journey = cockpit.getTripJourneyPresentation(baseTrip);
assert.strictEqual(journey.status_label, 'Chờ quay về');
assert.strictEqual(journey.location_label, 'Đang ở Điểm B');
assert.strictEqual(journey.next_action, 'Chọn hàng chiều về hoặc xác nhận quay về rỗng');
assert.deepStrictEqual(journey.legs.map(leg => leg.label), ['Giao hàng', 'Quay về rỗng']);
assert.strictEqual(journey.legs[0].status_label, 'Đã hoàn tất');
assert.strictEqual(journey.legs[1].status_label, 'Chờ thực hiện');

const completed = cockpit.getTripJourneyPresentation({
  ...baseTrip,
  status: 'completed',
  actual_return_at: '2026-08-26T15:25:00+07:00',
  legs: baseTrip.legs.map(leg => ({ ...leg, status: 'completed' }))
});
assert.strictEqual(completed.status_label, 'Đã hoàn tất');
assert.strictEqual(completed.location_label, 'Đã về Kho A');
assert.strictEqual(completed.next_action, 'Sẵn sàng nhận chuyến mới');

console.log('TRIP_JOURNEY_READABLE_UI_OK');
