const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('tracking page exposes a separate closeout selector for delivered DOs', () => {
  assert.match(html, /id=["']tracking-closeout-do-select["']/, 'Missing closeout DO selector.');
  assert.match(html, /id=["']tracking-closeout-content["']/, 'Missing closeout render container.');
  assert.match(html, /loadDeliveryOrderCloseout\(this\.value\)/, 'Closeout selector must load selected DO.');
});

check('POD evidence card selects a DO before opening the persisted completion workflow', () => {
  assert.match(html, /id=["']pod-delivery-do-select["']/, 'Missing POD DO selector.');
  assert.match(html, /id=["']btn-open-pod-form["']/, 'Missing button to open the completion record after selecting DO.');
  assert.doesNotMatch(html, /id=["']pod-entry-form["']/, 'Tracking must not expose an unpersisted POD entry form.');
  assert.match(appSource, /window\.populatePODDeliverySelector\s*=\s*function/, 'Missing POD selector population function.');
  assert.match(appSource, /window\.openPODFormForSelectedDO\s*=\s*async\s*function/, 'Missing completion hand-off function.');
  assert.match(appSource, /await\s+window\.submitPOD\(\)/, 'Selected DO must continue to the atomic completion workflow.');
});

check('closeout selector uses delivered/completed status instead of GPS live status', () => {
  assert.match(appSource, /function\s+isCloseoutReadyStatus\s*\(/, 'Missing closeout status guard.');
  const selector = appSource.match(/function\s+populateCloseoutDOSelector\s*\([^)]*\)\s*\{[\s\S]*?\n\}/);
  assert.ok(selector, 'Missing populateCloseoutDOSelector().');
  assert.match(selector[0], /isCloseoutReadyStatus/, 'Closeout selector must filter delivered/completed DOs.');
  assert.doesNotMatch(selector[0], /isGpsLiveTrackingStatus/, 'Closeout selector must not reuse live GPS guard.');
});

check('closeout view fetches the real backend closeout API', () => {
  assert.match(appSource, /window\.loadDeliveryOrderCloseout\s*=\s*async\s*function/, 'Missing loadDeliveryOrderCloseout().');
  assert.match(appSource, /\/api\/delivery-orders\/\$\{encodeURIComponent\(doId\)\}\/closeout/, 'Closeout view must call backend closeout API.');
  assert.match(appSource, /renderDeliveryOrderCloseout/, 'Closeout response must be rendered.');
});

check('closeout view opens the actual cost editor for the selected DO and Trip', () => {
  assert.match(appSource, /window\.openCloseoutActualCostEditor\s*=\s*async\s*function/, 'Missing closeout actual-cost handoff.');
  assert.match(appSource, /data-closeout-cost-action/, 'Closeout must render an explicit actual-cost action button.');
  assert.match(appSource, /editFioriDO\(doId\)/, 'Actual-cost handoff must open the DO form for the selected DO.');
  assert.match(appSource, /dataset\.tripId\s*=\s*tripId/, 'Actual-cost handoff must bind the resolved Trip to the save button.');
  assert.match(appSource, /dataset\.refreshCloseoutDoId\s*=\s*doId/, 'Saving actual cost must know which closeout to refresh.');
});

check('saving actual cost from closeout refreshes the closeout price table', () => {
  assert.match(appSource, /refreshCloseoutDoId/, 'Missing closeout refresh marker on actual-cost save.');
  assert.match(appSource, /loadDeliveryOrderCloseout\(refreshCloseoutDoId\)/, 'Actual-cost save must reload closeout after server confirmation.');
});

check('legacy tracking POD action opens the atomic delivery completion workbench', () => {
  const podHandler = appSource.match(/window\.submitPOD\s*=\s*async function[\s\S]*?\n\};/);
  assert.ok(podHandler, 'Missing submitPOD handler.');
  assert.match(podHandler[0], /switchView\('delivery-completion'\)/, 'Legacy POD action must open the completion module.');
  assert.match(podHandler[0], /openDeliveryCompletionEditor\(doId\)/, 'Selected DO must open in the atomic completion editor.');
  assert.doesNotMatch(podHandler[0], /\/api\/pod\//, 'Legacy tracking must not write a partial POD record.');
  assert.doesNotMatch(podHandler[0], /\/api\/invoices\/post/, 'Legacy tracking must not post accounting separately.');
});

check('closeout POD cards expose persisted POD document names', () => {
  assert.match(appSource, /pod\.photo_url/, 'Closeout must render POD file/photo evidence from the database.');
  assert.match(appSource, /POD\/hop dong/, 'Closeout must label the attached POD/contract evidence.');
});

if (failures.length) {
  throw new Error(`Tracking closeout UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('TRACKING_CLOSEOUT_UI_OK');
