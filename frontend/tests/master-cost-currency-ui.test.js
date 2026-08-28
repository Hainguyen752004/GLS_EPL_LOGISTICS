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

check('master cost formula exposes currency selector beside save controls', () => {
  assert.match(html, /id=["']md-cost-currency["']/, 'Master cost formula must expose a currency selector.');
  assert.match(html, /onchange=["']onMasterCostCurrencyChange\(\)["']/, 'Currency selector must refresh the formula UI when changed.');
  for (const code of ['VND', 'USD', 'THB', 'LAK']) {
    assert.match(html, new RegExp(`<option value=["']${code}["']`), `Currency selector must include ${code}.`);
  }
});

check('cost formula table labels currency dynamically instead of hard-coded VND', () => {
  assert.match(html, /id=["']md-cost-unit-price-label["']/, 'Unit price header must have a dynamic currency label hook.');
  assert.doesNotMatch(html, /data-i18n=["']th_cost_unit_price["'][^>]*>Đơn Giá Cấu Hình \(VNĐ\)/, 'Header should not hard-code VNĐ.');
  assert.match(html, /class=["'][^"']*md-cost-currency-suffix/, 'Cost amount inputs need a visible currency suffix.');
});

check('custom cost and save flow preserve selected currency', () => {
  assert.match(appSource, /function\s+masterCostCurrencyCode\s*\(/, 'App must centralize selected master cost currency.');
  assert.match(appSource, /window\.onMasterCostCurrencyChange\s*=/, 'App must expose currency change handler.');
  assert.match(appSource, /masterFormulaStore\[currentKey\]\.currency\s*=\s*currency/, 'Saving formula must persist selected currency in the preset store.');
  assert.match(appSource, /fetch\(`\$\{API_BASE\}\/api\/cost-formulas`/, 'Saving formula must call the real cost formula API.');
  assert.match(appSource, /body:\s*JSON\.stringify\(payload\)/, 'Cost formula API call must send the saved payload.');
  assert.match(appSource, /updateMasterCostCurrencyUI\s*\(\)/, 'App must update visible labels/suffixes after load or save.');
});

check('vehicle type cost formulas use stable database identities', () => {
  assert.match(appSource, /function\s+costFormulaKeyForVehicleType\s*\(/, 'Formula keys must be derived from the vehicle type identity.');
  assert.match(appSource, /vehicle_type_id:\s*selectedVehicleTypeId/, 'Formula saves must include the selected vehicle type ID.');
  const renderStart = appSource.indexOf('window.renderDynamicFormulaVehicleTypes');
  const renderEnd = appSource.indexOf('// --- CUSTOMER MANAGEMENT LOGIC', renderStart);
  const renderer = appSource.slice(renderStart, renderEnd);
  assert.doesNotMatch(renderer, /`preset-\$\{idx\s*\+\s*1\}`/, 'Vehicle types must never be bound to formulas by row position.');
  assert.match(renderer, /selectFormulaVehicleType\(firstFormulaKey,\s*firstCard/, 'Rendering must synchronize the selected card, badge and form values.');
});

check('vehicle type cost formulas are isolated by currency and guard unsaved changes', () => {
  assert.match(appSource, /function\s+costFormulaKeyForVehicleType\s*\(vehicleType,\s*currency/, 'Formula key must include the selected currency.');
  assert.match(appSource, /vehicle-type::\$\{[^}]+\}::\$\{[^}]+\}/, 'Formula storage key must combine vehicle type and currency.');
  assert.match(appSource, /window\.requestCostFormulaContextChange\s*=/, 'Vehicle/currency changes must pass through one guarded context switch.');
  assert.match(appSource, /Lưu thay đổi và chuyển/, 'Dirty form warning must offer save and switch.');
  assert.match(appSource, /Bỏ thay đổi/, 'Dirty form warning must offer discard.');
  assert.match(appSource, /Ở lại/, 'Dirty form warning must offer staying on the current form.');
  assert.match(appSource, /if\s*\(!saved\)\s*return/, 'A failed save must prevent switching context.');
});

if (failures.length) {
  throw new Error(`Master cost currency UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('MASTER_COST_CURRENCY_UI_OK');
