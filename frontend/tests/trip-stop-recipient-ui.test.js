const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('Trip modal captures delivery stop recipient details', () => {
  for (const id of [
    'trip-return-stop-plan',
    'trip-return-stop-name',
    'trip-return-receiver-name',
    'trip-return-receiver-phone',
    'trip-return-delivery-note',
  ]) {
    assert.match(html, new RegExp(`id=["']${id}["']`), `Missing ${id}.`);
  }
  assert.match(html, /Điểm dừng & người nhận/, 'Trip modal must clearly name stop and recipient configuration.');
});

check('Trip preview and submit payload include stop plan', () => {
  assert.match(app, /function\s+tripReturnStopPlan\s*\(/, 'App must collect stop plan from the modal.');
  assert.match(app, /stop_plan:\s*tripReturnStopPlan\(\)/, 'Create Trip payload must send stop_plan.');
  assert.match(app, /receiver_name/, 'Preview/payload must include receiver_name.');
  assert.match(app, /receiver_phone/, 'Preview/payload must include receiver_phone.');
  assert.match(app, /delivery_note/, 'Preview/payload must include delivery_note.');
});

if (failures.length) {
  throw new Error(`Trip stop recipient UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('TRIP_STOP_RECIPIENT_UI_OK');
