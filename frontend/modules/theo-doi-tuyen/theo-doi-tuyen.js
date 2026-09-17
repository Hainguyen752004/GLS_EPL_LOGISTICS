/* Theo dõi tuyến — trung tâm điều hành, bố cục lấy từ màn "Theo dõi và kiểm soát" của EPL_System.
 *
 *   thanh công cụ (tìm · tự cập nhật · sổ sự cố · báo sự cố)
 *   dải ô số      (bấm một ô là lọc danh sách theo đúng ô đó)
 *   ba cột        (danh sách chuyến · bản đồ + diễn biến + sửa chữa · hồ sơ chuyến)
 *
 * Bản đồ vẽ TUYẾN KẾ HOẠCH nối các điểm đã khai toạ độ, chấm xe đứng ở MỐC ĐÃ XÁC NHẬN TỚI gần
 * nhất. Bên Lào không gắn GPS, "xe tới điểm X" là do Bãi bấm khi tài xế gọi về — nên không nội suy
 * vị trí giữa hai chặng: không biết thì không vẽ. Tuyến chưa khai toạ độ thì bỏ hẳn phần bản đồ.
 *
 * Số liệu cả màn lấy một lần từ /api/theo-doi để danh sách vài chục chuyến không thành vài chục
 * lượt gọi; mở một chuyến mới gọi chi tiết phiếu đó.
 */
