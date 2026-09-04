/**
 * Đơn vị chi phí phải nhất quán trên toàn dự án.
 *
 * Chủ dự án đã chốt: **mọi đơn giá chi phí quy về "trên 1 km"** — anh cho biết
 * trước đó chính anh nhập lẫn lộn, có chỗ để theo 100 km, có chỗ để theo 1 km.
 *
 * Mâu thuẫn tìm được lúc rà soát:
 *
 *   fuel_norm     form nhập xe ghi "Lít/100km"
 *                 nhãn công thức ghi "lít/km"      <- sai
 *                 models.py ghi "lít/km"           <- sai
 *                 giá trị thật 18 và 26            <- chỉ hợp lý ở lít/100km
 *                                                     (26 lít cho 1 km là vô lý)
 *
 *   Hệ quả: công thức `DISTANCE x FUEL_NORM x FUEL_PRICE` ăn vào dữ liệu thật
 *   sẽ ra chi phí xăng dầu GẤP 100 LẦN. Bản xem trước không lộ ra vì nó
 *   hardcode 0,25 (lít/km) thay vì dùng giá trị thật của loại xe.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const backendRoot = path.join(frontendRoot, '..', 'backend');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const models = fs.readFileSync(path.join(backendRoot, 'app', 'models.py'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(frontendRoot, 'js', 'lang.json'), 'utf8').replace(/^﻿/, ''));

/** Bỏ các dòng ghi chú — chúng nhắc lại đơn vị cũ để giải thích vì sao đổi. */
function codeOnly(source) {
  return source
    .split(String.fromCharCode(10))
    .filter(line => !/^\s*(\/\/|#|\/?\*)/.test(line))
    .join(String.fromCharCode(10));
}

// --- 1. Không còn chỗ nào ghi fuel_norm là lít/km --------------------------

[['app.js', app], ['index.html', html], ['models.py', models]].forEach(([name, source]) => {
  assert.ok(
    !/lít\/km|lit\/km|Lít\/km|L\/km/.test(codeOnly(source)),
    `${name} còn ghi định mức nhiên liệu theo lít/km`
  );
});

// Trước đây chỗ này đếm đúng năm nhãn `lít/100km` — chúng nằm trong danh sách
// hạng tử của trình dựng công thức kéo thả. Trình đó đã bị gỡ (mã chết: không
// còn thẻ nào trong trang gọi tới, và nó tính bằng một bộ hằng số mẫu riêng),
// nên phép đếm đó chỉ còn khóa lại một con số tình cờ.
//
// Điều thật sự cần giữ là: mọi nhãn định mức nhiên liệu đều mang đơn vị
// lít/100km, không bao giờ lít/km — phần kiểm ở trên đã lo việc đó cho cả ba
// tệp. Ở đây chỉ chốt thêm rằng trình dựng cũ không quay lại.
['currentFormulaTokens', 'renderVisualFormula', 'calculateFormulaPreviewResult'].forEach(name => {
  assert.ok(!app.includes(name), `${name} là mã chết, không được còn trong app.js`);
});
assert.match(html, /Lít\/100km/, 'form nhập xe phải ghi đơn vị');
assert.match(models, /lít\/100km/, 'ghi chú cột trong models.py phải ghi đơn vị');

// --- 2. Bản dịch không được ghi đè mất đơn vị -----------------------------
//
// lang.json ghi đè nhãn theo data-i18n, nên sửa HTML mà quên sửa bản dịch thì
// đơn vị biến mất ngay khi trang tải xong.
['vi', 'en', 'la'].forEach(code => {
  assert.match(
    lang.th_fuel_norm[code],
    /100km/,
    `bản dịch th_fuel_norm.${code} phải mang đơn vị`
  );
  assert.match(lang.lbl_veh_fuel_norm[code], /100km/, `bản dịch lbl_veh_fuel_norm.${code} phải mang đơn vị`);
});

// --- 3. fuel_norm khong duoc nhan thanh tien ma khong chia 100 -----------
//
// Truoc day phan nay kiem ham xem truoc cua trinh dung cong thuc keo tha, noi
// co dong `fuelNormPer100Km / 100`. Trinh do da bi go (ma chet). Nhung dieu no
// bao ve thi van con that: `fuel_norm` la LIT/100KM — gia tri that trong co so
// du lieu la 18 va 26, va 26 lit cho 1 km la vo ly. Nhan thang no voi gia dau
// se ra chi phi GAP 100 LAN.
//
// Hien tai fuel_norm chi duoc doc de HIEN THI, khong dung tinh tien o dau ca.
// Chot lai dieu do: he nao co ai viet `fuel_norm * gia_dau` thi bai kiem nay
// bao ngay, de nho chia 100 truoc.
{
  const dong = app.split(String.fromCharCode(10));
  dong.forEach((line, index) => {
    if (!/fuel_norm|fuelNorm/.test(line)) return;
    if (/^\s*(\/\/|\*|\/\*)/.test(line)) return;
    assert.ok(
      !line.includes('*'),
      `app.js dong ${index + 1} nhan fuel_norm thanh tien ma chua chia 100: ${line.trim()}`
    );
  });
}

// --- 4. base_rate là đơn giá trên 1 km ------------------------------------

assert.match(models, /base_rate.*đ\/km/, 'ghi chú cột base_rate phải nêu rõ đơn vị đ/km');
{
  const start = app.indexOf('window.renderDynamicFormulaVehicleTypes');
  const fn = app.slice(start, app.indexOf('firstCard', start));
  // Thẻ loại xe không còn hiện base_rate; nó hiện chi phí xăng dầu / 1 km lấy
  // từ công thức ĐÃ LƯU, theo đơn vị tiền tệ đang chọn — vì base_rate chưa bao
  // giờ được dùng để tính gì, và nút Lưu ghi vào bảng khác nên nó không đổi.
  // The hien TONG mot chuyen mau (vi nam cau phan khac don vi nen khong cong
  // thang duoc), va boc tach them binh quan moi km + xang dau moi km.
  assert.match(fn, /\/chuyến mẫu/, 'the phai noi ro tong do la cua mot chuyen mau');
  assert.match(fn, /estimate\.perKm/, 'the phai co gia thanh moi km de so sanh giua cac loai xe');
  assert.match(fn, /fa-gas-pump/, 'the phai boc tach chi phi xang dau');
  assert.match(fn, /masterCostCurrencyCode\(\)/, 'thẻ phải theo đơn vị tiền tệ đang chọn');
}

// --- 5. base_rate không được rót vào ô cước phí / 1kg ---------------------
//
// Hai trường khác hẳn thứ nguyên: đ/km và đ/kg.
{
  const start = app.indexOf('function ensureVehicleTypeFormula');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '}', start));
  assert.ok(!/String\(vehicleType\.base_rate/.test(fn), 'không được dùng đ/km làm giá trị dự phòng cho đ/kg');
}

// --- 6. Phép tính chi phí thật vẫn là "trên 1 km" -------------------------
//
// Trước đây phần này bám vào tên biến `fuelCost = Math.round(r.km * fuelRate)`.
// Phép tính giờ nằm trong mô hình hạng tử, nên kiểm ĐÚNG Ý: đơn giá khai
// "mỗi km" phải nhân với số km, và số km phải là tổng km của tuyến đang chọn.

{
  const model = require('path').join(__dirname, '..', 'js', 'formula-model.js');
  const M = require(model);
  assert.strictEqual(M.FACTORS.per_km.unit, '/km');
  assert.strictEqual(M.FACTORS.per_km.of({ km: 137, tonnes: 3, stops: 1 }), 137,
    'don gia moi km phai nhan voi so km, khong phai 100 km');

  const P = require(require('path').join(__dirname, '..', 'js', 'quotation-pricing.js'));
  const result = P.price({
    store: { k: { vehicleTypeName: 'X', terms: [{ key: 'fuel', label: 'Xăng dầu /km', operator: 'add', factor: 'per_km', rate: 4800 }] } },
    vehicleTypes: [{ id: 'T', name: 'X' }], cargoType: 'X',
    route: { id: 'R', name: 'R', distance_km: 137 },
  });
  assert.strictEqual(result.cost, 4800 * 137, 'báo giá phải lấy tổng km của tuyến đang chọn');
}

// Và không được còn chệch đơn vị kiểu chia 100 km ẩn ở đâu đó.
{
  const code = app.split(String.fromCharCode(10)).filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*') && !trimmed.startsWith('/*');
  }).join(String.fromCharCode(10));
  assert.ok(!/km\s*\/\s*100/.test(code), 'không được chia số km cho 100');
}

console.log('cost-unit-consistency: tất cả kiểm tra đã qua');
