/**
 * Khối chi phí trên báo giá và trên đơn vận chuyển.
 *
 * Bản cũ sai tiền ở cả hai màn:
 *
 *   Báo giá  — chỉ có ba ô cố định (nhiên liệu / tài xế / cầu đường). Cước phí
 *              theo kg không có chỗ hiện và không hề được đọc, nên cấu phần lớn
 *              nhất biến mất khỏi giá. Phí bãi bị cộng vào ô "Phí cầu đường"
 *              nên ô đó nói sai tên con số. Lại nhân thêm một hệ số bịa
 *              `max_weight / 15000`, và có số cứng dự phòng nên chưa nạp được
 *              cấu hình vẫn hiện ra một con số trông rất chắc chắn.
 *
 *   Đơn hàng — đổi tuyến là đơn giá bị ghi đè bằng `số km × 6250 + 800000`. Hai
 *              con số không có nguồn nào, không dính gì đến công thức đã cấu
 *              hình, và nó xóa mất đơn giá đã chốt bên báo giá.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

/** Bỏ dòng chú thích, để phần phủ định không khớp vào chính lời giải thích. */
function stripComments(source) {
  return source.split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*') && !trimmed.startsWith('/*');
  }).join('\n');
}

const code = stripComments(app);

// --- 1. Không còn con số nào tự bịa ra ----------------------------------

// Chỉ xét đúng đường tính giá: hai hàm tính cước, hàm đổi tuyến của đơn, và
// module định giá. (Trình dựng công thức kéo thả cũ đã bị ẩn cũng còn hằng số
// mẫu; đó là mã chết cần dọn riêng, không phải việc của bài kiểm này.)
const pricingPaths = [
  code.slice(code.indexOf('window.autoCalculateMasterDataCost = function'),
    code.indexOf('let newRouteCounter')),
  stripComments(fs.readFileSync(path.join(ROOT, 'js', 'quotation-pricing.js'), 'utf8')),
].join(String.fromCharCode(10));
assert.ok(pricingPaths.length > 2000, 'phải tìm được đường tính giá');

['6250', '800000', '500000', '300000', '200000', '15000'].forEach(magic => {
  assert.ok(!pricingPaths.includes(magic), `không được còn số cứng ${magic} trong phần tính tiền`);
});
// Hệ số bịa `max_weight / 15000`: không có nguồn nào, và nó lấy tải trọng TỐI
// ĐA của loại xe chứ không phải khối lượng hàng thật.
assert.ok(!/max_weight \|\| 15000/.test(pricingPaths), 'không được còn hệ số bịa theo tải trọng tối đa');

assert.ok(!/const multiplier = /.test(pricingPaths), 'không được còn hệ số nhân bịa');

// Lưu cấu hình cũng không được bịa đơn giá khi ô trống.
//
// Bản trước rót sẵn 6.250 / 500.000 / 300.000 / 200.000 / 1.500 vào khi ô trống, nên
// bấm Lưu mà chưa nhập gì là cơ sở dữ liệu có một bộ đơn giá không ai đặt ra, mà
// màn hình lại báo "Đã cấu hình". Đúng phải là 0 — khi đó màn hình nói thật.
{
  const fn = code.slice(code.indexOf('window.saveCostFormula = async function'));
  const than = fn.slice(0, fn.indexOf(String.fromCharCode(10) + '};'));
  ['6,250', '500,000', '300,000', '200,000', '1,500'].forEach(bia => {
    assert.ok(!than.includes(bia), `không được bịa đơn giá ${bia} khi ô trống`);
  });
  assert.ok(/\|\| '0'/.test(than), 'ô trống phải lưu 0');
}

// --- 2. Mọi con số đi qua một chỗ duy nhất -----------------------------

assert.ok(/QuotationPricing\.price\(/.test(code), 'phải dùng module định giá dùng chung');
assert.strictEqual((code.match(/QuotationPricing\.price\(/g) || []).length, 1,
  'đúng một màn gọi: báo giá (form Đơn vận chuyển đã trục xuất cùng SO)');
assert.ok(html.includes('js/quotation-pricing.js?v='), 'phải nạp module định giá');
// Nạp SAU formula-model, vì nó dùng FormulaModel.
assert.ok(html.indexOf('formula-model.js') < html.indexOf('quotation-pricing.js'));

// --- 3. Báo giá: đủ đầu vào, đủ cấu phần -------------------------------
//
// KHOI BAO GIA CU (`#qtv2-khoi-cu`) DA BO HAN, nen cac o `qt-weight-kg /
// qt-cargo-type / qt-cost-breakdown / qt-cost-status` khong con trong HTML va
// cac phep khang dinh ve chung da bo khoi bai kiem nay. Duong tinh tien cua
// man bao gia DANG CHAY nam o may chu (`/api/quotations/price-preview`), va no
// co bo kiem rieng ben backend.
//
// Nhung `window.autoCalculateMasterDataCost` thi VAN CON, va van phai dung:
// man Cong thuc gia thanh goi no moi lan doi don gia
// (`oninput="autoCalculateMasterDataCost('qt')"`, va `cost-formula-builder.js`
// goi sau khi sua cong thuc). Phan duoi giu nguyen cac phep chot ve CACH TINH
// trong ham do — do la phan da tung sai tien, va no khong lien quan gi den
// viec o nhap nam o man nao.

{
  const fn = code.slice(code.indexOf('window.autoCalculateMasterDataCost = function'));
  assert.ok(/document\.getElementById\('qt-weight-kg'\)/.test(fn), 'phải đọc ô tải trọng (kg)');
  assert.ok(/\/ 1000/.test(fn), 'kg phải quy về tấn');
  assert.ok(/distance_km|eplRoutes/.test(fn), 'phải lấy số km từ tuyến đang chọn');
  assert.ok(/store: masterFormulaStore/.test(fn), 'phải dùng công thức đã cấu hình');
  // KHÔNG đọc năm ô md-cost-* nữa: chúng là công thức của loại xe MỞ GẦN NHẤT
  // trên màn Dữ liệu gốc, không phải loại xe đang chọn trên báo giá.
  assert.ok(!/md-cost-/.test(fn.slice(0, fn.indexOf('\n};'))),
    'không được đọc ô đơn giá của màn Dữ liệu gốc');
}

// Bảng chi phí vẽ động, không phải ba ô cố định viết cứng trong trang.
//
// Form Đơn vận chuyển đã trục xuất cùng SO (10/09); bảng cấu phần chi phí của
// màn báo giá mới do bao-gia-v2.js tự vẽ, nên ở đây chỉ chốt hàm vẽ còn tồn tại.
assert.ok(/function renderCostBreakdown\(/.test(code), 'phải còn hàm vẽ bảng cấu phần');

// --- 3b. Tiền VNĐ làm tròn về đồng, và không có dòng "bình quân/km" trên báo giá --
//
// 4.461.200 / 44 từng hiện ra "101.390,909 VNĐ/km": đồng không có đơn vị nhỏ hơn,
// và con số đó lẫn dấu chấm với dấu phẩy nên đọc rất dễ nhầm.
{
  const fn = code.slice(code.indexOf('function formatWorkflowCurrencyAmount'),
    code.indexOf('window.formatWorkflowCurrencyAmount'));
  assert.ok(/maximumFractionDigits: 0/.test(fn), 'tiền VNĐ phải làm tròn về đồng');
}
{
  // Dòng "/km" chỉ có nghĩa khi mẫu số là GIÁ THÀNH. Chia cả tổng (gồm cước theo
  // khối lượng) cho số km ra một con số không phải đơn giá của thứ gì cả — mà
  // đặt cạnh "xăng dầu 4.800 đ/km" thì trông như hệ thống hỏng.
  const M = require(path.join(ROOT, 'js', 'formula-model.js'));
  const terms = M.defaultTerms();
  const rates = { fuel: 4800, driver: 400000, toll: 150000, wh: 100000, rate: 1200 };
  terms.forEach(term => { term.rate = rates[term.key]; });
  const result = M.evaluate(terms, { km: 44, tonnes: 3 });
  assert.strictEqual(result.perKm, result.cost / 44, 'mẫu số phải là giá thành');
  assert.strictEqual(Math.round(result.perKm), 19573);
  // 101.391 đ/km là con số cũ (tổng chia km) — không được quay lại.
  assert.notStrictEqual(Math.round(result.perKm), 101391);

  const fn = code.slice(code.indexOf('function renderCostBreakdown'),
    code.indexOf('window.autoCalculateMasterDataCost = function'));
  assert.ok(/Giá thành mỗi km/.test(fn), 'dòng /km phải nói rõ là giá thành');
  assert.ok(!/Tổng cước báo giá<\/td>/.test(fn));
}

// --- 3c. Hai khối tách rời: tiền THU và tiền CHI ---------------------
//
// Bốn cấu phần xăng dầu / phụ cấp / BOT / phí bãi là tiền CHI RA, còn cước phí
// theo kg là tiền THU CỦA KHÁCH. Trước đây cộng cả năm vào một dòng "Tổng cước
// báo giá", nên con số 4.461.200 không phải giá thành (861.200) cũng không phải
// giá bán (3.600.000).
{
  const fn = code.slice(code.indexOf('function renderCostBreakdown'),
    code.indexOf('window.autoCalculateMasterDataCost = function'));
  assert.ok(/qt-cost-group-\$\{kind\}/.test(fn), 'phải chia nhóm theo loại cấu phần');
  assert.ok(/quote\.rows\.filter\(row => row\.kind === kind\)/.test(fn));
  assert.ok(/quote\.revenue/.test(fn) && /quote\.cost/.test(fn) && /quote\.profit/.test(fn));
  assert.ok(/marginPct/.test(fn), 'phải hiện tỉ lệ lợi nhuận');
}
// Ô giá bán nhận CưỚC THU KHÁCH, không phải tổng đại số của mọi cấu phần.
assert.ok(/setWorkflowTotalField\('qt-selling-price', quote\.revenue/.test(code));
// Và khi Lưu thì gửi ba con số tách rời vào đúng ba cột đã có của bảng quotations.
assert.ok(/total_cost: quote\.cost/.test(code), 'phải lưu giá thành');
assert.ok(/selling_price: quote \? quote\.revenue/.test(code), 'phải lưu cước thu khách');
// CỌ Ý không lưu tỉ lệ lợi nhuận: bảng quotations không có cột đó, và tỉ lệ suy ra
// được từ hai con số trên. Lưu thêm một cột thứ ba là tạo ra ba con số có thể trôi
// khỏi nhau.
// (`window.saveOracleQT` da bo cung khoi bao gia cu; man moi luu qua
// `bao-gia-v2.js`, va no khong gui `margin_pct` — bang `quotations` khong co
// cot do va ti le suy ra duoc tu hai con so kia.)
// CSS của hai nhóm phải có thật.
['.qt-cost-group-revenue', '.qt-cost-group-cost', '.qt-cost-subtotal', '.cf-kind-tag'].forEach(sel => {
  assert.ok(new RegExp(sel.replace('.', '\\.') + '[\\s,:{]').test(html), `thiếu CSS cho ${sel}`);
});
// Bon o an `qt-fuel / qt-driver / qt-toll / qt-selling-price` da bo cung khoi
// bao gia cu. `autoCalculateMasterDataCost` van ghi vao chung qua `write()`,
// va ham do da co san `if (!input) return` — nen mat vat chua khong nem loi.
// Phí bãi KHÔNG được gộp vào ô phí cầu đường.
assert.ok(!/tollCost \+ warehouseFee|toll \+ wh/.test(pricingPaths), 'không được gộp phí bãi vào phí cầu đường');

// Nhãn "Đã áp dụng công thức Master Data" trước đây luôn hiện, kể cả khi chưa
// tính được gì. Nay là chỗ báo trạng thái thật.
assert.ok(!html.includes('Đã áp dụng công thức Master Data'), 'không được còn nhãn khẳng định bừa');
assert.ok(/setCostStatusBadge\(/.test(code), 'phải còn chỗ báo trạng thái tính được / chưa tính được');

// --- 4. Thiếu đầu vào thì hiện lời nhắc, KHÔNG hiện số ------------------

{
  const fn = code.slice(code.indexOf('function renderCostBreakdown'));
  assert.ok(/if \(!quote\.ready\)/.test(fn), 'chưa tính được thì phải rẽ nhánh riêng');
  assert.ok(/qt-cost-blocked/.test(fn), 'phải có khối nói rõ thiếu gì');
  assert.ok(/quote\.blockers\.map/.test(fn), 'phải liệt kê từng thứ còn thiếu');
}
{
  // Bốn ô ẩn phải để TRỐNG khi chưa tính được. Ghi 0 vào đó là con số 0 chảy
  // tiếp sang đơn vận chuyển như thể đó là giá đã chốt.
  const fn = code.slice(code.indexOf('window.autoCalculateMasterDataCost = function'));
  assert.ok(/input\.value = ''/.test(fn));
  assert.ok(/delete input\.dataset\.vndValue/.test(fn));
}
// CSS của cả hai trạng thái phải có thật.
['.qt-cost-table', '.qt-cost-blocked', '.qt-cost-total', '.qt-cost-notes'].forEach(selector => {
  const rule = new RegExp(selector.replace('.', '\\.') + '[\\s,:{]');
  assert.ok(rule.test(html), `thiếu CSS cho ${selector}`);
});

// --- 8. Nhãn cấu phần do người dùng đặt không được thành mã ------------

{
  const fn = code.slice(code.indexOf('function renderCostBreakdown'),
    code.indexOf('window.autoCalculateMasterDataCost = function'));
  const labelUses = fn.match(/\$\{[^}]*row\.label[^}]*\}/g) || [];
  assert.ok(labelUses.length >= 1);
  labelUses.forEach(use => assert.ok(/escapeHtml\(/.test(use), `nhãn phải thoát ký tự: ${use}`));
  const messageUses = fn.match(/\$\{[^}]*item\.message[^}]*\}/g) || [];
  messageUses.forEach(use => assert.ok(/escapeHtml\(/.test(use), `lời nhắc phải thoát ký tự: ${use}`));
  assert.ok(!/eval\(|new Function/.test(fn));
}

console.log('cost-breakdown-ui: tất cả kiểm tra đã qua');
