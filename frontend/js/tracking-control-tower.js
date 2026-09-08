(function () {
  'use strict';
  const state = { items: [], kpis: {}, selected: '', filter: 'total', query: '', sort: 'priority', scope: 'all', mode: 'fleet', request: 0, routeRequest: 0, routeCache: {} };
  let map, layer, timer, mounted = false, incidentRow, baseLayers, currentBase = 'satellite', usedFallback = false;
  const el = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const date = value => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) : 'Chưa xác định';
  const metric = (v, unit) => v != null && Number.isFinite(Number(v)) ? `${Number(v).toLocaleString('vi-VN')} ${unit}` : 'Chưa có dữ liệu';
  const position = g => g && g.lat != null && g.lng != null && Number.isFinite(Number(g.lat)) && Number.isFinite(Number(g.lng)) && Math.abs(g.lat) <= 90 && Math.abs(g.lng) <= 180;
  const selected = () => state.items.find(r => r.key === state.selected);
  const base = () => typeof API_BASE !== 'undefined' ? API_BASE : '';
  // Bon trang thai GPS, khong ba. `simulated` la vi tri TINH doc theo tuyen khi
  // thiet bi khong gui gi con moi — no phai co nhan RIENG: goi no la "GPS moi
  // cap nhat" thi nguoi truc tin vao mot vi tri khong ai do duoc, con goi no la
  // "chua co vi tri" thi ho di goi tai xe cho mot xe dang hien binh thuong tren
  // ban do. Ca hai deu sai theo mot huong khac nhau.
  const gpsLabel = r => r.gps.status === 'fresh' ? 'GPS mới cập nhật'
    : r.gps.status === 'simulated' ? 'Vị trí mô phỏng theo tuyến'
    : r.gps.status === 'stale' ? 'GPS cũ / chưa rõ thời gian' : 'Chưa có vị trí GPS';
  // "Co vi tri dung duoc" = that con moi HOAC mo phong. Dung de loc va de xep
  // do uu tien, thay vi so `!== 'fresh'` o ba cho khac nhau roi lech nhau.
  const gpsOn = r => r.gps.status === 'fresh' || r.gps.status === 'simulated';
  const filters = [['total', 'DO theo chuyến'], ['overdue', 'Quá hạn giao'], ['gps_unavailable', 'GPS thiếu / cũ'], ['awaiting_pod', 'Đã đến · chờ POD'], ['incidents', 'Có sự cố mở'], ['returning', 'Đã giao · Trip còn mở']];
  const matches = (r, f) => ({ total: true, overdue: r.overdue, gps_unavailable: !gpsOn(r), awaiting_pod: r.awaiting_pod, incidents: r.open_incident_count > 0, returning: r.status === 'delivered' })[f];
  const severity = r => r.open_incident_count ? 'red' : r.overdue ? 'amber' : !gpsOn(r) ? 'gray' : r.awaiting_pod ? 'purple' : 'blue';
  const labels = { planned: 'Kế hoạch', ready: 'Sẵn sàng', in_transit: 'Đang vận chuyển', arrived: 'Đã đến', completed: 'Hoàn tất', cancelled: 'Đã hủy', delivered: 'Đã giao', dispatched: 'Đã điều phối', outbound: 'Lượt đi', delivery: 'Giao hàng', pickup: 'Lấy hàng', empty_return: 'Về rỗng', backhaul: 'Hàng chiều về', warehouse_transfer: 'Chuyển kho' };

  function mount() {
    if (mounted || !el('view-tracking')) return;
    mounted = true;
    const view = el('view-tracking');
    view.classList.add('ct-view');
    const root = document.createElement('div'); root.id = 'tracking-control-tower';
    root.innerHTML = `<header class="ct-header"><div><h2>Theo dõi và kiểm soát</h2><p>Chuyến · vị trí · bằng chứng giao hàng</p></div>
      <label class="ct-search"><i class="fa-solid fa-magnifying-glass"></i><input id="ct-search" type="search" placeholder="Tìm Trip, DO, khách, xe, tài xế" aria-label="Tìm chuyến"></label>
      <label class="ct-auto"><input id="ct-auto" type="checkbox"> Tự cập nhật 30 giây</label><button data-action="refresh"><i class="fa-solid fa-rotate"></i> Cập nhật</button><button class="ct-danger" data-action="incident"><i class="fa-solid fa-triangle-exclamation"></i> Báo sự cố</button></header>
      <div id="ct-status" role="status" aria-live="polite"></div><div id="ct-kpis" class="ct-kpis"></div>
      <div class="ct-board"><section class="ct-list-panel"><header class="ct-section-head"><h3>Chuyến đang theo dõi <span id="ct-count"></span></h3><div class="ct-segment" id="ct-sort" role="group" aria-label="Sắp xếp chuyến"><button data-sort="priority">Ưu tiên</button><button data-sort="due">Hạn giao</button><button data-sort="customer">Khách hàng</button></div></header><div id="ct-list"></div>
      <footer class="ct-legend-row"><small><i class="ct-dot ct-dot-red"></i>Cần xử lý · <i class="ct-dot ct-dot-amber"></i>Quá hạn · <i class="ct-dot ct-dot-purple"></i>Chờ POD · <i class="ct-dot ct-dot-gray"></i>Chưa có vị trí · <i class="ct-dot ct-dot-blue"></i>Đang chạy bình thường</small></footer></section>
      <section class="ct-map-panel"><header class="ct-section-head"><h3 id="ct-map-title">Bản đồ</h3><div class="ct-segment"><button data-mode="fleet">Đội xe</button><button data-mode="route">Tuyến đang chọn</button></div><select id="ct-basemap" aria-label="Nền bản đồ"><option value="satellite">Vệ tinh</option><option value="roads">Đường phố</option></select></header><div class="ct-maptools"><div class="ct-segment" id="ct-mapscope" role="group" aria-label="Phạm vi xe trên bản đồ"><button data-scope="all">Tất cả xe</button><button data-scope="problem">Chỉ có vấn đề</button></div><span class="ct-maplegend"><i class="ct-dot ct-dot-blue"></i>Đang chạy<i class="ct-dot ct-dot-amber"></i>Quá hạn<i class="ct-dot ct-dot-red"></i>Có sự cố<i class="ct-dot ct-dot-gray"></i>Chưa có vị trí</span></div><div id="ct-map-warning" role="status"></div><div id="ct-map" role="region" aria-label="Bản đồ GPS"></div><div id="ct-map-note" role="status"></div><div id="ct-route-strip"></div><div id="ct-metrics" class="ct-metrics"></div></section>
      <aside class="ct-detail-panel"><header class="ct-section-head"><h3>Hồ sơ chuyến</h3></header><div id="ct-detail"></div></aside></div>
      <dialog id="ct-incident"><form id="ct-incident-form"><header class="ct-section-head"><h3>Báo sự cố vận chuyển</h3><button type="button" data-action="close-incident" title="Đóng"><i class="fa-solid fa-xmark"></i></button></header><div class="ct-form-body"><p id="ct-incident-order"></p><div class="ct-form-grid">
      <label>Loại sự cố<select name="incident_type" required><option>Kẹt xe</option><option>Hỏng xe</option><option>Tai nạn</option><option>Thời tiết</option><option>Hàng hóa</option><option>Kiểm tra</option></select></label><label>Vị trí<input name="location" required maxlength="500"></label><label>Người báo cáo<input name="reporter" required maxlength="128"></label><label>Mức độ<select name="severity"><option>Medium</option><option>Low</option><option>High</option><option>Critical</option></select></label></div><label>Mô tả<textarea name="description" rows="5" maxlength="5000"></textarea></label><div id="ct-incident-error" role="alert"></div></div><footer><button type="button" data-action="close-incident">Hủy</button><button type="submit" class="ct-danger">Gửi báo cáo sự cố</button></footer></form></dialog>`;
    view.prepend(root);
    root.addEventListener('input', e => { if (e.target.id === 'ct-search') { state.query = e.target.value.toLocaleLowerCase('vi').trim(); render(); } });
    root.addEventListener('change', e => {

      if (e.target.id === 'ct-basemap') changeBasemap(e.target.value);
      if (e.target.id === 'ct-auto') {
        clearInterval(timer);
        if (e.target.checked) timer = setInterval(() => { if (!document.hidden && view.getClientRects().length && !el('ct-incident').open) load(); }, 30000);
      }
    });
    root.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.key) select(b.dataset.key);
      if (b.dataset.filter) { state.filter = b.dataset.filter; render(); }
      if (b.dataset.mode) { state.mode = b.dataset.mode; renderMap(); }
      if (b.dataset.sort) { state.sort = b.dataset.sort; render(); }
      // "Chi co van de" loc TREN BAN DO, khong loc ca danh sach: nguoi truc can
      // thay het chuyen o cot trai de doi chieu, nhung ban do co hai muoi diem
      // chong nhau thi khong nhin ra chuyen nao dang can xu.
      if (b.dataset.scope) { state.scope = b.dataset.scope; render(); }
      if (b.dataset.action === 'refresh') await load();
      if (b.dataset.action === 'incident') openIncident();
      if (b.dataset.action === 'close-incident') el('ct-incident').close();
      if (b.dataset.action === 'dispatch') window.switchView?.('dispatch');
      if (b.dataset.action === 'milestone') await ghiMocTiepTheo(b);
      if (b.dataset.action === 'completion') moHoanTatGiaoHang();
      if (b.dataset.document) await downloadDocument(b);
    });
    el('ct-incident-form').addEventListener('submit', saveIncident);
    render();
  }
  //: Bieu tuong cho tung moc — de nguoi dung nhan ra viec ke tiep bang hinh,
  //: khong phai doc chu. Moc nao khong co bieu tuong rieng thi dung dau cham
  //: tron: mot bieu tuong sai nghia con te hon khong co bieu tuong.
  const BIEU_TUONG_MOC = {
    check_in: '<i class="fa-solid fa-right-to-bracket"></i>',
    pickup: '<i class="fa-solid fa-boxes-packing"></i>',
    departure: '<i class="fa-solid fa-truck-fast"></i>',
    arrival: '<i class="fa-solid fa-map-pin"></i>',
    unloading: '<i class="fa-solid fa-dolly"></i>',
    delivered: '<i class="fa-solid fa-circle-check"></i>',
  };
  //: Hàm này trả về MARKUP, nên chèn thẳng — ĐỪNG bọc `esc()` quanh nó. Bọc thì
  //: nút hiện đúng chuỗi `<i class="fa-solid fa-dolly"></i> Ghi mốc: Dỡ hàng`
  //: thành chữ trên mặt nút (lỗi đã xảy ra thật). Không cần thoát vì `ma` chỉ
  //: dùng làm KHÓA tra bảng, không lọt vào chuỗi trả về; khóa lạ thì rơi vào
  //: dấu chấm tròn cố định.
  const bieuTuongMoc = ma => BIEU_TUONG_MOC[ma] || '<i class="fa-solid fa-circle"></i>';

  //: Moc nao thi xe dang o dau tren tuyen. Dung de gui kem toa do khi ghi moc —
  //: do chinh la cach "cap nhat vi tri bang nut" khi chua co GPS that.
  const TIEN_DO_MOC = {
    check_in: 0, pickup: 0, departure: 0.05, arrival: 1, unloading: 1, delivered: 1,
  };

  /**
   * Toa do tren tuyen ung voi mot ti le, can theo DO DAI tung chang.
   *
   * Cung phep noi suy nhu ben may chu (`services/gps_simulation.py`). Lam o day
   * de nut ghi moc gui kem mot toa do HOP LY: ghi moc "xuat ben" ma gui toa do
   * diem giao thi xe nhay tới dich ngay khi vua roi ben.
   */
  function toaDoTrenTuyen(r, tiLe) {
    const chang = (r.route_segments || []).filter(s =>
      s && s.from_lat != null && s.from_lng != null && s.to_lat != null && s.to_lng != null);
    if (!chang.length) return null;
    const diem = [[Number(chang[0].from_lat), Number(chang[0].from_lng), 0]];
    chang.forEach(s => diem.push([Number(s.to_lat), Number(s.to_lng), Number(s.dist_km) || 1]));
    const tong = diem.slice(1).reduce((t, d) => t + d[2], 0) || 1;
    let can = Math.max(0, Math.min(1, tiLe)) * tong, daQua = 0;
    for (let i = 1; i < diem.length; i += 1) {
      const km = diem[i][2] || 0;
      if (daQua + km >= can || i === diem.length - 1) {
        const p = km <= 0 ? 0 : Math.max(0, Math.min(1, (can - daQua) / km));
        return {
          lat: Number((diem[i - 1][0] + (diem[i][0] - diem[i - 1][0]) * p).toFixed(6)),
          lng: Number((diem[i - 1][1] + (diem[i][1] - diem[i - 1][1]) * p).toFixed(6)),
        };
      }
      daQua += km;
    }
    return null;
  }

  /**
   * GHI MOC KE TIEP cua chuyen, va cap nhat vi tri xe theo moc do.
   *
   * Chu du an chot: tam thoi khong co GPS that thi dung NUT de cap nhat vi tri.
   * Ham nay lam dung viec do — nhung khong dat truc tiep trang thai don. Duong
   * dung la ghi mot SU KIEN cua lenh van chuyen: may chu tu do dong bo trang
   * thai don, va su kien vao lich su chuyen. Dat thang trang thai thi duoc mot
   * nua — don doi mau nhung truc tien do van trong, va khong ai biet ai ghi luc
   * nao.
   *
   * `source: 'manual'` vi day la NGUOI bam, khong phai thiet bi gui. Ghi
   * 'device' cho mot lan bam tay la lam ban chinh cai dau vet minh vua tao.
   */
  async function ghiMocTiepTheo(nut) {
    const r = selected();
    if (!r || !r.next_milestone) return;
    if (!r.freight_order_id) {
      thongBao('Chuyến này chưa có lệnh vận chuyển nên chưa ghi được mốc nào.');
      return;
    }
    const moc = r.next_milestone;
    const xuongDong = String.fromCharCode(10, 10);
    if (!window.confirm(`Ghi mốc "${moc.ten}" cho ${r.do_id}?`
      + xuongDong
      + 'Mốc này vào lịch sử chuyến và cập nhật vị trí xe trên bản đồ. Không hoàn lại được.')) return;
    if (nut) nut.disabled = true;
    try {
      const than = {
        event_type: moc.ma,
        source: 'manual',
        expected_version: r.freight_order_version,
        event_time: new Date().toISOString(),
        location_text: moc.ma === 'check_in' || moc.ma === 'pickup'
          ? (r.origin || null) : (r.destination || null),
        speed_kmh: moc.ma === 'departure' ? 40 : 0,
        note: `Điều phối viên ghi mốc "${moc.ten}" trên màn Theo dõi`,
      };
      // Toa do theo dung moc: day la cach cap nhat vi tri khi chua co GPS that.
      const diem = toaDoTrenTuyen(r, TIEN_DO_MOC[moc.ma] != null ? TIEN_DO_MOC[moc.ma] : 0);
      if (diem) { than.lat = diem.lat; than.lng = diem.lng; }
      else if (r.gps && r.gps.lat != null) { than.lat = r.gps.lat; than.lng = r.gps.lng; }
      const tra = await fetch(`${base()}/api/tms/freight-orders/${encodeURIComponent(r.freight_order_id)}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': `moc-${r.freight_order_id}-${moc.ma}-${Date.now()}` },
        body: JSON.stringify(than),
      });
      const goi = await tra.json().catch(() => ({}));
      if (!tra.ok) {
        // Noi RA loi cua may chu. Ba loi hay gap o day la sai thu tu moc, sai
        // phien ban, va ngoai khung phan cong — ba viec phai xu khac nhau, nen
        // mot cau "co loi xay ra" thi nguoi dung khong biet lam gi tiep.
        thongBao((goi.error && goi.error.message) || `Không ghi được mốc "${moc.ten}" (HTTP ${tra.status}).`);
        return;
      }
      thongBao(`Đã ghi mốc "${moc.ten}" cho ${r.do_id} và cập nhật vị trí xe.`);
      await load();
    } catch (loi) {
      thongBao('Không gọi được máy chủ: ' + (loi && loi.message));
    } finally {
      if (nut) nut.disabled = false;
    }
  }

  /**
   * Mo form hoan tat giao hang (POD, ky nhan, chot gia) cho DON DANG CHON.
   *
   * Truyen theo ma don, khong chi doi man: man Hoan tat giao hang co the dang
   * chon mot don khac, va nguoi dung se ky POD cho don sai. Dua ma don sang
   * roi de man do tu chon.
   */
  function moHoanTatGiaoHang() {
    const r = state.items.find(x => x.key === state.selected);
    window.switchView?.('delivery-completion');
    if (r && r.do_id) {
      // Cho man kia nap xong roi moi chon — chon ngay thi danh sach con rong.
      setTimeout(() => {
        if (typeof window.selectCompletionDO === 'function') window.selectCompletionDO(r.do_id);
        else if (typeof window.chonDonHoanTat === 'function') window.chonDonHoanTat(r.do_id);
      }, 400);
    }
  }

  function thongBao(chu) {
    if (typeof window.showToast === 'function') window.showToast(chu);
    else window.alert(chu);
  }

  function visible() {
    const priority = r => (r.open_incident_count ? 8 : 0) + (r.overdue ? 4 : 0) + (!gpsOn(r) ? 2 : 0) + (r.awaiting_pod ? 1 : 0);
    return state.items.filter(r => matches(r, state.filter) && (!state.query || [r.trip_id, r.do_id, r.customer_name, r.vehicle_id, r.driver_name, r.route_name].join(' ').toLocaleLowerCase('vi').includes(state.query))).sort((a, b) => {
      if (state.sort === 'customer') return String(a.customer_name || '').localeCompare(String(b.customer_name || ''), 'vi');
      if (state.sort === 'due') return (Date.parse(a.delivery_due) || Infinity) - (Date.parse(b.delivery_due) || Infinity);
      return priority(b) - priority(a) || a.do_id.localeCompare(b.do_id);
    });
  }
  function render() {
    if (!mounted) return;
    const rows = visible();
    if (state.selected && !rows.some(r => r.key === state.selected)) state.selected = '';
    el('ct-kpis').innerHTML = filters.map(([key, label]) => `<button class="ct-kpi" data-filter="${key}" aria-pressed="${state.filter === key}"><span>${label}</span><b>${state.kpis[key] ?? '—'}</b></button>`).join('');
    el('ct-count').textContent = rows.length;
    document.querySelectorAll('#ct-sort [data-sort]').forEach(b => {
      b.setAttribute('aria-pressed', b.dataset.sort === state.sort);
      b.classList.toggle('on', b.dataset.sort === state.sort);
    });
    el('ct-list').innerHTML = rows.map(r => {
      const done = r.legs.filter(l => l.status === 'completed').length;
      return `<button data-key="${esc(r.key)}" class="ct-trip ${severity(r)}" aria-pressed="${r.key === state.selected}"><strong>${esc(r.trip_id || r.do_id)}</strong><span>${esc(r.do_id)} · ${esc(r.customer_name || 'Chưa gán khách')}</span><span>${esc(r.route_name || [r.origin, r.destination].filter(Boolean).join(' → ') || 'Chưa có tuyến')}</span><span>${esc(r.vehicle_id || 'Chưa gán xe')} · ${esc(r.driver_name || 'Chưa gán tài xế')}</span><small>${esc(r.open_incident_count ? `${r.open_incident_count} sự cố chưa đóng` : r.overdue ? 'Quá hạn giao' : r.awaiting_pod ? 'Đã đến · chờ POD' : gpsLabel(r))}</small>${r.legs.length ? `<progress value="${done}" max="${r.legs.length}" aria-label="Chặng đã hoàn tất"></progress><span>${done}/${r.legs.length} chặng hoàn tất</span>` : ''}<span>Hạn giao: ${esc(date(r.delivery_due))}</span></button>`;
    }).join('') || '<p class="ct-empty">Không có chuyến phù hợp.</p>';
    renderDetail(); renderMap();
  }
  const pair = (label, value) => `<div><span>${label}</span><b>${esc(value || 'Chưa có dữ liệu')}</b></div>`;
  /**
   * NAM so lieu ca doi xe, hien khi chua chon chuyen nao — dung nhu dai
   * `mapinfo` cua ban mau.
   *
   * Ban mau co nam o: toc do TB doi, xe dung qua hai muoi phut, tre TB so han,
   * km hom nay, POD da ky hom nay. HAI trong nam o do KHONG dung duoc:
   *
   *   · "Xe dung qua 20 phut" doi lich su dung do cua tung xe — he thong khong
   *     luu vet GPS theo thoi gian, chi luu diem cuoi.
   *   · "Tre TB so han" doi mot du bao ETA that; `predicted_eta` cua may chu
   *     dang la `null`, va lay gio ke hoach lam du bao thi con so luon bang 0.
   *
   * Thay bang hai o co du lieu that: so xe dang theo doi, va so chuyen co vi
   * tri ve duoc. Dien mot con so bia vao mot o cho giong ban mau thi ca dai
   * mat tin — nguoi doc khong biet o nao thi tin duoc.
   */
  function soLieuDoiXe() {
    const rows = visible();
    const coViTri = rows.filter(x => position(x.gps));
    const dangChay = coViTri.filter(x => Number(x.gps.speed_kmh) > 0);
    const tocDoTB = dangChay.length
      ? Math.round(dangChay.reduce((t, x) => t + Number(x.gps.speed_kmh || 0), 0) / dangChay.length)
      : null;
    // Km da di hom nay: suy tu phan tram tien do cua tung chuyen. Chi tinh
    // nhung chuyen CO phan tram — chuyen khong biet di duoc bao nhieu thi khong
    // duoc coi la di duoc 0 km, do la hai chuyen khac nhau.
    const coTienDo = rows.filter(x => x.gps.progress_percent != null && x.route_distance_km);
    const kmDaDi = coTienDo.length
      ? Math.round(coTienDo.reduce((t, x) => t + Number(x.route_distance_km) * Number(x.gps.progress_percent) / 100, 0))
      : null;
    const podDaKy = rows.reduce((t, x) => t + (x.pod_count || 0), 0);
    const canPod = rows.filter(x => x.awaiting_pod).length;
    return pair('Xe đang theo dõi', String(state.kpis.vehicles ?? '—'))
      + pair('Chuyến có vị trí', `${coViTri.length} / ${rows.length}`)
      + pair('Tốc độ TB xe đang chạy', tocDoTB == null ? 'Chưa có xe nào đang chạy' : `${tocDoTB} km/h`)
      + pair('Km đã đi hôm nay', kmDaDi == null ? 'Chưa tính được' : `${kmDaDi.toLocaleString('vi-VN')} km`)
      + pair('POD đã ký', `${podDaKy} · còn ${canPod} chờ ký`);
  }

  //: Nhan nguon su kien. May chu chi co hai nguon that (`device`, `manual`), nen
  //: chi ve hai nhan do. Ban mau con co nhan `app` — khong co nguon nao nhu vay
  //: trong he thong, va ve mot nhan cho mot nguon khong ton tai la noi rang du
  //: lieu den tu mot cho ma nguoi doc khong tra lai duoc.
  const nguonSuKien = { device: 'GPS', manual: 'thủ công' };

  /**
   * DAI SO LIEU GPS o dau ho so — Toc do · Da di · Con · ETA.
   *
   * Ban mau co dai nay va no dang hoc: bon con so tra loi dung bon cau hoi dau
   * tien nguoi truc hoi ve mot chuyen dang chay. Truoc day ho so khong co no,
   * nguoi dung phai doc trong doan chu "Can chu y" de suy ra.
   */
  function daiGps(r) {
    const km = Number(r.route_distance_km || 0);
    const pt = r.gps.progress_percent;
    const daDi = (km && pt != null) ? `${(km * pt / 100).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} km` : '—';
    const con = r.gps.remaining_km != null
      ? `${Number(r.gps.remaining_km).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} km` : '—';
    const eta = r.predicted_eta && Number.isFinite(Date.parse(r.predicted_eta))
      ? new Date(r.predicted_eta).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' })
      : '—';
    const toc = r.gps.speed_kmh != null ? `${Number(r.gps.speed_kmh).toLocaleString('vi-VN')} km/h` : '—';
    return `<div class="ct-gpsbar">
      <div class="ct-gpsbar-head"><span>GPS</span><button data-action="refresh" class="ct-link" title="Đọc lại dữ liệu máy chủ"><i class="fa-solid fa-rotate"></i> cập nhật</button></div>
      <div class="ct-gpsgrid">
        <div><span>Tốc độ</span><b>${esc(toc)}</b></div>
        <div><span>Đã đi</span><b>${esc(daDi)}</b></div>
        <div><span>Còn</span><b>${esc(con)}</b></div>
        <div><span>ETA</span><b>${esc(eta)}</b></div>
      </div></div>`;
  }

  /**
   * TRUC TIEN DO VA BANG CHUNG — gop moc DA GHI voi moc CON PHAI GHI.
   *
   * Ban mau ve mot truc duy nhat trong do cac buoc da qua, buoc dang lam va buoc
   * chua tới nam cung mot cho, moi buoc co nhan nguon (`GPS` / `thu cong`) va so
   * anh kem theo. Ban truoc cua man nay tach thanh HAI khoi roi nhau — "Tien do
   * chang" va "Su kien thuc te" — nen nguoi doc phai tu ghep xem chuyen dang o
   * buoc nao va buoc ke tiep la gi.
   *
   * Ba trang thai cua moc, va vi sao phai phan biet:
   *   · `done` — da ghi, co gio va nguon that.
   *   · `now`  — moc KE TIEP can ghi. Day la thu nguoi truc can thay nhat, vi no
   *              la viec cua ho.
   *   · `todo` — chua tới, lam mo va khong ghi gio that (chi ghi gio du kien).
   *
   * Buoc POD dat o CUOI truc: no khong nam trong chuoi moc cua may chu, nhung
   * trong nghiep vu thi day la buoc cuoi that — chua ky POD thi chuyen khong
   * doi soat duoc.
   */
  function trucTienDo(r) {
    const daGhi = new Map((r.events || []).map(e => [e.type, e]));
    const moc = (r.milestones || []).map(m => {
      const e = daGhi.get(m.ma);
      const laKeTiep = r.next_milestone && r.next_milestone.ma === m.ma;
      return {
        ten: e && e.location ? e.location : m.ten,
        loai: e ? 'done' : (laKeTiep ? 'now' : 'todo'),
        gio: e ? date(e.time) : '',
        nguon: e ? (nguonSuKien[e.source] || e.source || '') : '',
        anh: e ? (e.document_count || 0) : 0,
        ghiChu: e && e.note && e.note !== e.location ? e.note : '',
      };
    });
    // Buoc POD, ghep tu so ban ghi POD that.
    moc.push({
      ten: 'POD · ký nhận giao hàng',
      loai: (r.pod_count || 0) > 0 ? 'done' : (r.status === 'arrived' ? 'now' : 'todo'),
      gio: (r.pods || [])[0] ? date(r.pods[0].time) : '',
      nguon: (r.pod_count || 0) > 0 ? 'thủ công' : '',
      anh: (r.pods || []).reduce((t, p) => t + ((p.documents || []).length), 0),
      ghiChu: (r.pod_count || 0) > 0 ? '' : 'Chưa ký nhận',
    });

    return `<h4>Tiến độ và bằng chứng <small class="ct-src-note">${Object.values(nguonSuKien).join(' · ')}</small></h4>
      <ol class="ct-track">${moc.map(m => `<li class="${m.loai}">
        <div class="ct-track-head"><strong>${esc(m.ten)}</strong>${m.gio ? `<em>${esc(m.gio)}</em>` : ''}${m.nguon ? `<span class="ct-src">${esc(m.nguon)}</span>` : ''}</div>
        ${m.ghiChu ? `<span>${esc(m.ghiChu)}</span>` : ''}
        ${m.anh ? `<span class="ct-track-photo">${'<i></i>'.repeat(Math.min(m.anh, 4))} ${m.anh} ảnh / chứng từ</span>` : ''}
      </li>`).join('')}</ol>`;
  }

  function renderDetail() {
    const r = selected();
    document.querySelectorAll('#tracking-control-tower [data-action="incident"]').forEach(b => { b.disabled = !r || !r.vehicle_id; });
    if (!r) { el('ct-detail').innerHTML = '<p class="ct-empty">Chưa chọn chuyến.</p>'; el('ct-metrics').innerHTML = soLieuDoiXe(); return; }
    const phone = String(r.driver_phone || '').replace(/[^+0-9]/g, '');
    el('ct-detail').innerHTML = `<div class="ct-summary">${pair('Trip', r.trip_id)}${pair('DO · khách hàng', `${r.do_id} · ${r.customer_name || ''}`)}${pair('Tuyến', r.route_name)}${pair('Hạn giao', date(r.delivery_due))}</div>
      <h4>Tổ lái</h4><div class="ct-crew"><div><strong>${esc(r.driver_name || 'Chưa gán tài xế')}</strong><span>${esc(r.vehicle_id || 'Chưa gán xe')} · Phụ xe: ${esc(r.co_driver_name || 'Chưa gán')}</span></div>${phone ? `<a href="tel:${phone}" title="Gọi tài xế"><i class="fa-solid fa-phone"></i></a>` : ''}</div>
      ${daiGps(r)}
      <h4>Cần chú ý</h4><div class="ct-alert ${r.gps.status === 'fresh' ? 'blue' : 'amber'}">${esc(gpsLabel(r))}<br><small>Vị trí cuối: ${esc(date(r.gps.last_update))}</small></div>${r.overdue ? '<div class="ct-alert amber">Đã quá hạn giao trên DO, chưa ghi nhận giao hoàn tất.</div>' : ''}
      ${r.incidents.map(i => `<div class="ct-alert red"><strong>${esc(i.incident_type)}</strong> · ${esc(i.status)}<br>${esc(i.description || i.location || '')}</div>`).join('')}
      <h4>Chặng của chuyến</h4><ol class="ct-timeline">${r.legs.map(l => `<li class="${l.status === 'completed' ? 'done' : ''}"><strong>${esc(l.origin)} → ${esc(l.destination)}</strong><span>${esc(labels[l.status] || l.status)} · ${esc(labels[l.type] || l.type)}</span><small>${l.actual_arrival_at ? 'Thực tế' : 'Kế hoạch'}: ${esc(date(l.actual_arrival_at || l.planned_arrival_at))}</small></li>`).join('') || '<li>Chưa có chặng Trip.</li>'}</ol>
      ${trucTienDo(r)}
      <h4>Bằng chứng giao hàng · ${r.pod_count || 0}</h4>${(r.pods || []).map(p => `<div class="ct-pod"><strong>${esc(p.receiver_name || 'Chưa có người nhận')}</strong><span>${esc(p.location || '')} · ${esc(date(p.time))}</span>${p.documents.map(d => `<button data-document="${esc(d.id)}" data-name="${esc(d.file_name)}" title="Tải chứng từ POD"><i class="fa-solid fa-download"></i> ${esc(d.file_name)}</button>`).join('')}</div>`).join('') || '<p>Chưa có bản ghi POD của chuyến này.</p>'}<div class="ct-actions">${r.next_milestone ? `<button class="ct-primary" data-action="milestone" title="Ghi mốc thật vào lịch sử chuyến và cập nhật vị trí xe">${bieuTuongMoc(r.next_milestone.ma)} Ghi mốc: ${esc(r.next_milestone.ten)}</button>` : ''}<button data-action="completion" ${r.status === 'arrived' ? '' : 'disabled'} title="${r.status === 'arrived' ? 'Mở form ký nhận POD và chốt giá' : 'Phải ghi nhận xe đã đến nơi trước khi ký POD'}"><i class="fa-solid fa-file-signature"></i> Mở hoàn tất giao hàng</button><button data-action="incident" ${!r.vehicle_id ? 'disabled' : ''}><i class="fa-solid fa-triangle-exclamation"></i> Báo sự cố</button><button data-action="dispatch"><i class="fa-solid fa-arrow-left"></i> Mở Điều phối</button></div>`;
    el('ct-metrics').innerHTML = pair(r.gps.status === 'fresh' ? 'Tốc độ ghi nhận' : 'Tốc độ lần cuối', metric(r.gps.speed_kmh, 'km/h')) + pair('Tổng tuyến kế hoạch', metric(r.route_distance_km, 'km')) + pair('Đến theo kế hoạch', date(r.planned_arrival_at)) + pair('ETA từ GPS', 'Chưa có nguồn dự báo');
  }
  function renderMap() {
    if (!map && window.L) {
      el('ct-map').innerHTML = '';
      map = L.map('ct-map').setView([10.8, 106.7], 9);
      baseLayers = {
        roads: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }),
        satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' }),
      };
      Object.entries(baseLayers).forEach(([name, tiles]) => tiles.on('tileerror', () => {
        if (name !== currentBase) return;
        if (name === 'roads' && !usedFallback) {
          usedFallback = true; changeBasemap('satellite');
          el('ct-map-warning').textContent = 'Không kết nối được OpenStreetMap. Đã chuyển sang nền vệ tinh Esri.';
        } else el('ct-map-warning').textContent = 'Chưa tải được một phần nền bản đồ. Vui lòng kiểm tra kết nối hoặc đổi nền.';
      }));
      baseLayers.satellite.addTo(map);
      el('ct-basemap').value = 'satellite';
      layer = L.layerGroup().addTo(map);
    }
    document.querySelectorAll('#tracking-control-tower [data-mode]').forEach(b => {
      b.setAttribute('aria-pressed', b.dataset.mode === state.mode);
      b.classList.toggle('on', b.dataset.mode === state.mode);
    });
    document.querySelectorAll('#tracking-control-tower [data-scope]').forEach(b => {
      b.setAttribute('aria-pressed', b.dataset.scope === state.scope);
      b.classList.toggle('on', b.dataset.scope === state.scope);
    });
    el('ct-basemap').disabled = !window.L;
    // "Chi co van de" = co su co, hoac qua han, hoac khong co vi tri dung duoc.
    // KHONG tinh "cho POD" la van de tren ban do: xe da do o diem giao roi, ve
    // no thanh mot diem canh bao giua ban do thi nguoi truc di tim mot xe dang
    // dung yen dung cho.
    const coVanDe = x => x.open_incident_count > 0 || x.overdue || !gpsOn(x);
    const r = selected();
    let rows = state.mode === 'route' ? r ? [r] : [] : visible();
    if (state.mode !== 'route' && state.scope === 'problem') rows = rows.filter(coVanDe);
    el('ct-map-title').textContent = state.mode === 'route' ? 'Tuyến tham chiếu' : 'Bản đồ đội xe';
    el('ct-map-note').textContent = !window.L ? 'Chưa tải được thư viện bản đồ.' : state.mode === 'route' ? 'Đường xanh: tuyến kế hoạch theo điểm trạm Master Data, không phải vệt GPS live hay kết luận lệch tuyến.' : (state.scope === 'problem' && !rows.length
      // Noi THANG khi bo loc lam trong ban do. "0/0 chuyen co vi tri" la dung
      // du lieu nhung doc ra nhu bo loc hong — nguoi dung se bam lai vai lan roi
      // tuong man hinh loi, trong khi cau tra loi that la "khong co van de nao".
      ? 'Không có chuyến nào đang có vấn đề — không xe nào lệch hạn, mất vị trí hay có sự cố mở. Bấm "Tất cả xe" để xem lại toàn đội.'
      : `${rows.filter(r => position(r.gps)).length}/${rows.length} chuyến có vị trí · ${rows.filter(r => r.gps.status === 'simulated').length} điểm mô phỏng theo tuyến${state.scope === 'problem' ? ' · đang lọc: chỉ chuyến có vấn đề' : ''}. Chưa có GPS: không vẽ xe.`);
    if (!map) {
      el('ct-map').innerHTML = '<div class="ct-empty">Chưa tải được bản đồ. Danh sách và hồ sơ chuyến vẫn có thể tra cứu.</div>';
      return;
    }
    layer.clearLayers(); const bounds = [];
    rows.forEach(item => {
      if (!position(item.gps)) return;
      const point = [Number(item.gps.lat), Number(item.gps.lng)]; bounds.push(point);
      const mau = { red: '#d32f2f', amber: '#ef9f27', purple: '#7c3aed', gray: '#788493', blue: '#1a73e8' }[severity(item)] || '#1a73e8';
      // HUY HIEU XE, khong phai mot vong tron nho — va ve TREN CUNG.
      //
      // Ban truoc dung `L.circleMarker` ban kinh 8px, ve TRUOC cac co diem dau
      // va diem den (divIcon 34px). Voi mot chuyen DA DEN NOI thi xe nam dung
      // duoi co diem den va bi phu kin: do duoc tren man hinh — che do "Tuyen
      // dang chon" chi thay duong va hai co, khong thay xe o dau ca.
      //
      // `zIndexOffset` cao dua huy hieu len tren moi diem tram, va bien so hien
      // san khi dang xem mot tuyen — dung nhu ban mau, de doi chieu duoc xe nao
      // dang o dau ma khong phai re chuot tung diem.
      const noi = item.key === state.selected;
      const bien = esc(item.vehicle_id || item.do_id);
      L.marker(point, {
        zIndexOffset: noi ? 1200 : 1000,
        icon: L.divIcon({
          className: '',
          html: `<span class="ct-veh-marker${noi ? ' on' : ''}" style="--ct-marker:${mau}"><i class="fa-solid fa-truck"></i></span>`,
          iconSize: [30, 30], iconAnchor: [15, 15],
        }),
      }).bindTooltip(`${bien} · ${esc(gpsLabel(item))}`,
        state.mode === 'route' ? { permanent: true, direction: 'right', offset: [14, 0], className: 'ct-veh-label' } : {})
        .on('click', () => select(item.key)).addTo(layer);
    });
    if (state.mode === 'route' && r) {
      const waypoints = routeWaypoints(r);
      const points = waypoints.map(w => [w.lat, w.lng]);
      if (points.length > 1) {
        waypoints.forEach((w, index) => {
          const role = index === 0 ? 'origin' : index === waypoints.length - 1 ? 'destination' : 'stop';
          const color = role === 'origin' ? '#dc2626' : role === 'destination' ? '#059669' : '#1d4ed8';
          const glyph = role === 'origin' ? '<i class="fa-solid fa-flag"></i>' : role === 'destination' ? '<i class="fa-solid fa-flag-checkered"></i>' : String(index + 1);
          L.marker([w.lat, w.lng], { icon: L.divIcon({ className: '', html: `<span class="ct-route-marker" style="--ct-marker:${color}">${glyph}</span>`, iconSize: [34, 34], iconAnchor: [17, 17] }) }).bindTooltip(`${esc(w.label)} · ${role === 'origin' ? 'Điểm đi' : role === 'destination' ? 'Điểm đến' : 'Điểm trung chuyển'}`).addTo(layer);
        });
        el('ct-route-strip').innerHTML = waypoints.map((w, index) => `<span><b>${index + 1}</b>${esc(w.label)}</span>`).join('<i class="fa-solid fa-arrow-right"></i>');
        bounds.push(...points);
        drawRoadRoute(r.key, points);
      }
      else el('ct-map-note').textContent = 'Tuyến chưa đủ tọa độ tham chiếu để vẽ. Không suy diễn đường đi từ tên địa điểm.';
    } else {
      el('ct-route-strip').innerHTML = '';
    }
    requestAnimationFrame(() => { map.invalidateSize(); if (bounds.length) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13, animate: false }); });
  }
  function routeWaypoints(r) {
    const points = [];
    (r.route_segments || []).forEach(s => {
      const from = { lat: s.from_lat ?? s.origin_lat, lng: s.from_lng ?? s.origin_lng, label: s.from || s.origin };
      const to = { lat: s.to_lat ?? s.destination_lat, lng: s.to_lng ?? s.destination_lng, label: s.to || s.destination };
      if (position(from) && (!points.length || points[points.length - 1].label !== from.label)) points.push({ lat: Number(from.lat), lng: Number(from.lng), label: from.label || 'Điểm tuyến' });
      if (position(to) && (!points.length || points[points.length - 1].label !== to.label)) points.push({ lat: Number(to.lat), lng: Number(to.lng), label: to.label || 'Điểm tuyến' });
    });
    return points;
  }
  async function drawRoadRoute(key, fallbackPoints) {
    const token = ++state.routeRequest;
    const cacheKey = fallbackPoints.map(([lat, lng]) => `${lat.toFixed(5)},${lng.toFixed(5)}`).join('|');
    try {
      let roadPoints = state.routeCache[cacheKey];
      if (!roadPoints) {
        const coords = fallbackPoints.map(([lat, lng]) => `${lng},${lat}`).join(';');
        const response = await fetch(`https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`);
        const data = await response.json();
        if (!response.ok || !Array.isArray(data.routes) || !data.routes[0]?.geometry?.coordinates) {
          throw new Error(data.message || `HTTP ${response.status}`);
        }
        roadPoints = data.routes[0].geometry.coordinates
          .map(([lng, lat]) => [Number(lat), Number(lng)])
          .filter(([lat, lng]) => position({ lat, lng }));
        if (roadPoints.length < 2) throw new Error('OSRM không trả đủ điểm tuyến.');
        state.routeCache[cacheKey] = roadPoints;
      }
      if (token !== state.routeRequest || key !== state.selected || state.mode !== 'route') return;
      L.polyline(roadPoints, { color: '#1a73e8', weight: 5, opacity: 0.88 }).addTo(layer);
      el('ct-map-note').textContent = 'Đường xanh: tuyến kế hoạch theo chuẩn đường xe chạy từ OSRM. Đây chưa phải vệt GPS live.';
      requestAnimationFrame(() => { map.invalidateSize(); map.fitBounds(roadPoints, { padding: [30, 30], maxZoom: 13, animate: false }); });
    } catch (error) {
      if (token !== state.routeRequest || key !== state.selected || state.mode !== 'route') return;
      L.polyline(fallbackPoints, { color: '#1a73e8', weight: 4, opacity: 0.7, dashArray: '6 8' }).addTo(layer);
      el('ct-map-note').textContent = `Chưa gọi được OSRM, đang vẽ nối điểm trạm Master Data để đối chiếu: ${error.message}`;
    }
  }
  function changeBasemap(name) {
    if (!map || !baseLayers?.[name]) return;
    Object.values(baseLayers).forEach(tiles => { if (map.hasLayer(tiles)) map.removeLayer(tiles); });
    currentBase = name; el('ct-basemap').value = name;
    el('ct-map-warning').textContent = '';
    baseLayers[name].addTo(map);
  }
  function select(key) { state.selected = key; if (selected()?.route_segments?.length) state.mode = 'route'; render(); }
  async function load(doId) {
    mount(); if (!mounted) return;
    const request = ++state.request; el('ct-status').textContent = 'Đang đọc dữ liệu máy chủ…';
    try {
      const response = await fetch(`${base()}/api/tracking/control-tower`), payload = await response.json();
      if (!response.ok) throw new Error(payload.error?.message || payload.detail?.message || (typeof payload.detail === 'string' && payload.detail) || `HTTP ${response.status}`);
      if (!Array.isArray(payload.items) || !payload.kpis) throw new Error('Dữ liệu theo dõi không đúng định dạng.');
      if (request !== state.request) return;
      state.items = payload.items; state.kpis = payload.kpis;
      if (doId) {
        state.filter = 'total'; state.query = ''; el('ct-search').value = '';
        state.selected = state.items.find(r => r.do_id === doId)?.key || '';
      }
      el('ct-status').textContent = `Dữ liệu máy chủ: ${date(payload.generated_at)} · GPS quá 15 phút được đánh dấu cũ.`;
    } catch (error) {
      if (request !== state.request) return;
      state.items = []; state.kpis = {}; state.selected = '';
      el('ct-status').textContent = `Không tải được dữ liệu: ${error.message}. Chưa xác nhận được trạng thái chuyến.`;
    }
    render();
  }
  function openIncident() {
    incidentRow = selected(); if (!incidentRow?.vehicle_id) return;
    const form = el('ct-incident-form'); form.reset();
    el('ct-incident-order').textContent = `${incidentRow.do_id} · ${incidentRow.vehicle_id}`;
    form.elements.location.value = position(incidentRow.gps) && incidentRow.gps.status === 'fresh' ? `${incidentRow.gps.lat}, ${incidentRow.gps.lng}` : '';
    el('ct-incident-error').textContent = ''; el('ct-incident').showModal();
  }
  async function saveIncident(event) {
    event.preventDefault(); const form = event.target, button = form.querySelector('[type="submit"]');
    if (button.disabled || !incidentRow) return; button.disabled = true;
    try {
      const response = await fetch(`${base()}/api/incidents`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...Object.fromEntries(new FormData(form)), do_id: incidentRow.do_id, vehicle_id: incidentRow.vehicle_id }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || data.detail?.message || (typeof data.detail === 'string' && data.detail) || `HTTP ${response.status}`);
      el('ct-incident').close(); await load();
    } catch (error) { el('ct-incident-error').textContent = `Chưa xác nhận lưu báo cáo: ${error.message}`; }
    finally { button.disabled = false; }
  }
  async function downloadDocument(button) {
    button.disabled = true;
    try {
      const response = await fetch(`${base()}/api/pod-documents/${encodeURIComponent(button.dataset.document)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = button.dataset.name; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { el('ct-status').textContent = `Không tải được chứng từ POD: ${error.message}`; }
    finally { button.disabled = false; }
  }
  window.TrackingControlTower = { load, select, render };
})();
