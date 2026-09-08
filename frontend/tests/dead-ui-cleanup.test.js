/**
 * Bốn nhóm giao diện chết hoặc nói dối, đã dọn.
 *
 *   1. TÁM HÀM VẼ BẢNG CHẾT HẲN. `renderQuotations`, `renderVehicles`, … tìm
 *      `table-quotations`, `table-vehicles`, … — không một id nào trong tám id
 *      đó tồn tại trong index.html, nên cả tám thoát ngay ở dòng
 *      `if (!tbody) return;`. `confirmAICheckin` gọi một trong số đó để "làm
 *      mới màn hình" sau khi mở barrier, nên thông báo "Đã mở barrier" hiện ra
 *      mà không có gì trên màn đổi cả.
 *
 *   2. THẺ "CC FORM" TRÊN DASHBOARD. 30 ô nhập không ai đọc, và 8 nút Lưu ghi
 *      cơ sở dữ liệu THẬT nhưng ghi dữ liệu của MỘT FORM KHÁC ở tab khác.
 *
 *   3. NÚT "CHỌN FILE HỢP ĐỒNG". Chọn xong toast báo "đã đính kèm", mà
 *      `so-contract-file` không xuất hiện trong bất kỳ tệp JS nào — không
 *      upload, không FormData. Tệp bị bỏ ngay tại đó.
 *
 *   4. `innerHTML +=` TRONG VÒNG LẶP. Mỗi vòng tuần tự hóa lại toàn bộ nội
 *      dung hiện có rồi phân tích lại — O(n²). Với 500 xe là dựng lại cả bảng
 *      500 lần.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function stripComments(source) {
  return source.replace(/\r\n/g, '\n').split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*')
      && !trimmed.startsWith('/*') && !trimmed.startsWith('*/');
  }).join('\n');
}
const code = stripComments(app);

// --- 1. Tám hàm vẽ bảng chết đã được gỡ --------------------------------

['renderQuotations', 'renderSalesOrders', 'renderDashboardDeliveryOrders',
  'renderDashboardRoutes', 'renderDispatches', 'renderIncidents',
  'renderInvoices', 'renderVehicles'].forEach(ten => {
  assert.ok(!new RegExp(`function ${ten}\\s*\\(`).test(code),
    `${ten} là mã chết — tbody của nó không tồn tại trong index.html`);
  assert.ok(!new RegExp(`(?<![\\w.])${ten}\\(\\)`).test(code),
    `còn chỗ gọi ${ten}()`);
});
// Và tám id tbody đó vẫn không tồn tại — nếu ai thêm lại thì phải xem lại
// bài kiểm này, vì lúc đó chúng không còn là mã chết nữa.
['table-quotations', 'table-sales-orders', 'table-delivery-orders',
  'table-dispatches', 'table-routes', 'table-incidents',
  'table-invoices', 'table-vehicles'].forEach(id => {
  assert.ok(!html.includes(`id="${id}"`), `${id} đã xuất hiện — hãy xem lại bài kiểm này`);
});

