const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const cockpit = require(path.join(frontendRoot, 'js', 'tms-cockpit-utils.js'));
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

function idCount(source, id) {
  const escapedId = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return (source.match(new RegExp(`\\bid=["']${escapedId}["']`, 'g')) || []).length;
}

function sourceBlock(pattern, message) {
  const match = appSource.match(pattern);
  assert.ok(match, message);
  return match[0];
}

function interactiveOpening(source, activationPattern) {
  return source.match(new RegExp(
    `<button\\b(?=[^>]*\\btype=["']button["'])(?=[^>]*(?:${activationPattern}))[^>]*>`,
    'i'
  ));
}

[
  'dispatch-workbench',
  'dispatch-queue',
  'dispatch-timeline',
  'dispatch-detail',
  // Cot thu ba. Truoc day khoi canh bao nam trong ngan keo 'Cong cu' va phai
  // bam moi mo; ngan keo do da bo vi no chi co dung mot muc.
  'dispatch-exceptions'
].forEach((id) => check(`unique #${id}`, () => {
  assert.strictEqual(idCount(html, id), 1, `Expected exactly one #${id}`);
}));

[
  'dispatch-calendar-date',
  'dispatch-view-day',
  'dispatch-view-week'
].forEach((id) => check(`calendar control #${id}`, () => {
  assert.strictEqual(idCount(html, id), 1, `Expected exactly one #${id}`);
}));

