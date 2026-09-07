/**
 * Màn lập kế hoạch giao hàng — thiết kế lại.
 *
 * Bản trước: bảy thẻ đếm cao 90px xếp ngang chiếm gần một phần ba màn hình mà
 * chỉ để hiện bảy con số, rồi bảng DO, rồi hai phần ba màn hình TRỐNG bên
 * dưới. Muốn lập một Trip thì phải rời màn này sang màn Điều phối và chọn lại
 * đúng những DO vừa xem.
 *
 * Bản này: bảy con chip cao 34px (cùng thông tin, một phần tư chiều cao, và
 * bấm vào là lọc), bảng DO có ô tick, và khoảng trống bên phải thành bảng
 * "Trip đang lập" — tick DO là thấy ngay tuyến rồi tạo Trip tại chỗ.
 *
 * Phần đáng giá nhất của bài kiểm này là mục 3: nó chạy THẬT hàm quyết định
 * chặn/không chặn, đối chiếu với năm điều kiện của
 * `create_trip_from_delivery_orders`. Bốn trong năm điều kiện đó chỉ lộ ra khi
 * tôi chạy thử luồng trên cơ sở dữ liệu thật, không phải khi đọc mã.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i > 0, `không thấy ${neo}`);
  return app.slice(i, app.indexOf(NL + (ket || '}'), i) + 2);
}

// --- 1. Bảy thẻ đếm cao thành bảy con chip ---------------------------

{
  // Bảy id `do-stage-*` và `do-count-*` phải còn — phần JS đang chạy dùng
  // chúng, và giữ hợp đồng thì không phải sửa lan ra.
  ['incident', 'overdue', 'undated', 'near_late', 'pending', 'active', 'completed']
    .forEach(ro => {
      assert.ok(html.includes(`id="do-stage-${ro}"`), `thiếu chip ${ro}`);
      assert.ok(html.includes(`id="do-count-${ro}"`), `thiếu ô đếm ${ro}`);
    });
  // Và chúng phải là chip, không phải thẻ cao như cũ.
  const soChip = (html.match(/class="do-chip"/g) || []).length;
  assert.strictEqual(soChip, 7, `phải có đúng 7 chip, thấy ${soChip}`);
  assert.ok(!/class="do-stage-tab"/.test(html), 'còn thẻ đếm kiểu cũ');

  // Một dòng gợi ý cho rổ ĐANG mở, thay vì bảy dòng cùng lúc.
  assert.ok(html.includes('id="do-stage-hint"'));
  const t = than('function veChipVaChanTrang(soDongHien)');
  assert.ok(/do-stage-hint/.test(t) && /bucket\?\.hint/.test(t),
    'dòng gợi ý phải lấy từ DoBoard.BUCKETS của rổ đang mở');
  // Rổ rỗng vẫn hiện, chỉ mờ đi — ẩn thì người dùng không biết rổ đó tồn tại.
  assert.ok(/classList\.toggle\('empty'/.test(t), 'rổ rỗng phải mờ đi chứ không ẩn');
}

// --- 2. Hai cột, và bảng Trip đang lập ------------------------------

{
  assert.ok(html.includes('class="do-plan-layout"'), 'phải có bố cục hai cột');
  assert.ok(/\.do-plan-layout\s*\{[^}]*grid-template-columns/.test(html),
    'cột phải dựng bằng grid');
  // Màn hẹp thì xếp dọc, không để bảng 372px chen bảng DO.
  assert.ok(/@media \(max-width: 1200px\)[\s\S]{0,200}do-plan-layout/.test(html),
    'phải có nhánh màn hẹp');

  ['do-trip-builder', 'do-side-empty', 'do-side-full', 'do-side-list',
    'do-side-block', 'do-side-route', 'do-side-cta',
    'trip-departure-at', 'trip-avg-speed', 'trip-type',
    'do-pick-all', 'do-plan-count'].forEach(id => {
    assert.ok(html.includes(`id="${id}"`), `thiếu ${id}`);
  });

  // KHÔNG được có ô chọn xe/tài xế ở đây: endpoint tạo Trip không nhận
  // vehicle_id/driver_id, điều xe là bước riêng. Hiện ô đó là hàm ý nó được
  // lưu, mà không.
  const i = html.indexOf('id="do-trip-builder"');
  const khoi = html.slice(i, html.indexOf('<!-- 3.3 Route Reference Strip -->', i));
  assert.ok(!/id="trip-vehicle|id="trip-driver/.test(khoi),
    'tạo Trip không nhận xe/tài xế — đừng hỏi ở đây');
  assert.ok(/switchView\('dispatch'\)/.test(khoi),
    'phải nói rõ xe được gán ở bước Điều phối');
}

// --- 3. Chặn đúng NĂM điều kiện của backend -------------------------
//
// Chạy thật `veBangTripDangLap` trong một DOM tối giản. Đây là phần bắt được
// lỗi thật: bốn trong năm điều kiện dưới đây chỉ lộ ra khi chạy thử luồng
// trên cơ sở dữ liệu thật.

{
  const cat = (neo) => {
    const i = app.indexOf(neo);
    assert.ok(i > 0, neo);
    return i;
  };
  // Cắt từ chỗ khai `doDaChon` — nó nằm TRƯỚC các hàm, và thiếu nó thì
  // đoạn mã cắt ra không chạy được.
  const dau = cat('const doDaChon = new Set();');
  const cuoi = cat('window.veBangTripDangLap = veBangTripDangLap;');
  // `routeSegments` va `routeSegmentDistanceKm` nam GAN CUOI app.js, ngoai
  // doan cat — nen phai keo them chung vao, khong thi doan ma khong chay.
  const phuTro = ['function routeSegments(route) {',
    'function routeSegmentDistanceKm(segment) {'].map(neo => {
    const i = app.indexOf(neo);
    assert.ok(i > 0, `khong thay ${neo}`);
    return app.slice(i, app.indexOf(NL + '}', i) + 2);
  }).join(NL);
  const doan = phuTro + NL + app.slice(dau, cuoi);

  // DOM giả: chỉ cần các phần tử mà hàm chạm tới.
  function moiTruong(dsDon, dsTuyen) {
    const o = {};
    const nut = { disabled: false, style: {} };
    const tao = () => ({ style: {}, innerHTML: '', textContent: '', classList: { toggle() {} } });
    ['do-side-empty', 'do-side-full', 'do-side-count', 'do-side-list',
      'do-side-block', 'do-side-route', 'do-side-cta-text',
      'trip-avg-speed'].forEach(id => { o[id] = tao(); });
    o['trip-avg-speed'].value = '45';
    o['do-side-cta'] = nut;
    const document = {
      getElementById: id => o[id] || null,
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const f = new Function(
      'document', 'eplDeliveryOrders', 'eplRoutes', 'escapeHtml', 'escapeJsAttr',
      'window', 'CSS',
      doan + NL + 'return { veBangTripDangLap, doLapTripDuoc, doDuKhungGio,'
      + ' routeSegmentDistanceKm, lechQuangDuongTuyen, doDaChon };'
    );
    const api = f(document, dsDon, dsTuyen, String, String, {}, { escape: String });
    dsDon.forEach(d => api.doDaChon.add(String(d.id)));
    api.veBangTripDangLap();
    return { nut, o, api };
  }

  const GIO = {
    pickup_window_start: '2026-09-08T07:00:00+07:00',
    pickup_window_end: '2026-09-08T09:00:00+07:00',
    delivery_window_start: '2026-09-08T13:00:00+07:00',
    delivery_window_end: '2026-09-08T17:00:00+07:00',
  };
  const TUYEN_OK = {
    id: 'RT-OK', name: 'A → B', distance_km: 44.7,
    segments_json: JSON.stringify([{ from: 'A', to: 'B', distance_km: 44.7 }]),
  };
  // Tuyến LỆCH: khai 44,0 nhưng chặng cộng lại 44,7. Đúng hiện trạng của
  // `DEMO-RT-VSIP2A-CATLAI` trong cơ sở dữ liệu thật.
  const TUYEN_LECH = {
    id: 'RT-LECH', name: 'C → D', distance_km: 44.0,
    segments_json: JSON.stringify([{ from: 'C', to: 'D', dist_km: 44.7 }]),
  };
  const donOK = { id: 'DO-1', canonical_status: 'pending', route_id: 'RT-OK', ...GIO };

  // (a) Đủ điều kiện -> KHÔNG chặn.
  {
    const { nut } = moiTruong([donOK], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, false, 'DO đủ điều kiện thì phải tạo được');
  }
  // (b) Không phải `pending` -> chặn (DELIVERY_ORDER_NOT_PENDING).
  {
    const { nut } = moiTruong(
      [{ ...donOK, canonical_status: 'in_transit' }], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, true, 'chỉ DO chờ vận chuyển mới lập Trip');
  }
  // (c) Thiếu khung giờ -> chặn (DELIVERY_TIME_WINDOW_REQUIRED).
  //     Backend đòi CẢ BỐN mốc, không chỉ giờ giao.
  {
    const { nut } = moiTruong(
      [{ ...donOK, delivery_window_end: null }], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, true, 'thiếu một trong bốn mốc là chặn');
  }
  // (d) Hai tuyến khác nhau -> chặn (DELIVERY_ORDERS_INCOMPATIBLE).
  //     Bản thiết kế mẫu ghi "nên tách 2 Trip, hoặc giữ 1 Trip đi vòng (thêm
  //     ~18 km)" — sai: backend KHÔNG TẠO ĐƯỢC, chứ không phải đi vòng.
  {
    const { nut } = moiTruong(
      [donOK, { ...donOK, id: 'DO-2', route_id: 'RT-LECH' }],
      [TUYEN_OK, TUYEN_LECH]);
    assert.strictEqual(nut.disabled, true, 'khác tuyến là không tạo được');
  }
  // (e) Chưa gán tuyến -> chặn.
  {
    const { nut } = moiTruong([{ ...donOK, route_id: null }], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, true, 'DO chưa gán tuyến thì chặn');
  }
  // (f) Tuyến lệch quãng đường -> chặn (ROUTE_DISTANCE_MISMATCH).
  {
    const { nut, api } = moiTruong(
      [{ ...donOK, route_id: 'RT-LECH' }], [TUYEN_LECH]);
    assert.strictEqual(nut.disabled, true, 'tuyến lệch quãng đường thì chặn');
    const lech = api.lechQuangDuongTuyen(TUYEN_LECH);
    assert.ok(lech && Math.abs(lech.tongChang - 44.7) < 0.01, JSON.stringify(lech));
    assert.strictEqual(api.lechQuangDuongTuyen(TUYEN_OK), null);
  }

  // (g) `segments_json` dùng BỐN tên khóa khác nhau trong dữ liệu thật —
  //     `dist_km` ở tuyến demo, `distance_km` ở tuyến E2E. Đọc đúng một tên
  //     là ra 0 km ở nửa số tuyến.
  //
  //     Phép đọc này dùng `routeSegmentDistanceKm` CÓ SẴN trong app.js, chứ
  //     không viết lại: hai nguồn cho cùng một phép đọc là chỗ để chúng trôi
  //     khỏi nhau, và bản có sẵn đã xử lý đúng cả bốn tên khóa.
  {
    const { api } = moiTruong([donOK], [TUYEN_OK]);
    [['distance_km', 12], ['dist_km', 12], ['distance', 12], ['km', 12]]
      .forEach(([khoa, gt]) => {
        assert.strictEqual(api.routeSegmentDistanceKm({ [khoa]: gt }), gt, khoa);
      });
    assert.strictEqual(api.routeSegmentDistanceKm({}), 0);
    assert.strictEqual(api.routeSegmentDistanceKm({ distance_km: 'rác' }), 0);
    // Và app.js KHÔNG được có bản trùng lặp nào nữa.
    assert.ok(!/function kmCuaChang|function changCuaTuyen/.test(app),
      'còn hàm đọc chặng trùng lặp — dùng routeSegments/routeSegmentDistanceKm');
  }
}

// --- 4. Gửi đúng phong bì backend đòi ------------------------------

{
  const t = than('window.taoTripTuDO = async function', '};');
  assert.ok(/\/api\/tms\/trips\/from-delivery-orders/.test(t));
  assert.ok(/do_ids: dsChon\.map/.test(t), 'phải gửi danh sách DO');
  // Bốn trường BẮT BUỘC của TripFromDeliveryOrdersRequest.
  ['id:', 'do_ids:', 'planned_departure_at:', 'avg_speed_kmh:']
    .forEach(k => assert.ok(t.includes(k), `thiếu ${k}`));
  // `id` cũng là khóa idempotency — gửi lại cùng mã không tạo bản thứ hai.
  assert.ok(/'Idempotency-Key': maTrip/.test(t));
  // Chặn tại chỗ trước khi gửi, thay vì để backend trả 422.
  assert.ok(/Chưa nhập giờ xuất bến/.test(t));
  assert.ok(/tocDo <= 0/.test(t));
  // Thất bại phải nói LỜI CỦA MÁY CHỦ.
  assert.ok(/baoLoiMayChu\(res, viec\)/.test(t) && /baoMatKetNoi\(viec, e\)/.test(t));
}

// --- 5. Chặn số dòng vẽ ra ----------------------------------------
//
// Quy mô thật là hàng nghìn đơn. Dựng hết vào một lần innerHTML là dựng lại
// đúng lỗi đã phải sửa ở màn lịch xe.

{
  assert.ok(/const GIOI_HAN_DONG_DO = \d+;/.test(app), 'phải có giới hạn số dòng');
  const gh = Number(app.match(/const GIOI_HAN_DONG_DO = (\d+);/)[1]);
  assert.ok(gh > 0 && gh <= 200, `giới hạn phải hợp lý, thấy ${gh}`);
  assert.ok(/list\.slice\(0, GIOI_HAN_DONG_DO\)\.forEach/.test(app),
    'phải cắt danh sách TRƯỚC khi vẽ');
  // Và phải NÓI RA phần bị cắt, không âm thầm bỏ bớt.
  assert.ok(/Đang hiện \$\{GIOI_HAN_DONG_DO\} trên \$\{list\.length\} DO/.test(app),
    'phải nói rõ đang hiện bao nhiêu trên tổng bao nhiêu');
}

// --- 6. Tab Tuyến tham chiếu: dải thẻ cuộn ngang thành BẢNG ---------
//
// Bản trước là dải thẻ 300px cuộn ngang — muốn so quãng đường giữa hai tuyến
// thì phải cuộn qua cuộn lại, và xem chặng thì phải mở hộp thoại.

{
  assert.ok(html.includes('id="route-reference-table"'), 'phải là bảng');
  assert.ok(!/flex:0 0 300px/.test(app), 'còn dải thẻ cuộn ngang kiểu cũ');
  ['th_route', 'th_distance', 'th_segments', 'th_used_by']
    .forEach(k => assert.ok(html.includes(k), `thiếu cột ${k}`));
  assert.ok(html.includes('id="route-hide-test"'), 'phải có nút ẩn tuyến kiểm thử');
}

{
  // Cột 'Đang dùng bởi' nối thẳng với chốt 409 LOCKED_RECORD của
  // `delete_route`. Chạy THẬT hàm đếm.
  const i = app.indexOf('function demChungTuDungTuyen(routeId)');
  assert.ok(i > 0, 'phải có hàm đếm chứng từ dùng tuyến');
  const t = app.slice(i, app.indexOf(NL + '}', i) + 2);
  const dem = new Function('crmQuotations', 'crmSalesOrders', 'eplDeliveryOrders',
    t + NL + 'return demChungTuDungTuyen;');

  const f = dem(
    [{ route_id: 'RT-1' }, { route_id: 'RT-1' }],
    [{ route_id: 'RT-1' }],
    [{ route_id: 'RT-1' }, { route_id: 'RT-2' }]);
  const kq = f('RT-1');
  assert.strictEqual(kq.tong, 4, JSON.stringify(kq));
  // Phải NÓI RÕ vướng ở loại chứng từ nào, không chỉ một con số tổng.
  assert.deepStrictEqual(kq.chi_tiet, ['2 báo giá', '1 đơn', '1 lệnh giao hàng']);
  assert.strictEqual(f('RT-9').tong, 0);
  assert.deepStrictEqual(f('RT-9').chi_tiet, []);
  // Mã rỗng không được đếm bừa mọi chứng từ chưa gán tuyến.
  assert.strictEqual(f('').tong, 0);
  assert.strictEqual(f(null).tong, 0);
}

{
  // Bản cũ viết cứng `km / 50` rồi gọi đó là 'giờ chạy thực tế'. 50 km/h
  // không có nguồn nào, mà con số ra trông y hệt một con số thật.
  const i = app.indexOf('function renderRoutes(data) {');
  // Lọc chú thích TRƯỚC khi dò. Chú thích giải thích bản cũ có trích nguyên
  // `(totalKm / 50)`, và một phép dò thô sẽ bắt vào chính câu giải thích rồi
  // báo là lỗi vẫn còn — đúng cái bẫy đã gặp mấy lần trong dự án này.
  const t = app.slice(i, i + 8000)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split(NL).filter(d => !d.trim().startsWith('//')).join(NL);
  assert.ok(!/km \/ 50/.test(t), 'còn tốc độ 50 km/h viết cứng');
  assert.ok(/tocDo > 0 \?/.test(t), 'chỉ hiện thời gian khi CÓ tốc độ kế hoạch');
  assert.ok(/ở \$\{tocDo\} km\/h/.test(t), 'phải nói rõ tính ở tốc độ nào');
  // Tuyến lệch quãng đường phải được cảnh báo NGAY trong bảng.
  assert.ok(/lech$/m.test(t) || /lechQuangDuongTuyen\(r\)/.test(t),
    'phải kiểm lệch quãng đường');
  assert.ok(/lệch/.test(t), 'phải nói ra chỗ lệch');
  // Nút trong dòng không được kéo theo hành vi mở chặng của cả dòng.
  assert.ok((t.match(/event\.stopPropagation\(\)/g) || []).length >= 2,
    'nút trong dòng phải chặn nổi bọt sự kiện');
}

console.log('lap-ke-hoach-giao-hang-ui: tất cả kiểm tra đã qua');
