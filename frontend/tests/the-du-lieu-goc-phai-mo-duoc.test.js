/**
 * MỞ TỪNG THẺ CỦA MÀN DỮ LIỆU GỐC VÀ ĐÒI NÓ HIỆN NỘI DUNG.
 *
 * LỖI ĐÃ XẢY RA THẬT, và nó làm CHÍN trong mười hai thẻ trắng trơn.
 *
 * `#md-tab-formulas` thiếu một thẻ `</div>`. Bộ phân tích HTML tự vá cây theo
 * cách của nó, nên chín thẻ sau đó — `md-tab-veh-types`, `md-tab-vehicles`,
 * `md-tab-drivers`, `md-tab-currencies`, `md-tab-customers`,
 * `md-tab-tax-codes`, `md-tab-accounting-periods`, `md-tab-carriers`,
 * `md-tab-account-mappings` — có CHA THẬT là `#md-tab-formulas` thay vì
 * `#master-data-core-panel`.
 *
 * Hậu quả: `switchMasterDataTab` đặt `display:block` cho thẻ được chọn, nhưng
 * `#md-tab-formulas` lúc đó đang `display:none`. Một tổ tiên bị ẩn thì con cháu
 * không hiện được bất kể `display` của chúng là gì. Người dùng bấm thẻ 3 và
 * thấy đúng đầu trang rồi trắng hết phần dưới.
 *
 * VÌ SAO KHÔNG BÀI KIỂM NÀO CŨ BẮT ĐƯỢC:
 *
 *   · Trình duyệt KHÔNG báo lỗi. HTML thiếu thẻ đóng không sinh ngoại lệ nào,
 *     không có gì trong console. Mọi bài kiểm đọc-văn-bản vẫn xanh vì chữ vẫn
 *     nằm trong tệp.
 *   · `moi-man-phai-hien-noi-dung` mở 13 MÀN, nhưng màn Dữ liệu gốc chỉ được
 *     kiểm ở thẻ đang mở sẵn (Tuyến đường) — chín thẻ hỏng nằm sau nó.
 *   · Đếm dấu ngoặc bằng regex thì không đáng tin: `<div` xuất hiện cả trong
 *     chuỗi JavaScript và trong chú thích.
 *
 * Nên bài này đo bằng CÂY DOM THẬT, và đo hai điều khác nhau:
 *
 *   1. Mọi thẻ phải là con của CÙNG MỘT khung. Đây là phép kiểm bắt đúng
 *      nguyên nhân, và lời báo của nó chỉ thẳng vào thẻ đang "ăn" các thẻ khác.
 *   2. Mở từng thẻ thì nội dung của nó phải THẬT SỰ hiện. Đây là phép kiểm bắt
 *      đúng hậu quả — kể cả khi nguyên nhân lần sau là một thứ khác (một
 *      `hidden` đặt sai, một luật CSS mới, một khung bọc thêm vào).
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

let JSDOM;
let VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.log('the-du-lieu-goc-phai-mo-duoc: BỎ QUA (chưa cài jsdom)');
  process.exit(0);
}

/** Mười hai thẻ của màn Dữ liệu gốc, theo đúng thứ tự trên dải nút. */
const CAC_THE = [
  'md-tab-setup', 'md-tab-routes', 'md-tab-formulas', 'md-tab-veh-types',
  'md-tab-vehicles', 'md-tab-drivers', 'md-tab-currencies', 'md-tab-customers',
  'md-tab-tax-codes', 'md-tab-accounting-periods', 'md-tab-carriers',
  'md-tab-account-mappings',
];

const loi = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  const chu = String((e && e.message) || e);
  if (/Not implemented: Window/.test(chu)) return;
  loi.push(chu.split('\n')[0]);
});

const than = html
  .replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
  .replace(/<link\b[^>]*>/g, '');