(function () {
  const { API, NN, esc, so, AUTH, tag } = EPL;
  let root, BANG = null, P = null, PARTS = [], KM = null, nguon = 'kho';
  let sap = 'uu-tien', locO = '', dongHo = null;
  let MAP = null, lopNen = null, lopVe = null, cheDoBD = 'mot';
  const q = (s) => root.querySelector(s);
  const laBai = () => AUTH.la('yard');

  /* ---------------------------------------------------------------- dải ô số */
  // Mỗi ô: khoá từ điển · lấy số ở đâu · lọc danh sách thế nào khi bấm vào.
  const O_SO = [
    { id: 'dang_chay', khoa: 'td_running', loc: (c) => ['dispatched', 'transit'].includes(c.transport_status) },
    { id: 'chua_xuat_ben', khoa: 'td_notout', loc: (c) => c.transport_status === 'dispatched' },
    { id: 'di_lau', khoa: 'td_long', mau: 'do', loc: (c) => c.di_lau },
    { id: 'cho_hoa_don', khoa: 'td_await_inv', loc: (c) => c.transport_status === 'arrived' && !c.invoiced },
    { id: 'su_co_mo', khoa: 'td_open_inc', mau: 'do', loc: (c) => c.su_co_mo > 0 },
    { id: 'cho_cap_phat', khoa: 'td_await_iss', mau: 'vang', loc: (c) => c.cho_cap_phat > 0 },
    { id: 'chua_thu_tien', khoa: 'td_unpaid', loc: (c) => c.finance_status !== 'paid' },
  ];

  function veOSo() {
    const k = (BANG && BANG.kpi) || {};
    q('#tdt-o-so').innerHTML = O_SO.map(o => `<button class="tdt-o ${o.mau || ''} ${locO === o.id ? 'chon' : ''}" data-o="${o.id}">
      <span class="l">${NN.h(o.khoa)}</span><span class="v">${so(k[o.id] || 0)}</span></button>`).join('');
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
    q('#tdt-dem').textContent = ds.length ? String(ds.length) : '';
    q('#tdt-the-ds').innerHTML = ds.length ? ds.map(c => {
      const canh = [];
      if (c.su_co_mo) canh.push(`<div class="canh do">${NN.h('td_inc_open', { n: c.su_co_mo })}</div>`);
      if (c.cho_cap_phat) canh.push(`<div class="canh vang">${NN.h('td_iss_wait', { n: c.cho_cap_phat })}</div>`);
      if (c.di_lau) canh.push(`<div class="canh do">${NN.h('td_days_out', { n: c.so_ngay_di })}</div>`);
      return `<button class="tdt-the ${P && P.id === c.id ? 'chon' : ''} ${c.su_co_mo ? 'gap' : ''}" data-c="${c.id}">
        <div class="so"><span class="mono">${esc(c.doc_no)}</span>${tag(c.transport_status)}</div>
        <div class="kh" lang="lo">${esc(c.customer_name || '—')}</div>
        <div class="tuyen" lang="lo">${esc(c.origin || '')} → ${esc(c.destination || '')}</div>
        <div class="xe">${esc(c.truck_no || '')}${c.plate_head ? ' · <span lang="lo">' + esc(c.plate_head) + '</span>' : ''}
          ${c.driver_name ? ' · <span lang="lo">' + esc(c.driver_name) + '</span>' : ''}</div>
        ${canh.join('')}
        <div class="chan"><span>${c.so_diem ? NN.h('td_legs', { toi: c.stop_reached, tong: c.so_diem }) : NN.h('no_route')}</span>
          <span>${EPL.ngay(c.out_date)}</span></div></button>`;
    }).join('') : `<div class="tdt-trong">${NN.h('td_none_watch')}</div>`;
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
    // Bản đồ là phần PHỤ của màn: hỏng bản đồ thì vẫn phải xem được tiến độ, diễn biến, chi phí.
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
        const daToi = s.seq <= (c.stop_reached || 0);
        L.circleMarker([s.lat, s.lng], { radius: 9, weight: 2, color: daToi ? MAU.xong : '#2F5D8A',
          fillColor: daToi ? MAU.xong : '#fff', fillOpacity: 1 })
          .bindTooltip(`${s.seq}. ${esc(s.name)}`, { direction: 'top' }).addTo(lopVe);
        diemVe.push([s.lat, s.lng]);
      });
      if (c.vi_tri) {
        L.marker([c.vi_tri.lat, c.vi_tri.lng], { icon: chamXe(mauCuaChuyen(c), c.truck_no), zIndexOffset: 500 })
          .bindTooltip(`${esc(c.truck_no || '')} · ${NN.t('map_pos_at', { ten: c.vi_tri.name })}`, { direction: 'top' })
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

  /* ---------------------------------------------------------------- cột giữa */
  function rate(ma) { return { USD: P.rate_usd, THB: P.rate_thb, VND: P.rate_vnd, LAK: 1 }[ma] || 1; }

  function ve() {
    const co = !!P;
    q('#tdt-su-co').disabled = q('#tdt-ghi-chu').disabled = q('#tdt-mo-phieu').disabled = !co;
    if (!co) {
      q('#tdt-tien-do').innerHTML = `<div class="muted">${NN.h('td_pick')}</div>`;
      q('#tdt-dau').innerHTML = ''; q('#tdt-khoi-cho').hidden = true;
      q('#tdt-su-kien').innerHTML = q('#tdt-sua').innerHTML = '';
      q('#tdt-sua-tom').innerHTML = ''; q('#tdt-xe').innerHTML = `<div class="muted small">${NN.h('td_pick')}</div>`;
      return;
    }
    q('#tdt-dau').innerHTML = `${tag(P.transport_status)} ${tag(P.finance_status)}`;
    const diem = P.route_stops || [], toi = P.stop_reached || 0;
    if (!diem.length) {
      q('#tdt-tien-do').innerHTML = `<div class="muted small">${NN.h('no_route')}</div>`;
    } else {
      q('#tdt-tien-do').innerHTML = `<div class="tdt-tuyen">${diem.map(s => {
        const done = s.seq <= toi, now = s.seq === toi + 1 && P.transport_status !== 'arrived';
        return `<div class="tdt-moc ${done ? 'done' : ''} ${now ? 'now' : ''}"><div class="cham">${done ? '✓' : s.seq}</div>
          <div class="ten" lang="lo">${esc(s.name)}</div><div class="km">${s.seq > 1 ? '+' + so(s.km_from_prev, 1) + ' km' : NN.t('origin')}</div>
          ${laBai() && now ? `<button class="btn sm ok" data-toi="${s.seq}">${NN.h('mark_stop')}</button>` : ''}</div>`; }).join('')}</div>
        <div class="small muted">${NN.h('total_km')}: <b>${so(diem.reduce((a, s) => a + (s.km_from_prev || 0), 0), 1)}</b> km · ${NN.h('ev_arrive_stop')}: ${toi}/${diem.length}</div>`;
      q('#tdt-tien-do').querySelectorAll('[data-toi]').forEach(b => b.addEventListener('click', () => toiDiem(+b.dataset.toi, diem.length)));
    }

    const ev = (P.events || []).slice().reverse();
    q('#tdt-su-kien').innerHTML = ev.length ? ev.map(e => `<tr><td class="nowrap">${EPL.ngayGio(e.ts)}</td>
      <td><span class="tag ${e.kind === 'incident' ? 'tdt-tag-in' : e.kind === 'repair' ? 'tdt-tag-rp' : 'plain'}">${NN.h('ev_' + e.kind)}${e.incident_type ? ' · ' + NN.h('inc_' + e.incident_type) : ''}</span></td>
      <td lang="lo">${e.stop_seq ? esc((diem.find(s => s.seq === e.stop_seq) || {}).name || e.stop_seq) : '—'}</td><td lang="lo">${esc(e.note) || ''}</td><td lang="lo">${esc(e.by_user) || ''}</td></tr>`).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('log_empty')}</td></tr>`;

    const cho = (P.events || []).filter(e => e.status === 'reported');
    q('#tdt-khoi-cho').hidden = !cho.length;
    q('#tdt-cho-duyet').innerHTML = cho.map(e => `<tr><td class="nowrap">${EPL.ngayGio(e.ts)}</td><td>${NN.h(e.kind === 'refuel' ? 'ev_refuel' : 'inc_' + (e.incident_type || 'other'))}</td><td lang="lo">${esc(e.note || '')}</td>
      <td class="num">${e.reported_cost != null ? so(e.reported_cost) + ' ' + esc(e.currency || 'LAK') : '—'}</td><td lang="lo">${esc(e.by_user || '')}</td>
      <td class="no-print">${laBai() || AUTH.la('acct', 'fuel') ? `<button class="btn sm ok" data-duyet="${e.id}">${NN.h('approve')}</button> <button class="btn sm danger" data-tu-choi="${e.id}">${NN.h('reject')}</button>` : ''}</td></tr>`).join('');
    q('#tdt-cho-duyet').querySelectorAll('[data-duyet]').forEach(b => b.addEventListener('click', () => duyet(cho.find(e => e.id === b.dataset.duyet))));
    q('#tdt-cho-duyet').querySelectorAll('[data-tu-choi]').forEach(b => b.addEventListener('click', () => tuChoi(cho.find(e => e.id === b.dataset.tuChoi))));

    const sua = (P.expenses || []).filter(d => d.section === 'repair'); let tong = 0;
    q('#tdt-sua').innerHTML = sua.length ? sua.map(d => { const t = d.qty * d.unit_price * rate(d.currency); tong += t;
      return `<tr><td lang="lo">${esc(EPL.khoanMuc(d))}</td><td>${d.source ? NN.h('src_' + d.source) : '—'}</td><td class="num">${so(d.qty)}</td><td class="num">${so(t)}</td><td><span class="acct">${esc(d.acct_code || '')}</span></td></tr>`; }).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('no_expense')}</td></tr>`;
    q('#tdt-sua-tom').innerHTML = `${NN.h('total')}: <b>${so(tong)} LAK</b> · ${NN.h('sections_status')} V: ${NN.h((P.sections || {}).repair === 'wait' ? 'stt_wait2' : 'stt_' + ((P.sections || {}).repair || 'wait'))}`;

    veHoSo();
    veBanDo();
    q('#tdt-su-co').hidden = q('#tdt-ghi-chu').hidden = !laBai() || P.finance_status === 'paid';
  }

  /* ---------------------------------------------------------------- cột phải */
  function veHoSo() {
    const o = (k, v, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(v == null || v === '' ? '—' : v)}</span></div>`;
    const m = P.sections || {};
    const nhanMuc = ['sec1', 'sec2', 'sec3', 'sec4', 'sec5', 'sec6'];
    const maMuc = ['info', 'trans', 'fuel', 'travel', 'repair', 'other'];
    q('#tdt-xe').innerHTML = `
      <div class="tdt-ho-so-so"><b class="mono">${esc(P.doc_no)}</b>
        <div class="small muted">${P.company === 'joint' ? NN.h('co_joint') + ' · ' + esc(P.owner_name || '') : NN.h('co_epl')}</div></div>
      <div class="tdt-o-hs">
        ${o('truck_no', P.truck_no)}${o('driver', P.driver_name, true)}
        ${o('plate_head', P.plate_head, true)}${o('plate_trailer', P.plate_trailer, true)}
        ${o('customer', P.customer_name, true)}${o('goods_type', P.goods_type ? NN.t(P.goods_type) : '')}
        ${o('origin', P.origin, true)}${o('dest', P.destination, true)}
        ${o('w_origin', P.weight_origin != null ? so(P.weight_origin, 2) + ' t' : '')}${o('w_dest', P.weight_dest != null ? so(P.weight_dest, 2) + ' t' : '')}
        ${o('d_out', EPL.ngay(P.out_date))}${o('d_back', EPL.ngay(P.back_date))}
      </div>
      <div class="tdt-muc"><div class="small muted">${NN.h('td_sections')}</div>
        <div class="tdt-muc-hang">${maMuc.map((k, i) => `<span class="tdt-muc-o ${m[k] || 'wait'}" title="${esc(NN.t(nhanMuc[i]))}">
          <b>${['I', 'II', 'III', 'IV', 'V', 'VI'][i]}</b></span>`).join('')}</div></div>`;
  }

  /* ---------------------------------------------------------------- tải & thao tác */
  async function tai(giuChon) {
    BANG = await API.get('/api/theo-doi?tat_ca=1');
    q('#tdt-luc').innerHTML = NN.h('td_asof', { luc: EPL.ngayGio(BANG.luc) });
    veOSo(); veDanhSach();
    if (giuChon && P) { const con = BANG.chuyen.find(c => c.id === P.id); if (!con) { P = null; ve(); } }
  }
  async function mo(id) {
    try { P = await API.get('/api/trips/' + id); veDanhSach(); ve(); } catch (e) { EPL.baoLoi(e); }
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

  EPL.modules['theo-doi-tuyen'] = {
    async init(r, ctx) {
      root = r;
      [PARTS, KM] = await Promise.all([API.get('/api/parts'), API.get('/api/khoan-muc')]);
      q('#tdt-q').addEventListener('input', veDanhSach);
      q('#tdt-chi-chay').addEventListener('change', veDanhSach);
      q('#tdt-tu-dong').addEventListener('change', e => datTuDong(e.target.checked));
      q('#tdt-lam-moi').addEventListener('click', () => tai(true).catch(EPL.baoLoi));
      q('#tdt-so-su-co').addEventListener('click', moSo);
      q('#tdt-mo-phieu').addEventListener('click', () => P && EPL.di('phieu-xuat-xe', { id: P.id }));
      q('#tdt-su-co').addEventListener('click', moSuCo);
      q('#tdt-ghi-chu').addEventListener('click', ghiChu);
      q('#tdt-f-co-sua').addEventListener('change', e => { q('#tdt-f-sua').hidden = !e.target.checked; });
      root.querySelectorAll('.tdt-sap button').forEach(b => b.addEventListener('click', () => {
        root.querySelectorAll('.tdt-sap button').forEach(x => x.classList.toggle('active', x === b));
        sap = b.dataset.sap; veDanhSach();
      }));
      root.querySelectorAll('.tdt-bd-tab button').forEach(b => b.addEventListener('click', () => {
        root.querySelectorAll('.tdt-bd-tab button').forEach(x => x.classList.toggle('active', x === b));
        cheDoBD = b.dataset.bd; veBanDo();
      }));
      q('#tdt-nen').addEventListener('change', e => { datNen(e.target.value); });
      root.querySelectorAll('.tdt-nguon button').forEach(b => b.addEventListener('click', () => datNguon(b.dataset.src)));
      q('#tdt-f-part').addEventListener('change', () => datNguon('kho'));
      await tai();
      const t = ctx.tham || {};
      const dau = t.id || (loc()[0] || {}).id;
      if (dau) await mo(dau); else ve();
    },
    destroy() {
      clearInterval(dongHo); dongHo = null;
      if (MAP) { MAP.remove(); MAP = null; lopNen = lopVe = null; }
    },
    onLang() { if (root) { veOSo(); veDanhSach(); ve(); } },
  };
})();
