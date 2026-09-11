/* eslint-env browser */
/* global L */
/**
 * Trang tài xế — chỉ đọc/ghi qua API EPL đang chạy, KHÔNG có dữ liệu giả.
 *
 * Bốn việc tài xế làm được, đúng bốn đường API của hệ:
 *   1. Xem chuyến của mình        GET  /api/tracking/control-tower   (lọc theo tài xế)
 *   2. Ghi mốc đang đi tới đâu    POST /api/tms/freight-orders/{fo}/events
 *   3. Báo sự cố                  POST /api/incidents
 *   4. Hoàn tất giao hàng         GET  /api/delivery-orders/{do}/closeout  (đọc giá đã chốt)
 *                                 POST /api/delivery-orders/{do}/complete-delivery (POD + chốt giá)
 *
 * HAI MÀN. `man-ds` là danh sách, `man-chitiet` là màn đầy che kín. Bấm thẻ thì MỞ màn chi
 * tiết chứ không đổ nội dung xuống dưới danh sách như bản trước — trên điện thoại, nội dung
 * đổ xuống dưới bắt người ta cuộn qua danh sách mỗi lần muốn xem, và nút việc thì nằm tít
 * cuối trang. Giờ nút việc dán ở ĐÁY MÀN, luôn trong tầm ngón tay.
 *
 * GỐC API: mặc định gọi cùng origin (`/api/...`) — `chay.py` phục vụ trang này và chuyển tiếp
 * `/api` sang máy chủ EPL, nên trình duyệt không vướng CORS. Mở trực tiếp bằng tệp thì đổi gốc
 * ở ô cấu hình hiện ra khi không gọi được.
 */
