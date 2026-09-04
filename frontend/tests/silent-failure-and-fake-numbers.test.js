/**
 * Bốn lỗi thuộc cùng một họ: màn hình nói một điều mà dữ liệu nói điều khác.
 *
 *   1. Tuyến đường trên 999 km bị lưu vào cơ sở dữ liệu SAI 1.000 LẦN, vì tổng
 *      số km được đọc lại từ chuỗi đã định dạng kiểu Việt: `toLocaleString`
 *      biến 1250 thành "1.250 km", rồi `parseFloat("1.250")` cho ra 1,25.
 *      Thông báo vẫn nói "đã lưu thành công".
 *
 *   2. Nút "Gửi báo cáo sự cố" LUÔN thất bại nhưng LUÔN báo thành công: máy
 *      chủ bắt buộc trường `reporter` mà form không có ô nào để nhập, hàm
 *      không kiểm `res.ok`, và phong bì lỗi không có khóa `message` nên
 *      `data.message` rơi vào chuỗi mặc định "Báo cáo sự cố thành công!".
 *
 *   3. Hai bảng kế toán treo "Đang tải..." vĩnh viễn khi gọi API thất bại, và
 *      một bản ghi có `total`/`debit` là NULL làm vỡ nửa bảng.
 *
 *   4. Đồng hồ sức chứa thùng xe ở màn Điều phối bịa cả hai con số: sức chứa
 *      cứng 30 m³ và khối lượng đã xếp cứng 6,0 m³ — nên người điều phối LUÔN
 *      thấy "Xe còn trống 80%" bất kể đơn thật nặng hay nhẹ.
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
    return !trimmed.startsWith('//') && !trimmed.startsWith('*')
      && !trimmed.startsWith('/*') && !trimmed.startsWith('*/');
  }).join('\n');
}
const code = stripComments(app);

function hamThan(ten) {
  const i = code.indexOf(ten);
  assert.ok(i > 0, `phải tìm được ${ten}`);
  const j = code.indexOf('\n};', i);
  assert.ok(j > i, `phải tìm được cuối ${ten}`);
  return code.slice(i, j);
}

// --- 1. Tổng số km: đọc con số, không đọc chuỗi đã định dạng -------------

{
  // Chứng minh lại chính lỗi cũ, để không ai quay lại cách đó.
  assert.strictEqual((1250).toLocaleString('vi-VN'), '1.250');
  assert.strictEqual(parseFloat('1.250'), 1.25);

  const fn = hamThan('window.saveRouteConfig = async function');
  assert.ok(!/route-total-distance'\)\?\.innerText/.test(fn),
    'không được đọc lại tổng km từ chuỗi đã định dạng');
  assert.ok(/dataset\?\.km/.test(fn), 'phải đọc con số thật từ dataset');
  // Chưa tính được thì phải chặn, không được lưu một tuyến 0 km trong im lặng.
  assert.ok(/Number\.isFinite/.test(fn));
}
{
  // MỌI chỗ ghi vào ô tổng km đều phải ghi cả dataset, không thì lúc Lưu sẽ
  // đọc con số của tuyến mở trước đó.
  //
  // Cách đếm: lấy từng chỗ `getElementById('route-total-distance')` rồi xét
  // đoạn ngay sau nó. Đếm `distEl`/`totalEl` trên toàn tệp thì bắt cả những
  // biến cùng tên ở hàm khác — đó là lý do phép đếm đầu tiên báo sai.
  const viTri = [];
  const mau = /getElementById\('route-total-distance'\)/g;
  let khop;
  while ((khop = mau.exec(code)) !== null) viTri.push(khop.index);
  assert.ok(viTri.length >= 4, `phải có ít nhất 4 chỗ dùng ô tổng km (thấy ${viTri.length})`);

  viTri.forEach(i => {
    const doan = code.slice(i, i + 420);
    // Chỗ nào GHI chữ vào ô đó thì phải ghi cả dataset ngay trong đoạn đó.
    if (/\.innerText = /.test(doan)) {
      assert.ok(/dataset\.km = /.test(doan),
        `có chỗ ghi chữ vào ô tổng km mà không ghi dataset:\n${doan.slice(0, 200)}`);
    }
  });
}