const tepJs = [...html.matchAll(/src="\/static\/js\/([a-z0-9\-.]+\.js)/g)].map(m => m[1]);

const dom = new JSDOM(than, {
  url: 'http://127.0.0.1/', runScripts: 'dangerously', virtualConsole: vc,
});
const w = dom.window;
const d = w.document;
w.fetch = (u) => Promise.resolve({
  ok: true,
  status: 200,
  json: () => Promise.resolve(String(u).includes('lang.json')
    ? JSON.parse(fs.readFileSync(path.join(ROOT, 'js/lang.json'), 'utf8'))
    : { items: [], total: 0, data: { items: [] } }),
  text: () => Promise.resolve('{}'),
});
w.alert = () => {};
w.confirm = () => true;
w.prompt = () => '';
tepJs.forEach(ten => {
  const s = d.createElement('script');
  try {
    s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
  } catch (e) {
    return;
  }
  d.body.appendChild(s);
});

/** Phần tử này có tổ tiên nào đang che nó không — trả về tổ tiên đó. */
function toTienChe(el) {
  for (let x = el.parentElement; x && x !== d.body; x = x.parentElement) {
    if (x.hasAttribute('hidden')) return x;
    const st = x.getAttribute('style') || '';
    if (/display\s*:\s*none/i.test(st)) return x;
  }
  return null;
}

setTimeout(() => {
  // --- 1. NGUYÊN NHÂN: mọi thẻ phải cùng một cha -------------------------
  const thieu = CAC_THE.filter(id => !d.getElementById(id));
  assert.deepStrictEqual(thieu, [],
    'thiếu thẻ trong index.html: ' + thieu.join(', '));

  const chuan = d.getElementById(CAC_THE[0]).parentElement;
  assert.ok(chuan && chuan.id, 'thẻ đầu tiên phải nằm trong một khung có id');

  const lech = CAC_THE
    .map(id => [id, d.getElementById(id).parentElement])
    .filter(([, cha]) => cha !== chuan)
    .map(([id, cha]) => `${id} nằm trong #${(cha && cha.id) || '?'}`);
  assert.deepStrictEqual(lech, [],
    'thẻ Dữ liệu gốc bị lồng sai chỗ — gần như chắc chắn là THIẾU MỘT `</div>` '
    + 'ở thẻ đứng trước. Đếm lại cân bằng <div>/</div> trong vùng đó. Chi tiết: '
    + lech.join(' · '));

  // --- 2. HẬU QUẢ: mở từng thẻ thì nội dung phải hiện --------------------
  assert.strictEqual(typeof w.switchMasterDataTab, 'function',
    'không có switchMasterDataTab — màn Dữ liệu gốc không đổi thẻ được');

  const khongHien = [];
  CAC_THE.forEach(id => {
    w.switchMasterDataTab(id);
    const el = d.getElementById(id);
    const st = el.getAttribute('style') || '';
    if (/display\s*:\s*none/i.test(st)) {
      khongHien.push(`${id} (chính nó vẫn display:none sau khi mở)`);
      return;
    }
    const che = toTienChe(el);
    if (che) {
      khongHien.push(`${id} (bị #${che.id || che.className} che)`);
    }
  });
  assert.deepStrictEqual(khongHien, [],
    'mở thẻ ra mà nội dung không hiện được: ' + khongHien.join(' · '));

  // --- 3. Và không thẻ nào được "ăn" nút của thẻ khác --------------------
  //
  // Phép kiểm này bắt cùng một lỗi từ một góc khác, và nó là góc dễ đọc nhất:
  // lúc lồng sai, `#md-tab-formulas` đếm được 55 nút vì nó chứa cả nút của
  // chín thẻ kia; sau khi sửa nó còn 7 nút.
  const tongNut = CAC_THE.reduce((n, id) => n + d.getElementById(id).querySelectorAll('button').length, 0);
  const nutTrongKhung = chuan.querySelectorAll('button').length;
  assert.ok(tongNut <= nutTrongKhung,
    `tổng nút của các thẻ (${tongNut}) lớn hơn số nút trong khung bọc `
    + `(${nutTrongKhung}) — nghĩa là có thẻ đang đếm trùng nút của thẻ khác`);

  assert.deepStrictEqual(loi.slice(0, 3), [],
    'có lỗi JS khi mở các thẻ: ' + loi.slice(0, 3).join(' | '));

  console.log('the-du-lieu-goc-phai-mo-duoc: %d thẻ đều cùng cha và đều mở được',
    CAC_THE.length);
  process.exit(0);
}, 1500);