(function () {
  'use strict';

  var GOC_LUU = 'EPL_TAIXE_API_BASE';
  var TAIXE_LUU = 'EPL_TAIXE_ID';
  var NEN_LUU = 'EPL_TAIXE_NEN_BANDO';

  var MOC = {
    check_in: 'Vào bãi', pickup: 'Lấy hàng', departure: 'Xuất bến',
    arrival: 'Đến điểm giao', unloading: 'Dỡ hàng', delivered: 'Giao xong'
  };
  //: Mốc nào thì xe đang ở đâu trên tuyến — dùng để gửi kèm toạ độ khi ghi mốc.
  var TIEN_DO = { check_in: 0, pickup: 0, departure: 0.05, arrival: 1, unloading: 1, delivered: 1 };
  //: Nhãn + màu viền thẻ theo trạng thái chuyến.
  var TRANG_THAI = {
    dispatched: ['Đã điều phối · chờ xuất bến', 'vang', 'den'],
    in_transit: ['Đang trên đường', 'do', 'di'],
    arrived: ['Đã đến · chờ ký nhận', 'vang', 'den'],
    delivered: ['Đã giao · chờ xe về bãi', 'luc', 'giao']
  };

  /* LỚP NỀN BẢN ĐỒ CÓ DỰ PHÒNG. Đo được trên mạng của dự án: `tile.openstreetmap.org` KHÔNG
   * tới được, nên bản đồ ra một ô xám trơn — có tuyến, có toạ độ, nhưng không có ảnh nền, và
   * người xem đọc ra là "bản đồ hỏng". Thử lần lượt rồi NHỚ nguồn nào chạy được. */
  var NGUON_NEN = [
    { ma: 'osm-de', url: 'https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
      chon: { subdomains: 'abc', maxZoom: 18, attribution: '&copy; OpenStreetMap' } },
    { ma: 'osm', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      chon: { subdomains: 'abc', maxZoom: 19, attribution: '&copy; OpenStreetMap' } },
    { ma: 'esri',
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      chon: { maxZoom: 19, attribution: 'Tiles &copy; Esri' } }
  ];

  var el = function (id) { return document.getElementById(id); };
  var esc = function (v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var so = function (v, le) {
    var n = Number(v);
    return isFinite(n) ? n.toLocaleString('vi-VN', { maximumFractionDigits: le == null ? 0 : le }) : '—';
  };
  var gio = function (v) {
    if (!v) return '—';
    var d = new Date(v);
    return isNaN(d) ? String(v) : d.toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    });
  };
  var gioNgan = function (v) {
    if (!v) return '—';
    var d = new Date(v);
    return isNaN(d) ? String(v)
      : d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  };
  var tien = function (v, ma) { return so(v) + ' ' + (ma || 'VND'); };
  /** Bây giờ, dạng `YYYY-MM-DDTHH:MM` theo giờ máy — đúng dạng `<input datetime-local>` đọc.
   *  KHÔNG dùng `toISOString()`: hàm đó trả giờ UTC, nên ô giờ hiện sớm 7 tiếng ở Việt Nam. */
  var bayGio = function () {
    var d = new Date(), hai = function (x) { return ('0' + x).slice(-2); };
    return d.getFullYear() + '-' + hai(d.getMonth() + 1) + '-' + hai(d.getDate())
      + 'T' + hai(d.getHours()) + ':' + hai(d.getMinutes());
  };
  var chuDau = function (ten) {
    var t = String(ten || '').trim().split(/\s+/);
    return ((t[0] || '?')[0] + (t.length > 1 ? t[t.length - 1][0] : '')).toUpperCase();
  };

  var trangThai = { taiXe: '', chon: '', dong: [], danhSachTaiXe: [], dangTai: false };

  function goc() {
    try { return localStorage.getItem(GOC_LUU) || ''; } catch (e) { return ''; }
  }
  function nho(khoa, gia) { try { localStorage.setItem(khoa, gia); } catch (e) { /* chặn lưu trữ */ } }
  function doc(khoa) { try { return localStorage.getItem(khoa) || ''; } catch (e) { return ''; } }

  function bao(chu, lau) {
    var b = el('bao');
    b.textContent = chu; b.hidden = false;
    clearTimeout(bao._t);
    bao._t = setTimeout(function () { b.hidden = true; }, lau || 3200);
  }

  function loi(chu) {
    var o = el('loi');
    if (!chu) { o.hidden = true; o.textContent = ''; return; }
    o.hidden = false;
    o.innerHTML = esc(chu)
      + '<div style="margin-top:.6rem"><button type="button" class="nut nho" id="nut-doi-goc">'
      + 'Đổi địa chỉ máy chủ API</button></div>';
    el('nut-doi-goc').onclick = function () {
      var moi = window.prompt('Địa chỉ máy chủ EPL (để trống = gọi cùng địa chỉ trang này):', goc());
      if (moi === null) return;
      nho(GOC_LUU, String(moi).trim().replace(/\/+$/, ''));
      location.reload();
    };
  }

  /** Gọi API. Trả `{ma, ok, than}` — KHÔNG ném khi máy chủ trả lỗi nghiệp vụ, vì lời lỗi đó là
   *  thứ tài xế cần đọc (sai thứ tự mốc, chưa tới giờ, thiếu POD…). */
  function api(duong, tuyChon) {
    return fetch(goc() + duong, tuyChon || {}).then(function (r) {
      return r.text().then(function (t) {
        var than = null;
        try { than = t ? JSON.parse(t) : null; } catch (e) { than = { raw: t }; }
        return { ma: r.status, ok: r.ok, than: than };
      });
    });
  }

  var duLieu = function (g) { return g && typeof g === 'object' && 'data' in g ? g.data : g; };
  var loiCua = function (g) {
    var d = g && g.than;
    return (d && d.error && d.error.message) || (d && d.detail && d.detail.message)
      || (d && typeof d.detail === 'string' ? d.detail : '') || ('HTTP ' + (g && g.ma));
  };

  // ------------------------------------------------------------------ hình học tuyến
  var chuyenChang = function (dong) {
    return (dong.route_segments || dong.segments || []).filter(function (s) {
      return s && s.from_lat != null && s.to_lat != null;
    });
  };

  /** Điểm trên tuyến ứng với một tỉ lệ, cân theo độ dài từng chặng. Cùng phép nội suy mà máy
   *  chủ dùng (`services/gps_simulation.py`), nên mốc ghi tay đặt xe đúng chỗ trên bản đồ. */
  function toaDo(dong, tiLe) {
    var chang = chuyenChang(dong);
    if (!chang.length) return null;
    var diem = [[+chang[0].from_lat, +chang[0].from_lng, 0]];
    chang.forEach(function (s) { diem.push([+s.to_lat, +s.to_lng, +s.dist_km || 1]); });
    var tong = diem.slice(1).reduce(function (t, d) { return t + d[2]; }, 0);
    if (!tong) return { lat: diem[0][0], lng: diem[0][1] };
    var muc = Math.max(0, Math.min(1, tiLe)) * tong, di = 0;
    for (var i = 1; i < diem.length; i++) {
      if (di + diem[i][2] >= muc) {
        var p = diem[i][2] ? (muc - di) / diem[i][2] : 0;
        return {
          lat: +(diem[i - 1][0] + (diem[i][0] - diem[i - 1][0]) * p).toFixed(6),
          lng: +(diem[i - 1][1] + (diem[i][1] - diem[i - 1][1]) * p).toFixed(6)
        };
      }
      di += diem[i][2];
    }
    var c = diem[diem.length - 1];
    return { lat: c[0], lng: c[1] };
  }

  /** Cắt một đường nhiều điểm ở tỉ lệ `p` (0..1) theo ĐỘ DÀI THẬT, trả [đã đi, còn lại].
   *
   *  Cắt theo SỐ ĐIỂM thì sai: `duong_bo` dày điểm ở khúc quanh và thưa ở đoạn thẳng, nên
   *  50% số điểm không phải 50% quãng đường — vạch đỏ sẽ lệch xa chỗ xe thật đang ở. */
  function catDuong(diem, p) {
    if (!diem || diem.length < 2) return [diem || [], []];
    var d = [0], i;
    for (i = 1; i < diem.length; i++) {
      var dx = (diem[i][0] - diem[i - 1][0]);
      var dy = (diem[i][1] - diem[i - 1][1]) * Math.cos(diem[i][0] * Math.PI / 180);
      d.push(d[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    var tong = d[d.length - 1];
    if (!tong) return [diem, []];
    var muc = Math.max(0, Math.min(1, p)) * tong;
    for (i = 1; i < diem.length; i++) {
      if (d[i] >= muc) {
        var t = (d[i] - d[i - 1]) ? (muc - d[i - 1]) / (d[i] - d[i - 1]) : 0;
        var giua = [diem[i - 1][0] + (diem[i][0] - diem[i - 1][0]) * t,
                    diem[i - 1][1] + (diem[i][1] - diem[i - 1][1]) * t];
        return [diem.slice(0, i).concat([giua]), [giua].concat(diem.slice(i))];
      }
    }
    return [diem, []];
  }

  // ------------------------------------------------------------------ nạp dữ liệu
  function napTaiXe() {
    return api('/api/drivers').then(function (g) {
      if (!g.ok) throw new Error(loiCua(g));
      var ds = duLieu(g.than) || [];
      ds = (Array.isArray(ds) ? ds : ds.items || []).filter(function (x) {
        return String(x.role || '').toLowerCase().indexOf('phụ') < 0;
      });
      ds.sort(function (a, b) { return String(a.name || a.id).localeCompare(String(b.name || b.id), 'vi'); });
      trangThai.danhSachTaiXe = ds;
      var chon = el('chon-taixe');
      chon.innerHTML = '<option value="">— Tôi là ai? —</option>'
        + ds.map(function (d) {
          return '<option value="' + esc(d.id) + '">' + esc(d.name || d.id)
            + ' · ' + esc(d.id) + '</option>';
        }).join('');
      var luu = doc(TAIXE_LUU);
      if (luu && ds.some(function (d) { return d.id === luu; })) {
        chon.value = luu; trangThai.taiXe = luu;
      }
      veToi();
    });
  }

  function veToi() {
    var t = trangThai.danhSachTaiXe.filter(function (d) { return d.id === trangThai.taiXe; })[0];
    el('toi-ten').textContent = t ? (t.name || t.id) : 'Chọn tên của bạn';
    el('toi-ma').textContent = t
      ? (t.id + (t.license_type ? ' · ' + t.license_type : '')) : 'Chạm để chọn';
    el('toi-chu').textContent = t ? chuDau(t.name || t.id) : '?';
  }

  function nap() {
    if (trangThai.dangTai) return Promise.resolve();
    trangThai.dangTai = true;
    return api('/api/tracking/control-tower').then(function (g) {
      if (!g.ok) throw new Error(loiCua(g));
      var d = duLieu(g.than) || {};
      el('gio-server').textContent = 'Số liệu lúc ' + gio(d.server_time || new Date().toISOString());
      var tatCa = d.items || [];
      // TÀI XẾ CHỈ THẤY CHUYẾN CỦA MÌNH — kể cả khi đi phụ xe.
      trangThai.dong = trangThai.taiXe
        ? tatCa.filter(function (x) {
          return x.driver_id === trangThai.taiXe || x.co_driver_id === trangThai.taiXe;
        })
        : [];
      el('dem').textContent = trangThai.taiXe
        ? trangThai.dong.length + '/' + tatCa.length + ' chuyến là của tôi' : '';
      // Chuyến đang mở mà biến mất khỏi danh sách (đã đóng) thì đóng luôn màn chi tiết.
      if (trangThai.chon && !chonDong()) dongChiTiet();
      loi('');
      ve();
    }).catch(function (e) {
      loi('Không đọc được dữ liệu từ máy chủ: ' + (e && e.message));
    }).then(function () { trangThai.dangTai = false; });
  }

  // ------------------------------------------------------------------ màn 1: danh sách
  function chonDong() {
    return trangThai.dong.filter(function (x) { return x.key === trangThai.chon; })[0] || null;
  }

  function veDanhSach() {
    var o = el('ds');
    if (!trangThai.taiXe) {
      o.innerHTML = '<div class="trong"><span class="to">🚚</span>Chạm vào tên bạn ở trên để xem chuyến.</div>';
      return;
    }
    if (!trangThai.dong.length) {
      o.innerHTML = '<div class="trong"><span class="to">☕</span>Hôm nay bạn chưa được xếp chuyến nào đang chạy.</div>';
      return;
    }
    o.innerHTML = trangThai.dong.map(function (r) {
      var tt = TRANG_THAI[r.status] || [r.status || 'Chưa rõ', '', ''];
      var chang = r.legs || [];
      var xong = chang.filter(function (l) { return l.status === 'completed'; }).length;
      var dau = (chuyenChang(r)[0] || {}).from || r.origin || '';
      var cuoi = (chuyenChang(r).slice(-1)[0] || {}).to || r.destination || '';
      return '<button type="button" class="the-chuyen ' + tt[2] + '" data-key="' + esc(r.key) + '">'
        + '<div class="hang1"><span class="ma">' + esc(r.do_id || r.trip_id) + '</span>'
        + '<span class="mui" aria-hidden="true">›</span></div>'
        + '<div class="phu">' + esc(r.customer_name || '') + ' · ' + esc(r.trip_id || '') + '</div>'
        + '<div class="tuyen"><i></i><b>' + esc(dau) + '</b><em></em>'
        + '<b style="text-align:right">' + esc(cuoi) + '</b><i class="cuoi"></i></div>'
        + '<div class="chips">'
        + '<span class="chip ' + tt[1] + '">' + esc(tt[0]) + '</span>'
        + (r.overdue ? '<span class="chip do">Quá hạn giao</span>' : '')
        + (r.open_incident_count
          ? '<span class="chip do">' + r.open_incident_count + ' sự cố chưa đóng</span>' : '')
        + '<span class="chip">' + xong + '/' + chang.length + ' chặng</span>'
        + '<span class="chip">' + esc(r.vehicle_id || 'Chưa gán xe') + '</span>'
        + '<span class="chip">Hạn ' + esc(gioNgan(r.delivery_due)) + '</span>'
        + '</div></button>';
    }).join('');
    Array.prototype.forEach.call(o.querySelectorAll('[data-key]'), function (b) {
      b.onclick = function () { moChiTiet(b.getAttribute('data-key')); };
    });
  }

  // ------------------------------------------------------------------ màn 2: chi tiết
  function moChiTiet(khoa) {
    trangThai.chon = khoa;
    el('man-chitiet').hidden = false;
    el('man-ds').hidden = true;
    document.body.style.overflow = 'hidden';
    veChiTiet();
  }

  function dongChiTiet() {
    trangThai.chon = '';
    el('man-chitiet').hidden = true;
    el('man-ds').hidden = false;
    document.body.style.overflow = '';
    veDanhSach();
  }

  function oTin(nhan, giaTri) {
    return '<div class="o-tin"><span>' + esc(nhan) + '</span><b>' + esc(giaTri || '—') + '</b></div>';
  }
  function loaiChang(t) {
    return { delivery: 'Chặng giao', outbound: 'Đi ngang', pickup: 'Đi lấy hàng',
             empty_return: 'Về rỗng', backhaul: 'Hàng về',
             warehouse_transfer: 'Chuyển kho' }[t] || t;
  }

  function veChiTiet() {
    var r = chonDong();
    if (!r) return;
    var g = r.gps || {}, moc = r.next_milestone || null;
    var chuaGiao = (r.legs || []).some(function (l) {
      return l.type === 'delivery' && ['completed', 'cancelled'].indexOf(l.status) < 0;
    });
    var chuaToiNoi = chuaGiao && r.status !== 'arrived' && r.status !== 'delivered';

    el('ct-ma').textContent = r.do_id || r.trip_id || '—';
    el('ct-phu').textContent = (r.customer_name || '') + ' · ' + (r.vehicle_id || 'chưa gán xe');

    // --- thanh mốc: xong / đang tới / chưa ---
    var daGhi = {};
    (r.events || []).forEach(function (e) { daGhi[e.type] = true; });
    var dsMoc = (r.milestones && r.milestones.length ? r.milestones
      : Object.keys(MOC).map(function (k) { return { ma: k, ten: MOC[k] }; }));
    el('ct-moc').innerHTML = dsMoc.map(function (m) {
      var xong = !!daGhi[m.ma], toi = moc && moc.ma === m.ma;
      return '<div class="b' + (xong ? ' xong' : '') + (toi ? ' toi' : '') + '">'
        + '<div class="o">' + (xong ? '✓' : toi ? '●' : '') + '</div>'
        + '<small>' + esc(m.ten || MOC[m.ma] || m.ma) + '</small></div>';
    }).join('');
    // Kéo mốc ĐANG TỚI vào giữa tầm nhìn: sáu mốc rộng hơn màn 390px, và mốc đang tới
    // thường là mốc cuối — không cuộn thì tài xế không thấy chính việc mình sắp làm.
    var oToi = el('ct-moc').querySelector('.b.toi');
    if (oToi && el('ct-moc').scrollTo) {
      el('ct-moc').scrollTo({
        left: Math.max(0, oToi.offsetLeft - el('ct-moc').clientWidth / 2 + oToi.offsetWidth / 2),
        behavior: 'smooth'
      });
    }

    // --- các thẻ nội dung ---
    var canh = '';
    if (r.overdue) {
      canh += '<div class="luuy nang"><span aria-hidden="true">⏰</span><div>'
        + '<b>Lệnh này đã quá hạn giao.</b> Nếu còn đang trên đường, hãy báo sự cố để điều độ biết lý do.'
        + '</div></div>';
    }
    if (r.open_incident_count) {
      canh += '<div class="luuy nang"><span aria-hidden="true">⚠</span><div>'
        + '<b>' + r.open_incident_count + ' sự cố chưa đóng</b> trên chuyến này.</div></div>';
    }
    if (g.status === 'simulated') {
      canh += '<div class="luuy"><span aria-hidden="true">📍</span><div>'
        + 'Vị trí trên bản đồ đang là <b>mô phỏng theo tuyến</b>, không phải GPS của máy bạn. '
        + 'Ghi mốc ở dưới để cập nhật vị trí thật.</div></div>';
    }

    el('ct-noidung').innerHTML =
      '<div class="the"><h3>Lệnh giao hàng</h3><div class="luoi">'
      + oTin('Khách hàng', r.customer_name)
      + oTin('Mã chuyến', r.trip_id)
      + oTin('Tuyến', r.route_name)
      + oTin('Hạn giao', gio(r.delivery_due))
      + oTin('Xe', r.vehicle_id)
      + oTin('Tổ lái', (r.driver_name || '') + (r.co_driver_name ? ' + ' + r.co_driver_name : ''))
      + '</div>' + canh + '</div>'
      + '<div class="the"><h3>Chặng của chuyến</h3><ol class="chang">'
      + (r.legs || []).map(function (l) {
        return '<li class="' + (l.status === 'completed' ? 'xong' : '') + '">'
          + '<b>' + esc(l.origin) + ' → ' + esc(l.destination) + '</b>'
          + '<small><span class="nhan-chang">' + esc(loaiChang(l.type)) + '</span>'
          + esc(l.status === 'completed' ? 'đã xong' : l.status === 'cancelled' ? 'đã huỷ' : 'chưa đi')
          + '</small><small>'
          + (l.actual_arrival_at ? 'Đến thực tế: ' + esc(gio(l.actual_arrival_at))
            : 'Kế hoạch: ' + esc(gio(l.planned_arrival_at))) + '</small></li>';
      }).join('') + '</ol></div>';

    // --- thanh việc dán đáy ---
    el('ct-viec').innerHTML =
      (moc ? '<button type="button" class="nut chinh" id="nut-moc">📍 Ghi mốc: '
        + esc(moc.ten || MOC[moc.ma] || moc.ma) + '</button>' : '')
      + '<div class="cap">'
      + '<button type="button" class="nut luc" id="nut-hoantat"' + (chuaToiNoi ? ' disabled' : '')
      + '>✍ Hoàn tất giao</button>'
      + '<button type="button" class="nut canh" id="nut-suco"'
      + (r.vehicle_id ? '' : ' disabled') + '>⚠ Báo sự cố</button>'
      + '</div>'
      + (chuaToiNoi
        ? '<p class="goi-y">Ghi mốc <b>Đến điểm giao</b> trước, rồi mới ký nhận được.</p>'
        : !chuaGiao ? '<p class="goi-y">Đã ký nhận đủ các điểm giao của lệnh này.</p>' : '');
    if (el('nut-moc')) el('nut-moc').onclick = function () { ghiMoc(this); };
    el('nut-hoantat').onclick = moHoanTat;
    el('nut-suco').onclick = moSuCo;

    veBanZo(r);
  }

  function ve() { veDanhSach(); if (trangThai.chon) veChiTiet(); }

  // ------------------------------------------------------------------ bản đồ
  var bd = { map: null, nen: null, iNen: 0, loiNen: 0, daVe: false, lop: [] };

  function veBanZo(r) {
    var hop = el('banzo'), thay = el('banzo-thay');
    var g = r.gps || {};
    var duong = (r.duong_bo || []).filter(function (p) {
      return p && p.length >= 2 && isFinite(+p[0]) && isFinite(+p[1]);
    }).map(function (p) { return [+p[0], +p[1]]; });
    var chang = chuyenChang(r);

    var den = new Date(r.predicted_eta || r.planned_arrival_at || 0);
    el('banzo-so').innerHTML =
      '<div><span>Đã đi</span><b>' + so(g.progress_percent, 0) + '%</b></div>'
      + '<div><span>Còn lại</span><b>' + so(g.remaining_km, 1) + ' km</b></div>'
      + '<div><span>Tốc độ</span><b>' + so(g.speed_kmh, 0) + ' <small>km/h</small></b></div>'
      + '<div><span>Đến lúc</span><b>' + (isNaN(den) || !+den ? '—'
        : den.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }))
      + '</b></div>';

    // Không có Leaflet (mất mạng CDN) hoặc không có toạ độ: nói thật, đừng để ô xám trơn.
    if (typeof L === 'undefined' || !window.L || typeof L.map !== 'function') {
      hop.classList.add('tat'); thay.hidden = false;
      thay.innerHTML = 'Không tải được thư viện bản đồ.<br>Vẫn ghi mốc và ký nhận bình thường được.';
      return;
    }
    if (!duong.length && !chang.length) {
      hop.classList.add('tat'); thay.hidden = false;
      thay.textContent = 'Tuyến này chưa có toạ độ để vẽ bản đồ.';
      return;
    }
    hop.classList.remove('tat'); thay.hidden = true;

    if (!bd.map) {
      bd.map = L.map(hop, { zoomControl: false, attributionControl: true, tap: false });
      L.control.zoom({ position: 'topright' }).addTo(bd.map);
      var nhoNen = doc(NEN_LUU);
      bd.iNen = Math.max(0, NGUON_NEN.map(function (n) { return n.ma; }).indexOf(nhoNen));
      datNen();
    }
    bd.lop.forEach(function (l) { bd.map.removeLayer(l); });
    bd.lop = [];
    var giu = function (l) { bd.lop.push(l.addTo(bd.map)); return l; };

    // Tuyến: phần đã đi tô đỏ đậm, phần còn lại nét mảnh xám — đọc một cái là biết còn xa bao nhiêu.
    var net = duong.length ? duong
      : [[+chang[0].from_lat, +chang[0].from_lng]].concat(chang.map(function (s) {
        return [+s.to_lat, +s.to_lng];
      }));
    var cat = catDuong(net, (Number(g.progress_percent) || 0) / 100);
    if (cat[1].length > 1) {
      giu(L.polyline(cat[1], { color: '#8a857e', weight: 4, opacity: .75, dashArray: '7 8' }));
    }
    if (cat[0].length > 1) {
      giu(L.polyline(cat[0], { color: '#b4121b', weight: 6, opacity: .95 }));
    }

    // Ghim các điểm dừng: đầu tuyến xanh, các điểm giữa số thứ tự, điểm cuối đỏ.
    var ghim = function (lat, lng, chu, lop, nhan) {
      giu(L.marker([lat, lng], {
        icon: L.divIcon({
          className: '', html: '<div class="diem-ghim ' + lop + '">' + chu + '</div>',
          iconSize: [23, 23], iconAnchor: [11, 11]
        })
      })).bindPopup(nhan);
    };
    if (chang.length) {
      ghim(+chang[0].from_lat, +chang[0].from_lng, '◆', 'dau', esc(chang[0].from || 'Điểm đi'));
      chang.forEach(function (s, i) {
        var cuoi = i === chang.length - 1;
        ghim(+s.to_lat, +s.to_lng, cuoi ? '◆' : String(i + 1), cuoi ? 'cuoi' : '',
          esc(s.to || '') + '<br>' + so(s.dist_km, 1) + ' km');
      });
    }
    if (g.lat != null && g.lng != null) {
      giu(L.marker([+g.lat, +g.lng], {
        icon: L.divIcon({ className: '', html: '<div class="xe-ghim">🚚</div>',
          iconSize: [34, 34], iconAnchor: [17, 17] }),
        zIndexOffset: 500
      })).bindPopup('Xe ' + esc(r.vehicle_id || '') + '<br>' + so(g.speed_kmh, 0) + ' km/h');
    }

    var bo = L.latLngBounds(net);
    if (g.lat != null) bo.extend([+g.lat, +g.lng]);
    bd.map.fitBounds(bo, { padding: [26, 26] });
    // Ô bản đồ mới hiện lần đầu thì Leaflet chưa biết kích thước thật của nó.
    setTimeout(function () { if (bd.map) bd.map.invalidateSize(); }, 120);
  }

  function datNen() {
    var n = NGUON_NEN[bd.iNen] || NGUON_NEN[0];
    if (bd.nen) bd.map.removeLayer(bd.nen);
    bd.loiNen = 0; bd.daVe = false;
    bd.nen = L.tileLayer(n.url, n.chon).addTo(bd.map);
    bd.nen.on('tileload', function () {
      if (!bd.daVe) { bd.daVe = true; nho(NEN_LUU, n.ma); }
    });
    bd.nen.on('tileerror', function () {
      // Nguồn nào cũng lỗi vài ô lẻ; chỉ đổi nguồn khi nó CHƯA hề vẽ được ô nào.
      if (bd.daVe) return;
      if (++bd.loiNen >= 4 && bd.iNen < NGUON_NEN.length - 1) { bd.iNen++; datNen(); }
    });
  }

  // ------------------------------------------------------------------ 2. ghi mốc
  function ghiMoc(nut) {
    var r = chonDong();
    if (!r || !r.next_milestone) return;
    var moc = r.next_milestone, ten = moc.ten || MOC[moc.ma] || moc.ma;
    if (!r.freight_order_id) { bao('Chuyến này chưa có lệnh vận chuyển nên chưa ghi được mốc.'); return; }
    if (!window.confirm('Ghi mốc "' + ten + '" cho ' + r.do_id + ' vào lúc này?\n\n'
      + 'Mốc vào lịch sử chuyến và cập nhật vị trí xe. Không hoàn lại được.')) return;
    nut.disabled = true;
    var than = {
      event_type: moc.ma, source: 'manual', expected_version: r.freight_order_version,
      event_time: new Date().toISOString(),
      location_text: (moc.ma === 'check_in' || moc.ma === 'pickup') ? (r.origin || null) : (r.destination || null),
      speed_kmh: moc.ma === 'departure' ? 40 : 0,
      note: 'Tài xế ghi mốc "' + ten + '" trên trang tài xế'
    };
    var diem = toaDo(r, TIEN_DO[moc.ma] == null ? 0 : TIEN_DO[moc.ma]);
    if (diem) { than.lat = diem.lat; than.lng = diem.lng; }
    else if (r.gps && r.gps.lat != null) { than.lat = r.gps.lat; than.lng = r.gps.lng; }
    api('/api/tms/freight-orders/' + encodeURIComponent(r.freight_order_id) + '/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
        'Idempotency-Key': 'txe-' + r.freight_order_id + '-' + moc.ma + '-' + Date.now() },
      body: JSON.stringify(than)
    }).then(function (g) {
      if (!g.ok) { bao(loiCua(g), 6000); return; }
      bao('Đã ghi mốc "' + ten + '".');
      return nap();
    }).catch(function (e) { bao('Không gọi được máy chủ: ' + (e && e.message), 6000); })
      .then(function () { nut.disabled = false; });
  }

  // ------------------------------------------------------------------ 3. báo sự cố
  function moSuCo() {
    var r = chonDong();
    if (!r) return;
    el('suco-boicanh').textContent = r.do_id + ' · xe ' + (r.vehicle_id || '—')
      + ' · ' + (r.route_name || '');
    el('hop-suco').showModal();
  }

  el('form-suco').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var r = chonDong();
    if (!r) return;
    var f = new FormData(this), nut = this.querySelector('button[type=submit]');
    nut.disabled = true;
    api('/api/incidents', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        do_id: r.do_id, vehicle_id: r.vehicle_id,
        incident_type: f.get('incident_type'), severity: f.get('severity'),
        location: f.get('location'), description: f.get('description'),
        reporter: (r.driver_name || trangThai.taiXe) + ' (tài xế)'
      })
    }).then(function (g) {
      if (!g.ok) { bao(loiCua(g), 6000); return; }
      el('hop-suco').close(); el('form-suco').reset();
      bao('Đã gửi báo cáo sự cố. Điều phối sẽ thấy ngay.');
      return nap();
    }).catch(function (e) { bao('Không gửi được: ' + (e && e.message), 6000); })
      .then(function () { nut.disabled = false; });
  });

  // ------------------------------------------------------------------ 4. hoàn tất giao hàng
  var hoSoKy = { dong: null, closeout: null, ky: {} };

  function moHoanTat() {
    var r = chonDong();
    if (!r) return;
    hoSoKy.dong = r; hoSoKy.ky = {};
    el('ht-dau').innerHTML = '<div class="luoi">'
      + oTin('Lệnh giao hàng', r.do_id) + oTin('Khách', r.customer_name)
      + oTin('Xe', r.vehicle_id) + oTin('Tuyến', r.route_name) + '</div>';
    el('ht-diem').innerHTML = '<div class="trong">Đang đọc hồ sơ giá…</div>';
    el('ht-gia').innerHTML = '';
    el('hop-hoantat').showModal();
    api('/api/delivery-orders/' + encodeURIComponent(r.do_id) + '/closeout').then(function (g) {
      hoSoKy.closeout = g.ok ? duLieu(g.than) : null;
      veHoanTat(g.ok ? '' : loiCua(g));
    }).catch(function (e) { hoSoKy.closeout = null; veHoanTat(e && e.message); });
  }

  function veHoanTat(loiGia) {
    var r = hoSoKy.dong, c = hoSoKy.closeout || {};
    // POD phải nộp cho ĐÚNG các chặng giao của lệnh này — máy chủ đối chiếu từng chặng.
    var chang = (r.legs || []).filter(function (l) {
      return l.type === 'delivery' && ['completed', 'cancelled'].indexOf(l.status) < 0;
    });
    if (!chang.length) {
      el('ht-diem').innerHTML = '<div class="loi">Lệnh này không còn chặng giao nào cần ký.</div>';
      el('nut-chot').disabled = true;
      return;
    }
    el('nut-chot').disabled = false;
    el('ht-diem').innerHTML = chang.map(function (l, i) {
      var n = i + 1;
      return '<div class="diem"><h4><i>' + n + '</i>' + esc(l.destination)
        + (chang.length > 1 ? ' <small style="color:var(--nhat);font-weight:600">(điểm '
          + n + '/' + chang.length + ')</small>' : '') + '</h4>'
        + '<label class="nhap"><span>Giao lúc</span>'
        + '<input type="datetime-local" data-ky="' + n + '-luc" value="' + bayGio() + '" required>'
        + '</label>'
        + '<label class="nhap"><span>Người nhận</span>'
        + '<input data-ky="' + n + '-nguoi" value="' + esc(l.receiver_name || '') + '" required></label>'
        + '<label class="nhap"><span>Số điện thoại người nhận</span>'
        + '<input type="tel" inputmode="tel" data-ky="' + n + '-sdt" value="'
        + esc(l.receiver_phone || '') + '"></label>'
        + '<label class="nhap"><span>Kết quả giao</span><select data-ky="' + n + '-ketqua">'
        + '<option value="delivered_full">Giao đủ hàng</option>'
        + '<option value="delivered_partial">Giao thiếu</option>'
        + '<option value="refused">Khách từ chối nhận</option></select></label>'
        + '<label class="nhap"><span>Ảnh biên bản / phiếu giao (bắt buộc)</span>'
        + '<input type="file" accept="image/*" capture="environment" data-ky="' + n + '-anh" required></label>'
        + '<label class="nhap"><span>Chữ ký người nhận — ký trực tiếp bên dưới</span></label>'
        + '<canvas class="kyten" data-canvas="' + n + '"></canvas>'
        + '<div class="hang"><span id="ky-trangthai-' + n + '">Chưa ký</span>'
        + '<button type="button" data-xoaky="' + n + '">Ký lại</button></div>'
        + '<label class="nhap" style="margin-top:.75rem"><span>Tình trạng hàng / ghi chú</span>'
        + '<textarea data-ky="' + n + '-ghichu" placeholder="Nguyên niêm phong, không móp vỡ"></textarea></label>'
        + '<input type="hidden" data-ky="' + n + '-leg" value="' + esc(l.id) + '">'
        + '</div>';
    }).join('');
    Array.prototype.forEach.call(el('ht-diem').querySelectorAll('canvas[data-canvas]'), gioKy);

    var com = c.commercials || {}, maTien = com.currency_thu || c.currency || 'VND';
    var dong = c.configured_cost_lines || [];
    el('ht-gia').innerHTML = loiGia
      ? '<div class="loi">Chưa đọc được hồ sơ giá (' + esc(loiGia) + '). Vẫn ký nhận được; '
        + 'phần giá do điều phối chốt lại.</div>'
      : '<table class="gia"><thead><tr><th>Khoản mục</th><th class="so">Chốt ban đầu</th>'
        + '<th class="so">Khách trả thêm</th></tr></thead><tbody>'
        + (dong.length ? dong.map(function (d, i) {
          return '<tr><td>' + esc(d.name) + '</td><td class="so">' + so(d.original_amount) + '</td>'
            + '<td class="so"><input type="number" min="0" step="1000" value="0" '
            + 'data-them="' + i + '" data-ten="' + esc(d.name) + '"></td></tr>';
        }).join('') : '<tr><td colspan="3">Chưa có khoản mục nào từ công thức.</td></tr>')
        + '</tbody></table>'
        + '<div class="tong"><span>Cước theo báo giá</span><span>'
        + esc(tien(com.base_selling_price, maTien)) + '</span></div>'
        + '<div class="tong cuoi"><span>Giá cuối (tạm tính)</span><span id="ht-giacuoi">'
        + esc(tien(com.base_selling_price, maTien)) + '</span></div>';
    Array.prototype.forEach.call(el('ht-gia').querySelectorAll('[data-them]'), function (i) {
      i.oninput = function () {
        var t = 0;
        Array.prototype.forEach.call(el('ht-gia').querySelectorAll('[data-them]'), function (x) {
          t += Number(x.value || 0) || 0;
        });
        el('ht-giacuoi').textContent = tien((Number(com.base_selling_price) || 0) + t, maTien);
      };
    });
  }

  /** Ô ký bằng ngón tay → ảnh PNG riêng. Máy chủ đòi ảnh chữ ký KHÁC ảnh biên bản, nên ký
   *  trực tiếp là cách hợp lý nhất trên điện thoại (khỏi phải chụp thêm một tấm). */
  function gioKy(canvas) {
    var n = canvas.getAttribute('data-canvas');
    var ty = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ty; canvas.height = canvas.clientHeight * ty;
    var ctx = canvas.getContext('2d');
    ctx.scale(ty, ty); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.strokeStyle = '#17181c';
    var dangVe = false, daVe = false;
    var diem = function (ev) {
      var h = canvas.getBoundingClientRect();
      var t = ev.touches ? ev.touches[0] : ev;
      return { x: t.clientX - h.left, y: t.clientY - h.top };
    };
    var batDau = function (ev) {
      ev.preventDefault(); dangVe = true; var p = diem(ev);
      ctx.beginPath(); ctx.moveTo(p.x, p.y);
    };
    var keo = function (ev) {
      if (!dangVe) return; ev.preventDefault(); var p = diem(ev);
      ctx.lineTo(p.x, p.y); ctx.stroke(); daVe = true;
      var o = el('ky-trangthai-' + n);
      o.textContent = 'Đã ký'; o.className = 'daky';
    };
    var ketThuc = function () { dangVe = false; hoSoKy.ky[n] = daVe; };
    canvas.addEventListener('pointerdown', batDau);
    canvas.addEventListener('pointermove', keo);
    canvas.addEventListener('pointerup', ketThuc);
    canvas.addEventListener('pointerleave', ketThuc);
    var xoa = el('ht-diem').querySelector('[data-xoaky="' + n + '"]');
    if (xoa) {
      xoa.onclick = function () {
        ctx.clearRect(0, 0, canvas.width, canvas.height); daVe = false; hoSoKy.ky[n] = false;
        var o = el('ky-trangthai-' + n);
        o.textContent = 'Chưa ký'; o.className = '';
      };
    }
  }

  function canvasThanhBlob(canvas) {
    return new Promise(function (ok) { canvas.toBlob(ok, 'image/png'); });
  }

  el('form-hoantat').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var r = hoSoKy.dong, c = hoSoKy.closeout || {};
    if (!r) return;
    var than = el('ht-diem'), canvasList = than.querySelectorAll('canvas[data-canvas]');
    var nut = el('nut-chot');
    var lay = function (n, k) { return than.querySelector('[data-ky="' + n + '-' + k + '"]'); };

    var dong = [], tep = [], thieu = '';
    Array.prototype.forEach.call(canvasList, function (cv) {
      var n = cv.getAttribute('data-canvas');
      var anh = lay(n, 'anh').files[0];
      if (!anh) { thieu = thieu || 'Điểm giao ' + n + ' chưa có ảnh biên bản.'; return; }
      if (!hoSoKy.ky[n]) { thieu = thieu || 'Điểm giao ' + n + ' chưa có chữ ký người nhận.'; return; }
      var luc = lay(n, 'luc').value;
      if (!luc) { thieu = thieu || 'Điểm giao ' + n + ' chưa nhập giờ giao.'; return; }
      dong.push({
        leg_id: lay(n, 'leg').value, vehicle_id: r.vehicle_id, stop_no: Number(n),
        delivery_time: new Date(luc).toISOString(),
        location_text: (r.legs || []).filter(function (l) { return l.id === lay(n, 'leg').value; })
          .map(function (l) { return l.destination; })[0] || r.destination || '',
        receiver_name: lay(n, 'nguoi').value, receiver_phone: lay(n, 'sdt').value,
        delivery_result: lay(n, 'ketqua').value,
        cargo_condition: lay(n, 'ghichu').value || 'Nguyên niêm phong',
        file_field: 'pod_' + n, signature_file_field: 'sig_' + n,
        note: 'Tài xế ký nhận trên trang tài xế'
      });
      tep.push({ ten: 'pod_' + n, ten_tep: 'pod-' + n + '.jpg', blob: anh });
    });
    if (thieu) { bao(thieu, 5000); return; }

    var phu = [];
    Array.prototype.forEach.call(el('ht-gia').querySelectorAll('[data-them]'), function (i) {
      var v = Number(i.value || 0) || 0;
      if (v > 0) {
        phu.push({
          name: i.getAttribute('data-ten'), original_amount: '0', actual_amount: String(v),
          note: 'Tài xế khai khi ký nhận'
        });
      }
    });

    nut.disabled = true;
    Promise.all(Array.prototype.map.call(canvasList, function (cv) { return canvasThanhBlob(cv); }))
      .then(function (cacKy) {
        var form = new FormData();
        form.append('payload', JSON.stringify({
          trip_id: r.trip_id,
          currency_code: (c.commercials && c.commercials.currency_thu) || c.currency || 'VND',
          pod_entries: dong, charge_adjustments: phu
        }));
        tep.forEach(function (t) { form.append(t.ten, t.blob, t.ten_tep); });
        Array.prototype.forEach.call(canvasList, function (cv, i) {
          form.append('sig_' + cv.getAttribute('data-canvas'), cacKy[i], 'chu-ky-' + (i + 1) + '.png');
        });
        return api('/api/delivery-orders/' + encodeURIComponent(r.do_id) + '/complete-delivery', {
          method: 'POST',
          headers: { 'Idempotency-Key': 'txe-hoantat-' + r.do_id + '-' + Date.now() },
          body: form
        });
      })
      .then(function (g) {
        if (!g.ok) { bao(loiCua(g), 7000); return; }
        var d = duLieu(g.than) || {};
        el('hop-hoantat').close();
        bao('Đã ký nhận và chốt giá cho ' + r.do_id
          + (d.commercials ? '. Giá cuối: ' + tien(d.commercials.final_selling_price,
            d.commercials.currency_code || 'VND') : '') + '.', 6000);
        dongChiTiet();
        return nap();
      })
      .catch(function (e) { bao('Không gửi được: ' + (e && e.message), 7000); })
      .then(function () { nut.disabled = false; });
  });

  // ------------------------------------------------------------------ nối nút
  Array.prototype.forEach.call(document.querySelectorAll('[data-dong]'), function (b) {
    b.onclick = function () { var d = b.closest('dialog'); if (d) d.close(); };
  });
  el('chon-taixe').onchange = function () {
    trangThai.taiXe = this.value;
    nho(TAIXE_LUU, trangThai.taiXe);
    veToi();
    if (trangThai.chon) dongChiTiet();
    nap();
  };
  el('nut-quaylai').onclick = dongChiTiet;
  var lamMoi = function () { nap().then(function () { bao('Đã cập nhật.'); }); };
  el('nut-capnhat').onclick = lamMoi;
  el('nut-capnhat-2').onclick = lamMoi;
  // Nút back của máy: đóng màn chi tiết thay vì rời trang.
  window.addEventListener('popstate', function () { if (trangThai.chon) dongChiTiet(); });

  napTaiXe().then(nap).catch(function (e) {
    loi('Không đọc được danh sách tài xế: ' + (e && e.message));
  });
  // Tự cập nhật khi quay lại tab — tài xế mở/tắt máy liên tục.
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && trangThai.taiXe) nap();
  });
})();