// --- 1b. `postInvoice` — mã chết NGUY HIỂM, đã gỡ hẳn -------------------
//
// Hàm này ghi một hoá đơn thật cùng bút toán sổ cái qua `POST /api/invoices/post`
// và tự chọn lệnh giao hàng bằng "lệnh đã giao ĐẦU TIÊN tìm thấy". Chỗ gọi duy
// nhất là nút "Post" trên thẻ minh hoạ ở Bảng điều khiển; nút đó đã bỏ, nên
// từ đó không ai gọi được nó nữa — nhưng nó vẫn nằm đó, chờ một nút mới.
//
// Bỏ nó KHÔNG mất tính năng: hoá đơn được phát hành ngay trong bước hoàn tất
// giao hàng (`delivery_completion_service` gọi `post_ar_invoice` cùng giao dịch
// với POD và giá cuối). Đó là lý do bộ dữ liệu demo có hoá đơn mà không ai bấm
// "Post" lần nào.
{
  assert.ok(!/window\.postInvoice\s*=/.test(code),
    'window.postInvoice đã sống lại — hàm này ghi hoá đơn thật cho một lệnh '
    + 'giao hàng nó TỰ CHỌN, và không màn nào cần nó vì bước hoàn tất giao '
    + 'hàng đã phát hành hoá đơn trong cùng giao dịch');
  assert.ok(!/(?<![\w.])postInvoice\s*\(/.test(code), 'còn chỗ gọi postInvoice()');
  assert.ok(!/onclick="[^"]*postInvoice/.test(html), 'còn nút gọi postInvoice trong index.html');
}
{
  // `confirmAICheckin` phải gọi hàm vẽ THẬT, không thì thông báo "Đã mở
  // barrier" hiện ra mà màn hình không đổi gì.
  const i = code.indexOf('confirmAICheckin');
  assert.ok(i > 0);
  const fn = code.slice(i, code.indexOf('\n};', i));
  assert.ok(/renderDeliveryOrders\(/.test(fn), 'phải gọi hàm vẽ thật của màn DO');
}

// --- 2. Thẻ CC FORM: không ô nào sửa được, không nút nào ghi form khác ---

{
  // Cắt đúng khối bằng cân bằng thẻ `div`, không lấy một cửa sổ ký tự cố
  // định — cửa sổ như thế lố sang màn hình khác và bắt nhầm những ô nhập
  // thật, đang chạy tốt, của màn đó.
  const dong = html.replace(/\r\n/g, '\n').split('\n');
  const batDau = dong.findIndex(l => l.includes('CC FORM'));
  assert.ok(batDau > 0, 'phải tìm được khối CC FORM');
  // Thẻ `card-panel` bọc ngoài nằm ngay trên dòng tiêu đề.
  let goc = batDau;
  while (goc > 0 && !dong[goc].includes('class="card-panel"')) goc -= 1;
  let can = 0;
  let ketThuc = goc;
  for (let k = goc; k < dong.length; k += 1) {
    can += (dong[k].match(/<div/g) || []).length - (dong[k].match(/<\/div>/g) || []).length;
    if (k > goc && can <= 0) { ketThuc = k; break; }
  }
  assert.ok(ketThuc > goc + 100, 'khối CC FORM phải đủ lớn');
  const than = dong.slice(goc, ketThuc + 1).join('\n');

  // Mọi ô nhập phải `disabled` — đúng như cờ "Mẫu minh họa" trên thẻ đã nói.
  const oMo = than.match(/<(?:input|select|textarea)\b(?![^>]*\bdisabled\b)[^>]*>/g) || [];
  assert.deepStrictEqual(oMo.slice(0, 3), [],
    `còn ${oMo.length} ô nhập sửa được trong khối CC FORM — gõ vào đó không ai đọc`);

  // Không nút nào được ghi cơ sở dữ liệu từ khối này.
  //
  // `submitIncident` LỌT QUA lần dọn trước và chỉ lộ ra ở lần rà soát nút toàn
  // dự án: thẻ "BÁO CÁO SỰ CỐ" có một nút Submit ghi một sự cố THẬT vào cơ sở
  // dữ liệu, mà đọc giá trị từ form sự cố của màn Theo dõi (`inc-do-id`,
  // `inc-veh-id`, …) — không phải từ thẻ này, vì mọi ô của thẻ đều `disabled`.
  // Bấm vào là ghi một sự cố rỗng. Danh sách này là danh sách CHẶN, nên nó chỉ
  // đúng khi có đủ tên; thêm tên vào đây mỗi lần tìm ra một nút cùng loại.
  // Soi LỆNH GỌI THẬT, không soi chú thích: chú thích nêu tên hàm là tài liệu
  // giải thích vì sao nút đó đã bị bỏ, và bắt nó là buộc người sửa phải xoá
  // đúng phần giải thích khiến lần sau có người thêm nút lại.
  const thanKhongChuThich = than.replace(/<!--[\s\S]*?-->/g, '');
  ['saveMasterForm', 'sendMasterForm', 'submitMasterForm',
    'approveMasterForm', 'publishMasterForm', 'submitIncident',
    'submitIncidentReport', 'postInvoice'].forEach(ten => {
    assert.ok(!thanKhongChuThich.includes(ten),
      `${ten} ghi dữ liệu của MỘT FORM KHÁC ở tab khác — không được gọi từ thẻ minh họa`);
  });

  // Và MỌI thẻ phải có đúng một nút đi tới màn thật — không thẻ nào thiếu.
  //
  // Trước lần rà soát này chỉ 5 trong 8 thẻ có nút, nên người xem không suy ra
  // được thẻ nào mở được: ba thẻ cuối trông như chỉ để đọc.
  //
  // Đếm CẢ HAI đường điều hướng. Thẻ "Kế hoạch tuyến đường" mở một THẺ của màn
  // Dữ liệu gốc (`openMasterSetupStep('md-tab-routes')`) chứ không mở một màn —
  // vì tuyến đường là dữ liệu gốc, không phải một bước vận hành. Đếm riêng
  // `switchView` là bắt sai một nút đang trỏ đúng chỗ.
  {
    const soThe = (than.match(/class="master-form-card"/g) || []).length;
    const soNut = (than.match(
      /onclick="(?:switchView\('[\w-]+'\)|openMasterSetupStep\('[\w-]+'\))"/g) || []).length;
    assert.strictEqual(soNut, soThe,
      `${soThe} thẻ nhưng ${soNut} nút mở màn — mọi thẻ phải có một nút`);
  }

  // Bước Đơn hàng (SO) đã bỏ khỏi luồng, nên không còn thẻ nào cho nó.
  assert.ok(!than.includes('SALES ORDER'),
    'thẻ SALES ORDER còn trong khối — bước Đơn hàng đã bỏ khỏi luồng, để lại là '
    + 'nói với người xem rằng luồng có một bước mà nó không có');

  // Thay vào đó là nút đi tới màn thật.
  assert.ok(/onclick="switchView\('[\w-]+'\)"[^>]*>\s*<i[^>]*><\/i> Mở /.test(than),
    'thẻ phải có nút mở màn hình thật');
}

// --- 3. Tab đính kèm đã dùng được thật ---------------------------------
//
// Bản trước ở đây có một ô chọn tệp, và khi chọn xong nó báo "Đã chọn hợp
// đồng/báo giá đính kèm: <tên tệp>". Nhưng `so-contract-file` không xuất hiện
// trong bất kỳ tệp JS nào — không upload, không FormData. Tệp bị bỏ ngay tại
// đó, còn người dùng thì tưởng đã đính kèm xong.
//
// Nay có bảng `sales_order_documents`, bốn endpoint, và giao diện thật.

{
  const i = html.indexOf('id="so-tab-attachments"');
  assert.ok(i > 0);
  const than = html.slice(i, i + 3000);

  // Ô chọn tệp cũ, và câu toast khẳng định đã đính kèm, không được còn.
  assert.ok(!/id="so-contract-file"/.test(than));
  assert.ok(!/Đã chọn hợp đồng/.test(html),
    'không được nói "Đã chọn hợp đồng đính kèm" mà không gửi tệp đi đâu');

  // Ô chọn tệp mới phải gọi hàm tải lên THẬT.
  const motDong = than.split(String.fromCharCode(10)).join(' ');
  assert.ok(/id="so-doc-file"[^>]*onchange="taiLenTaiLieuSO\(\)"/.test(motDong),
    'ô chọn tệp phải gọi hàm tải lên');
  assert.ok(/id="so-doc-list"/.test(than), 'phải có chỗ hiện danh sách tệp đã đính kèm');
  assert.ok(/id="so-doc-type"/.test(than), 'phải chọn được loại chứng từ');
}
{
  // Ba hàm phải tồn tại và thực sự gọi máy chủ.
  const i = code.indexOf('window.taiLenTaiLieuSO = async function');
  assert.ok(i > 0, 'phải có hàm tải lên');
  const fn = code.slice(i, code.indexOf(String.fromCharCode(10) + '};', i));
  assert.ok(/new FormData\(\)/.test(fn), 'phải gửi bằng FormData');
  assert.ok(/method: 'POST'/.test(fn));
  assert.ok(/\/documents/.test(fn));
  // Chặn cỡ tệp ngay tại đây thay vì gửi 25 MB lên rồi nhận 413.
  assert.ok(/25 \* 1024 \* 1024/.test(fn), 'phải chặn cỡ tệp trước khi gửi');
  // Chưa lưu đơn thì chưa có chỗ gắn tệp vào.
  assert.ok(/maDonDangMo\(\)/.test(fn));
  // Thất bại phải nói ra, không im lặng.
  assert.ok(/baoLoiMayChu/.test(fn) && /baoMatKetNoi/.test(fn));
  // Xóa lựa chọn để chọn lại CÙNG một tệp vẫn kích hoạt `onchange`.
  assert.ok(/oTep\.value = ''/.test(fn));
}
assert.ok(/window\.napTaiLieuSO = async function/.test(code), 'phải có hàm nạp danh sách');
assert.ok(/window\.xoaTaiLieuSO = async function/.test(code), 'phải có hàm xóa');
{
  // Mở đơn thì nạp danh sách của CHÍNH đơn đó; mở đơn mới thì vẽ lại, không
  // thì danh sách của đơn trước còn nằm đó và người dùng tưởng đơn mới đã có
  // sẵn hợp đồng đính kèm.
  const soLanGoi = (code.match(/window\.napTaiLieuSO\(\)/g) || []).length;
  assert.ok(soLanGoi >= 2, `phải nạp lại ở cả lúc mở đơn cũ lẫn đơn mới (thấy ${soLanGoi})`);
}
{
  // Tên tệp và ghi chú do người dùng đặt: phải thoát ký tự khi dựng HTML.
  const i = code.indexOf('function veDanhSachTaiLieuSO');
  assert.ok(i > 0);
  const fn = code.slice(i, code.indexOf(String.fromCharCode(10) + '}', i));
  ['file_name', 'document_type_label', 'note', 'download_url'].forEach(truong => {
    const dung = fn.match(new RegExp('[$][{][^}]*' + truong + '[^}]*[}]', 'g')) || [];
    dung.forEach(x => assert.ok(/escapeHtml\(|escapeJsAttr\(|coTep\(/.test(x),
      `${truong} phải được thoát ký tự: ${x}`));
  });
}

// --- 4. Không còn `innerHTML +=` -------------------------------------
//
// `innerHTML +=` đọc ra TOÀN BỘ nội dung hiện có, nối chuỗi, rồi phân tích lại
// từ đầu — O(n²) trong một vòng lặp. Nó còn HỦY rồi tạo lại mọi node con đã
// có, nên xóa mất trình lắng nghe sự kiện và trạng thái ô nhập của những dòng
// đã vẽ trước. `insertAdjacentHTML('beforeend', …)` không có cả hai vấn đề đó.

{
  const con = (code.match(/\.innerHTML \+=/g) || []).length;
  assert.strictEqual(con, 0, `còn ${con} chỗ dùng innerHTML +=`);
  const daDoi = (code.match(/insertAdjacentHTML\('beforeend'/g) || []).length;
  assert.ok(daDoi >= 40, `phải có ít nhất 40 chỗ đã đổi (thấy ${daDoi})`);
}

console.log('dead-ui-cleanup: tất cả kiểm tra đã qua');
