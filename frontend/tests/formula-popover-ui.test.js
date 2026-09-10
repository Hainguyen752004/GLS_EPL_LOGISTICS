/**
 * Trình cấu hình công thức giá thành — bong bóng mở từ câu công thức.
 *
 * Ba vấn đề của bản cũ:
 *
 *   1. Ô nhập đơn giá và khung công thức là hai khối rời nhau, nên phải cuộn
 *      xuống nhập rồi cuộn lên xem tổng.
 *   2. Công thức viết CỨNG thành chuỗi "(Xăng dầu × số km) + Phụ cấp tài xế +
 *      ..." nên đổi cách tính là không được, mà sửa số xong câu đó vẫn đọc y
 *      như cũ.
 *   3. Không có tổng tiền, nên cấu hình xong không biết một chuyến thành bao
 *      nhiêu.
 *
 * Nay câu công thức là một cái nút: bấm vào mở bong bóng cấu hình động (thêm,
 * bớt, đổi dấu, đổi hệ số nhân), còn thẻ phía sau là chỗ đọc tổng.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

/** Bỏ dòng chú thích, để phần phủ định không khớp vào chính lời giải thích. */
const code = app.split('\n').filter(line => {
  const trimmed = line.trim();
  return !trimmed.startsWith('//') && !trimmed.startsWith('*') && !trimmed.startsWith('/*');
}).join('\n');

const editor = code.slice(code.indexOf('window.renderCostFormulaEditor = function'));
const POPOVER = code.slice(
  code.indexOf('function renderCostFormulaPopover'),
  code.indexOf('window.renderCostFormulaEditor = function'),
);
assert.ok(POPOVER.length > 500, 'phải tìm được hàm dựng bong bóng');
assert.ok(editor.length > 500, 'phải tìm được hàm vẽ trình cấu hình');

// --- 1. Câu công thức là một cái NÚT mở bong bóng -------------------------

assert.ok(/<button[^>]*class="cf-trigger"/.test(editor), 'câu công thức phải là một cái nút bấm được');
assert.ok(/id="cf-trigger"/.test(editor));
assert.ok(/onclick="toggleCostFormulaPopover\(\)"/.test(editor), 'bấm vào phải mở bong bóng');
// Trình đọc màn hình phải biết nút này mở ra một hộp thoại, và đang mở hay đóng.
assert.ok(/aria-haspopup="dialog"/.test(editor));
assert.ok(/aria-expanded="\$\{costFormulaPopoverOpen \? 'true' : 'false'\}"/.test(editor));
assert.ok(/class="cf-trigger-icon"/.test(editor), 'nút phải có icon để nhìn ra là bấm được');

