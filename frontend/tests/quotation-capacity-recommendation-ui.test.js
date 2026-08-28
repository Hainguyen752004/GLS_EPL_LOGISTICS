const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

for (const id of ['qt-weight-kg', 'qt-volume-m3', 'qt-pallet-count', 'qt-vehicle-recommendations']) {
  assert.ok(html.includes(`id="${id}"`), `Quotation form must expose ${id}.`);
}

assert.match(app, /window\.refreshQuotationVehicleRecommendations\s*=\s*function/, 'Quotation recommendation renderer is required.');
assert.match(app, /disabled\s*=\s*hasDemand\s*&&\s*!evaluation\.fits/, 'Unsuitable vehicle types must be disabled.');
assert.match(app, /CAPACITY_NOT_CONFIGURED/, 'Missing capacity configuration must be explained.');
assert.match(app, /Không có loại xe đơn lẻ đủ tải/, 'No-fit state must explain split trip or outsource options.');
assert.match(app, /readyVehicles[\s\S]*vehicle\.id/, 'Recommendation cards must expose currently ready vehicle ids.');
assert.match(app, /const capacityState = window\.refreshQuotationVehicleRecommendations\(\)/, 'Quotation save must revalidate capacity.');
assert.match(app, /if \(!capacityState\.valid\)/, 'Quotation save must stop when selected type is unsuitable.');

console.log('QUOTATION_CAPACITY_RECOMMENDATION_UI_OK');
