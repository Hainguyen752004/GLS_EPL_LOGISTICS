/**
 * Chưa có tỷ giá thì phải NÓI LÀ CHƯA CÓ, không được lấy một con số cũ ra
 * dùng thay.
 *
 * Bản trước, mỗi đồng tiền mang kèm một `defaultRate` viết cứng — USD 25.450,
 * THB 710, LAK 1,18 — và `workflowCurrencyRate` rơi về con số đó bất cứ khi
 * nào ô tỷ giá trống hoặc không đọc được. Ba con số ấy không có nguồn nào và
 * không bao giờ được cập nhật.
 *
 * Chúng còn được nhân đôi ở HTML: `<input id="rate-usd" value="25,450">`. Và
 * `renderCurrencyRateHistory` chỉ ghi đè ô nhập KHI máy chủ có tỷ giá, nên khi
 * chưa ai lưu gì, ô nhập giữ nguyên 25.450 — nhìn y hệt một tỷ giá đã lưu,
 * trong khi ô "Đang áp dụng" ngay bên cạnh ghi "Chưa lưu".
 *
 * Hậu quả: màn báo giá hiện "$141.41 USD" cho khách, quy đổi từ một tỷ giá
 * không ai chọn. Con số bịa trông không khác gì con số đúng.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// --- 1. Không còn tỷ giá viết cứng ở cả hai tầng -----------------------

{
  // Chỉ soi dòng LỆNH: chú thích ở đầu khối có trích ba con số cũ để giải
  // thích, và trích dẫn thì không phải mã chạy.
  // Phải bỏ CẢ KHỐI `/* ... */`, không chỉ những dòng mở đầu bằng `*`. Khối
  // chú thích ngay trên WORKFLOW_CURRENCY_META trích nguyên ba con số cũ để
  // giải thích, và các dòng giữa khối bắt đầu bằng chữ thường — lọc theo ký
  // tự đầu dòng sẽ giữ chúng lại rồi báo sai là "còn tỷ giá viết cứng".
  const lenh = app
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split(NL)
    .filter(d => !d.trim().startsWith('//'))
    .join(NL);
  assert.ok(!/defaultRate/.test(lenh), 'còn defaultRate — tỷ giá dự phòng viết cứng');
  [/\b25450\b/, /rateInputId: 'rate-thb', [^}]*710/, /rateInputId: 'rate-lak', [^}]*1\.18/]
    .forEach(m => assert.ok(!m.test(lenh), `còn tỷ giá viết cứng: ${m}`));
}
['value="25,450"', 'id="rate-thb" class="fiori-input" value="710"',
  'id="rate-lak" class="fiori-input" value="1.18"']
  .forEach(x => assert.ok(!html.includes(x), `còn tỷ giá viết cứng trong HTML: ${x}`));

// Và ba ô đó phải nói rõ khi trống.
['rate-usd', 'rate-thb', 'rate-lak'].forEach(id => {
  const o = html.match(new RegExp('<input[^>]*id="' + id + '"[^>]*>'));
  assert.ok(o, `không thấy ô ${id}`);
  assert.ok(/placeholder="Chưa có tỷ giá"/.test(o[0]), `${id} phải có placeholder nói rõ`);
});

// --- 2. Chạy THẬT ba hàm quy đổi, không dò chữ -------------------------

function nap() {
  const dau = app.indexOf('const WORKFLOW_CURRENCY_META = {');
  const cuoi = app.indexOf('function selectedWorkflowCurrencyMeta');
  assert.ok(dau > 0 && cuoi > dau);
  const doan = app.slice(dau, cuoi);

  const oNhap = {};
  const document = {
    getElementById: (id) => (id in oNhap ? { value: oNhap[id] } : null),
  };
  const window = {
    CurrencyRateUtils: {
      parseCurrencyRateNumber: (raw) => {
        if (raw == null || String(raw).trim() === '') return NaN;
        return Number(String(raw).split(',').join(''));
      },
    },
  };
  const appState = { currencies: [] };
  const f = new Function('document', 'window', 'appState',
    doan + NL
    + 'return { workflowCurrencyRate, workflowCurrencyConversionLabel,'
    + ' formatWorkflowCurrencyAmount };');
  return { ham: f(document, window, appState), oNhap };
}

{
  const { ham, oNhap } = nap();

  // Chưa có tỷ giá: KHÔNG được trả về một con số.
  assert.strictEqual(ham.workflowCurrencyRate('USD'), null);
  assert.strictEqual(ham.workflowCurrencyRate('THB'), null);
  assert.strictEqual(ham.workflowCurrencyRate('LAK'), null);
  // VND là đồng bản vị: tỷ lệ 1 là định nghĩa, không phải giá trị dự phòng.
  assert.strictEqual(ham.workflowCurrencyRate('VND'), 1);

  const nhan = ham.workflowCurrencyConversionLabel(3600000, 'USD');
  assert.ok(/chưa có tỷ giá USD/.test(nhan), nhan);
  assert.ok(!/\$/.test(nhan), `không được hiện số quy đổi bịa: ${nhan}`);
  assert.ok(!/141/.test(nhan), `3.600.000 / 25.450 = 141,4 — con số cũ đã quay lại: ${nhan}`);

  const tien = ham.formatWorkflowCurrencyAmount(3600000, 'USD');
  assert.ok(/3\.600\.000 VNĐ/.test(tien), tien);
  assert.ok(/chưa có tỷ giá USD/.test(tien), tien);

  // Ô trống hoặc rác cũng phải cho ra null, không rơi về số cũ.
  oNhap['rate-usd'] = '';
  assert.strictEqual(ham.workflowCurrencyRate('USD'), null);
  oNhap['rate-usd'] = 'khong-phai-so';
  assert.strictEqual(ham.workflowCurrencyRate('USD'), null);
  oNhap['rate-usd'] = '0';
  assert.strictEqual(ham.workflowCurrencyRate('USD'), null, 'tỷ giá 0 là vô nghĩa');
  oNhap['rate-usd'] = '-5';
  assert.strictEqual(ham.workflowCurrencyRate('USD'), null, 'tỷ giá âm là vô nghĩa');
}

{
  // Có tỷ giá thật thì quy đổi bình thường.
  const { ham, oNhap } = nap();
  oNhap['rate-usd'] = '26,000';
  assert.strictEqual(ham.workflowCurrencyRate('USD'), 26000);
  const tien = ham.formatWorkflowCurrencyAmount(2600000, 'USD');
  assert.ok(/\$100/.test(tien), tien);
  assert.ok(!/chưa có tỷ giá/.test(tien), tien);
}

// --- 3. Nạp lịch sử tỷ giá phải XÓA ô khi máy chủ chưa có -------------

{
  const i = app.indexOf('function renderCurrencyRateHistory');
  assert.ok(i > 0);
  const than = app.slice(i, app.indexOf(NL + '}' + NL, i));
  assert.ok(/input\.value = item\.current_rate == null \? '' : format\(item\.current_rate\)/
    .test(than),
    'chưa lưu tỷ giá thì phải XÓA ô nhập, không để nguyên con số cũ nằm đó');
}

console.log('khong-bia-ty-gia: tất cả kiểm tra đã qua');