// Bong bóng CHỈ dựng khi mở — không dựng sẵn rồi ẩn bằng CSS, vì như vậy
// các ô nhập vẫn nằm trong luồng tab dù người dùng không thấy gì.
assert.ok(/\$\{costFormulaPopoverOpen \? renderCostFormulaPopover\(/.test(editor));
assert.ok(/role="dialog"/.test(code));

// --- 2. Đóng được bằng Esc và bấm ra ngoài -------------------------------

assert.ok(/event\.key === 'Escape'[\s\S]{0,80}toggleCostFormulaPopover\(false\)/.test(code), 'Esc phải đóng');
assert.ok(/addEventListener\('mousedown'/.test(code), 'bấm ra ngoài phải đóng');
assert.ok(/closest\('#cf-pop'\)/.test(code), 'bấm bên trong bong bóng thì không được đóng');

// Trình lắng nghe gắn MỘT LẦN ở tầng document, không gắn lại mỗi lần vẽ: vẽ lại
// xảy ra mỗi lần gõ một chữ số, gắn trong đó là sau vài chục lần gõ có vài chục
// trình lắng nghe cùng chạy.
{
  const inRender = editor.slice(0, editor.indexOf('syncBuiltinCostInputs();'));
  assert.ok(!/addEventListener/.test(inRender), 'không được gắn trình lắng nghe trong hàm vẽ');
  assert.ok(!/document\.addEventListener/.test(POPOVER),
    'không được gắn trình lắng nghe khi dựng bong bóng');
}

// --- 3. Cấu hình ĐỘNG: đổi dấu, đổi hệ số, thêm và bớt cấu phần ----------

const pop = POPOVER;

assert.ok(/setCostTermField\(\$\{index\}, 'operator'/.test(pop), 'phải đổi được dấu + / −');
assert.ok(/setCostTermField\(\$\{index\}, 'factor'/.test(pop), 'phải đổi được hệ số nhân');
assert.ok(/setCostTermField\(\$\{index\}, 'rate'/.test(pop), 'phải nhập được đơn giá');
assert.ok(/setCostTermField\(\$\{index\}, 'label'/.test(pop), 'cấu phần tự thêm phải đặt được tên');
assert.ok(/onclick="addCostTerm\(\)"/.test(pop), 'phải thêm được cấu phần');
assert.ok(/onclick="removeCostTerm\(\$\{index\}\)"/.test(pop), 'phải xóa được cấu phần');
assert.ok(/moveCostTerm\(\$\{index\}, -1\)/.test(pop) && /moveCostTerm\(\$\{index\}, 1\)/.test(pop),
  'phải đổi được thứ tự hạng tử');

// Dấu và hệ số là DANH SÁCH CHỌN sinh từ mô hình, không viết cứng: thêm một hệ
// số mới trong formula-model.js là màn hình có ngay, không phải sửa hai chỗ.
assert.ok(/Object\.entries\(M\.OPERATORS\)/.test(pop));
assert.ok(/factorOptions\.map/.test(pop) && /Object\.entries\(M\.FACTORS\)/.test(pop));

// Năm cấu phần dựng sẵn không cho xóa, để công thức không rỗng ruột — nhưng
// phải NÓI RÕ vì sao nút mờ, thay vì để người dùng bấm mãi không được.
assert.ok(/\$\{row\.builtin \? 'disabled' : ''\}/.test(pop));
assert.ok(/đặt đơn giá 0 nếu không dùng/.test(pop), 'nút mờ phải giải thích cách bỏ cấu phần');

// --- 4. Câu công thức SINH TỪ hạng tử, không viết cứng -------------------

assert.ok(/M\.toText\(costFormulaTerms\.filter/.test(editor), 'câu công thức phải sinh từ hạng tử theo nhóm chi phí/cước');
assert.ok(!/\(Xăng dầu × số km\) \+ Phụ cấp/.test(code), 'không được còn công thức viết cứng trong app.js');
assert.ok(!/\(Xăng dầu × số km\) \+ Phụ cấp/.test(html), 'không được còn công thức viết cứng trong index.html');

// --- 5. Tổng tiền hiện trên THẺ, không nằm sau bong bóng -----------------

// Ba con so tach roi, khong phai mot tong: gia thanh (tien CHI ra), cuoc thu
// khach (tien THU ve), va loi nhuan. Cong ca nam cau phan vao mot so thi ket
// qua khong phai gia thanh cung khong phai gia ban.
assert.ok(/id="cf-cost"/.test(editor), 'phải có giá thành');
assert.ok(/id="cf-revenue"/.test(editor), 'phải có cước thu khách');
assert.ok(/id="cf-total"/.test(editor), 'phải có lợi nhuận');
assert.ok(/id="cf-margin"/.test(editor), 'phải có tỉ lệ lợi nhuận');
assert.ok(/id="cf-perkm"/.test(editor));
// Ba con số nay nằm trong khung "Chuyến mẫu để xem trước" ở cột phải, nên ngữ
// cảnh "chuyến mẫu" do ĐẦU KHUNG nói một lần, thay vì nhắc lại trong từng nhãn.
// Điều phải giữ là: người đọc biết đây là chuyến mẫu, không phải một báo giá
// thật — nên kiểm cả hai phần chứ không chỉ kiểm một chuỗi nhãn.
assert.ok(/Chuyến mẫu để xem trước/.test(editor),
  'khung kết quả phải nói rõ đây là chuyến mẫu');
assert.ok(/không ảnh hưởng báo giá/i.test(editor),
  'phải nói rõ đổi chuyến mẫu không ảnh hưởng báo giá thật');
assert.ok(/>Giá thành\b/.test(editor), 'phải có nhãn giá thành');
assert.ok(/Cước thu khách/.test(editor));
// Và cặp km/tấn phải sửa được NGAY trên thẻ, không phải chỉ trong hộp thoại
// sửa công thức: muốn thử "cùng tuyến này nhưng 30 tấn" thì không nên bắt người
// dùng mở một hộp thoại nghe như sắp đổi cấu hình.
{
  const summary = editor.slice(editor.indexOf('<div id="cf-issues">'),
    editor.indexOf('renderCostFormulaPopover(result, money)'));
  assert.ok(/setCostSampleTrip\('km'/.test(summary),
    'ô km của chuyến mẫu phải nằm trên thẻ, ngoài hộp thoại');
  assert.ok(/setCostSampleTrip\('tonnes'/.test(summary),
    'ô tấn của chuyến mẫu phải nằm trên thẻ, ngoài hộp thoại');
}
assert.ok(/Giá thành mỗi km/.test(editor), 'dòng /km phải nói rõ mẫu số là giá thành');
assert.ok(!/Tổng chi phí chuyến mẫu/.test(editor), 'không được còn một "tổng" gộp');
// Ba con so phai nằm NGOÀI hộp thoại: đóng hộp thoại lại vẫn phải đọc được.
{
  const summary = editor.slice(editor.indexOf('<div id="cf-issues">'));
  assert.ok(/id="cf-cost"/.test(summary) && /id="cf-revenue"/.test(summary),
    'ba con số phải ở phần thẻ');
}
// Hộp thoại có cột "Loại" để khai từng cấu phần là chi phí hay giá bán.
assert.ok(/setCostTermField\(\$\{index\}, 'kind'/.test(pop), 'phải đổi được loại cấu phần');
assert.ok(/Object\.entries\(M\.KINDS\)/.test(pop), 'danh sách loại sinh từ mô hình');
assert.ok(/id="cf-pcost"/.test(pop) && /id="cf-prevenue"/.test(pop)
  && /id="cf-pprofit"/.test(pop) && /id="cf-pmargin"/.test(pop),
  'chân hộp thoại phải có cả ba con số');

// Lỗi công thức cũng phải ở trên thẻ. Nếu chỉ nằm trong bong bóng thì đóng lại
// là lỗi biến mất khỏi mắt, rồi báo giá vẫn chạy bằng công thức sai.
assert.ok(/<div id="cf-issues">/.test(editor), 'khối lỗi phải nằm trên thẻ');
assert.ok(!/cf-issues/.test(POPOVER), 'khối lỗi không được nằm trong hộp thoại');
assert.ok(/problems\(costFormulaTerms\)/.test(code), 'phải hỏi mô hình về công thức tự mâu thuẫn');
assert.ok(/issue\.level === 'error'/.test(code));

// --- 6. Sửa trong bong bóng thì thẻ phía sau đổi theo NGAY ---------------
//
// Hai chỗ hiển thị cùng một cấu phần; lệch nhau là người dùng không biết tin cái nào.
{
  const totals = code.slice(code.indexOf('function updateCostFormulaTotals'), code.indexOf('function renderCostFormulaIssues'));
  ['cf-sum-amount-', 'cf-sum-rate-', 'cf-sum-mul-', 'cf-sum-label-', 'cf-sum-sign-', 'cf-sum-unit-',
    'cf-sum-kind-', 'cf-amount-', 'cf-mul-', 'cf-cost', 'cf-revenue', 'cf-total', 'cf-margin',
    'cf-pcost', 'cf-prevenue', 'cf-pprofit', 'cf-pmargin', 'cf-perkm', 'cf-text'].forEach(id => {
    assert.ok(totals.includes(id), `sửa xong phải cập nhật ${id}`);
  });
  // Chỉ cập nhật con số, KHÔNG dựng lại bảng: dựng lại là mất con trỏ giữa lúc gõ.
  assert.ok(!/renderCostFormulaEditor\(\)/.test(totals), 'không được vẽ lại cả bảng khi đang gõ');
  assert.ok(!/innerHTML/.test(totals.replace(/issues\.innerHTML[^\n]*/g, '')), 'chỉ đổi chữ, không đổi cấu trúc');
}

// --- 7. Hạng tử được LƯU và nạp lại ------------------------------------

assert.ok(/terms: costFormulaTerms/.test(code), 'lưu cấu hình phải gửi kèm hạng tử');
assert.ok(/FormulaModel\.normalize\(stored\.terms\)/.test(code), 'nạp lại phải đọc hạng tử đã lưu');
// Chưa từng lưu hạng tử thì dựng từ năm đơn giá cũ, để không mất cấu hình cũ.
assert.ok(/FormulaModel\.defaultTerms\(\)/.test(code));

// Năm ô `md-cost-*` vẫn phải còn trong trang: nhiều chỗ khác đọc trực tiếp chúng.
['md-cost-fuel-rate', 'md-cost-driver-allowance', 'md-cost-toll-fee',
  'md-cost-warehouse-fee', 'md-cost-freight-rate'].forEach(id => {
  assert.ok(html.includes(`id="${id}"`), `${id} phải còn tồn tại để các chỗ khác đọc`);
  assert.ok(code.includes(id), `${id} phải được ghi đồng bộ`);
});
assert.ok(/syncBuiltinCostInputs\(\)/.test(editor), 'vẽ xong phải ghi ngược vào năm ô cũ');

// --- 8. CSS của bong bóng phải có thật -----------------------------------

['.cf-trigger', '.cf-pop', '.cf-pop-head', '.cf-pop-close', '.cf-pop-body', '.cf-pop-foot',
  '.cf-add', '.cf-del', '.cf-issues', '.cf-row', '.cf-row-top', '.cf-row-calc',
  '.cf-amount', '.cf-move', '.cf-kind', '.cf-sum-item'].forEach(selector => {
  // Bat cả `.cf-del { }` lan `.cf-row-actions .cf-del:hover`.
  const rule = new RegExp(selector.replace('.', '\\.') + '[\\s,:{]');
  assert.ok(rule.test(html), `thiếu CSS cho ${selector} — bong bóng sẽ hiện ra không có hình dạng`);
});
// Hộp thoại phải đặt `fixed` giữa màn hình.
//
// Bản đầu neo `position:absolute` vào câu công thức. Sai: khung cha có cắt nội
// dung, nên hộp thoại bị cắt mất mép trái — cột "Dấu" và nửa tiêu đề nằm ngoài
// vùng thấy được. Neo tuyệt đối chỉ an toàn khi mọi tổ tiên của nó đều không
// cắt, mà điều đó không kiểm được từ chỗ vẽ.
assert.ok(/\.cf-pop-backdrop \{[^}]*position:fixed/.test(html));
assert.ok(/\.cf-pop \{[^}]*max-height/.test(html), 'hộp thoại phải có trần chiều cao');
assert.ok(!/\.cf-pop \{[^}]*position:absolute/.test(html), 'không được neo tuyệt đối nữa');
// Và phải được vẽ NGOÀI khối đầu thẻ, không thì lại bị chính khung đó cắt.
assert.ok(/class="cf-pop-backdrop"/.test(POPOVER));
assert.ok(editor.indexOf('renderCostFormulaPopover(') > editor.indexOf('class="cf-note"'),
  'hộp thoại phải nằm sau cùng trong chuỗi vẽ');
// Cao quá thì cuộn DỌC trong thân hộp thoại.
assert.ok(/\.cf-pop-body \{[^}]*overflow-y:auto/.test(html));
// Và TUYỆT ĐỐI không cuộn ngang: chính việc đó làm mất cột "Thành tiền" và cột
// nút ở bản bảy cột trước đó.
assert.ok(/\.cf-pop-body \{[^}]*overflow-x:hidden/.test(html));
// Dạng thẻ, không phải bảng bảy cột.
assert.ok(!/cf-pop-table/.test(html), 'không được còn CSS của bảng cũ');
assert.ok(!/cf-op-col/.test(html));
assert.ok(!/cf-row-actions/.test(html));
// Thành tiền tự tách sang phải và không bao giờ bị cắt.
assert.ok(/\.cf-amount \{[^}]*margin-left:auto/.test(html));
assert.ok(/\.cf-amount \{[^}]*white-space:nowrap/.test(html));
// Màn hẹp thì các ô xuống dòng, không tràn ra ngoài.
assert.ok(/\.cf-row-calc \{[^}]*flex-wrap:wrap/.test(html));
assert.ok(/\.cf-row-top \{[^}]*flex-wrap:wrap/.test(html));

// Bàn phím phải thấy được mình đang ở đâu.
assert.ok(/\.cf-trigger:focus-visible/.test(html));

// --- 9. Bảng đơn giá cũ đã ẩn, không còn hai bảng chồng nhau ------------

assert.ok(/display:none; background: #ffffff/.test(html), 'bảng đơn giá cũ phải được ẩn');

// --- 10. Nhãn người dùng đặt không được thành mã ------------------------

assert.ok(!/eval\(|new Function/.test(pop + editor), 'không được có đường chạy chuỗi thành mã');
{
  // Mọi chỗ chèn nhãn vào HTML đều phải qua escapeHtml.
  const labelUses = (pop + editor).match(/\$\{[^}]*row\.label[^}]*\}/g) || [];
  assert.ok(labelUses.length >= 4);
  labelUses.forEach(use => {
    assert.ok(/escapeHtml\(/.test(use), `nhãn phải được thoát ký tự: ${use}`);
  });
}

console.log('formula-popover-ui: tất cả kiểm tra đã qua');
