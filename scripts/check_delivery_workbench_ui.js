const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'frontend', 'index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'frontend', 'js', 'app.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

function sectionById(source, id) {
  const start = source.indexOf(`<section id="${id}"`);
  if (start === -1) return '';
  const next = source.indexOf('\n        <!--', start + 1);
  return source.slice(start, next === -1 ? source.length : next);
}

const delivery = sectionById(html, 'view-delivery-shipment');
const dispatch = sectionById(html, 'view-dispatch');
const ids = Array.from(html.matchAll(/id="([^"]+)"/g)).map(match => match[1]);
const duplicateIds = Array.from(new Set(ids.filter((id, index) => ids.indexOf(id) !== index)));

assert(delivery, 'delivery shipment section must exist');
assert(dispatch, 'dispatch section must exist');

assert(delivery.includes('id="delivery-cockpit-hero"'), 'delivery should use the modern cockpit hero header');
assert(delivery.includes('id="delivery-status-strip"'), 'delivery KPI area should be a compact status strip');
assert(delivery.includes('delivery-empty-state'), 'delivery should use compact empty states instead of large blank panels');
assert(delivery.includes('Chuyến/DO đang vận chuyển'), 'delivery should focus on active shipment/DO cockpit');
assert(delivery.includes('POD / Chứng từ'), 'delivery should explain POD lives inside DO detail');
assert(delivery.includes('id="trip-return-guidance-toggle"'), 'delivery guidance should be collapsed behind a compact note button');
assert(delivery.includes('onclick="openTripReturnGuidanceModal()"'), 'delivery guidance button should open a modal');
assert(delivery.includes('id="trip-return-guidance-modal"'), 'delivery guidance should render in a modal form');
assert(delivery.includes('id="trip-return-guidance-list"'), 'delivery guidance should still keep a note list container');
assert(!delivery.includes('DO chờ xếp chuyến'), 'delivery must not duplicate the planning DO queue');
assert(!delivery.includes('Kho & POD'), 'POD must not be a standalone delivery tab');
assert(!delivery.includes('id="delivery-panel-board"'), 'delivery should not keep planning board panel');
assert(!delivery.includes('id="delivery-panel-warehouse"'), 'delivery should not keep warehouse/POD panel');
assert(!delivery.includes('id="delivery-running-tabs"'), 'delivery should not nest running sub-tabs');
assert(!delivery.includes('id="delivery-running-panel-calendar"'), 'dispatch calendar must not live inside delivery');
assert(!delivery.includes('id="delivery-running-panel-alerts"'), 'operations alerts must not live inside delivery');

assert(dispatch.includes('id="dispatch-calendar-panel"'), 'dispatch should own calendar panel');
assert(dispatch.includes('id="dispatch-capacity-board"'), 'dispatch should own capacity board');
assert(dispatch.includes('id="dispatch-calendar-conflicts"'), 'dispatch should own operations alerts');
assert(!html.includes('id="ops-planning-tab-trip"'), 'planning should not keep the duplicate Trip tab');
assert(!html.includes('id="ops-planning-folder-trip"'), 'planning should not keep the duplicate Trip panel');

assert(!delivery.includes('delivery-shipment-flow-tabs'), 'old four-card flow tab bar should be removed');
assert(!delivery.includes('delivery-flow-panel-do'), 'old DO-only panel should be removed');
assert(!delivery.includes('delivery-flow-panel-trip'), 'old Trip-only panel should be removed');
assert(!delivery.includes('delivery-flow-panel-dispatch'), 'old Dispatch-only panel should be removed');
assert(!delivery.includes('delivery-flow-panel-warehouse'), 'old Warehouse-only panel should be removed');
assert(!delivery.includes('delivery-do-context-panel'), 'large static instruction panel should be removed');

const createTripCalls = (delivery.match(/openTripReturnAction\('create-trip'\)/g) || []).length;
assert(createTripCalls === 1, `delivery should expose exactly one create Trip action, found ${createTripCalls}`);

assert(js.includes('function switchDeliveryWorkbenchView'), 'JS should define switchDeliveryWorkbenchView');
assert(js.includes('window.switchDeliveryShipmentFlowTab = switchDeliveryWorkbenchView'), 'old delivery switch function should alias to the simplified workbench');
assert(js.includes('function openTripReturnGuidanceModal'), 'JS should open delivery guidance as a modal');
assert(js.includes('window.openTripReturnGuidanceModal = openTripReturnGuidanceModal'), 'guidance modal opener should be exported for inline button');
assert(!js.includes('function toggleTripReturnGuidance'), 'guidance should not use inline expand/collapse in the page body');
assert(js.includes('document.body.appendChild(modal)'), 'Trip action modal should be moved out of hidden view sections before opening');
assert(js.includes("switchView('dispatch')"), 'delivery should navigate to dispatch when scheduling is needed');
assert(!js.includes("tabsId: 'delivery-shipment-folder-tabs'"), 'enterprise module auto-tabs should not wrap delivery-shipment again');
assert(duplicateIds.length === 0, `HTML should not contain duplicate ids: ${duplicateIds.join(', ')}`);

[
  'trip-return-kpis',
  'trip-return-queue',
  'trip-return-detail',
  'dispatch-calendar-panel',
  'dispatch-calendar-kpis',
  'dispatch-calendar-lanes',
  'fiori-shipment-tbody'
].forEach(id => assert(ids.includes(id), `required render target ${id} should exist`));

if (!process.exitCode) {
  console.log('DELIVERY_WORKBENCH_UI_OK');
}
