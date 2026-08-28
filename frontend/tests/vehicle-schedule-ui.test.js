const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const utils = require('../js/tms-cockpit-utils.js');

test('vehicle schedule returns one vehicle timetable with trip and availability cells', () => {
  const schedule = utils.buildVehicleSchedule({
    vehicles: [{ id: 'V-01', brand: 'Isuzu', type: 'Container 20FT' }],
    transport_trips: [{
      id: 'TRIP-01', vehicle_id: 'V-01', driver_id: 'D-01',
      planned_departure_at: '2026-08-24T08:00:00+07:00',
      planned_return_at: '2026-08-26T16:00:00+07:00',
      status: 'in_transit', return_distance_km: 44
    }]
  }, 'V-01', '2026-08-24');

  assert.equal(schedule.vehicle_id, 'V-01');
  assert.equal(schedule.days.length, 7);
  assert.equal(schedule.days[0].status, 'busy');
  assert.equal(schedule.days[1].trip_ids[0], 'TRIP-01');
  assert.equal(schedule.days[3].status, 'available');
  assert.equal(schedule.days[0].items[0].return_distance_label, 'Quay đầu: 44.0 km');
});

test('vehicle schedule UI is located inside the vehicle record and old dispatch timetable is removed', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');
  assert.match(html, /id="vehicle-form-tab-schedule"/);
  assert.match(html, /id="vehicle-schedule-grid"/);
  assert.doesNotMatch(app, /Mở thời khóa biểu tuần/);
});
