/**
 * Màn lập kế hoạch giao hàng — bản 3.
 *
 * Đường đi của màn này: bản 1 là bảy thẻ đếm cao 90px xếp ngang chiếm gần một
 * phần ba màn hình, rồi bảng DO, rồi hai phần ba màn hình TRỐNG bên dưới. Bản
 * 2 nén bảy thẻ thành bảy con chip và lấp chỗ trống bên phải bằng một bảng
 * "Trip đang lập" rộng 372px. Bản 3 bỏ luôn bảng bên phải: bảng DO chiếm hết
 * chiều rộng, và phần tóm tắt lựa chọn xuống một THANH HÀNH ĐỘNG NỔI chỉ hiện
 * khi đã tick DO — chưa chọn gì thì không có khối rỗng nào chiếm chỗ. Bảy con
 * chip cũng gọn còn BA nhóm, bảy tình trạng chi tiết vào một ô chọn.
 *
 * Phần đáng giá nhất của bài kiểm này là mục 3: nó chạy THẬT hàm quyết định
 * chặn/không chặn, đối chiếu với năm điều kiện của
 * `create_trip_from_delivery_orders`. Bốn trong năm điều kiện đó chỉ lộ ra khi
 * chạy thử luồng trên cơ sở dữ liệu thật, không phải khi đọc mã.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i > 0, `không thấy ${neo}`);
  return app.slice(i, app.indexOf(NL + (ket || '}'), i) + 2);
}

// --- 1. Bảy con chip gọn thành BA nhóm + một ô chọn ------------------

{
  ['need', 'run', 'all'].forEach(nhom => {
    assert.ok(html.includes(`id="do-group-${nhom}"`), `thiếu chip nhóm ${nhom}`);
    assert.ok(html.includes(`id="do-group-count-${nhom}"`), `thiếu ô đếm ${nhom}`);
  });
  const soChip = (html.match(/class="do-chip( active)?"/g) || []).length;
  assert.strictEqual(soChip, 3, `phải có đúng 3 chip nhóm, thấy ${soChip}`);
  assert.ok(!/class="do-stage-tab"/.test(html), 'còn thẻ đếm bản 1');
  assert.ok(!/class="do-chips"/.test(html), 'còn dải bảy chip bản 2');

  // Bảy tình trạng chi tiết KHÔNG mất, chỉ dời vào ô chọn — và ô chọn phải
  // phủ đúng bảy rổ của DoBoard, không thừa không thiếu.
  const i = html.indexOf('id="do-status-filter"');
  assert.ok(i > 0, 'thiếu ô chọn tình trạng');
  const oChon = html.slice(i, html.indexOf('</select>', i));
  ['incident', 'overdue', 'undated', 'near_late', 'pending', 'active', 'completed']
    .forEach(ro => {
      assert.ok(oChon.includes(`value="${ro}"`), `ô chọn thiếu rổ ${ro}`);
      // Và phải dịch được — đây từng là chỗ DUY NHẤT trong màn chỉ có
      // tiếng Việt, vì bảy option không có `data-i18n`.
      assert.ok(oChon.includes(`data-i18n="stage_${ro}"`), `rổ ${ro} chưa có i18n`);
      ['vi', 'en', 'la'].forEach(ng => {
        assert.ok(lang[`stage_${ro}`] && lang[`stage_${ro}`][ng],
          `stage_${ro} thiếu bản dịch ${ng}`);
      });
    });

  // Nhãn ba nhóm và nút bỏ chọn cũng phải có đủ ba ngôn ngữ.
  ['grp_need', 'grp_run', 'grp_all', 'btn_clear_pick'].forEach(k => {
    assert.ok(lang[k], `lang.json thiếu ${k}`);
    ['vi', 'en', 'la'].forEach(ng => {
      assert.ok(lang[k][ng], `${k} thiếu bản dịch ${ng}`);
    });
  });

  // Ba nhóm phải gộp ĐÚNG bảy rổ, không bỏ rơi rổ nào ra ngoài mọi nhóm.
  const t = than('const NHOM_DO = {', '};');
  const nhom = new Function(t + NL + 'return NHOM_DO;')();
  assert.deepStrictEqual(
    [...nhom.need, ...nhom.run].sort(),
    ['incident', 'overdue', 'undated', 'near_late', 'pending', 'active'].sort(),
    'ba nhóm phải phủ hết rổ chưa hoàn thành');
  assert.strictEqual(nhom.all, null, 'nhóm "Tất cả" không lọc gì');

  // Số đếm trong chip và trong ô chọn cùng lấy từ `deliveryOrderStage`, tức
  // cùng phép chia rổ với bảng — không thể lệch nhau.
  const v = than('function veChipVaChanTrang(soDongHien)');
  assert.ok(/deliveryOrderStage\(d\)/.test(v), 'đếm phải theo cùng phép chia rổ');
  assert.ok(/do-group-count-/.test(v) && /do-status-filter/.test(v),
    'phải cập nhật cả chip nhóm và ô chọn');
  // Đổi ngôn ngữ xong, nhãn option không được dồn thành "Gần trễ (2) (2)".
  assert.ok(/textContent\.replace\(\/\\s\*\\\(\\d\+\\\)\$\//.test(v),
    'phải bóc phần đếm cũ khỏi nhãn trước khi ghi lại');
}

// --- 2. Bảng hết chiều rộng, thanh hành động NỔI --------------------

{
  assert.ok(!/class="do-plan-layout"/.test(html), 'còn bố cục hai cột bản 2');
  assert.ok(!html.includes('id="do-trip-builder"'), 'còn bảng Trip đang lập bản 2');

  ['do-fab', 'do-fab-n', 'do-fab-route', 'do-fab-warn', 'do-fab-go',
    'do-fab-go-text', 'trip-departure-at', 'trip-avg-speed', 'trip-type',
    'do-pick-all', 'do-plan-count', 'do-plan-note'].forEach(id => {
    assert.ok(html.includes(`id="${id}"`), `thiếu ${id}`);
  });

  // Chưa tick DO nào thì thanh phải ĐANG ẨN ngay trong HTML tĩnh, không chờ
  // JS chạy mới ẩn — không thì mỗi lần tải trang nó nháy một cái.
  const i = html.indexOf('<div class="do-fab" id="do-fab"');
  assert.ok(i > 0, 'thanh hành động phải nằm ngoài panel, dạng nổi');
  assert.ok(/<div class="do-fab" id="do-fab" hidden>/.test(html),
    'thanh hành động phải ẩn sẵn');
  // Thanh nổi là khối cuối cùng trước `</body>`, nên cắt tới đó là đủ và
  // không phụ thuộc vào cách thụt lề hay kiểu kết dòng của vùng này —
  // index.html TRỘN cả LF và CRLF, neo theo kết dòng là hỏng.
  const fab = html.slice(i, html.indexOf('</body>', i));
  assert.ok(fab.length > 400 && fab.length < 4000, `khối thanh nổi: ${fab.length}`);

  // KHÔNG được có ô chọn xe/tài xế: endpoint tạo Trip không nhận
  // vehicle_id/driver_id, điều xe là bước riêng. Hiện ô đó là hàm ý nó
  // được lưu, mà không.
  assert.ok(!/id="trip-vehicle|id="trip-driver/.test(fab),
    'tạo Trip không nhận xe/tài xế — đừng hỏi ở đây');
  // Hai trường BẮT BUỘC của endpoint phải nằm ngay trên thanh, không ẩn đi.
  assert.ok(fab.includes('id="trip-departure-at"') && fab.includes('id="trip-avg-speed"'),
    'giờ xuất bến và tốc độ là bắt buộc, phải ở ngay thanh');

  // Bảng có đủ chín cột, kể cả cột Hàng mới.
  const j = html.indexOf('<table class="do-plan-table">');
  const thead = html.slice(j, html.indexOf('</thead>', j));
  // `<th[ >]` chứ không phải `<th` — không thì `<thead>` cũng bị đếm.
  assert.strictEqual((thead.match(/<th[ >]/g) || []).length, 9,
    'bảng phải có 9 cột (gồm ô tick và cột Hàng)');
  assert.ok(thead.includes('data-i18n="th_cargo"'), 'thiếu cột Hàng');
  assert.ok(html.includes('colspan="9"'), 'dòng trống phải trải đủ 9 cột');
}

{
  // Cột "Hàng" phải hiện SỐ THẬT. Bản mẫu v3 ghi "1 × 40'", nhưng bảng
  // `delivery_orders` KHÔNG có số container — chỉ `weight_kg`,
  // `pallet_count`, `volume_m3`, `packaging_spec`.
  const t = than('function moTaHangHoa(do_item)');
  ['weight_kg', 'pallet_count', 'volume_m3', 'packaging_spec'].forEach(c => {
    assert.ok(t.includes(c), `phải đọc ${c}`);
  });
  assert.ok(!/container|40'|20'/i.test(t), 'không có số container trong CSDL — đừng bịa');
  const f = new Function(t + NL + 'return moTaHangHoa;')();
  // Ba con số cùng hiện khi có cả ba — kg, pallet và m³ quyết định xe chở
  // được hay không theo ba cách khác nhau.
  assert.strictEqual(
    f({ weight_kg: 3000, pallet_count: 4, volume_m3: 12 }).chinh,
    '3.000 kg · 4 pallet · 12 m³');
  assert.strictEqual(f({ weight_kg: 3000 }).chinh, '3.000 kg');
  assert.strictEqual(f({ packaging_spec: 'Thùng carton' }).phu, 'Thùng carton');
  // DO chưa khai gì thì phải NÓI RA là chưa khai, không hiện "0 kg".
  const trong = f({});
  assert.strictEqual(trong.chinh, '—', `DO trống không được hiện 0: ${trong.chinh}`);
  assert.strictEqual(f(null).chinh, '—', 'DO rỗng cũng không được vỡ');
}

{
  // Ô tick phải trao THẲNG chính nó cho `tickDO`. Bản trước chỉ nhận mã DO
  // rồi đi dò lại đúng ô vừa phát ra sự kiện — một vòng vẽ quanh cái đã nằm
  // trong tay, và nó kéo `CSS.escape` vào chỉ để dùng đúng một lần trong cả
  // tệp. Bỏ đi thì hàm chạy được cả ngoài trình duyệt.
  assert.ok(/onchange="tickDO\('\$\{doId\}', this\.checked, this\)"/.test(app),
    'ô tick phải truyền chính nó vào tickDO');
  const t = than('window.tickDO = function (id, tick, o)', '};');
  assert.ok(/o\.closest === 'function'/.test(t), 'phải kiểm trước khi gọi closest');
  assert.ok(!/querySelector/.test(t), 'không cần dò lại ô vừa bấm');
  // Lọc chú thích trước khi dò — chú thích ở trên có nhắc tên API cũ.
  const than_ma = app.split(NL).filter(d => !d.trim().startsWith('//')).join(NL);
  assert.ok(!/CSS\.escape/.test(than_ma), 'mã chạy không được cần CSS.escape');

  // Chạy thật với một ô giả: tick vào thì dòng phải mang lớp `picked`, bỏ
  // tick thì mất — đây là dấu hiệu duy nhất cho biết dòng nào đang được chọn.
  const doan = than('const doDaChon = new Set();', '') + NL + t;
  const f = new Function('document', 'veThanhHanhDong', 'window',
    doan + NL + 'return { tickDO: window.tickDO, doDaChon };');
  const lop = new Set();
  const dong = { classList: { toggle: (n, b) => (b ? lop.add(n) : lop.delete(n)) } };
  const api = f({}, () => {}, {});
  api.tickDO('DO-9', true, { closest: () => dong });
  assert.ok(api.doDaChon.has('DO-9') && lop.has('picked'), 'tick vào phải nhớ và tô');
  api.tickDO('DO-9', false, { closest: () => dong });
  assert.ok(!api.doDaChon.has('DO-9') && !lop.has('picked'), 'bỏ tick phải quên và bỏ tô');
  // Không có ô (gọi từ mã khác) thì vẫn phải nhớ, không được vỡ.
  api.tickDO('DO-9', true, null);
  assert.ok(api.doDaChon.has('DO-9'), 'thiếu ô thì vẫn phải nhớ lựa chọn');
}

// --- 3. Chặn đúng NĂM điều kiện của backend -------------------------
//
// Chạy thật `veThanhHanhDong` trong một DOM tối giản. Đây là phần bắt được
// lỗi thật: bốn trong năm điều kiện dưới đây chỉ lộ ra khi chạy thử luồng
// trên cơ sở dữ liệu thật.

{
  const cat = (neo) => {
    const i = app.indexOf(neo);
    assert.ok(i > 0, neo);
    return i;
  };
  // Cắt từ chỗ khai `doDaChon` — nó nằm TRƯỚC các hàm, thiếu nó thì đoạn mã
  // cắt ra không chạy được — đến hết `veThanhHanhDong`.
  const dau = cat('const doDaChon = new Set();');
  const cuoi = cat('window.veThanhHanhDong = veThanhHanhDong;');
  // Bốn hàm đọc tuyến nằm GẦN CUỐI app.js, ngoài đoạn cắt — phải kéo thêm
  // vào, không thì đoạn mã không chạy.
  const phuTro = ['function routeSegments(route) {',
    'function routeSegmentDistanceKm(segment) {',
    'function routeTotalDistanceKm(route) {',
    'function formatRouteKm(km) {'].map(neo => {
    const i = app.indexOf(neo);
    assert.ok(i > 0, `khong thay ${neo}`);
    return app.slice(i, app.indexOf(NL + '}', i) + 2);
  }).join(NL);
  const doan = phuTro + NL + app.slice(dau, cuoi);

  // DOM giả: chỉ cần các phần tử mà hàm chạm tới.
  function moiTruong(dsDon, dsTuyen) {
    const o = {};
    const nut = { disabled: false, style: {} };
    const tao = () => ({
      style: {}, innerHTML: '', textContent: '', hidden: false,
      classList: { toggle() {} },
    });
    ['do-fab', 'do-fab-n', 'do-fab-route', 'do-fab-warn', 'do-fab-go-text',
      'trip-avg-speed'].forEach(id => { o[id] = tao(); });
    o['trip-avg-speed'].value = '45';
    o['do-fab-go'] = nut;
    const document = {
      getElementById: id => o[id] || null,
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const f = new Function(
      'document', 'eplDeliveryOrders', 'eplRoutes', 'escapeHtml', 'escapeJsAttr',
      'window', 'CSS',
      doan + NL + 'return { veThanhHanhDong, doLapTripDuoc, doDuKhungGio,'
      + ' routeSegmentDistanceKm, lechQuangDuongTuyen, doDaChon };'
    );
    const api = f(document, dsDon, dsTuyen, String, String, {}, { escape: String });
    dsDon.forEach(d => api.doDaChon.add(String(d.id)));
    const kq = api.veThanhHanhDong();
    return { nut, o, api, kq };
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
  // `DEMO-RT-VSIP2A-CATLAI` trong cơ sở dữ liệu thật trước khi sửa.
  const TUYEN_LECH = {
    id: 'RT-LECH', name: 'C → D', distance_km: 44.0,
    segments_json: JSON.stringify([{ from: 'C', to: 'D', dist_km: 44.7 }]),
  };
  const donOK = { id: 'DO-1', canonical_status: 'pending', route_id: 'RT-OK', ...GIO };

  // (a) Đủ điều kiện -> KHÔNG chặn, và thanh phải HIỆN.
  {
    const { nut, o, kq } = moiTruong([donOK], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, false, 'DO đủ điều kiện thì phải tạo được');
    assert.strictEqual(kq.chanLai, false);
    assert.strictEqual(o['do-fab'].hidden, false, 'có DO đã tick thì thanh phải hiện');
    assert.strictEqual(o['do-fab-n'].textContent, '1');
    assert.strictEqual(o['do-fab-warn'].hidden, true, 'không chặn thì không cảnh báo');
  }
  // (a') Không tick gì -> thanh phải ẨN. Đây là điểm bản 3 khác bản 2: bản 2
  //      luôn chiếm 372px kể cả khi rỗng.
  {
    const { o } = moiTruong([], [TUYEN_OK]);
    assert.strictEqual(o['do-fab'].hidden, true, 'chưa tick gì thì phải ẩn hẳn');
  }
  // (b) Không phải `pending` -> chặn (DELIVERY_ORDER_NOT_PENDING).
  {
    const { nut, kq } = moiTruong(
      [{ ...donOK, canonical_status: 'in_transit' }], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, true, 'chỉ DO chờ vận chuyển mới lập Trip');
    assert.ok(/chờ vận chuyển/.test(kq.lyDo), kq.lyDo);
  }
  // (c) Thiếu khung giờ -> chặn (DELIVERY_TIME_WINDOW_REQUIRED).
  //     Backend đòi CẢ BỐN mốc, không chỉ giờ giao.
  {
    const { nut, kq } = moiTruong(
      [{ ...donOK, delivery_window_end: null }], [TUYEN_OK]);
    assert.strictEqual(nut.disabled, true, 'thiếu một trong bốn mốc là chặn');
    assert.ok(/khung giờ/.test(kq.lyDo), kq.lyDo);
  }
  // (d) Hai tuyến khác nhau -> chặn (DELIVERY_ORDERS_INCOMPATIBLE).
  //     Bản mẫu v3 ghi "nên tách 2 Trip, hoặc giữ 1 Trip đi vòng (+~18 km)"
  //     và có nút "Tạo 2 Trip →" — cả hai đều sai: một lần gọi endpoint chỉ
  //     tạo MỘT Trip của MỘT tuyến, chứ không phải đi vòng thêm km.
  {
    const { nut, kq } = moiTruong(
      [donOK, { ...donOK, id: 'DO-2', route_id: 'RT-LECH' }],
      [TUYEN_OK, TUYEN_LECH]);
    assert.strictEqual(nut.disabled, true, 'khác tuyến là không tạo được');
    assert.ok(/CÙNG MỘT tuyến/.test(kq.lyDo), kq.lyDo);
    assert.ok(!/đi vòng|Tạo 2 Trip/.test(kq.lyDo), 'đừng hứa việc endpoint không làm');
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
  // MỘT quyết định chặn, dùng cho cả thanh và cho lúc bấm — hai phép kiểm
  // song song là chỗ để nút bảo "được" mà lệnh gửi lên bị từ chối.
  assert.ok(/veThanhHanhDong\(\)/.test(t),
    'lúc bấm phải hỏi lại chính hàm đã quyết định chặn/không chặn');
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
  const v = than('function veChipVaChanTrang(soDongHien)');
  assert.ok(/soDongHien > hien/.test(v) && /trên \$\{soDongHien\}/.test(v),
    'phải nói rõ đang hiện bao nhiêu trên tổng bao nhiêu');
}

{
  // Ba con số máy chủ tính thêm (`open_incidents`, `arrived`, `overdue`) chỉ
  // có ở `/api/delivery-orders/analysis`. Bản 2 hiện chúng dưới bảy thẻ đếm;
  // bỏ bảy thẻ mà không dời sang chỗ khác là giao diện mất luôn phần nói ra
  // VIỆC CẦN LÀM, chỉ còn phần đếm dòng.
  const t = than('function ghiChuRoDO()');
  ['open_incidents', 'arrived', 'overdue'].forEach(c => {
    assert.ok(t.includes(c), `phải dùng ${c} của máy chủ`);
  });
  const f = new Function('deliveryOrderAnalysis', t + NL + 'return ghiChuRoDO;');
  assert.strictEqual(f(null)(), '', 'chưa có phân tích thì không nói bừa');
  assert.strictEqual(f({ buckets: {} })(), '', 'không có việc thì không nói gì');
  const cau = f({ buckets: {
    incident: { open_incidents: 2 },
    active: { arrived: 3 },
    overdue: { count: 1 },
  } })();
  assert.ok(/2 sự cố/.test(cau) && /3 DO đã đến điểm/.test(cau)
    && /1 DO đã quá hạn/.test(cau), cau);
  // Và hàm cũ nói với bảy thẻ đã biến mất thì không được còn lại.
  assert.ok(!/updateDeliveryOrderStageTabs|do-count-|do-stage-/.test(app),
    'còn mã nói với bảy thẻ đếm đã bị thay');
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
