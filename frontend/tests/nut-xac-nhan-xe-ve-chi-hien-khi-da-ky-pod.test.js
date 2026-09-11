/**
 * Nút "Xác nhận xe đã về bãi" chỉ hiện khi ĐÃ KÝ POD đủ chặng giao.
 *
 * Đo trên dữ liệu thật (11/09): một chuyến khứ hồi vừa xuất bến, chưa ký POD nào, vẫn hiện
 * nút đó. Bấm vào thì máy chủ từ chối bằng `OPEN_DELIVERY_LEG` — "Phải hoàn tất POD cho tất
 * cả chặng giao trước khi xác nhận xe quay về". Một nút chỉ có thể lỗi thì tệ hơn không có
 * nút: người trực bấm, thấy lỗi, rồi không biết mình làm sai ở đâu.
 *
 * Còn chuyến ĐÃ giao xong mà chặng về chưa đi (đúng trạng thái "xe đang quay về") thì nút
 * PHẢI hiện — đó là bước cuối để đóng chuyến và nhả xe.
 *
 * Bài kiểm CHẠY THẬT hàm, không quét chữ: điều kiện này là logic, và một bài quét chữ sẽ
 * xanh ngay cả khi phép so sánh bị viết ngược.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// Lấy `changVeCua` + `tripChoXacNhanVe` ra chạy độc lập.
const iVe = app.indexOf('const changVeCua = raw =>');
const iHam = app.indexOf('function tripChoXacNhanVe(raw) {');
const jHam = app.indexOf(String.fromCharCode(10) + '}', iHam) + 2;
assert.ok(iVe > 0 && iHam > iVe, 'không thấy changVeCua / tripChoXacNhanVe');
const khoiVe = app.slice(iVe, app.indexOf(';', app.indexOf('leg_type ||', iVe)) + 1);
const chay = new Function('LOAI_CHANG_VE',
  khoiVe + String.fromCharCode(10) + app.slice(iHam, jHam)
  + String.fromCharCode(10) + 'return tripChoXacNhanVe;');
const tripChoXacNhanVe = chay(['empty_return', 'backhaul']);

const chang = (loai, trangThai) => ({ leg_type: loai, status: trangThai });

// 1. Khứ hồi, chưa ký POD chặng giao → KHÔNG hiện nút (máy chủ sẽ trả OPEN_DELIVERY_LEG).
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit',
  legs: [chang('delivery', 'planned'), chang('empty_return', 'planned')],
}), false, 'chưa ký POD mà vẫn hiện nút xác nhận xe về');

// 2. Tuyến có điểm trung chuyển: chặng đi ngang đã đóng, chặng giao CHƯA → vẫn không hiện.
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit',
  legs: [chang('outbound', 'completed'), chang('delivery', 'planned'), chang('empty_return', 'planned')],
}), false);

// 3. Đã giao xong, chặng về chưa đi → PHẢI hiện (đây là bước đóng chuyến, nhả xe).
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit',
  legs: [chang('outbound', 'completed'), chang('delivery', 'completed'),
         chang('empty_return', 'planned'), chang('empty_return', 'planned')],
}), true, 'chuyến đã giao, chặng về chưa đi thì phải hiện nút');

// 4. Chặng giao bị huỷ cũng coi là đã xong (không còn gì để ký).
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit',
  legs: [chang('delivery', 'cancelled'), chang('backhaul', 'planned')],
}), true);

// 5. Chặng về đã đi hết, hoặc chuyến đã đóng, hoặc chuyến một chiều → không hiện.
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit', legs: [chang('delivery', 'completed'), chang('empty_return', 'completed')],
}), false);
assert.strictEqual(tripChoXacNhanVe({
  status: 'completed', legs: [chang('delivery', 'completed'), chang('empty_return', 'planned')],
}), false);
assert.strictEqual(tripChoXacNhanVe({
  status: 'in_transit', legs: [chang('delivery', 'completed')],
}), false, 'chuyến một chiều không có chặng về thì không có gì để xác nhận');

console.log('nut-xac-nhan-xe-ve-chi-hien-khi-da-ky-pod: OK');
