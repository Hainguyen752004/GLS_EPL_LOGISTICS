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

// ---------------------------------------------------------------------------
// MAN BAO GIA DANG CHAY (`bao-gia-v2.js`) cung phai co cua chan tai trong.
//
// Cac phep khang dinh tren chot man Bao gia CU. Man dang chay la man moi, va
// mot lo that da do duoc: `do_vua_tai` o may chu TRUOC DAY chi xet `max_weight`,
// nen mot lo 40 m3 tren xe lanh 22 m3 duoc cham la "phu hop" va 30 pallet tren
// xe 8 pallet cung vay. Nguoi ban chon dung cai the mau xanh do, luu lai, roi
// nhan 409 tu cua chan o duong ghi — man hinh noi mot cau, may chu noi cau khac.
//
// Nay ca hai ben dung CUNG MOT BO DANH GIA ba chieu. Phia may chu co
// `backend/tests/test_bao_gia_cua_chan_tai_trong.py` chot lai; day la nua phia
// giao dien.
{
  const quotationSource = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'bao-gia-v2.js'), 'utf8');

  // The loai xe "khong du tai" phai bi chan khi bam, khong chi doi mau.
  assert.match(quotationSource, /if \(n\.dataset\.hong\)/,
    'New quotation screen must block clicking an unsuitable vehicle type.');
  assert.match(quotationSource, /khong_du_tai/,
    'New quotation screen must read the server capacity verdict.');

  // Va thong bao phai noi DUNG CHIEU vuot. Noi "khong du tai" cho mot lo hang
  // nhe ma khoi lon la noi sai: nguoi ban doi sang xe nang hon roi van vuong.
  assert.match(quotationSource, /function lyDoKhongDu\(/,
    'New quotation screen must explain which capacity dimension is exceeded.');
  assert.match(quotationSource, /WorkflowUIUtils\.evaluateVehicleCapacity/,
    'It must reuse the shared evaluator, not compute capacity on its own — two '
    + 'separate implementations drift and then only one gets fixed.');
  ['tải trọng', 'thể tích', 'số pallet'].forEach(chieu => {
    assert.ok(quotationSource.includes(chieu),
      `Capacity message must be able to name "${chieu}".`);
  });
}

console.log('QUOTATION_CAPACITY_RECOMMENDATION_UI_OK');
