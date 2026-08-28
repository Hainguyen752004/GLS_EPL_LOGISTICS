const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');
const parking = fs.readFileSync(path.join(root, 'js', 'parking-list.js'), 'utf8');

test('Parking List is a dedicated application view', () => {
  assert.match(html, /data-view="parking-list"/);
  assert.match(html, /id="view-parking-list"/);
  assert.match(html, /id="parking-create-modal"/);
  assert.match(html, /parking-list\.js/);
  assert.match(app, /targetView === 'parking-list'/);
});

test('Parking List uses real APIs, package QR labels and paginated DO loading', () => {
  assert.match(parking, /\/api\/parking-lists\/auto-from-do\//);
  assert.match(parking, /label\.qr_path/);
  assert.match(parking, /page_size=200/);
  assert.match(parking, /for \(let page = 2; page <= pages; page \+= 1\)/);
  assert.match(html, /id="parking-scan-modal"/);
  assert.match(parking, /\/api\/parking-qr\//);
  assert.match(parking, /submitParkingQrScan/);
  assert.doesNotMatch(parking, /advanceParkingStatus/);
  assert.doesNotMatch(parking, /Math\.random|mock|fake/i);
});

test('automatic creation only asks how many Packing Lists to split', () => {
  assert.match(html, /id="parking-list-count-input"/);
  assert.match(html, /Hệ thống tự lấy khách hàng, tuyến, hàng hóa và số kiện/);
  assert.doesNotMatch(html, /id="parking-store-id"/);
  assert.doesNotMatch(html, /id="parking-box-count"/);
});

test('print views contain package and item traceability fields', () => {
  for (const marker of ['STORE', 'ROUTE', 'WAVE', 'GATE', 'Barcode', 'Item ID Laos', 'Item ID Thai']) {
    assert.ok(parking.includes(marker), `missing print marker: ${marker}`);
  }
});
