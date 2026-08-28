const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('GPS live has an explicit in-transit status guard', () => {
  assert.match(appSource, /function\s+isGpsLiveTrackingStatus\s*\(/, 'Missing isGpsLiveTrackingStatus().');
  const guard = appSource.match(/function\s+isGpsLiveTrackingStatus\s*\([^)]*\)\s*\{[\s\S]*?return[\s\S]*?;\s*\n\}/);
  assert.ok(guard, 'Could not read isGpsLiveTrackingStatus() body.');
  assert.match(guard[0], /in_transit/, 'GPS live guard must allow canonical in_transit.');
  assert.match(guard[0], /Đang vận chuyển|dang[_ ]van[_ ]chuyen/, 'GPS live guard must allow Vietnamese in-transit status.');
  assert.doesNotMatch(guard[0], /dispatched|ready_for_dispatch|pending/, 'GPS live guard must not allow waiting/dispatch-only statuses.');
});

check('tracking dropdown only includes in-transit orders', () => {
  const selector = appSource.match(/function\s+populateTrackingDOSelector\s*\([^)]*\)\s*\{[\s\S]*?\n\}/);
  assert.ok(selector, 'Missing populateTrackingDOSelector().');
  assert.match(selector[0], /\.filter\s*\([^)]*isGpsLiveTrackingStatus/, 'Tracking dropdown must filter by the GPS live status guard.');
  assert.doesNotMatch(selector[0], /vehicle_id\s*\|\||status\s*===\s*['"]Dispatched['"]/, 'Tracking dropdown must not treat assigned/dispatched-but-waiting DOs as live.');
});

check('tracking map fallback does not auto-select waiting transport', () => {
  const initMap = appSource.match(/window\.initGPSTrackingMap\s*=\s*async\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/);
  assert.ok(initMap, 'Missing initGPSTrackingMap().');
  assert.match(initMap[0], /liveDOs/, 'Tracking map should use a live-only DO list.');
  assert.doesNotMatch(initMap[0], /allDOs\.find\(d\s*=>\s*d\.vehicle_id/, 'Tracking map must not fall back to any DO just because it has a vehicle.');
});

check('trackDO blocks waiting transport before fetching GPS', () => {
  const track = appSource.match(/window\.trackDO\s*=\s*async\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/);
  assert.ok(track, 'Missing trackDO().');
  assert.match(track[0], /matchedDO\.id[\s\S]*!isGpsLiveTrackingStatus/, 'trackDO must reject known non-live DO statuses.');
  assert.match(track[0], /updateTrackingHeader\s*\(\s*null\s*\)/, 'Rejected tracking must clear the live header.');
});

if (failures.length) {
  throw new Error(`Tracking live contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('TRACKING_LIVE_UI_OK');
