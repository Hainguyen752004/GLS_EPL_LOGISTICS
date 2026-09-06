/**
 * Bắt lỗi rồi chỉ `console.error` là NÓI SAI với người dùng, không phải
 * "mất một tính năng".
 *
 * `loadSalesOrders` hỏng thì `crmSalesOrders` GIỮ NGUYÊN giá trị cũ và không
 * vẽ lại gì — màn hình vẫn hiện danh sách của lần nạp trước như thể đó là dữ
 * liệu hiện tại. Còn khi chưa nạp được lần nào thì mảng rỗng, và hàm vẽ hiện
 * đúng dòng "Chưa có dữ liệu": người dùng đọc thành "công ty chưa có đơn
 * nào", trong khi sự thật là máy chủ không trả lời.
 *
 * Toàn tệp từng có 18 chỗ như vậy.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
// app.js xuống dòng kiểu CRLF. Không bỏ ký tự CR đi thì mọi phép tìm theo
// hình dạng dòng (`\n};`, `\n}`) đều KHÔNG khớp, và bài kiểm lặng lẽ cắt
// nhầm đoạn rồi báo sai — chứ không báo là nó không tìm thấy gì.
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const dong = app.split(NL);

// --- 1. Không còn catch nào chỉ ghi console -----------------------------
//
// Trừ đúng hai chỗ đã ghi rõ lý do trong chú thích ngay tại đó.
const MIEN = ['translateAllDOMTexts', 'calculateRealDistance'];

const conNuot = [];
for (let i = 0; i < dong.length; i += 1) {
  if (!/^\s*\}\s*catch\s*\(\s*\w+\s*\)\s*\{\s*$/.test(dong[i])) continue;
  const than = [];
  for (let k = i + 1; k < Math.min(i + 8, dong.length); k += 1) {
    const t = dong[k].trim();
    if (t.startsWith('}')) break;
    if (t.startsWith('//')) continue;
    than.push(t);
  }
  if (!than.length || !than.every(t => t.startsWith('console.'))) continue;

  let ten = '?';
  for (let j = i; j >= Math.max(0, i - 400); j -= 1) {
    const m = dong[j].match(/(?:window\.)?(?:async )?function\s+(\w+)|window\.(\w+)\s*=\s*(?:async\s*)?function/);
    if (m) { ten = m[1] || m[2]; break; }
  }
  if (MIEN.includes(ten)) continue;
  conNuot.push(`${ten} (dòng ${i + 1})`);
}
assert.deepStrictEqual(conNuot, [],
  'catch chỉ ghi console — người dùng không biết dữ liệu trên màn là bản cũ');

// --- 2. Hàm gom lời báo phải tồn tại và phải GOM ------------------------
//
// Vì sao phải gom: `showToast` XÓA toast cũ trước khi hiện toast mới. Mở màn
// hình là hàng chục hàm nạp chạy song song, nên mất mạng sẽ bắn ra hàng chục
// lời báo giống nhau và chỉ cái CUỐI CÙNG ở lại — thường là cái ít quan
// trọng nhất.
assert.ok(/function baoNapThatBai\(viec, loi\)/.test(app), 'phải có hàm baoNapThatBai');
{
  const i = app.indexOf('function baoNapThatBai(viec, loi)');
  const than = app.slice(i, app.indexOf(NL + '}', i));
  assert.ok(/setTimeout/.test(than) && /clearTimeout/.test(than),
    'phải gom các lời báo lại, không bắn từng cái');
  assert.ok(/console\.error/.test(than), 'vẫn phải ghi console cho người sửa lỗi');
  assert.ok(/showToast/.test(than), 'và phải nói cho người dùng biết');
  assert.ok(/bản cũ|thiếu/.test(than),
    'phải cảnh báo số liệu đang hiện có thể sai, không chỉ nói "lỗi"');
}
{
  // `showToast` phải thật sự xóa toast cũ — đó là tiền đề của việc gom.
  const i = app.indexOf('window.showToast = function');
  const than = app.slice(i, i + 400);
  assert.ok(/data-app-toast.*forEach\(el => el\.remove\(\)\)/.test(than),
    'nếu showToast không còn xóa toast cũ thì hãy xem lại việc gom ở baoNapThatBai');
}

// --- 2b. Và gom THẬT: chạy thử chứ không dò chữ -------------------------

async function thuGomLoiBao() {
  const i = app.indexOf('const dsNapThatBai = new Set();');
  const j = app.indexOf('window.baoNapThatBai = baoNapThatBai;');
  assert.ok(i > 0 && j > i);
  const goi = [];
  const dung = new Function('showToast', 'console',
    app.slice(i, j) + NL + 'return baoNapThatBai;');
  const baoNapThatBai = dung(m => goi.push(m), { error() {} });

  ['phương tiện', 'đơn hàng', 'sự cố', 'công thức giá thành', 'tỷ giá']
    .forEach(x => baoNapThatBai(x, new Error('thử')));

  // Chưa hết thời gian gom thì chưa được bắn.
  assert.strictEqual(goi.length, 0, 'không được bắn ngay, phải đợi gom');

  return new Promise(resolve => setTimeout(() => {
    assert.strictEqual(goi.length, 1, `5 lỗi phải gộp thành 1 lời báo, thấy ${goi.length}`);
    assert.ok(goi[0].includes('phương tiện'), 'phải kể tên vài mục hỏng');
    assert.ok(/2 mục khác/.test(goi[0]), 'quá 3 mục thì phải tóm tắt phần còn lại');
    resolve();
  }, 700));
}

// --- 3. Các hàm nạp chính phải dùng nó ---------------------------------
[
  ['loadFioriVehicles', 'phương tiện'],
  ['loadSalesOrders', 'đơn hàng vận chuyển'],
  ['loadDeliveryOrders', 'vận hành'],
  ['loadIncidents', 'sự cố'],
  ['loadCostFormulasFromBackend', 'công thức giá thành'],
  ['syncAllDynamicDropdowns', 'ô chọn'],
  ['hydrateFinanceState', 'tài chính'],
].forEach(([ten, dauHieu]) => {
  // Neo vào chỗ ĐỊNH NGHĨA, không phải chỗ gọi. `app.indexOf(ten)` bắt đúng
  // chỗ gọi đầu tiên trong tệp, và cắt 4000 ký tự từ đó ra là đọc nhầm thân
  // của một hàm hoàn toàn khác.
  const dang = [
    `async function ${ten}(`,
    `function ${ten}(`,
    `window.${ten} = async function`,
    `window.${ten} = function`,
  ];
  const viTri = dang.map(d => app.indexOf(d)).filter(x => x >= 0);
  assert.ok(viTri.length, `không thấy định nghĩa của ${ten}`);
  const dau = Math.min(...viTri);
  // Cắt tới HẾT hàm, không lấy một cửa sổ ký tự cố định:
  // `syncAllDynamicDropdowns` dài hơn 4000 ký tự nên `catch` của nó nằm ngoài
  // cửa sổ, và bài kiểm báo sai là "không có báo lỗi".
  const ketA = app.indexOf(NL + '};' + NL, dau);
  const ketB = app.indexOf(NL + '}' + NL, dau);
  const ket = Math.min(ketA < 0 ? Infinity : ketA, ketB < 0 ? Infinity : ketB);
  const than = app.slice(dau, ket === Infinity ? dau + 4000 : ket);
  assert.ok(than.includes('baoNapThatBai'), `${ten} phải báo khi nạp hỏng`);
  assert.ok(than.includes(dauHieu), `lời báo của ${ten} phải nói rõ nạp hỏng cái gì`);
});

// --- 4. Lưu phương tiện: hỏng thì phải nói, và giữ form mở --------------
{
  const i = app.indexOf('window.saveFioriVehicle = async function');
  assert.ok(i > 0, 'không thấy định nghĩa saveFioriVehicle');
  const than = app.slice(i, app.indexOf(NL + '}', i));
  assert.ok(/baoLoiMayChu\(res, 'Lưu phương tiện'\)/.test(than),
    'máy chủ từ chối thì phải nói rõ lý do');
  assert.ok(/baoMatKetNoi\('Lưu phương tiện'/.test(than),
    'mất mạng thì phải nói CHƯA lưu, không được im');
  // Thất bại thì KHÔNG được đóng form — đóng đi là người dùng mất hết những
  // gì vừa gõ.
  const truoc = than.slice(0, than.indexOf('closeFioriVehicleForm'));
  assert.ok(/if \(!res\.ok\) return/.test(truoc),
    'phải thoát trước khi đóng form');
}

// --- 5. Đường tạo báo giá chết đã gỡ ------------------------------------
//
// `legacySaveOracleQT` tạo báo giá bằng một đường RIÊNG mà không ai gọi tới,
// và nó không có nhánh `else`: máy chủ từ chối thì KHÔNG CÓ GÌ xảy ra.
assert.ok(!app.includes('legacySaveOracleQT = async function'));
assert.ok(/window\.saveOracleQT\s*=/.test(app), 'đường tạo báo giá thật phải còn');

thuGomLoiBao().then(() => {
  console.log('khong-nuot-loi: tất cả kiểm tra đã qua');
}).catch(err => {
  console.error(err);
  process.exit(1);
});
