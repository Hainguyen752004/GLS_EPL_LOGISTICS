/* Theo dõi tuyến — trung tâm điều hành, bố cục dựng lại theo bản mẫu "trip-tracking" anh gửi:
 *
 *   thanh trên (tìm · chỉ phiếu chưa xong · tự cập nhật · sổ sự cố · báo sự cố)
 *   dải ô số   (bấm một ô là lọc danh sách theo đúng ô đó)
 *   ba cột     (danh sách chuyến · bản đồ + mốc chặng + ba tab · hồ sơ chuyến)
 *
 * Ba cột cao đúng phần màn còn trống và mỗi khối tự cuộn bên trong, nên cả màn vừa MỘT màn hình —
 * đó là điểm chính của bản mẫu. Chiều cao do js đo, không đoán bằng CSS, vì thanh điều hướng có hai
 * kiểu (thanh bên · thanh trên) và cả trang còn co giãn theo mức zoom.
 *
 * Khác bản mẫu một chỗ cố ý: BẢN ĐỒ LÀ LEAFLET THẬT. Bản mẫu vẽ hình SVG minh hoạ và README của nó
 * dặn "khi có GPS thì thay renderMap() bằng Leaflet" — bên mình đã có GPS thật từ điện thoại tài xế
 * nên dùng thẳng bản đồ thật, giữ nguyên phần còn lại của bố cục.
 *
 * Số liệu cả màn lấy một lần từ /api/theo-doi để danh sách vài chục chuyến không thành vài chục
 * lượt gọi; mở một chuyến mới gọi chi tiết phiếu đó.
 */
