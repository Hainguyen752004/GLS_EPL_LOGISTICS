const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');
const cockpit = require('../js/tms-cockpit-utils.js');

assert.ok(html.includes('id="trip-return-status-tabs"'), 'delivery control tower needs status tabs');
assert.ok(html.includes('id="trip-return-detail-tabs"'), 'selected trip needs focused detail tabs');
assert.ok(html.includes('id="trip-return-detail-pane"'), 'selected detail tab needs one stable content pane');
assert.ok(!html.includes('id="trip-return-kpis"'), 'old KPI-card strip should be removed');
assert.ok(html.includes('class="delivery-control-heading"'), 'control tower title needs a distinct structural header');
assert.ok(html.includes('--delivery-border-strong: #aebfd1;'), 'control tower needs a clearly visible outer border token');
assert.ok(html.includes('--delivery-divider: #bdcad8;'), 'control tower needs a stronger section divider token');
assert.ok(html.includes('background: #f1f5f9;'), 'trip queue needs its own contrasting surface');
assert.ok(html.includes('border-right: 2px solid var(--delivery-divider);'), 'queue and detail need a clear desktop divider');
assert.ok(html.includes('background: #dcecff;'), 'selected trip needs a stronger selected surface');
assert.ok(html.includes('box-shadow: inset 0 0 0 1px #9bc5ef;'), 'selected trip needs a visible selection boundary');
assert.ok(html.includes('border: 1px solid var(--delivery-border);'), 'detail content needs a stable section boundary');

assert.ok(app.includes('function setTripReturnStatusTab('), 'status tabs need a controller');
assert.ok(app.includes('function setTripReturnDetailTab('), 'detail tabs need a controller');
assert.ok(app.includes('Chặng đường'));
assert.ok(app.includes('Xe & nhân sự'));
assert.ok(app.includes('POD'));
assert.ok(app.includes('Sự kiện'));
assert.ok(app.includes('Việc cần làm tiếp'));

assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [{ leg_type: 'delivery', status: 'in_transit' }]
}), 'active');
assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [
    { leg_type: 'delivery', status: 'completed' },
    { leg_type: 'empty_return', status: 'planned' }
  ]
}), 'waiting_return');
assert.strictEqual(cockpit.getTripStatusGroup({ status: 'completed', legs: [] }), 'completed');
assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [{ leg_type: 'delivery', status: 'completed' }]
}), 'missing_return');

console.log('DELIVERY_CONTROL_TOWER_UI_OK');