// --- 2. Báo cáo sự cố: có ô người báo cáo, và kiểm res.ok ----------------

assert.ok(html.includes('id="inc-reporter"'),
  'form sự cố phải có ô Người báo cáo — máy chủ bắt buộc trường này');
{
  const fn = hamThan('window.submitIncidentReport = async function');
  assert.ok(/inc-reporter/.test(fn), 'phải đọc ô người báo cáo');
  assert.ok(/reporter/.test(fn) && /body: JSON\.stringify\(\{[^}]*reporter/.test(fn),
    'phải gửi trường reporter lên máy chủ');
  assert.ok(/if \(!res\.ok\)/.test(fn), 'phải kiểm res.ok');
  // Thất bại thì KHÔNG được nói thành công, và KHÔNG được đóng form.
  const nhanhLoi = fn.slice(fn.indexOf('if (!res.ok)'), fn.indexOf('showToast(data.message'));
  assert.ok(/return;/.test(nhanhLoi), 'thất bại thì phải dừng lại');
  assert.ok(!/closeIncidentModal/.test(nhanhLoi),
    'thất bại thì phải GIỮ form mở — đóng nó là xóa mất những gì vừa nhập');
  // Chuỗi khẳng định thành công không được là giá trị mặc định khi thiếu message.
  assert.ok(!/data\.message \|\| 'Báo cáo sự cố thành công!'/.test(fn));
}

// --- 3. Kế toán: gọi API thất bại phải nói ra, và NULL không làm vỡ bảng --

{
  const fn = hamThan('async function loadAccountingData');
  assert.ok(/} else {/.test(fn), 'phải có nhánh else cho cả hai lần gọi API');
  assert.ok(/bao_khong_nap_duoc/.test(fn), 'phải có chỗ báo là chưa nạp được');
  // Không được để bảng treo nguyên chuỗi "Đang tải...".
  assert.ok(/Chưa nạp được/.test(fn));
  // Tiền phải qua `|| 0`: một bản ghi NULL không được làm vỡ cả bảng.
  assert.ok(!/inv\.total\.toLocaleString/.test(fn),
    'inv.total có thể là NULL — phải qua || 0');
  assert.ok(!/gl\.debit\.toLocaleString/.test(fn));
  assert.ok(!/gl\.credit\.toLocaleString/.test(fn));
  assert.ok(/Number\(gia_tri \|\| 0\)/.test(fn), 'phải có guard cho tiền');
  // 401/403 phải nói là thiếu quyền, không nói chung là lỗi máy chủ.
  assert.ok(/401/.test(fn) && /403/.test(fn));
  // `innerHTML +=` trong vòng lặp parse lại toàn bộ chuỗi mỗi vòng.
  assert.ok(!/innerHTML \+=/.test(fn), 'không được cộng dồn innerHTML trong vòng lặp');
}

// --- 4. Đồng hồ sức chứa: đọc số thật, thiếu thì nói thiếu --------------

{
  const fn = hamThan('window.onDispatchVehicleChange = function');
  // Hai con số bịa của bản cũ.
  assert.ok(!/const usedVol = 6\.0/.test(fn), 'không được cứng 6,0 m³ đã xếp');
  assert.ok(!/\|\| 30\.0/.test(fn), 'không được bịa sức chứa 30 m³');
  // Phải đọc đơn đang chọn, không phải một hằng số.
  assert.ok(/dispatch-selected-do/.test(fn), 'phải đọc đơn đang chọn');
  assert.ok(/volume_m3/.test(fn), 'phải đọc thể tích thật của đơn');
  assert.ok(/volume_capacity_m3/.test(fn), 'phải đọc sức chứa thật của xe');
  // Thiếu số thì nói thiếu, không bịa một tỉ lệ phần trăm.
  assert.ok(/chưa khai thể tích/.test(fn), 'thiếu số phải nói rõ là chưa khai');
  // Quá tải phải nhìn ra được, không chỉ là thanh xanh đầy.
  assert.ok(/QUÁ TẢI/.test(fn), 'quá tải phải nói rõ');
  assert.ok(/#b91c1c/.test(fn), 'quá tải phải đổi màu thanh');
}

console.log('silent-failure-and-fake-numbers: tất cả kiểm tra đã qua');
