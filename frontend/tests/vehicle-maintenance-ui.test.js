const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');

const formStart = html.indexOf('id="fiori-object-page"');
const formEnd = html.indexOf('id="md-tab-vehicles"', formStart);
const vehicleForm = html.slice(formStart, formEnd);

assert.match(vehicleForm, /class="vehicle-profile-hero"/, 'Vehicle image must use a top profile header.');
assert.ok(
  vehicleForm.indexOf('id="fiori-veh-image-preview-wrap"') < vehicleForm.indexOf('id="fiori-veh-id"'),
  'Vehicle image must appear before vehicle identity fields.'
);
assert.match(vehicleForm, /id="vehicle-form-tab-maintenance"/, 'Vehicle form needs a maintenance history tab.');
assert.match(vehicleForm, /id="vehicle-maintenance-list"/, 'Vehicle form needs a real maintenance list.');
assert.match(vehicleForm, /id="vehicle-maintenance-request-form"/, 'Vehicle form needs a repair request form.');
assert.match(vehicleForm, /class="vehicle-dialog-shell"/, 'Vehicle dialog needs one stable outer frame.');
assert.match(html, /\.vehicle-dialog-shell\s*\{[^}]*height:\s*min\(/s, 'Vehicle dialog height must be fixed relative to the viewport.');
assert.match(html, /\.vehicle-dialog-shell\s*\{[^}]*grid-template-rows:\s*auto\s+minmax\(0,1fr\)\s+auto/s, 'Only the vehicle dialog body may resize and scroll.');
assert.match(html, /\.vehicle-form-scroll\s*\{[^}]*scrollbar-gutter:\s*stable/s, 'Vehicle dialog must reserve scrollbar space to prevent horizontal jumping.');
assert.match(vehicleForm, /id="fiori-veh-status-text"/, 'Operational status must be read-only.');
assert.doesNotMatch(vehicleForm, /<select[^>]+id="fiori-veh-status"/, 'Operational status must not be manually selectable.');
assert.doesNotMatch(app, /status:\s*document\.getElementById\(['"]fiori-veh-status['"]\)/, 'Vehicle master save must not submit operational status.');
assert.match(app, /\/api\/vehicles\/\$\{encodeURIComponent\(vehicleId\)\}\/maintenance-requests/, 'Maintenance tab must read the real API.');
assert.match(app, /\/api\/vehicle-maintenance-requests\/\$\{encodeURIComponent\(requestId\)\}/, 'Maintenance actions must use the real request API.');

console.log('VEHICLE_MAINTENANCE_UI_OK');
