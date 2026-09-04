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

// Và mọi nhãn định mức đều phải mang đơn vị lít/100km.
assert.strictEqual((app.match(/lít\/100km/g) || []).length, 5, 'năm nhãn token trong app.js');
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

// --- 3. Bản xem trước phải chia 100 ---------------------------------------

{
  // Tim dinh nghia, khong phai cho GOI ham — indexOf tho se bat trung cho goi.
  const start = app.indexOf('window.calculateFormulaPreviewResult = function');
  assert.ok(start > 0, 'phải còn hàm xem trước công thức');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));

  // Hardcode 0,25 chính là thứ che mất mâu thuẫn đơn vị.
  assert.ok(!/const fuelNorm = 0\.25/.test(fn), 'không được hardcode giá trị theo lít/km');
  assert.match(fn, /fuelNormPer100Km/, 'phải nêu rõ giá trị là lít/100km');
  assert.match(fn, /fuelNormPer100Km \/ 100/, 'phải chia 100 để kết quả là tiền trên 1 km');
}

// --- 4. base_rate là đơn giá trên 1 km ------------------------------------

assert.match(models, /base_rate.*đ\/km/, 'ghi chú cột base_rate phải nêu rõ đơn vị đ/km');
{
  const start = app.indexOf('window.renderDynamicFormulaVehicleTypes');
  const fn = app.slice(start, app.indexOf('firstCard', start));
  assert.match(fn, /<small>đ\/km<\/small>/, 'thẻ loại xe phải ghi đơn vị đ/km');
  assert.match(fn, /Chưa đặt đơn giá\/km/, 'thiếu đơn giá phải nói rõ là đơn giá/km');
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

{
  const match = /const fuelCost = Math\.round\(([^)]*)\)/.exec(app);
  assert.ok(match, 'phải còn phép tính chi phí nhiên liệu');
  assert.match(match[1], /r\.km \* fuelRate/, 'chi phí nhiên liệu = số km × đơn giá trên 1 km');
}

console.log('cost-unit-consistency: tất cả kiểm tra đã qua');
