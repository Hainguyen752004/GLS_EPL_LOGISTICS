const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');

function functionBody(pattern, name) {
  const match = appSource.match(pattern);
  assert.ok(match, `Missing ${name}.`);
  return match[0];
}

const updateSOStatus = functionBody(
  /window\.updateSOStatus\s*=\s*async\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
  'updateSOStatus()'
);

assert.match(
  updateSOStatus,
  /executeWorkflowCommand\s*\(\s*['"]salesOrderConfirm['"]/,
  'SO confirmation must use the shared server-confirmed command flow.'
);
assert.match(updateSOStatus, /if\s*\(\s*!result\.ok\s*\)\s*return/, 'SO confirmation must stop when the API fails.');
assert.doesNotMatch(updateSOStatus, /catch\s*\([^)]*\)\s*\{\s*\}/, 'SO confirmation must not swallow network errors.');

const trackDO = functionBody(
  /window\.trackDO\s*=\s*async\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
  'trackDO()'
);

assert.match(trackDO, /if\s*\(\s*!res\.ok\s*\)/, 'GPS failures must be handled explicitly.');
assert.match(trackDO, /resetTrackingLiveMetrics\s*\(\s*\)/, 'GPS failures must clear stale live metrics.');
assert.doesNotMatch(trackDO, /mockTrack|speed_kmh:\s*48|remaining_distance_km:\s*18\.5|eta:\s*['"]14:30['"]/, 'GPS must never synthesize operational tracking data.');
assert.doesNotMatch(trackDO, /track\.speed_kmh\s*\|\|\s*0/, 'Missing GPS speed must not be displayed as a real zero.');
assert.doesNotMatch(trackDO, /track\.remaining_distance_km\s*\|\|\s*0/, 'Missing GPS distance must not be displayed as a real zero.');

assert.doesNotMatch(html, /toggleRouteDeviationSimulation|Thẻ Cảnh Báo Lệch/, 'Operational tracking must not expose a route-deviation simulation button.');
assert.doesNotMatch(html, /id=["']ai_btn_reject["']|data-i18n=["']ai_btn_reject["']/, 'AI check-in must not expose an unimplemented reject action.');
assert.doesNotMatch(html, /Route segment details go here\.|Internal notes\.|File attachments\./, 'Delivery Order must not show placeholder-only tabs.');
assert.doesNotMatch(html, /id=["']pod-(?:file-input|note|time|receiver)["']/, 'Tracking must not collect POD fields that it does not persist.');
// Truoc day man Theo doi co mot khung mo ta duong tat sang buoc hoan tat
// ("MO HO SO HOAN TAT GIAO HANG"), va phep khang dinh o day chot dong chu do.
// Khung ay bi `display:none` che tu lau nen khong ai doc duoc dong chu, va nay
// da bo han. Y nghia goc van phai giu: man Theo doi khong duoc thu bang chung
// giao hang ma khong luu (dong 42 ngay tren), va buoc hoan tat co luu that phai
// co man rieng de di tiep.
assert.match(html, /id=["']view-delivery-completion["']/,
  'The persisted delivery-completion workflow must have its own screen.');
assert.doesNotMatch(html, /MỞ HỒ SƠ HOÀN TẤT GIAO HÀNG/,
  'The dead hand-off panel was removed from Tracking — it must not come back.');

for (const legacyName of [
  'legacyModalApproveQuotation',
  'legacySubmitPOD',
  'legacyOptimizeMasterForm',
  'addNewFormulaPreset',
  'saveVisualFormula',
  'optimizeMasterForm',
  'markDOArrived'
]) {
  assert.doesNotMatch(appSource, new RegExp(`(?:function\\s+|window\\.)${legacyName}`), `${legacyName} must not remain in production code.`);
}

const publishMasterForm = functionBody(
  /window\.publishMasterForm\s*=\s*function\s*\([^)]*\)\s*\{[\s\S]*?\n\};/,
  'publishMasterForm()'
);
assert.doesNotMatch(publishMasterForm, /Đã phát lệnh[\s\S]*thành công/, 'Dispatch publish fallback must not claim success without an API call.');

const loadDispatchBoard = functionBody(
  /async function loadDispatchBoard\s*\(\)\s*\{[\s\S]*?\n\}/,
  'loadDispatchBoard()'
);
assert.match(loadDispatchBoard, /fetchAllPaginated\(`\$\{API_BASE\}\/api\/delivery-orders`/, 'Dispatch must load every Delivery Order page.');
assert.match(loadDispatchBoard, /fetchAllPaginated\(`\$\{API_BASE\}\/api\/vehicles\?paginated=true`/, 'Dispatch must load every vehicle page.');
assert.match(loadDispatchBoard, /fetchAllPaginated\(`\$\{API_BASE\}\/api\/tms\/trips`/, 'Dispatch must load every Trip page.');

const loadDriverShiftPlanner = functionBody(
  /window\.loadDriverShiftPlanner\s*=\s*async\s*function\s*\(\)\s*\{[\s\S]*?\n\};/,
  'loadDriverShiftPlanner()'
);
assert.match(loadDriverShiftPlanner, /fetchAllPaginated\(`\$\{API_BASE\}\/api\/vehicles\?paginated=true`/, 'Driver scheduling must load every vehicle page.');

console.log('REAL_API_UI_GUARDS_OK');
