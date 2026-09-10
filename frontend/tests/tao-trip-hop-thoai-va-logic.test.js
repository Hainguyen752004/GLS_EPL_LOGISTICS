/**
 * Hộp thoại Tạo chuyến (thiết kế lại 10/09) và ba lỗi logic module Trip.
 *
 * Chủ dự án chỉ ba ảnh: (1) bảng chuyến gắn cảnh báo "thiếu chặng về" lên MỌI
 * chuyến một chiều; (2) hộp thoại Tạo Trip lộ "Mã Freight Order" và "Version"
 * (chi tiết nội bộ), tự điền FO của một chuyến khác, vận tốc ghi cứng 45, chữ
 * không dấu, bố cục trống hơn nửa màn; (3) module Kế toán & tài chính không
 * dùng — gỡ lối vào và các nút "đối soát / hạch toán".
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo); assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1; return app.slice(i, j > 0 ? j : i + 6000);
}
const dlg = html.slice(html.indexOf('<div id="trip-return-action-modal"'), html.indexOf('MỞ SẴN, không để `display:none`'));

// 1. Chuyến một chiều KHÔNG "thiếu chặng về".
{
  const t = than('function tripThieuChangVe(raw)', 'function tripChoXacNhanVe');
  assert.ok(/'one_way'/.test(t) && /'multi_stop'/.test(t), 'một chiều và nhiều điểm dừng không có chặng về theo định nghĩa');
}

// 2. Bộ chọn lệnh chỉ đưa ra lệnh chờ điều phối CHƯA có chuyến sống.
{
  const t = than('function tripReturnAllDeliveryOrders()', 'function vanTocKeHoachChoDO');
  assert.ok(/appState\?\.transport_trips/.test(t), 'phải đối chiếu với danh sách chuyến');
  assert.ok(/canonical_status \|\| 'pending'\) === 'pending'/.test(t), 'chỉ lệnh đang chờ');
  assert.ok(/!coChuyen\.has/.test(t), 'loại lệnh đã có chuyến sống');
}

// 3. Vận tốc không ghi cứng: lấy từ loại xe trên báo giá, không có thì bắt nhập.
{
  assert.ok(!/tripReturnNumberValue\('trip-return-speed', 45\)/.test(app), 'không còn `|| 45`');
  assert.ok(!/tripReturnSetValue\('trip-return-speed', '45'\)/.test(app), 'không còn điền sẵn 45');
  const v = than('function vanTocKeHoachChoDO(doId)', 'function tripReturnAllRoutes');
  assert.ok(/vehicle_type_id/.test(v) && /avg_speed_kmh/.test(v), 'tra tốc độ từ loại xe của báo giá');
  const nop = than('async function submitTripReturnActionForm()', 'window.selectTripReturnWorkItem');
  assert.ok(/Nhập vận tốc kế hoạch/.test(nop), 'thiếu tốc độ thì chặn và nói rõ');
  assert.ok(!/trip-return-fo-id', preferredOrder/.test(app), 'không tự điền FO của lệnh/chuyến khác khi tạo chuyến mới');
}

// 4. Hộp thoại: FO và Version là ô ẩn; chữ có dấu; hai cột; khối điểm dừng còn.
{
  assert.ok(/type="hidden" id="trip-return-fo-id"/.test(dlg), 'Mã Freight Order phải là ô ẩn');
  assert.ok(/type="hidden" id="trip-return-version"/.test(dlg), 'Version phải là ô ẩn');
  assert.ok(!/Khong tao chang ve/.test(dlg) && /Không tạo chặng về/.test(dlg), 'chữ phải có dấu');
  assert.ok(/class="trip-dlg-body"/.test(dlg) && /class="trip-dlg-col"/.test(dlg), 'bố cục hai cột');
  assert.ok(/id="trip-return-speed-hint"/.test(dlg), 'phải nói tốc độ lấy từ đâu');
  assert.ok(/Điểm dừng & người nhận/.test(dlg));
  ['trip-return-trip-id', 'trip-return-trip-type', 'trip-return-purpose', 'trip-return-departure',
    'trip-return-speed', 'trip-return-dwell', 'do-picker-list', 'trip-return-route-preview'].forEach(id =>
    assert.ok(dlg.includes(`id="${id}"`), 'thiếu ' + id));
}

// 5. Kế toán: không còn lối vào từ menu / tìm kiếm / nút; điểm cuối là hồ sơ hoàn tất.
{
  assert.ok(!/data-view="accounting"/.test(html), 'menu không còn mục Kế toán');
  assert.ok(!/switchView\('accounting'\)/.test(html), 'không nút nào trong HTML mở Kế toán');
  assert.ok(!/\['Kế toán và tài chính', 'Hóa đơn, công nợ', 'accounting'/.test(khung), 'ô tìm không còn gợi ý Kế toán');
  assert.ok(!/'Qua hạch toán'/.test(app) && !/'Chuyển đối soát'/.test(app), 'không còn nút hạch toán / đối soát');
  assert.ok(/'Mở hồ sơ hoàn tất'/.test(app) && /'Xem hồ sơ hoàn tất'/.test(app), 'điểm cuối chuyến là hồ sơ hoàn tất');
}

console.log('tao-trip-hop-thoai-va-logic: OK');
