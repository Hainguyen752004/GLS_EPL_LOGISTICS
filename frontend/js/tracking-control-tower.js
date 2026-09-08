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
      if (b.dataset.action === 'arrive') await ghiNhanDaDenNoi(b);
      if (b.dataset.action === 'completion') moHoanTatGiaoHang();
      if (b.dataset.document) await downloadDocument(b);
    });
    el('ct-incident-form').addEventListener('submit', saveIncident);
    render();
  }
  /**
   * Ghi nhan XE DA DEN NOI.
   *
   * Khong dat truc tiep trang thai don. Duong dung la ghi mot SU KIEN `arrival`
   * cua lenh van chuyen: may chu tu do dong bo don sang "Da den noi — cho POD",
   * va su kien do vao lich su chuyen. Dat thang trang thai thi duoc mot nua —
   * don doi mau nhung muc "Su kien thuc te" van trong, va khong ai biet ai ghi
   * luc nao.
   *
   * `source: 'manual'` vi day la NGUOI bam, khong phai thiet bi gui. Ghi
   * 'device' cho mot lan bam tay la lam ban chinh cai dau vet minh vua tao.
   */
  async function ghiNhanDaDenNoi(nut) {
    const r = state.items.find(x => x.key === state.selected);
    if (!r) return;
    if (!r.freight_order_id) {
      thongBao('Chuyến này chưa có lệnh vận chuyển nên chưa ghi được mốc đã đến nơi.');
      return;
    }
    const xuongDong = String.fromCharCode(10, 10);
    if (!window.confirm(`Ghi nhận xe đã đến ${r.destination || 'điểm giao'} cho ${r.do_id}?`
      + xuongDong
      + 'Sau bước này đơn chuyển sang "Đã đến nơi — chờ POD" và mở được form ký nhận.')) return;
    if (nut) nut.disabled = true;
    try {
      const than = {
        event_type: 'arrival',
        source: 'manual',
        expected_version: r.freight_order_version,
        event_time: new Date().toISOString(),
        location_text: r.destination || null,
        speed_kmh: 0,
        note: 'Điều phối viên ghi nhận xe đã tới điểm giao',
      };
      // Gui kem toa do dang co, neu co: mot moc "da den" khong toa do thi ban do
      // khong ve duoc diem den, va nguoi doc sau khong biet xe dung o dau.
      if (r.gps && r.gps.lat != null && r.gps.lng != null) {
        than.lat = r.gps.lat; than.lng = r.gps.lng;
      }
      const tra = await fetch(`${base()}/api/tms/freight-orders/${encodeURIComponent(r.freight_order_id)}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `arrive-${r.freight_order_id}-${Date.now()}`,
        },
        body: JSON.stringify(than),
      });
      const goi = await tra.json().catch(() => ({}));
      if (!tra.ok) {
        // Noi RA loi cua may chu, khong noi "co loi xay ra": ba loi hay gap o
        // day la sai thu tu su kien, sai phien ban, va ngoai khung phan cong —
        // ba viec phai xu khac nhau.
        thongBao((goi.error && goi.error.message) || `Không ghi được mốc đã đến nơi (HTTP ${tra.status}).`);
        return;
      }
      thongBao(`Đã ghi nhận ${r.do_id} tới ${r.destination || 'điểm giao'}. Giờ mở được form ký nhận POD.`);
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

  function renderDetail() {
    const r = selected();
    document.querySelectorAll('#tracking-control-tower [data-action="incident"]').forEach(b => { b.disabled = !r || !r.vehicle_id; });
    if (!r) { el('ct-detail').innerHTML = '<p class="ct-empty">Chưa chọn chuyến.</p>'; el('ct-metrics').innerHTML = soLieuDoiXe(); return; }
    const phone = String(r.driver_phone || '').replace(/[^+0-9]/g, '');
    el('ct-detail').innerHTML = `<div class="ct-summary">${pair('Trip', r.trip_id)}${pair('DO · khách hàng', `${r.do_id} · ${r.customer_name || ''}`)}${pair('Tuyến', r.route_name)}${pair('Hạn giao', date(r.delivery_due))}</div>
      <h4>Tổ lái</h4><div class="ct-crew"><div><strong>${esc(r.driver_name || 'Chưa gán tài xế')}</strong><span>${esc(r.vehicle_id || 'Chưa gán xe')} · Phụ xe: ${esc(r.co_driver_name || 'Chưa gán')}</span></div>${phone ? `<a href="tel:${phone}" title="Gọi tài xế"><i class="fa-solid fa-phone"></i></a>` : ''}</div>
      <h4>Cần chú ý</h4><div class="ct-alert ${r.gps.status === 'fresh' ? 'blue' : 'amber'}">${esc(gpsLabel(r))}<br><small>Vị trí cuối: ${esc(date(r.gps.last_update))}</small></div>${r.overdue ? '<div class="ct-alert amber">Đã quá hạn giao trên DO, chưa ghi nhận giao hoàn tất.</div>' : ''}
      ${r.incidents.map(i => `<div class="ct-alert red"><strong>${esc(i.incident_type)}</strong> · ${esc(i.status)}<br>${esc(i.description || i.location || '')}</div>`).join('')}
      <h4>Tiến độ chặng</h4><ol class="ct-timeline">${r.legs.map(l => `<li class="${l.status === 'completed' ? 'done' : ''}"><strong>${esc(l.origin)} → ${esc(l.destination)}</strong><span>${esc(labels[l.status] || l.status)} · ${esc(labels[l.type] || l.type)}</span><small>${l.actual_arrival_at ? 'Thực tế' : 'Kế hoạch'}: ${esc(date(l.actual_arrival_at || l.planned_arrival_at))}</small></li>`).join('') || '<li>Chưa có chặng Trip.</li>'}</ol>
      <h4>Sự kiện thực tế · ${r.events.length}</h4><ol class="ct-timeline">${r.events.map(e => `<li class="done"><strong>${esc(e.type)}</strong><span>${esc(e.location || e.note || '')}</span><small>${esc(date(e.time))} · ${esc(e.source)}</small></li>`).join('') || '<li>Chưa có sự kiện của Trip.</li>'}</ol>
      <h4>Bằng chứng giao hàng · ${r.pod_count || 0}</h4>${(r.pods || []).map(p => `<div class="ct-pod"><strong>${esc(p.receiver_name || 'Chưa có người nhận')}</strong><span>${esc(p.location || '')} · ${esc(date(p.time))}</span>${p.documents.map(d => `<button data-document="${esc(d.id)}" data-name="${esc(d.file_name)}" title="Tải chứng từ POD"><i class="fa-solid fa-download"></i> ${esc(d.file_name)}</button>`).join('')}</div>`).join('') || '<p>Chưa có bản ghi POD của chuyến này.</p>'}<div class="ct-actions">${r.status === 'in_transit' ? `<button class="ct-primary" data-action="arrive"><i class="fa-solid fa-map-pin"></i> Ghi nhận đã đến nơi</button>` : ''}<button data-action="completion" ${r.status === 'arrived' ? '' : 'disabled'} title="${r.status === 'arrived' ? 'Mở form ký nhận POD và chốt giá' : 'Phải ghi nhận xe đã đến nơi trước khi ký POD'}"><i class="fa-solid fa-file-signature"></i> Mở hoàn tất giao hàng</button><button data-action="incident" ${!r.vehicle_id ? 'disabled' : ''}><i class="fa-solid fa-triangle-exclamation"></i> Báo sự cố</button><button data-action="dispatch"><i class="fa-solid fa-arrow-left"></i> Mở Điều phối</button></div>`;
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
      L.circleMarker(point, { radius: item.key === state.selected ? 11 : 8, color: '#fff', weight: 2, fillOpacity: 1, fillColor: mau }).bindTooltip(`${esc(item.vehicle_id || item.do_id)} · ${esc(gpsLabel(item))}`).on('click', () => select(item.key)).addTo(layer);
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