(function () {
  const { API, NN, esc, so, AUTH, tag } = EPL;
  let root, BANG = null, P = null, PARTS = [], nguon = 'kho';
  let sap = 'uu-tien', locO = '', dongHo = null, tab = 'dien-bien', CHUNG_TU = null;
  let MAP = null, lopNen = null, lopVe = null, cheDoBD = 'mot', VET = null, mocSang = 0;
  const q = (s) => root.querySelector(s);
  const laBai = () => AUTH.la('yard');

  /* ---------------------------------------------------------------- dải ô số */
  // Mỗi ô: khoá từ điển · lấy số ở đâu · lọc danh sách thế nào khi bấm vào.
  const O_SO = [
    { id: 'dang_chay', khoa: 'td_running', loc: (c) => ['dispatched', 'transit'].includes(c.transport_status) },
    { id: 'chua_xuat_ben', khoa: 'td_notout', loc: (c) => c.transport_status === 'dispatched' },
    { id: 'di_lau', khoa: 'td_long', mau: 'do', loc: (c) => c.di_lau },
    { id: 'gps_thieu', khoa: 'gps_missing', mau: 'vang',
      loc: (c) => ['dispatched', 'transit'].includes(c.transport_status) && (!c.gps || c.gps.cu) },
    { id: 'cho_hoa_don', khoa: 'td_await_inv', loc: (c) => c.transport_status === 'arrived' && !c.invoiced },
    { id: 'su_co_mo', khoa: 'td_open_inc', mau: 'do', loc: (c) => c.su_co_mo > 0 },
    { id: 'cho_cap_phat', khoa: 'td_await_iss', mau: 'vang', loc: (c) => c.cho_cap_phat > 0 },
    { id: 'chua_thu_tien', khoa: 'td_unpaid', loc: (c) => c.finance_status !== 'paid' },
  ];

  function veOSo() {
    const k = (BANG && BANG.kpi) || {};
    q('#tdt-o-so').innerHTML = O_SO.map(o => {
      const n = k[o.id] || 0;
      return `<button type="button" class="tdt2-tile ${o.mau || ''} ${locO === o.id ? 'chon' : ''}" data-o="${o.id}" title="${esc(NN.t('td_tile_hint'))}">
        <span class="l">${NN.h(o.khoa)}</span><span class="v ${n ? 'khac0' : ''}">${so(n)}</span></button>`;
    }).join('');
    q('#tdt-o-so').querySelectorAll('[data-o]').forEach(b => b.addEventListener('click', () => {
      locO = locO === b.dataset.o ? '' : b.dataset.o;      // bấm lại chính ô đó là bỏ lọc
      veOSo(); veDanhSach();
    }));
  }

  /* ---------------------------------------------------------------- cột trái */
  function loc() {
    if (!BANG) return [];
    const t = q('#tdt-q').value.trim().toLowerCase();
    const chiChay = q('#tdt-chi-chay').checked;
    const o = O_SO.find(x => x.id === locO);
    let ds = BANG.chuyen.slice();
    if (chiChay) ds = ds.filter(c => c.transport_status !== 'arrived' || c.finance_status !== 'paid');
    if (o) ds = ds.filter(o.loc);
    if (t) ds = ds.filter(c => [c.doc_no, c.truck_no, c.driver_name, c.customer_name, c.plate_head,
      c.plate_trailer, c.origin, c.destination].join(' ').toLowerCase().includes(t));
    // Ưu tiên: việc gấp lên trên — sự cố chưa duyệt, rồi đi lâu, rồi phiếu lĩnh chờ cấp.
    const diem = (c) => (c.su_co_mo ? 100 : 0) + (c.di_lau ? 50 : 0) + (c.cho_cap_phat ? 20 : 0)
      + (c.transport_status === 'transit' ? 5 : 0);
    if (sap === 'uu-tien') ds.sort((a, b) => diem(b) - diem(a) || String(b.out_date).localeCompare(String(a.out_date)));
    else if (sap === 'ngay') ds.sort((a, b) => String(b.out_date).localeCompare(String(a.out_date)));
    else ds.sort((a, b) => String(a.customer_name || '').localeCompare(String(b.customer_name || '')));
    return ds;
  }

  function veDanhSach() {
    const ds = loc();
    q('#tdt-dem').textContent = BANG ? `${ds.length} / ${BANG.chuyen.length}` : '';
    q('#tdt-the-ds').innerHTML = ds.length ? ds.map(c => {
      const canh = [];
      if (c.su_co_mo) canh.push(`<span class="canh do">${NN.h('td_inc_open', { n: c.su_co_mo })}</span>`);
      if (c.di_lau) canh.push(`<span class="canh do">${NN.h('td_days_out', { n: c.so_ngay_di })}</span>`);
      if (c.cho_cap_phat) canh.push(`<span class="canh vang">${NN.h('td_iss_wait', { n: c.cho_cap_phat })}</span>`);
      if (['dispatched', 'transit'].includes(c.transport_status) && (!c.gps || c.gps.cu)) {
        canh.push(`<span class="canh vang">${NN.h('gps_missing')}</span>`);
      } else if (c.gps) {
        canh.push(`<span class="canh xanh">${NN.h('gps_age', { n: Math.round(c.gps.tuoi_phut) })}</span>`);
      }
      return `<button type="button" class="tdt2-the ${P && P.id === c.id ? 'chon' : ''}" data-c="${c.id}">
        <span class="so"><span class="mono">${esc(c.doc_no)}</span>${tag(c.transport_status)}</span>
        <span class="kh" lang="lo">${esc(c.customer_name || '—')}</span>
        <span class="xe" lang="lo">${esc(c.origin || '')} → ${esc(c.destination || '')}</span>
        <span class="xe">${esc(c.truck_no || '')}${c.plate_head ? ' · <span lang="lo">' + esc(c.plate_head) + '</span>' : ''}${c.driver_name ? ' · <span lang="lo">' + esc(c.driver_name) + '</span>' : ''}</span>
        ${canh.length ? `<span class="chan">${canh.join(' · ')}</span>` : ''}
        <span class="chan"><span>${c.so_diem ? NN.h('td_legs', { toi: c.stop_reached, tong: c.so_diem }) : NN.h('no_route')}</span><span>${EPL.ngay(c.out_date)}</span></span>
      </button>`;
    }).join('') : `<div class="tdt2-trong">${NN.h('td_none_watch')}</div>`;
    q('#tdt-the-ds').querySelectorAll('[data-c]').forEach(b => b.addEventListener('click', () => mo(b.dataset.c)));
    if (cheDoBD === 'doi') veBanDo();
  }

  /* ---------------------------------------------------------------- bản đồ
   * Leaflet để SẴN trong dự án (frontend/vendor/leaflet), không gọi CDN: máy chủ bên Lào có lúc
   * không ra được Internet. Ảnh nền thì vẫn phải tải từ mạng — mất mạng thì nền trống nhưng đường
   * tuyến và các chấm vẫn vẽ, vì chúng lấy từ toạ độ trong DB.
   */
  const NEN = {
    've-tinh': ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      'Tiles © Esri'],
    'duong': ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      'Tiles © Esri'],
  };
  const MAU = { chay: '#2F5D8A', lau: '#A86B12', suCo: '#A83232', khong: '#7A858F', xong: '#145C4A' };

  function napLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (!document.getElementById('leaflet-css')) {
      const l = document.createElement('link');
      l.id = 'leaflet-css'; l.rel = 'stylesheet'; l.href = 'vendor/leaflet/leaflet.css';
      document.head.appendChild(l);
    }
    return new Promise((res, rej) => {
      const sc = document.createElement('script');
      sc.src = 'vendor/leaflet/leaflet.js';
      sc.onload = () => res(window.L);
      sc.onerror = () => rej(new Error('leaflet'));
      document.head.appendChild(sc);
    });
  }

  function mauCuaChuyen(c) {
    if (c.su_co_mo) return MAU.suCo;
    if (c.di_lau) return MAU.lau;
    if (c.transport_status === 'arrived') return MAU.xong;
    if (!c.vi_tri) return MAU.khong;
    return MAU.chay;
  }
  function chamXe(mau, chu) {
    return window.L.divIcon({ className: 'tdt-xe-cham',
      html: `<span style="background:${mau}"></span>${chu ? `<b>${esc(chu)}</b>` : ''}`,
      iconSize: [18, 18], iconAnchor: [9, 9] });
  }

  async function veBanDo() {
    // Bản đồ là phần PHỤ của màn: hỏng bản đồ thì vẫn phải xem được mốc chặng, diễn biến, chi phí.
    try { await veBanDoThat(); } catch (e) { /* không nối được thư viện hay ảnh nền — bỏ qua */ }
  }
  async function veBanDoThat() {
    const o = q('#tdt-map');
    if (!o) return;
    const L = await napLeaflet();
    if (!MAP) {
      MAP = L.map(o, { zoomControl: true, attributionControl: true, scrollWheelZoom: false });
      MAP.setView([18.6, 104.2], 7);
      datNen(q('#tdt-nen').value || 've-tinh');
    }
    if (lopVe) { MAP.removeLayer(lopVe); lopVe = null; }
    lopVe = L.layerGroup().addTo(MAP);

    const ds = cheDoBD === 'doi' ? loc() : (P ? [BANG.chuyen.find(c => c.id === P.id)].filter(Boolean) : []);
    const diemVe = [];

    if (cheDoBD === 'mot') {
      const c = ds[0];
      const dd = (c && c.stops || []).filter(s => s.lat != null && s.lng != null);
      if (!dd.length) {
        o.classList.add('trong');
        o.querySelectorAll('.tdt-map-trong').forEach(x => x.remove());
        const bao = document.createElement('div');
        bao.className = 'tdt-map-trong'; bao.innerHTML = NN.h('map_none');
        o.appendChild(bao);
        return;
      }
      o.classList.remove('trong');
      o.querySelectorAll('.tdt-map-trong').forEach(x => x.remove());
      const toaDo = dd.map(s => [s.lat, s.lng]);
      L.polyline(toaDo, { color: '#2F5D8A', weight: 4, opacity: .85 }).addTo(lopVe);
      dd.forEach(s => {
        const daToi = s.seq <= (c.stop_reached || 0), sang = s.seq === mocSang;
        L.circleMarker([s.lat, s.lng], { radius: sang ? 12 : 9, weight: sang ? 3 : 2,
          color: sang ? '#A86B12' : (daToi ? MAU.xong : '#2F5D8A'),
          fillColor: daToi ? MAU.xong : '#fff', fillOpacity: 1 })
          .bindTooltip(`${s.seq}. ${esc(s.name)}`, { direction: 'top' }).addTo(lopVe);
        diemVe.push([s.lat, s.lng]);
      });
      // Vệt GPS THẬT vẽ đè lên tuyến kế hoạch — đó mới là đường xe đã đi.
      if (VET && VET.trip_id === c.id && VET.vet.length > 1) {
        L.polyline(VET.vet.map(v => [v.lat, v.lng]), { color: '#145C4A', weight: 5, opacity: .95 }).addTo(lopVe);
        VET.vet.forEach(v => diemVe.push([v.lat, v.lng]));
      }
      if (c.vi_tri) {
        const laGps = c.vi_tri.nguon === 'gps';
        const chu = laGps
          ? `${NN.t('gps_src_gps')}${c.vi_tri.speed_kmh != null ? ' · ' + NN.t('gps_speed') + ' ' + so(c.vi_tri.speed_kmh, 0) + ' km/h' : ''}`
            + ` · ${NN.t('gps_age', { n: Math.round(c.vi_tri.tuoi_phut || 0) })}`
          : NN.t('map_pos_at', { ten: c.vi_tri.name });
        L.marker([c.vi_tri.lat, c.vi_tri.lng], { icon: chamXe(mauCuaChuyen(c), c.truck_no), zIndexOffset: 500 })
          .bindTooltip(`${esc(c.truck_no || '')} · ${esc(chu)}`, { direction: 'top' })
          .addTo(lopVe);
      }
    } else {
      ds.forEach(c => {
        if (!c.vi_tri) return;
        L.marker([c.vi_tri.lat, c.vi_tri.lng], { icon: chamXe(mauCuaChuyen(c), c.truck_no) })
          .bindTooltip(`${esc(c.doc_no)} · ${esc(c.truck_no || '')}<br>${esc(c.origin || '')} → ${esc(c.destination || '')}`,
            { direction: 'top' })
          .on('click', () => mo(c.id))
          .addTo(lopVe);
        diemVe.push([c.vi_tri.lat, c.vi_tri.lng]);
      });
      o.classList.remove('trong');
      o.querySelectorAll('.tdt-map-trong').forEach(x => x.remove());
    }
    if (diemVe.length) MAP.fitBounds(window.L.latLngBounds(diemVe).pad(0.25), { maxZoom: 11 });
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }

  function datNen(ma) {
    if (!MAP || !window.L) return;
    if (lopNen) MAP.removeLayer(lopNen);
    const [url, ghi] = NEN[ma] || NEN['ve-tinh'];
    lopNen = window.L.tileLayer(url, { maxZoom: 17, attribution: ghi }).addTo(MAP);
  }

  /* ---------------------------------------------------------------- chiều cao ba cột
   * Ba cột phải cao đúng phần màn còn trống thì cả màn mới vừa một màn hình. Không đặt cứng trong
   * CSS được: thanh điều hướng có hai kiểu (thanh bên · thanh trên) nên khối này bắt đầu ở độ cao
   * khác nhau, và cả trang còn co giãn theo mức zoom. Đo bằng offsetTop (đơn vị của trang, không
   * bị mức zoom làm lệch) rồi trừ khỏi chiều cao cửa sổ đã quy về cùng đơn vị.
   */
  /** Mở / đóng thanh xem nhanh hồ sơ chuyến.
   *  Bề rộng cột đổi có chuyển động nên bản đồ phải ĐO LẠI sau khi chạy xong, không thì Leaflet giữ
   *  kích thước cũ: nửa bản đồ xám, chấm xe lệch chỗ. Nghe transitionend, kèm một lần chờ dự phòng
   *  cho trường hợp người dùng đặt "giảm chuyển động" (không có sự kiện nào bắn ra). */
  function moHoSo(mo) {
    const cols = q('#tdt-cols'); if (!cols) return;
    if (cols.classList.contains('mo-ho-so') === mo) return;
    cols.classList.toggle('mo-ho-so', mo);
    let xong = false;
    const khiXong = (e) => {
      if (e && e.target !== cols) return;
      if (xong) return;
      xong = true; cols.removeEventListener('transitionend', khiXong);
      if (MAP) MAP.invalidateSize();
    };
    cols.addEventListener('transitionend', khiXong);
    setTimeout(khiXong, 380);
  }

  function caoCot() {
    const el = q('#tdt-cols'); if (!el) return;
    if ((window.innerWidth || 1600) <= 1000) { el.style.height = ''; return; }
    let tren = 0, n = el;
    while (n) { tren += n.offsetTop; n = n.offsetParent; }
    const ty = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    el.style.height = Math.max(420, (window.innerHeight || 900) / ty - tren - 24) + 'px';
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }

  /* ---------------------------------------------------------------- cột giữa: mốc chặng */
  function rate(ma) { return { USD: P.rate_usd, THB: P.rate_thb, VND: P.rate_vnd, LAK: 1 }[ma] || 1; }

  function veMoc() {
    if (!P) { q('#tdt-moc').innerHTML = ''; q('#tdt-moc-chan').innerHTML = ''; return; }
    const diem = P.route_stops || [], toi = P.stop_reached || 0;
    if (!diem.length) {
      q('#tdt-moc').innerHTML = `<div class="tdt2-trong" style="flex:1">${NN.h('no_route')}</div>`;
      q('#tdt-moc-chan').innerHTML = ''; return;
    }
    const tiep = diem.find(s => s.seq > toi);
    q('#tdt-moc').innerHTML = diem.map(s => {
      const done = s.seq <= toi, now = tiep && s.seq === tiep.seq && P.transport_status !== 'arrived';
      return `<button type="button" class="m ${done ? 'done' : ''} ${now ? 'next' : ''}" data-moc="${s.seq}">
        <i>${done ? '✓' : s.seq}</i><b lang="lo">${esc(s.name)}</b>
        <small>${s.seq > 1 ? '+' + so(s.km_from_prev, 1) + ' km' : NN.t('origin')}</small></button>`;
    }).join('');
    const tongKm = diem.reduce((a, s) => a + (s.km_from_prev || 0), 0);
    const diKm = diem.filter(s => s.seq <= toi).reduce((a, s) => a + (s.km_from_prev || 0), 0);
    q('#tdt-moc-chan').innerHTML = `<span>${NN.h('td_route_total')} <b>${so(tongKm, 1)} km</b> · ${NN.h('td_gone_km')} ${so(diKm, 1)} km</span>
      <span>${NN.h('ev_arrive_stop')} <b>${toi}/${diem.length}</b>${tiep ? ` · ${NN.h('td_next_stop')} <span lang="lo">${esc(tiep.name)}</span>` : ` · ${NN.h('td_done_route')}`}</span>`;
    q('#tdt-moc').querySelectorAll('[data-moc]').forEach(b => b.addEventListener('click', () => {
      mocSang = mocSang === +b.dataset.moc ? 0 : +b.dataset.moc;
      if (cheDoBD !== 'mot') { cheDoBD = 'mot'; root.querySelectorAll('#tdt-bd-tab button').forEach(x => x.classList.toggle('active', x.dataset.bd === 'mot')); }
      veBanDo();
    }));
  }

  /* ---------------------------------------------------------------- cột giữa: ba tab */
  const TAB = [['dien-bien', 'events'], ['chi-phi', 'sec5'], ['chung-tu', 'td_docs']];

  function demTab(id) {
    if (!P) return 0;
    if (id === 'dien-bien') return (P.events || []).length;
    if (id === 'chi-phi') return (P.expenses || []).filter(d => d.section === 'repair').length;
    return CHUNG_TU ? CHUNG_TU.length : 0;
  }

  function veTabs() {
    if (!P) {
      q('#tdt-tabs').innerHTML = ''; q('#tdt-tab-nut').innerHTML = '';
      q('#tdt-tab-than').innerHTML = `<div class="trong">${NN.h('td_pick')}</div>`;
      return;
    }
    q('#tdt-tabs').innerHTML = TAB.map(([id, khoa]) =>
      `<button type="button" class="tdt2-tab ${tab === id ? 'active' : ''}" data-tab="${id}">${NN.h(khoa)}<span class="n">${demTab(id)}</span></button>`).join('');
    q('#tdt-tabs').querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; veTabs(); }));

    const suaDuoc = laBai() && P.finance_status !== 'paid';
    q('#tdt-tab-nut').innerHTML = tab === 'dien-bien'
      ? (suaDuoc ? `<button type="button" class="tdt2-btn sm" id="tdt-ghi-chu">+ ${NN.h('add_note')}</button>` : '')
      : tab === 'chi-phi'
        ? (suaDuoc ? `<button type="button" class="tdt2-btn sm tan" id="tdt-khai-sua">+ ${NN.h('report_incident')}</button>` : '')
        : `<button type="button" class="tdt2-btn sm" id="tdt-mo-so-ct">${NN.h('ct_so')}</button>`;
    const ghi = q('#tdt-ghi-chu'); if (ghi) ghi.addEventListener('click', ghiChu);
    const khai = q('#tdt-khai-sua'); if (khai) khai.addEventListener('click', moSuCo);
    const moCt = q('#tdt-mo-so-ct'); if (moCt) moCt.addEventListener('click', () => EPL.di('chung-tu', { tab: 'so' }));

    if (tab === 'dien-bien') veTabDienBien();
    else if (tab === 'chi-phi') veTabChiPhi();
    else veTabChungTu();
  }

  function veTabDienBien() {
    const diem = P.route_stops || [];
    const ev = (P.events || []).slice().reverse();
    const duyetDuoc = laBai() || AUTH.la('fuel');   // dầu dọc đường là mục III → KT kho xăng dầu
    const than = ev.length ? `<table><thead><tr>
        <th style="width:112px">${NN.h('c_date')}</th><th style="width:132px">${NN.h('type')}</th>
        <th>${NN.h('note')}</th><th style="width:120px">${NN.h('resp')}</th><th class="no-print" style="width:118px"></th></tr></thead>
      <tbody>${ev.map(e => {
        const cho = e.status === 'reported';
        return `<tr><td class="nowrap">${EPL.ngayGio(e.ts)}</td>
          <td><span class="tag ${e.kind === 'incident' ? 'tdt-tag-in' : e.kind === 'repair' ? 'tdt-tag-rp' : 'plain'}">${NN.h('ev_' + e.kind)}${e.incident_type ? ' · ' + NN.h('inc_' + e.incident_type) : ''}</span></td>
          <td lang="lo">${esc(e.note) || ''}${e.stop_seq ? ` <span class="muted">· ${esc((diem.find(s => s.seq === e.stop_seq) || {}).name || e.stop_seq)}</span>` : ''}
            ${e.reported_cost != null ? ` <span class="muted">· ${so(e.reported_cost)} ${esc(e.currency || 'LAK')}</span>` : ''}
            ${cho ? ` <span class="tag partial">${NN.h('st_reported')}</span>` : ''}</td>
          <td lang="lo">${esc(e.by_user) || ''}</td>
          <td class="no-print">${cho && duyetDuoc ? `<button type="button" class="tdt2-btn sm" data-duyet="${e.id}">${NN.h('approve')}</button> <button type="button" class="tdt2-btn sm do" data-tu-choi="${e.id}">${NN.h('reject')}</button>` : ''}</td></tr>`;
      }).join('')}</tbody></table>` : `<div class="trong">${NN.h('log_empty')}</div>`;
    const cho = (P.events || []).filter(e => e.status === 'reported').length;
    q('#tdt-tab-than').innerHTML = than + `<div class="tdt2-chan">
      <span>${NN.h('td_ev_count', { n: ev.length })}${cho ? ` · <b style="color:var(--red)">${NN.h('td_inc_open', { n: cho })}</b>` : ''}</span>
      <span>${NN.h('td_last_ev')}: ${ev[0] ? EPL.ngayGio(ev[0].ts) : '—'}</span></div>`;
    q('#tdt-tab-than').querySelectorAll('[data-duyet]').forEach(b => b.addEventListener('click', () => duyet((P.events || []).find(e => e.id === b.dataset.duyet))));
    q('#tdt-tab-than').querySelectorAll('[data-tu-choi]').forEach(b => b.addEventListener('click', () => tuChoi((P.events || []).find(e => e.id === b.dataset.tuChoi))));
  }

  function veTabChiPhi() {
    const sua = (P.expenses || []).filter(d => d.section === 'repair');
    let tong = 0;
    const than = sua.length ? `<table><thead><tr>
        <th>${NN.h('item')}</th><th style="width:96px">${NN.h('source')}</th><th class="num" style="width:60px">${NN.h('qty')}</th>
        <th class="num" style="width:110px">${NN.h('unit_price')}</th><th class="num" style="width:120px">${NN.h('amount_lak')}</th>
        <th style="width:96px">${NN.h('acct_code')}</th></tr></thead>
      <tbody>${sua.map(d => { const t = (d.qty || 0) * (d.unit_price || 0) * rate(d.currency); tong += t;
        return `<tr><td lang="lo">${esc(EPL.khoanMuc(d))}</td><td>${d.source ? NN.h('src_' + d.source) : '—'}</td>
          <td class="num">${so(d.qty)}</td><td class="num">${so(d.unit_price)}${d.currency && d.currency !== 'LAK' ? ' ' + esc(d.currency) : ''}</td>
          <td class="num"><b>${so(t)}</b></td><td><span class="acct">${esc(d.acct_code || '')}</span></td></tr>`; }).join('')}</tbody></table>`
      : `<div class="trong">${NN.h('no_expense')}</div>`;
    const tt = (P.sections || {}).repair || 'wait';
    q('#tdt-tab-than').innerHTML = than + `<div class="tdt2-chan">
      <span>${NN.h('total')}: <b style="color:var(--ink)">${so(tong)} LAK</b></span>
      <span>${NN.h('td_cost_note')} · ${NN.h(tt === 'wait' ? 'stt_wait2' : 'stt_' + tt)}</span></div>`;
  }

  /** Chứng từ của chuyến: phiếu lĩnh · tạm ứng, tệp đính kèm, và sổ chứng từ nếu vai được xem. */
  function veTabChungTu() {
    if (CHUNG_TU === null) {
      q('#tdt-tab-than').innerHTML = `<div class="trong">${NN.h('loading')}</div>`;
      napChungTu();
      return;
    }
    const than = CHUNG_TU.length ? `<table><thead><tr>
        <th>${NN.h('doc_no')}</th><th>${NN.h('ct_loai')}</th><th style="width:104px">${NN.h('c_date')}</th>
        <th class="num" style="width:120px">${NN.h('amount')}</th><th style="width:110px">${NN.h('status')}</th></tr></thead>
      <tbody>${CHUNG_TU.map(c => `<tr>
        <td class="mono">${esc(c.so)}</td><td>${esc(c.ten)}</td><td>${EPL.ngay(c.ngay)}</td>
        <td class="num">${c.tien == null ? '—' : so(c.tien, c.tien_te === 'USD' ? 2 : 0) + ' ' + esc(c.tien_te || '')}</td>
        <td>${tag(c.mau, c.tt_khoa)}</td></tr>`).join('')}</tbody></table>`
      : `<div class="trong">${NN.h('td_no_docs')}</div>`;
    q('#tdt-tab-than').innerHTML = than + `<div class="tdt2-chan">
      <span>${NN.h('td_doc_count', { n: CHUNG_TU.length })}</span><span>${NN.h('td_doc_note')}</span></div>`;
  }

  async function napChungTu() {
    const id = P && P.id;
    // Ba nguồn, vai nào xem được nguồn nào thì lấy nguồn đó — không có quyền thì bỏ qua, đừng báo lỗi.
    const [vc, tep, so_ct] = await Promise.all([
      API.get(`/api/trips/${id}/vouchers`).catch(() => []),
      API.get(`/api/trips/${id}/tep`).catch(() => []),
      API.get(`/api/chung-tu?trip_id=${id}`).catch(() => null),
    ]);
    if (!P || P.id !== id) return;                       // đã bấm sang chuyến khác trong lúc chờ
    const ds = [];
    (vc || []).forEach(v => ds.push({
      so: v.doc_no, ten: NN.t(v.kind === 'fuel' ? 'v_fuel' : 'v_advance'), ngay: v.doc_date,
      tien: v.kind === 'fuel' ? v.qty_l : v.amount_lak, tien_te: v.kind === 'fuel' ? 'L' : 'LAK',
      mau: v.status === 'da_cap' ? 'paid' : v.status === 'huy' ? 'unpaid' : 'partial', tt_khoa: 'v_' + v.status,
    }));
    (tep || []).forEach(t => ds.push({
      so: t.filename, ten: NN.t('attach_ore'), ngay: t.ts, tien: null, tien_te: '',
      mau: 'paid', tt_khoa: 'ct_da_day',
    }));
    (so_ct && so_ct.ds ? so_ct.ds : []).forEach(c => ds.push({
      so: c.so, ten: c.loai_ten, ngay: c.ngay, tien: c.tien, tien_te: c.tien_te,
      mau: c.da_day ? 'paid' : 'partial', tt_khoa: c.da_day ? 'ct_da_day' : 'ct_chua_day',
    }));
    CHUNG_TU = ds;
    if (tab === 'chung-tu') veTabChungTu(); else veTabs();
  }

  /* ---------------------------------------------------------------- cột phải: hồ sơ chuyến */
  const MUC_MA = ['info', 'trans', 'fuel', 'travel', 'repair', 'other'];
  const MUC_SO = ['I', 'II', 'III', 'IV', 'V', 'VI'];
  const MUC_KHOA = ['sec1', 'sec2', 'sec3', 'sec4', 'sec5', 'sec6'];
  /** Tên trạng thái một mục — 'wait' trong từ điển là 'stt_wait2' (chưa gửi kiểm). */
  const tenTT = (tt) => NN.t(!tt || tt === 'wait' ? 'stt_wait2' : 'stt_' + tt);

  function veHoSo() {
    if (!P) { q('#tdt-xe').innerHTML = `<div class="tdt2-trong">${NN.h('td_pick')}</div>`; return; }
    const c = (BANG && BANG.chuyen.find(x => x.id === P.id)) || {};
    const kv = (k, v, cls) => `<div class="tdt2-kv"><span>${NN.h(k)}</span><b class="${cls || ''}">${v == null || v === '' ? '—' : v}</b></div>`;
    const m = P.sections || {};
    const diem = P.route_stops || [], toi = P.stop_reached || 0;
    const tiep = diem.find(s => s.seq > toi);
    const k = P.tinh || {};
    const cuoc = k.doanh_thu_lak || 0;
    // Chỉ có tổng cước, không có số đã thu từng phần — 'thu một phần' thì ghi rõ là không biết
    // còn bao nhiêu, chứ không lấy tổng cước ra làm số còn nợ.
    const nhanThu = P.finance_status === 'paid' ? 'td_paid_full' : P.finance_status === 'partial' ? 'td_paid_part' : 'td_unpaid_amt';
    const soThu = P.finance_status === 'partial' ? '—' : so(cuoc) + ' LAK';
    const canh = [];
    if (c.di_lau) canh.push(`<span class="tag partial">${NN.h('td_days_out', { n: c.so_ngay_di })}</span>`);
    if (c.su_co_mo) canh.push(`<span class="tag unpaid">${NN.h('td_inc_open', { n: c.su_co_mo })}</span>`);
    if (c.cho_cap_phat) canh.push(`<span class="tag partial">${NN.h('td_iss_wait', { n: c.cho_cap_phat })}</span>`);
    if (P.locked) canh.push(`<span class="tag paid">🔒 ${NN.h('s_locked')}</span>`);

    q('#tdt-xe').innerHTML = `
      <div>
        <div class="dau"><b class="mono">${esc(P.doc_no)}</b>${tag(P.transport_status)}</div>
        <div class="small muted">${P.company === 'joint' ? NN.h('co_joint') + ' · ' + esc(P.owner_name || '') : NN.h('co_epl')}</div>
        ${canh.length ? `<div class="tdt2-canh">${canh.join('')}</div>` : ''}
      </div>
      <div>
        ${kv('truck_no', `${esc(P.truck_no || '')}${P.plate_head ? ' · <span lang="lo">' + esc(P.plate_head) + '</span>' : ''}`)}
        ${kv('driver', `<span lang="lo">${esc(P.driver_name || '')}</span>`)}
        ${kv('customer', `<span lang="lo">${esc(P.customer_name || '')}</span>`)}
        ${kv('goods_type', P.goods_type ? NN.h(P.goods_type) : '')}
        ${kv('w_origin', P.weight_origin != null ? so(P.weight_origin, 2) + ' t' : '')}
        ${kv('w_dest', P.weight_dest != null ? so(P.weight_dest, 2) + ' t' : '')}
        ${kv('d_out', EPL.ngay(P.out_date))}
        ${kv('td_days', c.so_ngay_di != null ? NN.t('td_days_n', { n: c.so_ngay_di }) : '—', c.di_lau ? 'tre' : '')}
        ${kv('td_legs_short', diem.length ? `${toi}/${diem.length} · ${so(diem.reduce((a, s) => a + (s.km_from_prev || 0), 0), 1)} km` : '—')}
      </div>
      <div>
        <div class="tdt2-muc-dau"><span>${NN.h('td_sections')}</span><span>${MUC_MA.filter(x => ['verified', 'booked', 'paid'].includes(m[x])).length}/6</span></div>
        <div class="tdt2-duyet">${MUC_MA.map((ma, i) => { const tt = tenTT(m[ma]);
          return `<button type="button" class="tdt2-ap ${m[ma] || 'wait'}" data-muc="${ma}" title="${esc(NN.t(MUC_KHOA[i]) + ' — ' + tt)}">
          <b>${MUC_SO[i]}</b><span class="vong"></span></button>`; }).join('')}</div>
      </div>
      <div class="tdt2-tien">
        <div><small>${NN.h('td_fare_est')}</small><b>${so(cuoc)} LAK</b></div>
        <div class="${P.finance_status === 'unpaid' ? 'no' : ''}"><small>${NN.h(nhanThu)}</small><b>${soThu}</b></div>
      </div>
      <div class="tdt2-thao-tac">
        ${laBai() && tiep && P.transport_status !== 'arrived' && P.finance_status !== 'paid' ? `<button type="button" class="tdt2-btn dam" data-toi="${tiep.seq}">${NN.h('td_confirm_stop', { n: tiep.seq })}: <span lang="lo">${esc(tiep.name)}</span></button>` : ''}
        ${c.cho_cap_phat ? `<button type="button" class="tdt2-btn tan" data-cap>${NN.h('td_issue_fuel')}</button>` : ''}
        ${laBai() && P.finance_status !== 'paid' ? `<button type="button" class="tdt2-btn do" data-su-co>${NN.h('report_incident')}</button>` : ''}
      </div>`;

    q('#tdt-xe').querySelectorAll('[data-muc]').forEach(b => b.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: P.id })));
    const nutToi = q('#tdt-xe [data-toi]'); if (nutToi) nutToi.addEventListener('click', () => toiDiem(+nutToi.dataset.toi, diem.length));
    const nutCap = q('#tdt-xe [data-cap]'); if (nutCap) nutCap.addEventListener('click', () => EPL.di('cap-phat'));
    const nutSC = q('#tdt-xe [data-su-co]'); if (nutSC) nutSC.addEventListener('click', moSuCo);
  }

  /* ---------------------------------------------------------------- vẽ cả màn chi tiết */
  function ve() {
    const co = !!P;
    q('#tdt-su-co').disabled = q('#tdt-mo-phieu').disabled = !co;
    veMoc(); veTabs(); veHoSo(); veBanDo();
    caoCot();
  }

  /* ---------------------------------------------------------------- tải & thao tác */
  async function tai(giuChon) {
    BANG = await API.get('/api/theo-doi?tat_ca=1');
    q('#tdt-luc').innerHTML = NN.h('td_asof', { luc: EPL.ngayGio(BANG.luc) });
    veOSo(); veDanhSach();
    if (giuChon && P) { const con = BANG.chuyen.find(c => c.id === P.id); if (!con) { P = null; ve(); } }
  }
  async function mo(id) {
    try {
      P = await API.get('/api/trips/' + id);
      VET = await API.get('/api/trips/' + id + '/vet').catch(() => null);
      CHUNG_TU = null; mocSang = 0;
      veDanhSach(); ve(); moHoSo(true);
    } catch (e) { EPL.baoLoi(e); }
  }
  async function toiDiem(seq, tong) {
    try {
      P = await API.post(`/api/trips/${P.id}/events`, { kind: 'arrive_stop', stop_seq: seq });
      if (seq === tong && P.transport_status !== 'arrived') {
        const v = await EPL.hopNhap(NN.t('mark_arrived'), [{ id: 'weight_dest', label: 'weight_dest_prompt', type: 'number', value: P.weight_dest ?? '' },
          { id: 'odo_back', label: 'odo_back', type: 'number', value: P.odo_back ?? '' }, { id: 'back_date', label: 'd_back', type: 'date', value: P.back_date || EPL.homNay() }], NN.t('ok'));
        if (v) P = await API.post(`/api/trips/${P.id}/transport-status`, { status: 'arrived', ...v });
      }
      await tai(true); ve();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function ghiChu() {
    const v = await EPL.hopNhap(NN.t('add_note'), [{ id: 'note', label: 'note', value: '', lo: true }], NN.t('save'));
    if (!v || !v.note.trim()) return;
    try { P = await API.post(`/api/trips/${P.id}/events`, { kind: 'note', note: v.note }); ve(); } catch (e) { EPL.baoLoi(e); }
  }
  function moSuCo() {
    if (!P) return;
    const dlg = q('#tdt-hop');
    q('#tdt-f-diem').innerHTML = `<option value="">—</option>` + (P.route_stops || []).map(s => `<option value="${s.seq}" ${s.seq === (P.stop_reached || 0) + 1 ? 'selected' : ''}>${s.seq}. ${esc(s.name)}</option>`).join('');
    q('#tdt-f-ghi').value = ''; q('#tdt-f-co-sua').checked = false; q('#tdt-f-sua').hidden = true; q('#tdt-f-sl').value = '1'; q('#tdt-f-gia').value = '';
    q('#tdt-f-part').innerHTML = PARTS.filter(p => p.qty > 0).map(p => `<option value="${p.id}" data-gia="${p.unit_price || 0}">${esc(p.name)} · ${NN.t('stock_left')} ${so(p.qty)} ${NN.t(p.unit)}</option>`).join('') || `<option value="">${esc(NN.t('no_data'))}</option>`;
    datNguon('kho'); NN.apDung(dlg); dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const body = { kind: q('#tdt-f-co-sua').checked ? 'repair' : 'incident', incident_type: q('#tdt-f-loai').value, note: q('#tdt-f-ghi').value };
      if (q('#tdt-f-diem').value) body.stop_seq = +q('#tdt-f-diem').value;
      if (q('#tdt-f-co-sua').checked) {
        body.repair = { source: nguon, qty: EPL.doc(q('#tdt-f-sl').value), currency: q('#tdt-f-tien').value };
        if (nguon === 'kho') body.repair.part_id = q('#tdt-f-part').value; else body.repair.item_name = q('#tdt-f-ten').value;
        if (q('#tdt-f-gia').value !== '') body.repair.unit_price = EPL.doc(q('#tdt-f-gia').value);
      }
      try { P = await API.post(`/api/trips/${P.id}/events`, body); PARTS = await API.get('/api/parts'); EPL.toast(NN.t('saved'), 'ok'); await tai(true); ve(); } catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }
  async function duyet(e) {
    if (!e) return;
    const v = await EPL.hopNhap(NN.t('approve') + ' — ' + (e.note || ''), [
      { id: 'source', label: 'source', type: 'select', value: 'mua', options: [['mua', NN.t('src_mua')], ['kho', NN.t('src_kho')]] },
      { id: 'part_id', label: 'pick_part', type: 'select', value: '', options: [['', '—']].concat(PARTS.filter(p => p.qty > 0).map(p => [p.id, p.name + ' · ' + NN.t('stock_left') + ' ' + so(p.qty)])) },
      { id: 'item_name', label: 'item', value: e.note || '', lo: true },
      { id: 'qty', label: 'qty', type: 'number', value: '1' },
      { id: 'unit_price', label: 'unit_price', type: 'number', value: e.reported_cost != null ? e.reported_cost : '' },
      { id: 'currency', label: 'cur', type: 'select', value: e.currency || 'LAK', options: [['LAK', 'LAK'], ['VND', 'VND'], ['THB', 'THB'], ['USD', 'USD']] },
    ], NN.t('approve'));
    if (!v) return;
    if (v.source !== 'kho') delete v.part_id;
    if (v.unit_price === '') delete v.unit_price;
    try { P = await API.post(`/api/trips/${P.id}/events/${e.id}/duyet`, v); PARTS = await API.get('/api/parts'); EPL.toast(NN.t('saved'), 'ok'); await tai(true); ve(); } catch (x) { EPL.baoLoi(x); }
  }
  async function tuChoi(e) {
    if (!e) return;
    const v = await EPL.hopNhap(NN.t('reject') + ' — ' + (e.note || ''), [{ id: 'reason', label: 'reject_reason', value: '', lo: true }], NN.t('reject'));
    if (!v) return;
    try { P = await API.post(`/api/trips/${P.id}/events/${e.id}/duyet`, { reject: true, reason: v.reason }); await tai(true); ve(); } catch (x) { EPL.baoLoi(x); }
  }
  function datNguon(n) {
    nguon = n; root.querySelectorAll('.tdt-nguon button').forEach(b => b.classList.toggle('on', b.dataset.src === n));
    q('#tdt-f-o-part').hidden = n !== 'kho'; q('#tdt-f-o-ten').hidden = n !== 'mua';
    if (n === 'kho') { const o = q('#tdt-f-part').selectedOptions[0]; if (o) q('#tdt-f-gia').value = o.dataset.gia || ''; }
  }

  /** Sổ sự cố — mọi diễn biến bất thường của MỌI phiếu, không riêng chuyến đang mở. */
  async function moSo() {
    const dlg = q('#tdt-so');
    q('#tdt-so-than').innerHTML = `<tr><td colspan="7" class="empty">${NN.h('loading')}</td></tr>`;
    NN.apDung(dlg); dlg.showModal();
    try {
      const ds = await API.get('/api/theo-doi/su-co');
      q('#tdt-so-than').innerHTML = ds.length ? ds.map(e => `<tr>
        <td class="nowrap">${EPL.ngayGio(e.ts)}</td><td class="mono">${esc(e.doc_no || '')}</td><td>${esc(e.truck_no || '')}</td>
        <td>${NN.h(e.kind === 'refuel' ? 'ev_refuel' : 'ev_' + e.kind)}${e.incident_type ? ' · ' + NN.h('inc_' + e.incident_type) : ''}</td>
        <td lang="lo">${esc(e.note || '')}</td>
        <td class="num">${e.reported_cost != null ? so(e.reported_cost) + ' ' + esc(e.currency || 'LAK') : '—'}</td>
        <td>${tag(e.status === 'reported' ? 'partial' : e.status === 'approved' ? 'paid' : 'unpaid', 'st_' + e.status)}</td></tr>`).join('')
        : `<tr><td colspan="7" class="empty">${NN.h('td_inc_empty')}</td></tr>`;
    } catch (e) {
      q('#tdt-so-than').innerHTML = `<tr><td colspan="7" class="empty neg">${esc(e.message)}</td></tr>`;
    }
  }

  function datTuDong(bat) {
    clearInterval(dongHo); dongHo = null;
    if (bat) dongHo = setInterval(() => tai(true).catch(() => {}), 30000);
  }

  let choCao = 0;
  function khiDoiCo() { clearTimeout(choCao); choCao = setTimeout(caoCot, 80); }

  EPL.modules['theo-doi-tuyen'] = {
    async init(r, ctx) {
      root = r;
      PARTS = await API.get('/api/parts').catch(() => []);
      q('#tdt-q').addEventListener('input', veDanhSach);
      q('#tdt-chi-chay').addEventListener('change', veDanhSach);
      q('#tdt-tu-dong').addEventListener('change', e => datTuDong(e.target.checked));
      q('#tdt-lam-moi').addEventListener('click', () => tai(true).catch(EPL.baoLoi));
      q('#tdt-so-su-co').addEventListener('click', moSo);
      q('#tdt-mo-phieu').addEventListener('click', () => P && EPL.di('phieu-xuat-xe', { id: P.id }));
      q('#tdt-dong-hs').addEventListener('click', () => moHoSo(false));
      q('#tdt-su-co').addEventListener('click', moSuCo);
      q('#tdt-f-co-sua').addEventListener('change', e => { q('#tdt-f-sua').hidden = !e.target.checked; });
      root.querySelectorAll('#tdt-sap button').forEach(b => b.addEventListener('click', () => {
        root.querySelectorAll('#tdt-sap button').forEach(x => x.classList.toggle('active', x === b));
        sap = b.dataset.sap; veDanhSach();
      }));
      root.querySelectorAll('#tdt-bd-tab button').forEach(b => b.addEventListener('click', () => {
        root.querySelectorAll('#tdt-bd-tab button').forEach(x => x.classList.toggle('active', x === b));
        cheDoBD = b.dataset.bd; veBanDo();
      }));
      q('#tdt-nen').addEventListener('change', e => { datNen(e.target.value); });
      root.querySelectorAll('.tdt-nguon button').forEach(b => b.addEventListener('click', () => datNguon(b.dataset.src)));
      q('#tdt-f-part').addEventListener('change', () => datNguon('kho'));
      window.addEventListener('resize', khiDoiCo);
      await tai();
      const t = ctx.tham || {};
      const dau = t.id || (loc()[0] || {}).id;
      if (dau) await mo(dau); else ve();
      // Mở màn bằng đường dẫn có ?hs=0 thì thu sẵn thanh xem nhanh, nhường cả chỗ cho bản đồ.
      if (t.hs === '0') moHoSo(false);
      caoCot();
    },
    destroy() {
      clearInterval(dongHo); dongHo = null;
      window.removeEventListener('resize', khiDoiCo);
      if (MAP) { MAP.remove(); MAP = null; lopNen = lopVe = null; }
    },
    onLang() { if (root) { veOSo(); veDanhSach(); ve(); } },
  };
})();