check('dispatch calendar uses the selected date instead of system today', () => {
  const render = sourceBlock(
    /function\s+renderDispatchCalendar\s*\(\)\s*\{[\s\S]*?\n\}/,
    'Missing renderDispatchCalendar().'
  );
  assert.match(render, /dispatchCalendarDate/, 'Calendar render must use the selected planning date.');
  assert.doesNotMatch(render, /buildDispatchCalendar\([^\n]*new Date\(\)/, 'Calendar must not be fixed to today.');
});

[
  'dispatch-work-state-tabs',
  'dispatch-state-pending',
  'dispatch-state-scheduled',
  'dispatch-state-conflict',
  'dispatch-analysis-tabs',
  'dispatch-analysis-schedule',
  'dispatch-analysis-capacity',
  'dispatch-analysis-alerts',
  'dispatch-analysis-week'
].forEach((id) => check(`legacy #${id} removed`, () => {
  assert.strictEqual(idCount(html, id), 0, `Legacy tab contract #${id} must be removed`);
}));

check('dispatch workbench is not wrapped by dead enterprise tabs', () => {
  assert.doesNotMatch(
    appSource,
    /tabsId:\s*['"]dispatch-folder-tabs['"]/,
    'Dispatch must render the real workbench directly, not a wrapper tab with missing panels.'
  );
  assert.doesNotMatch(
    appSource,
    /#dispatch-orders-workspace|#dispatch-resource-workspace/,
    'Dispatch wrapper must not point to non-existent panel selectors.'
  );
});

check('Trip creation uses backend route builder from DO', () => {
  assert.match(
    appSource,
    /\/api\/tms\/trips\/from-delivery-orders/,
    'Create Trip must call the backend command that derives legs from DO route Master Data.'
  );
});

check('dispatch queue uses canonical pending status from backend', () => {
  assert.match(appSource, /DISPATCH_PENDING_CANONICAL_STATUSES/, 'Dispatch pending canonical status set is required.');
  assert.match(appSource, /DISPATCH_DONE_CANONICAL_STATUSES/, 'Dispatch done canonical status guard is required.');
});

check('queue rows use semantic buttons', () => {
  const opening = interactiveOpening(
    appSource,
    'onclick=["\x27]selectDispatchDO\\(|data-dispatch-(?:queue|do)'
  );
  assert.ok(opening, 'Dispatch queue rows must render as <button type="button"> controls.');
});

check('dispatch visual refresh classes are wired', () => {
  [
    ['DO cards', /dispatch-do-card--accent/],
    ['DO content button', /dispatch-do-select/],
    ['eye action', /dispatch-eye-action/],
    ['alert rows', /dispatch-alert-row/],
    // Chin dong truoc day o cho nay dò tên lớp của `renderDispatchWeekPlanner`
    // — mot trinh ve MA TRAN xe x ngay, mot dong cho MOI xe. Phep do bang
    // chinh khuon dong cua no: 500 xe -> 1,06 MB HTML va 3.500 nut bam trong
    // MOT lan `innerHTML`. Ba khoi chua cua no chua bao gio duoc dung trong
    // index.html, nen no chua tung chay; va phep do o day chi kiem xem chuoi
    // ten lop CO XUAT HIEN o dau do trong `html + appSource` hay khong, chu
    // khong kiem rang trinh ve do chay.
    //
    // Ban dang chay la `renderDispatchWeekTimetable`, va no lam khac han:
    // mot bang nang luc theo ngay roi moi lay danh sach xe cua ngay duoc
    // chon. Neo vao dung nhung lop cua ban do.
    ['week day summary band', /dispatch-week-day-summaries/],
    ['week day summary card', /dispatch-week-day-summary/],
    ['week day order count', /dispatch-day-order-count/]
  ].forEach(([label, pattern]) => {
    assert.match(`${html}\n${appSource}`, pattern, `${label} must use the refreshed dispatch styling classes.`);
  });
});

check('dispatch presents a four-step Trip-gated assignment workflow', () => {
  [
    'dispatch-step-do',
    'dispatch-step-trip',
    'dispatch-step-schedule',
    'dispatch-step-resources'
  ].forEach((id) => assert.strictEqual(idCount(html, id), 1, `Expected exactly one #${id}`));
  assert.match(html, /Chọn DO/);
  assert.match(html, /Xếp lịch xe/);
  assert.match(html, /Nhân sự &amp; xuất bến/);
});

check('dispatch workflow steps are compact modal launchers', () => {
  [
    ['dispatch-step-do', 'do'],
    ['dispatch-step-trip', 'trip'],
    ['dispatch-step-schedule', 'schedule'],
    ['dispatch-step-resources', 'resources']
  ].forEach(([id, step]) => {
    assert.match(
      html,
      new RegExp(`<button\\b(?=[^>]*\\bid=["']${id}["'])(?=[^>]*\\btype=["']button["'])(?=[^>]*openDispatchStepModal\\(["']${step}["']\\))[^>]*>`, 'i'),
      `#${id} must be a semantic button that opens the ${step} form.`
    );
  });
  assert.match(html, /dispatch-workflow-step-icon/, 'Compact workflow buttons need a stable icon slot.');
});

check('dispatch uses one reusable step modal for live forms', () => {
  [
    'dispatch-step-modal',
    'dispatch-step-modal-title',
    'dispatch-step-modal-description',
    'dispatch-step-modal-body'
  ].forEach((id) => assert.strictEqual(idCount(html, id), 1, `Expected exactly one #${id}`));
  assert.match(appSource, /window\.openDispatchStepModal\s*=\s*function/, 'Missing modal open behavior.');
  assert.match(appSource, /window\.closeDispatchStepModal\s*=\s*function/, 'Missing modal close behavior.');
  assert.match(appSource, /appendChild\s*\(\s*target\s*\)/, 'The modal must move the live form instead of cloning duplicate IDs.');
});

check('dispatch modal respects the assignment order', () => {
  const openModal = sourceBlock(
    /window\.openDispatchStepModal\s*=\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
    'Missing openDispatchStepModal().'
  );
  assert.match(openModal, /step\s*===\s*['"]trip['"][\s\S]*?!hasDO/, 'Trip form must require a selected DO.');
  assert.match(openModal, /step\s*===\s*['"]schedule['"][\s\S]*?!hasPlannedTrip/, 'Schedule form must require a planned Trip.');
  assert.match(openModal, /step\s*===\s*['"]resources['"][\s\S]*?!hasVehicle/, 'Resource form must require a selected vehicle.');
});

check('dispatch filters pending DOs by selected pickup date', () => {
  assert.strictEqual(typeof cockpit.filterDispatchOrdersByDate, 'function', 'Missing date-first DO filter helper.');
  const result = cockpit.filterDispatchOrdersByDate([
    { id: 'DO-24', pickup_window_start: '2026-08-24T08:00:00+07:00' },
    { id: 'DO-25', pickup_window_start: '2026-08-25T08:00:00+07:00' },
    { id: 'DO-NO-DATE' }
  ], '2026-08-24');
  assert.deepStrictEqual(result.orders.map((order) => order.id), ['DO-24']);
  assert.deepStrictEqual(result.undated.map((order) => order.id), ['DO-NO-DATE']);
});

check('dispatch resolves Trip gate states before vehicle selection', () => {
  assert.strictEqual(typeof cockpit.resolveDispatchTripGate, 'function', 'Missing Trip gate helper.');
  const trips = [
    { id: 'TRIP-DRAFT', status: 'draft', delivery_order_ids: ['DO-DRAFT'] },
    { id: 'TRIP-PLANNED', status: 'planned', delivery_order_ids: ['DO-PLANNED'] },
    { id: 'TRIP-LIVE', status: 'in_transit', delivery_order_ids: ['DO-LIVE'] }
  ];
  assert.strictEqual(cockpit.resolveDispatchTripGate('DO-MISSING', trips).state, 'missing');
  assert.strictEqual(cockpit.resolveDispatchTripGate('DO-DRAFT', trips).state, 'draft');
  assert.strictEqual(cockpit.resolveDispatchTripGate('DO-PLANNED', trips).state, 'ready');
  assert.strictEqual(cockpit.resolveDispatchTripGate('DO-LIVE', trips).state, 'unavailable');
});

check('dispatch never falls back to direct DO dispatch without a planned Trip', () => {
  const submit = sourceBlock(
    /window\.submitDispatch\s*=\s*async\s+function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
    'Missing submitDispatch().'
  );
  assert.doesNotMatch(submit, /\/api\/delivery-orders\/\$\{doId\}\/dispatch/, 'Dispatch must not bypass Trip planning.');
  assert.match(submit, /resolveDispatchTripGate/, 'Dispatch submission must enforce the Trip gate.');
});

check('dispatch DO cards expose operational context and Trip status', () => {
  const render = sourceBlock(
    /function\s+renderDispatchDOs\s*\([^)]*\)\s*\{[\s\S]*?\n\}/,
    'Missing renderDispatchDOs().'
  );
  ['customer', 'route', 'cargo', 'weight', 'pallet', 'pickup', 'delivery', 'trip'].forEach((field) => {
    assert.match(render, new RegExp(`dispatch-do-${field}`), `DO card must expose ${field}.`);
  });
});

check('weekly timetable is the default dispatch planning surface', () => {
  assert.match(appSource, /let\s+dispatchCalendarView\s*=\s*['"]week['"]/);
  assert.match(`${html}\n${appSource}`, /dispatch-week-timetable/);
  assert.match(`${html}\n${appSource}`, /dispatch-week-time-block/);
  assert.match(appSource, /item\.start_label/);
  assert.match(appSource, /item\.end_label/);
});

check('a free weekly cell assigns both planning date and vehicle', () => {
  const selection = sourceBlock(
    /window\.selectDispatchWeekSlot\s*=\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
    'Missing selectDispatchWeekSlot().'
  );
  assert.match(selection, /dispatchCalendarDate\s*=/, 'Weekly slot selection must set the selected planning date.');
  assert.match(selection, /selectDispatchVehicleLane\s*\(/, 'Weekly slot selection must assign the selected vehicle.');
});

check('dispatch detail panel uses compact action-first layout', () => {
  [
    ['detail card', /dispatch-detail-card/],
    ['detail hero', /dispatch-detail-hero/],
    ['detail facts', /dispatch-detail-facts/],
    ['quick action rail', /dispatch-quick-actions/],
    ['assignment card', /dispatch-assignment-card/],
    ['assignment grid', /dispatch-assignment-grid/],
    ['full width submit', /dispatch-submit-full/],
    ['status note', /dispatch-status-note/]
  ].forEach(([label, pattern]) => {
    assert.match(`${html}\n${appSource}`, pattern, `${label} must be present in the compact dispatch detail layout.`);
  });
  assert.doesNotMatch(
    appSource,
    /dispatch-calendar-detail-actions[\s\S]{0,2200}fiori-btn fiori-btn-secondary/,
    'Suggested actions must not render as stacked secondary form buttons in the narrow detail panel.'
  );
});

check('capacity tool drawer entry is removed', () => {
  assert.strictEqual(idCount(html, 'dispatch-tool-capacity'), 0, 'Capacity menu button must be removed.');
  assert.strictEqual(idCount(html, 'dispatch-tool-pane-capacity'), 0, 'Capacity drawer pane must be removed.');
  assert.doesNotMatch(appSource, /Năng lực điều phối/, 'Capacity drawer title must be removed.');
  assert.doesNotMatch(appSource, /allowed\s*=\s*\[[^\]]*['"]capacity['"]/, 'Capacity must not be an openDispatchTool option.');
  assert.doesNotMatch(appSource, /^\s*renderDispatchCapacityBoard\s*\(\s*\);/m, 'Calendar render must not populate the removed capacity drawer.');
});

check('timeline bars use semantic labelled buttons', () => {
  const opening = interactiveOpening(
    appSource,
    'onclick=["\x27]selectDispatchCalendarItem\\(|data-dispatch-(?:timeline|calendar)'
  );
  assert.ok(opening, 'Timeline bars must render as <button type="button"> controls.');
  const button = opening[0];
  assert.match(button, /aria-label=["']/, 'Timeline buttons need an aria-label.');
  [
    ['Trip code', /\$\{item\.id\}/],
    ['vehicle', /\$\{item\.vehicle_id\}/],
    ['driver', /\$\{item\.driver_id\}/],
    ['start time', /\$\{item\.start_label\}/],
    ['end time', /\$\{item\.end_label\}/],
    ['status', /\$\{item\.status_label\}/]
  ].forEach(([label, pattern]) => {
    assert.match(button, pattern, `Timeline aria-label must include ${label}.`);
  });
});

check('timeline div onclick removed', () => {
  assert.doesNotMatch(
    appSource,
    /<div\b[^>]*onclick=["']selectDispatchCalendarItem\(/i,
    'Timeline items must not use div onclick.'
  );
});

check('DO selection updates the unified selection', () => {
  const selectDO = sourceBlock(
    /window\.selectDispatchDO\s*=\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
    'Missing selectDispatchDO().'
  );
  assert.match(
    selectDO,
    /selectedDispatchCalendarOrderId\s*=\s*id\s*\|\|\s*["']{2}/,
    'selectDispatchDO() must update selectedDispatchCalendarOrderId.'
  );
  assert.match(selectDO, /renderDispatchCalendar\s*\(/, 'DO selection must rerender the workbench.');
});

check('calendar selection updates the unified selection', () => {
  const selectCalendarItem = sourceBlock(
    /function\s+selectDispatchCalendarItem\s*\([^)]*\)\s*\{[\s\S]*?\n\}/,
    'Missing selectDispatchCalendarItem().'
  );
  assert.match(
    selectCalendarItem,
    /selectedDispatchCalendarOrderId\s*=\s*orderId\s*\|\|\s*["']{2}/,
    'selectDispatchCalendarItem() must update selectedDispatchCalendarOrderId.'
  );
});

check('render has no implicit first selection', () => {
  assert.doesNotMatch(
    appSource,
    /selectedDispatchCalendarOrderId\s*\|\|\s*\(\s*calendar\.lanes\[0\]/,
    'renderDispatchCalendar() must not fall back to the first timeline item.'
  );
  assert.doesNotMatch(
    appSource,
    /(?:firstOrder|firstItem)\s*=\s*selectedDispatchCalendarOrderId\s*\|\|/,
    'The detail selection must remain empty until the user selects an item.'
  );
});

const fixtureDay = new Date(2026, 7, 20, 12, 0, 0);
const fixtureState = {
  delivery_orders: [
    {
      id: 'DO-MISSING-VEHICLE',
      status: 'Ready for Dispatch',
      driver_id: 'DRV-QUEUE',
      pickup_date: '2026-08-20T07:30:00',
      delivery_date: '2026-08-20T09:30:00',
      route_id: 'ROUTE-QUEUE',
      weight_kg: 400
    },
    { id: 'DO-VALID', status: 'Planned', route_id: 'ROUTE-VALID', weight_kg: 500 },
    { id: 'DO-MULTI-1', status: 'Planned', route_id: 'ROUTE-MULTI', weight_kg: 1000 },
    { id: 'DO-MULTI-2', status: 'Planned', route_id: 'ROUTE-MULTI', weight_kg: 650 }
  ],
  transport_trips: [
    {
      id: 'TRIP-VALID',
      status: 'planned',
      vehicle_id: 'VEH-01',
      driver_id: 'DRV-01',
      planned_departure_at: '2026-08-20T08:00:00',
      planned_return_at: '2026-08-20T10:00:00',
      delivery_order_ids: ['DO-VALID'],
      route_id: 'ROUTE-VALID'
    },
    {
      id: 'TRIP-MULTI',
      status: 'dispatched',
      vehicle_id: 'VEH-02',
      driver_id: 'DRV-02',
      planned_departure_at: '2026-08-20T11:00:00',
      planned_return_at: '2026-08-20T15:00:00',
      delivery_order_ids: ['DO-MULTI-1', 'DO-MULTI-2'],
      route_id: 'ROUTE-MULTI'
    }
  ],
  vehicles: [
    { id: 'VEH-01', status: 'available' },
    { id: 'VEH-02', status: 'available' },
    { id: 'VEH-IDLE', status: 'available' }
  ],
  drivers: [
    { id: 'DRV-01', status: 'available' },
    { id: 'DRV-02', status: 'available' },
    { id: 'DRV-QUEUE', status: 'available' }
  ],
  routes: [
    { id: 'ROUTE-VALID', name: 'Valid route' },
    { id: 'ROUTE-MULTI', name: 'Multi-stop route' },
    { id: 'ROUTE-QUEUE', name: 'Queue route' }
  ]
};

check('calendar includes idle vehicles as assignment lanes', () => {
  const calendar = cockpit.buildDispatchCalendar(fixtureState, fixtureDay, {});
  const idleLane = calendar.lanes.find((lane) => lane.resource_id === 'VEH-IDLE');
  assert.ok(idleLane, 'Every available vehicle needs a lane even when it has no scheduled Trip.');
  assert.deepStrictEqual(idleLane.items, []);
  assert.strictEqual(idleLane.is_available, true);
});

check('pending DO cards support desktop drag and touch selection', () => {
  assert.match(appSource, /draggable=["']true["']/, 'Pending DO cards must be draggable.');
  assert.match(appSource, /onDispatchDODragStart\(/, 'DO drag must publish the selected DO.');
  assert.match(appSource, /onDispatchLaneDrop\(/, 'Vehicle lanes must accept a dropped DO.');
  assert.match(appSource, /selectDispatchVehicleLane\(/, 'Touch users must be able to tap a vehicle lane.');
});

check('dispatch form submits canonical crew fields', () => {
  assert.match(appSource, /co_driver_id:\s*coDrvId/, 'Dispatch payload must use co_driver_id.');
  assert.doesNotMatch(appSource, /co_driver:\s*coDrvId/, 'Legacy co_driver payload key must be removed.');
});

check('missing-vehicle DO enters the queue', () => {
  const calendar = cockpit.buildDispatchCalendar(fixtureState, fixtureDay, {});
  const queued = calendar.unscheduled.find((item) => item.id === 'DO-MISSING-VEHICLE');
  assert.ok(queued, 'A DO with a driver but no vehicle must remain in the dispatch queue.');
  assert.match(queued.reason, /vehicle|xe/i, 'The queue reason must identify the missing vehicle.');
});

check('valid Trip enters a vehicle lane', () => {
  const calendar = cockpit.buildDispatchCalendar(fixtureState, fixtureDay, {});
  const trip = calendar.lanes.flatMap((lane) => lane.items).find((item) => item.id === 'TRIP-VALID');
  assert.ok(trip, 'A valid Trip must appear in a timeline lane.');
  assert.strictEqual(trip.kind, 'trip');
  assert.strictEqual(trip.vehicle_id, 'VEH-01');
  assert.strictEqual(trip.driver_id, 'DRV-01');
});

check('weekly planner marks dispatched vehicle days as busy', () => {
  const week = cockpit.buildDispatchWeekPlanner(fixtureState, fixtureDay);
  const vehicle = week.vehicle_rows.find((row) => row.vehicle_id === 'VEH-02');
  assert.ok(vehicle, 'Dispatched vehicle must appear in the weekly planner.');
  const tripDay = vehicle.days.find((day) => day.iso_date === '2026-08-20');
  const followingDay = vehicle.days.find((day) => day.iso_date === '2026-08-21');
  assert.strictEqual(tripDay.status, 'busy', 'The Trip day must be marked busy.');
  assert.deepStrictEqual(tripDay.trip_ids, ['TRIP-MULTI']);
  assert.strictEqual(followingDay.status, 'available', 'The following empty day must remain available.');
});

check('weekly planner always runs from Monday through Sunday', () => {
  const week = cockpit.buildDispatchWeekPlanner(fixtureState, fixtureDay);
  assert.strictEqual(week.days[0].iso_date, '2026-08-17');
  assert.strictEqual(week.days[6].iso_date, '2026-08-23');
});

check('weekly planner reserves the configured maintenance day', () => {
  const week = cockpit.buildDispatchWeekPlanner({
    ...fixtureState,
    vehicles: [...fixtureState.vehicles, { id: 'VEH-MAINT', status: 'available', maintenance_date: '2026-08-21' }]
  }, fixtureDay);
  const vehicle = week.vehicle_rows.find((row) => row.vehicle_id === 'VEH-MAINT');
  const maintenanceDay = vehicle.days.find((day) => day.iso_date === '2026-08-21');
  assert.strictEqual(maintenanceDay.status, 'maintenance');
  assert.match(maintenanceDay.maintenance_label, /Bảo dưỡng/);
});

check('weekly planner keeps row label to vehicle id only', () => {
  const week = cockpit.buildDispatchWeekPlanner({
    ...fixtureState,
    vehicles: [{ id: 'VEH-BRAND', brand: 'Hyundai', status: 'available' }]
  }, fixtureDay);
  const vehicle = week.vehicle_rows.find((row) => row.vehicle_id === 'VEH-BRAND');
  assert.ok(vehicle, 'Vehicle with brand metadata must appear.');
  assert.strictEqual(vehicle.label, 'VEH-BRAND', 'Row label must not append brand/model metadata.');
  assert.strictEqual(vehicle.brand_label, 'Hyundai');
});

check('weekly planner groups available vehicles by day', () => {
  const week = cockpit.buildDispatchWeekPlanner(fixtureState, fixtureDay);
  const tripDay = week.available_by_day.find((day) => day.key === week.days[3].key);
  const nextDay = week.available_by_day.find((day) => day.key === week.days[4].key);
  assert.ok(tripDay, 'Trip day availability group is required.');
  assert.ok(nextDay, 'Following day availability group is required.');
  assert.deepStrictEqual(tripDay.vehicles.map((vehicle) => vehicle.vehicle_id), ['VEH-IDLE']);
  assert.deepStrictEqual(nextDay.vehicles.map((vehicle) => vehicle.vehicle_id), ['VEH-01', 'VEH-02', 'VEH-IDLE']);
});

check('weekly planner locks every day touched by a multi-day return window', () => {
  const state = {
    ...fixtureState,
    transport_trips: [{
      ...fixtureState.transport_trips[0],
      id: 'TRIP-LONG-RETURN',
      vehicle_id: 'VEH-01',
      planned_departure_at: '2026-08-20T08:00:00',
      planned_return_at: '2026-08-23T09:30:00'
    }]
  };
  const week = cockpit.buildDispatchWeekPlanner(state, fixtureDay);
  const vehicle = week.vehicle_rows.find((row) => row.vehicle_id === 'VEH-01');
  ['2026-08-20', '2026-08-21', '2026-08-22', '2026-08-23'].forEach((date) => {
    assert.strictEqual(vehicle.days.find((day) => day.iso_date === date).status, 'busy');
  });
});

check('day fleet view summarizes, filters and paginates large vehicle sets', () => {
  const vehicles = Array.from({ length: 125 }, (_, index) => ({
    id: `VEH-${String(index + 1).padStart(3, '0')}`,
    status: 'available'
  }));
  const week = cockpit.buildDispatchWeekPlanner({ ...fixtureState, transport_trips: [], vehicles }, fixtureDay);
  const fleet = cockpit.buildDispatchDayFleet(week, '2026-08-17', { page: 2, page_size: 50 });
  assert.strictEqual(fleet.summary.total, 125);
  assert.strictEqual(fleet.summary.available, 125);
  assert.strictEqual(fleet.rows.length, 50);
  assert.strictEqual(fleet.page, 2);
  assert.strictEqual(fleet.total_pages, 3);
  assert.strictEqual(fleet.rows[0].vehicle_id, 'VEH-051');
  assert.strictEqual(fleet.rows[0].can_assign, true);
});

check('day fleet view explains why a vehicle cannot be assigned', () => {
  const week = cockpit.buildDispatchWeekPlanner(fixtureState, fixtureDay);
  const fleet = cockpit.buildDispatchDayFleet(week, '2026-08-20', { status: 'busy' });
  assert.ok(fleet.rows.length > 0);
  assert.ok(fleet.rows.every((row) => row.can_assign === false));
  assert.match(fleet.rows[0].availability_label, /Trip|bận/i);
});

check('weekly UI opens a day workbench and has no vehicle picker on the main calendar', () => {
  assert.match(appSource, /selectDispatchFleetDay/);
  assert.match(appSource, /dispatch-week-day-summary/);
  assert.match(appSource, /openDispatchDayWorkbench/);
  assert.match(appSource, /dispatchDayOrderSummary/);
  assert.doesNotMatch(appSource, /dispatch-fleet-picker-launcher/);
  assert.doesNotMatch(appSource, /openDispatchFleetPicker/);
  assert.doesNotMatch(appSource, /<section class="dispatch-day-fleet-list"/);
  assert.match(appSource, /buildDispatchDayFleet/);
});

check('day workbench provides a two-column DO and workflow form', () => {
  assert.match(html, /id="dispatch-day-workbench-modal"/);
  assert.match(html, /id="dispatch-day-workbench-body"/);
  assert.match(appSource, /dispatchDayWorkbenchState/);
  assert.match(appSource, /closeDispatchDayWorkbench/);
});

check('multi-DO Trip detail includes linked DOs and payload', () => {
  const detail = cockpit.buildDispatchCalendarDetail(fixtureState, 'TRIP-MULTI', fixtureDay);
  assert.strictEqual(detail.kind, 'trip', 'Trip detail must identify its kind.');
  assert.deepStrictEqual(
    detail.linked_delivery_orders.map((order) => order.id),
    ['DO-MULTI-1', 'DO-MULTI-2'],
    'Trip detail must expose its linked DOs in Trip order.'
  );
  assert.strictEqual(detail.total_payload_kg, 1650, 'Trip detail must total linked DO payload.');
});

check('empty selection produces empty detail', () => {
  const detail = cockpit.buildDispatchCalendarDetail(fixtureState, '', fixtureDay);
  assert.strictEqual(detail.kind, null);
  assert.strictEqual(detail.order, null);
  assert.deepStrictEqual(detail.linked_delivery_orders, []);
  assert.deepStrictEqual(detail.alerts, []);
  assert.deepStrictEqual(detail.suggested_actions, []);
});

function createDomHarness() {
  const listeners = new Map();
  const document = {
    activeElement: null,
    nodes: new Map(),
    getElementById(id) {
      return this.nodes.get(id) || null;
    },
    querySelectorAll(selector) {
      return Array.from(this.nodes.values()).filter((element) => element.matches(selector));
    }
  };

  function node(id, attributes = {}) {
    const element = {
      id,
      hidden: Boolean(attributes.hidden),
      attributes: { ...attributes },
      addEventListener(type, handler) {
        const key = `${id}:${type}`;
        listeners.set(key, [...(listeners.get(key) || []), handler]);
      },
      dispatchKey(key, options = {}) {
        const event = {
          key,
          shiftKey: Boolean(options.shiftKey),
          target: element,
          defaultPrevented: false,
          preventDefault() { this.defaultPrevented = true; }
        };
        (listeners.get(`${id}:keydown`) || []).forEach((handler) => handler(event));
        return event;
      },
      focus() {
        document.activeElement = element;
      },
      getAttribute(name) {
        return this.attributes[name] == null ? null : String(this.attributes[name]);
      },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      matches(selector) {
        if (selector === '[role="menuitem"]') return this.getAttribute('role') === 'menuitem';
        if (selector === '[data-drawer-focusable]') {
          return this.getAttribute('data-drawer-focusable') === 'true';
        }
        return false;
      }
    };
    document.nodes.set(id, element);
    return element;
  }
  return { document, node };
}

function installHarnessInteractions(harness) {
  const { document } = harness;
  const drawer = document.getElementById('dispatch-detail');
  const drawerItems = document.querySelectorAll('[data-drawer-focusable]');
  let drawerReturnFocus = null;

  drawer.openFrom = (trigger) => {
    drawerReturnFocus = trigger;
    drawer.hidden = false;
    drawerItems[0].focus();
  };
  drawer.close = () => {
    drawer.hidden = true;
    if (drawerReturnFocus) drawerReturnFocus.focus();
  };
  drawer.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') return drawer.close();
    if (event.key !== 'Tab') return;
    const first = drawerItems[0];
    const last = drawerItems[drawerItems.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
}

// BO bai kiem ban phim cua bang chon "Cong cu": bang chon do khong con.
// Bai kiem con lai ben duoi — bay cua khung chi tiet — thi giu, vi khung chi
// tiet van la mot hop thoai that.

check('test-local drawer focus trap and return contract', () => {
  const harness = createDomHarness();
  const trigger = harness.node('dispatch-row-trigger');
  const drawer = harness.node('dispatch-detail', {
    hidden: true,
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'dispatch-detail-title'
  });
  const close = harness.node('dispatch-detail-close', { 'data-drawer-focusable': 'true' });
  const action = harness.node('dispatch-detail-action', { 'data-drawer-focusable': 'true' });
  installHarnessInteractions(harness);

  drawer.openFrom(trigger);
  assert.strictEqual(harness.document.activeElement, close);
  action.focus();
  drawer.dispatchKey('Tab');
  assert.strictEqual(harness.document.activeElement, close);
  close.focus();
  drawer.dispatchKey('Tab', { shiftKey: true });
  assert.strictEqual(harness.document.activeElement, action);
  drawer.dispatchKey('Escape');
  assert.strictEqual(drawer.hidden, true);
  assert.strictEqual(harness.document.activeElement, trigger);
});

check('production drawer exposes the harness contract', () => {
  const combinedSource = `${html}\n${appSource}`;
  [
    // ArrowDown / ArrowUp da bo cung voi bang chon "Cong cu": bang chon do chi co
    // mot muc, va khoi canh bao nay la cot thu ba thuong truc cua ban dieu phoi.
    // Mot bang chon mot muc thi khong co gi de di chuyen bang mui len xuong.
    [/Escape/, 'Drawer behavior must handle Escape.'],
    [/\bTab\b/, 'Drawer behavior must trap Tab navigation.'],
    [/\.focus\s*\(/, 'Tools and drawer behavior must transfer and return focus.'],
    [/role=["']dialog["']/i, 'The detail drawer needs dialog semantics.'],
    [/aria-modal=["']true["']/i, 'The detail drawer needs aria-modal="true".'],
    [/aria-labelledby=["']dispatch-detail-title["']/i, 'The detail drawer needs an accessible title.']
  ].forEach(([pattern, message]) => assert.ok(pattern.test(combinedSource), message));
});

check('return trip form exposes empty, backhaul, and returned-goods purposes', () => {
  const combinedSource = `${html}\n${appSource}`;
  assert.match(combinedSource, /id=["']trip-return-purpose["']/);
  assert.match(combinedSource, /value=["']empty_return["']/);
  assert.match(combinedSource, /value=["']backhaul["']/);
  assert.match(combinedSource, /value=["']returned_goods["']/);
  assert.match(appSource, /function\s+syncTripReturnPurpose/);
  assert.match(appSource, /returned_goods[\s\S]*backhaul/);
  assert.match(appSource, /BACKHAUL_DO_REQUIRED|phải chọn DO/i);
});

check('empty detail hides actions and alerts', () => {
  assert.match(
    appSource,
    /if\s*\(\s*!detail(?:\?\.)?\.(?:order|kind)\s*\)[\s\S]*?(?:actionsEl|detailActionsEl)\.hidden\s*=\s*true/,
    'Detail actions must stay hidden when no DO or Trip is selected.'
  );
  assert.match(
    appSource,
    /if\s*\(\s*!detail(?:\?\.)?\.(?:order|kind)\s*\)[\s\S]*?(?:alertsEl|detailAlertsEl)\.hidden\s*=\s*true/,
    'Detail alerts must stay hidden when no DO or Trip is selected.'
  );
});

if (failures.length) {
  throw new Error(`Dispatch workbench contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('DISPATCH_WORKBENCH_UI_OK');
