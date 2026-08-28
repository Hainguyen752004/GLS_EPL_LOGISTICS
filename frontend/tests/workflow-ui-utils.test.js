const assert = require('assert');
const fs = require('fs');
const path = require('path');

const sourcePath = path.join(__dirname, '..', 'js', 'workflow-ui-utils.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const utils = require(sourcePath);

assert.strictEqual(utils.statusLabel('approved'), 'Đã duyệt');
assert.strictEqual(utils.statusLabel('Đang vận chuyển'), 'Đang vận chuyển');
assert.strictEqual(utils.workflowStatusKey('Đã xác nhận'), 'confirmed');
assert.deepStrictEqual(utils.workflowActionMode('draft'), {
  canEdit: true,
  canDelete: true,
  canView: true,
});
assert.strictEqual(utils.workflowActionMode('approved').canEdit, false);

const overloaded = utils.evaluateVehicleCapacity(
  { id: 'VT-20T', name: 'Xe 20 tan', max_weight: 20000, volume_capacity_m3: 40, pallet_capacity: 20 },
  { weight_kg: 30000, volume_m3: 20, pallet_count: 10 }
);
assert.strictEqual(overloaded.fits, false);
assert.deepStrictEqual(overloaded.reasons.map(item => item.dimension), ['weight']);

const recommendations = utils.recommendVehicleTypes([
  { id: 'VT-40T', name: 'Xe 40 tan', max_weight: 40000, volume_capacity_m3: 60, pallet_capacity: 30 },
  { id: 'VT-35T', name: 'Xe 35 tan', max_weight: 35000, volume_capacity_m3: 50, pallet_capacity: 24 },
  { id: 'VT-20T', name: 'Xe 20 tan', max_weight: 20000, volume_capacity_m3: 40, pallet_capacity: 20 },
], { weight_kg: 30000, volume_m3: 20, pallet_count: 10 });
assert.deepStrictEqual(recommendations.suitable.map(item => item.vehicleType.id), ['VT-35T', 'VT-40T']);
assert.deepStrictEqual(recommendations.unsuitable.map(item => item.vehicleType.id), ['VT-20T']);

const missingPalletCapacity = utils.evaluateVehicleCapacity(
  { id: 'VT-NO-PALLET', max_weight: 40000, volume_capacity_m3: 60, pallet_capacity: 0 },
  { weight_kg: 30000, volume_m3: 20, pallet_count: 10 }
);
assert.strictEqual(missingPalletCapacity.fits, false);
assert.strictEqual(missingPalletCapacity.reasons[0].code, 'CAPACITY_NOT_CONFIGURED');

assert.strictEqual(
  Object.prototype.hasOwnProperty.call(utils, 'fixDocumentVietnamese'),
  false,
  'Không được xuất helper sửa toàn bộ DOM ở runtime.'
);
assert.doesNotMatch(source, /createTreeWalker|MutationObserver/);

console.log('WORKFLOW_UI_UTILS_OK');
