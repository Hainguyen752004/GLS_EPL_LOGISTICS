/**
 * Hộp xác nhận / hộp nhập liệu TRONG ỨNG DỤNG — không dùng confirm/alert/prompt của trình duyệt.
 *
 * Chủ dự án bấm một nút, thấy hộp mặc định của Chrome tiêu đề "127.0.0.1:8001 says" và bảo làm
 * lại: *"đừng thông báo kiểu như trong ảnh nữa"*. Hộp gốc in địa chỉ máy chủ làm tiêu đề, dùng
 * font của hệ điều hành, không có gì của ứng dụng — anh demo bằng cách chiếu màn hình, nên nó
 * đọc như một lỗi kỹ thuật chứ không phải một bước nghiệp vụ.
 *
 * Bài này CHẠY THẬT hai hàm trong jsdom (không quét chữ), vì thứ dễ hỏng là hành vi: Promise
 * không giải, Esc không huỷ, hoặc `hoiNhapLieu` trả chuỗi rỗng lẫn với huỷ.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const { JSDOM } = require(path.join(ROOT, 'node_modules', 'jsdom'));
const ma = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8').split(String.fromCharCode(13)).join('');

/* ---- 1. KHÔNG còn hộp thoại gốc nào trong toàn bộ app.js ---- */
const conSot = ma.split(String.fromCharCode(10))
  .map((d, i) => [i + 1, d])
  .filter(([, d]) => /[^.a-zA-Z_](confirm|alert|prompt)\(/.test(d))
  .filter(([, d]) => !/^\s*(\*|\/\/)/.test(d))          // bỏ dòng chú thích
  .filter(([, d]) => !/hoiXacNhan|hoiNhapLieu|confirmDispatchWithoutCargo/.test(d));
assert.deepStrictEqual(conSot, [],
  'còn gọi confirm/alert/prompt gốc của trình duyệt ở: ' + conSot.map(x => 'dòng ' + x[0]).join(', '));

/* ---- 2. Chạy thật hai hộp ---- */
const dom = new JSDOM('<body></body>', { url: 'http://localhost/' });
const w = dom.window;
global.window = w; global.document = w.document;
const boc = ten => {
  const i = ma.indexOf('window.' + ten + ' = function');
  assert.ok(i > 0, 'không thấy ' + ten);
  return ma.slice(i, ma.indexOf(String.fromCharCode(10) + '};', i) + 3);
};
new w.Function('completionEscape',
  boc('hoiXacNhan') + String.fromCharCode(10) + boc('hoiNhapLieu'))(
  v => String(v == null ? '' : v).replace(/[<>&"']/g, c =>
    ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' }[c])));

const hop = () => w.document.getElementById('hop-xac-nhan');
const nut = k => hop().querySelector(`[data-hxn="${k}"]`);
const bam = el => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
const go = k => w.document.dispatchEvent(new w.KeyboardEvent('keydown', { key: k, bubbles: true }));

(async () => {
  /* 2a. hoiXacNhan: nội dung hiện đúng, không có tên miền/địa chỉ máy chủ nào. */
  let p = w.hoiXacNhan({ tieuDe: 'Xoá phương tiện', noiDung: ['Xoá xe 51C-123.45?', 'Không khôi phục được.'],
    nutOk: 'Xoá xe', nutHuy: 'Để lại', nguyHiem: true });
  const chu = hop().textContent;
  assert.ok(/Xoá phương tiện/.test(chu) && /51C-123\.45/.test(chu) && /Không khôi phục được/.test(chu));
  assert.ok(/Xoá xe/.test(nut('ok').textContent) && /Để lại/.test(nut('huy').textContent));
  assert.ok(hop().querySelector('.fiori-btn-danger'), 'việc không hoàn lại được phải tô nút đỏ');
  assert.ok(!/127\.0\.0\.1|localhost|says/.test(chu), 'lộ địa chỉ máy chủ như hộp gốc của trình duyệt');
  bam(nut('ok'));
  assert.strictEqual(await p, true);
  assert.strictEqual(hop(), null, 'bấm xong phải gỡ hộp khỏi trang');

  /* 2b. Nút huỷ, Esc, bấm ra nền → false. Ba đường thoát đều phải giải Promise. */
  for (const thoat of [() => bam(nut('huy')), () => go('Escape'), () => bam(hop())]) {
    p = w.hoiXacNhan({ tieuDe: 'X', noiDung: ['Y'] });
    thoat();
    assert.strictEqual(await p, false);
    assert.strictEqual(hop(), null);
  }

  /* 2c. Enter = đồng ý. */
  p = w.hoiXacNhan({ tieuDe: 'X', noiDung: ['Y'] });
  go('Enter');
  assert.strictEqual(await p, true);

  /* 2d. hoiNhapLieu: trả đúng chữ đã gõ, và cắt khoảng trắng thừa. */
  p = w.hoiNhapLieu({ tieuDe: 'Huỷ phiếu sửa chữa', nhan: 'Lý do huỷ', batBuoc: true });
  const o = hop().querySelector('input');
  assert.strictEqual(o.type, 'text');
  // Bắt buộc mà bỏ trống → KHÔNG đóng hộp, hiện dòng nhắc.
  bam(nut('ok'));
  assert.ok(hop(), 'ô bắt buộc bỏ trống mà hộp vẫn đóng');
  assert.strictEqual(hop().querySelector('.hxn-loi').hidden, false);
  o.value = '  xe đã sửa ở gara ngoài  ';
  o.dispatchEvent(new w.Event('input', { bubbles: true }));
  assert.strictEqual(hop().querySelector('.hxn-loi').hidden, true, 'gõ vào thì dòng nhắc phải tắt');
  bam(nut('ok'));
  assert.strictEqual(await p, 'xe đã sửa ở gara ngoài');

  /* 2e. HUỶ trả `null`, BỎ TRỐNG trả chuỗi rỗng — hai việc khác nhau, đúng như prompt cũ.
         Lẫn hai cái này là "để trống ngày bảo dưỡng" bị hiểu thành "thôi không làm nữa". */
  p = w.hoiNhapLieu({ tieuDe: 'Ngày bảo dưỡng', nhan: 'Ngày', kieu: 'date' });
  assert.strictEqual(hop().querySelector('input').type, 'date', 'phải dùng đúng kiểu ô, không bắt gõ tay YYYY-MM-DD');
  go('Escape');
  assert.strictEqual(await p, null);

  p = w.hoiNhapLieu({ tieuDe: 'Ngày bảo dưỡng', nhan: 'Ngày', kieu: 'date' });
  bam(nut('ok'));
  assert.strictEqual(await p, '', 'bỏ trống có chủ ý phải là chuỗi rỗng, không phải null');

  /* 2f. Giá trị sẵn có được đổ vào ô (đơn giá thực tế gợi ý theo dự toán). */
  p = w.hoiNhapLieu({ tieuDe: 'Đơn giá thực tế', nhan: 'Đơn giá', kieu: 'number', giaTri: '450000' });
  assert.strictEqual(hop().querySelector('input').value, '450000');
  go('Escape'); await p;

  console.log('hop-thoai-trong-ung-dung-khong-dung-cua-trinh-duyet: OK');
})().catch(e => { console.error(e); process.exit(1); });
