/* Trạm thu phí — danh mục trạm (16/10, anh Hải: «anh đi đường container — tính trạm thu phí để phiếu xuất xe có sẵn phí»).
 *
 * Mỗi trạm MỘT giá một lượt cho xe EPL (anh chọn 16/10). Tuyến đi qua trạm (màn Tuyến đường, thẻ «Trạm thu phí») thì phiếu xuất xe có mỗi
 * trạm một dòng phí cao tốc; số lượt = 1, thêm lượt về khi tuyến có km chiều về và trạm thu cả hai chiều. Bãi không thấy, không đặt giá
 * (anh Khampla A2) — máy chủ cũng bỏ giá Bãi gửi lên (routes/tram_thu_phi.py).
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], nuoc = '', chon = null;
  let MAP = null, lopVe = null, theoDau = null;
  const suaDuoc = () => AUTH.la('yard', 'acct', 'expacct');
  const thayGia = () => AUTH.role !== 'yard';
  const q = (s) => root.querySelector(s);
  const boDau = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const coGia = (t) => t.fee != null;
  const TRAM_IC = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 14V3M2.5 6h11M5.5 6l2 3.2M9.5 6l2 3.2"/></svg>';

  function loc() {
    const tu = boDau(q('#ttp-q').value.trim());
    return ds.filter(t => (!nuoc || (nuoc === 'chua_gia' ? !coGia(t) && t.active : t.country === nuoc))
      && (!tu || boDau(t.name + ' ' + (t.note || '')).includes(tu)));
  }

  function veDanhSach() {
    const dem = { '': ds.length, LA: ds.filter(t => t.country === 'LA').length, VN: ds.filter(t => t.country === 'VN').length,
      chua_gia: ds.filter(t => !coGia(t) && t.active).length };
    root.querySelectorAll('#ttp-nuoc button').forEach(b => { b.classList.toggle('on', b.dataset.nuoc === nuoc); b.querySelector('b').textContent = dem[b.dataset.nuoc]; });
    q('#ttp-loc-gia').hidden = !thayGia();
    root.querySelectorAll('.ttp-gia').forEach(o => { o.hidden = !thayGia(); });
    const rows = loc();
    q('#ttp-than').innerHTML = rows.length ? rows.map((t, i) => `<tr data-id="${esc(t.id)}" class="${chon === t.id ? 'sel' : ''} ${t.active ? '' : 'kh-tat'}">
        <td>${i + 1}</td>
        <td lang="lo"><b>${esc(t.name)}</b><span class="ttp-phu"><span class="tuy3-nuoc">${esc(t.country)}</span>${t.note ? ' · ' + esc(t.note) : ''}</span></td>
        ${thayGia() ? `<td class="num">${coGia(t) ? EPL.tien(t.fee, t.currency) : `<span class="ttp-canh">${NN.h('tuy_chua_gia')}</span>`}</td>` : ''}
        <td>${t.one_way ? NN.h('tuy_mot_chieu') : ''}</td>
        <td class="num">${so(t.so_tuyen || 0)}</td>
        <td>${EPL.tag(t.active ? 'ok' : 'plain', t.active ? 'active' : 'inactive')}</td>
        <td class="ttp-nut">${suaDuoc() ? `<button type="button" class="btn sm" data-sua="${esc(t.id)}">${NN.h('edit')}</button>${!t.so_tuyen ? `<button type="button" class="btn sm quiet ttp-xoa" data-xoa="${esc(t.id)}" title="${esc(NN.t('delete'))}">×</button>` : ''}` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h(ds.length ? 'no_data' : 'ttp_trong')}</td></tr>`;
    root.querySelectorAll('#ttp-than tr[data-id]').forEach(tr => tr.addEventListener('click', (e) => {
      if (e.target.closest('[data-sua], [data-xoa]')) return;
      chon = tr.dataset.id; veDanhSach(); soi(chon);
    }));
    root.querySelectorAll('#ttp-than [data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(t => t.id === b.dataset.sua)).catch(EPL.baoLoi)));
    root.querySelectorAll('#ttp-than [data-xoa]').forEach(b => b.addEventListener('click', () => xoa(ds.find(t => t.id === b.dataset.xoa)).catch(EPL.baoLoi)));
    veBanDo();
  }

  /** Hộp sửa / thêm trạm. Bãi không có ô giá. Vị trí: thêm tay thì dán toạ độ; trạm dò từ bản đồ đã có sẵn. */
  async function sua(t) {
    const moi = !t;
    const f = [
      { id: 'name', label: 'tuy_tram', value: t ? t.name : '', lo: true, bat_buoc: true, rong: true },
      { id: 'country', label: 'ttp_nuoc', type: 'select', value: t ? t.country : 'LA', options: [['LA', 'LA — Lào / ລາວ'], ['VN', 'VN — Việt Nam / ຫວຽດນາມ'], ['TH', 'TH — Thái Lan / ໄທ']] },
    ];
    if (thayGia()) f.push(
      { id: 'fee', label: 'tuy_gia_luot', type: 'number', value: t ? t.fee : '', goi_y: 'ttp_gia_goi_y' },
      { id: 'currency', label: 'cur', type: 'select', value: t ? t.currency : 'LAK', options: ['LAK', 'VND', 'THB', 'USD'].map(c => [c, c]) });
    f.push(
      { id: 'vi_tri', label: 'tuy_vi_tri', value: t && t.lat != null ? `${t.lat}, ${t.lng}` : '', placeholder: '18.44, 103.15', goi_y: 'ttp_vi_tri_goi_y' },
      { id: 'one_way', label: 'tuy_mot_chieu', type: 'bat', value: t ? t.one_way : false, nhan_bat: 'tuy_mot_chieu' },
      { id: 'note', label: 'note', value: t ? t.note || '' : '', rong: true });
    if (!moi) f.push({ id: 'active', label: 'status', type: 'bat', value: t.active, nhan_bat: 'active' });
    const kq = await EPL.hopNhap(NN.t(moi ? 'ttp_them' : 'edit') + (t ? ' — ' + t.name : ''), f, NN.t('save'), { cot: 2 });
    if (!kq) return;
    const m = String(kq.vi_tri || '').trim().match(/^(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)$/);
    const body = { name: kq.name, country: kq.country, one_way: kq.one_way, note: kq.note,
      lat: m ? +m[1] : (String(kq.vi_tri || '').trim() ? kq.vi_tri : null), lng: m ? +m[2] : null };
    if (thayGia()) { body.fee = kq.fee === '' ? null : kq.fee; body.currency = kq.currency; }
    if (!moi) body.active = kq.active;
    const r = await (moi ? API.post('/api/toll-stations', body) : API.put('/api/toll-stations/' + t.id, body));
    EPL.toast(NN.t('saved'), 'ok');
    ds = await API.get('/api/toll-stations'); chon = r.id; veDanhSach(); soi(r.id);
  }

  /** Xoá trạm thêm nhầm — chỉ trạm chưa tuyến nào gắn (máy chủ còn chặn trạm đã có trên phiếu). Hỏi bằng hộp của ứng dụng. */
  async function xoa(t) {
    if (!t || !(await EPL.hoi(NN.t('ttp_xoa_hoi', { ten: t.name }), '', NN.t('delete')))) return;
    await API.del('/api/toll-stations/' + t.id);
    EPL.toast(NN.t('ttp_da_xoa'), 'ok');
    ds = await API.get('/api/toll-stations'); if (chon === t.id) chon = null; veDanhSach();
  }

  /* ---------------------------------------------------------------- bản đồ */
  function napLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (!document.getElementById('leaflet-css')) {
      const l = document.createElement('link'); l.id = 'leaflet-css'; l.rel = 'stylesheet'; l.href = 'vendor/leaflet/leaflet.css';
      document.head.appendChild(l);
    }
    return new Promise((res, rej) => {
      const sc = document.createElement('script'); sc.src = 'vendor/leaflet/leaflet.js';
      sc.onload = () => res(window.L); sc.onerror = () => rej(new Error('leaflet'));
      document.head.appendChild(sc);
    });
  }
  function veBanDo() { veBanDoThat().catch(() => { const o = q('#ttp-map-bao'); if (o) { o.hidden = false; o.innerHTML = NN.h('tuy_nen_loi'); } }); }
  async function veBanDoThat() {
    const o = q('#ttp-map'); if (!o) return;
    const L = await napLeaflet();
    if (!root.isConnected) return;
    if (!MAP) {
      MAP = L.map(o, { zoomControl: true });
      MAP.setView([18.2, 104.0], 6);
      const nen = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Tiles © Esri · © OpenStreetMap' }).addTo(MAP);
      let h = null;
      nen.on('tileerror', () => { clearTimeout(h); h = setTimeout(() => { const b = q('#ttp-map-bao'); if (b) { b.hidden = false; b.innerHTML = NN.h('tuy_nen_loi'); } }, 800); });
      nen.on('tileload', () => { clearTimeout(h); const b = q('#ttp-map-bao'); if (b) b.hidden = true; });
    }
    if (lopVe) MAP.removeLayer(lopVe);
    lopVe = L.layerGroup().addTo(MAP);
    const co = loc().filter(t => t.lat != null && t.lng != null);
    co.forEach(t => {
      L.marker([t.lat, t.lng], {
        icon: L.divIcon({ className: 'tuy3-mk-o', html: `<span class="tuy3-tp${coGia(t) || !thayGia() ? '' : ' chua'}${chon === t.id ? ' on' : ''}">${TRAM_IC}</span>`, iconSize: [20, 20], iconAnchor: [10, 10] }),
        keyboard: false, zIndexOffset: chon === t.id ? 500 : 0,
      }).bindTooltip(`${esc(t.name)}${thayGia() && coGia(t) ? ' · ' + EPL.tien(t.fee, t.currency) : ''}`, { direction: 'top', offset: [0, -10] })
        .on('click', () => { chon = t.id; veDanhSach(); })
        .addTo(lopVe);
    });
    if (!chon && co.length) MAP.fitBounds(L.latLngBounds(co.map(t => [t.lat, t.lng])).pad(0.15), { maxZoom: 11 });
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }
  function soi(id) {
    const t = ds.find(x => x.id === id);
    if (MAP && t && t.lat != null) MAP.setView([t.lat, t.lng], Math.max(MAP.getZoom(), 13));
  }

  function caoKhung() {
    const el = q('#ttp'); if (!el) return;
    if ((window.innerWidth || 1600) <= 1000) { el.style.height = ''; return; }
    let tren = 0, n = el;
    while (n) { tren += n.offsetTop; n = n.offsetParent; }
    const ty = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    let cao = Math.max(420, (window.innerHeight || 900) / ty - tren - 20);
    el.style.height = cao + 'px';
    const de = document.documentElement, du = de.scrollHeight - de.clientHeight;
    if (du > 0 && cao > 420) { cao = Math.max(420, cao - du / ty); el.style.height = cao + 'px'; }
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }
  const khiDoiCo = () => caoKhung();

  EPL.modules['tram-thu-phi'] = {
    async init(r) {
      root = r; MAP = null; lopVe = null; chon = null;
      ds = await API.get('/api/toll-stations');
      q('#ttp-q').addEventListener('input', veDanhSach);
      root.querySelectorAll('#ttp-nuoc button').forEach(b => b.addEventListener('click', () => { nuoc = b.dataset.nuoc; chon = null; veDanhSach(); }));
      const them = q('#ttp-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null).catch(EPL.baoLoi));
      window.addEventListener('resize', khiDoiCo);
      if (window.ResizeObserver) { theoDau = new ResizeObserver(khiDoiCo); ['tbar', 'topbar'].forEach(id => { const e = document.getElementById(id); if (e) theoDau.observe(e); }); }
      veDanhSach();
      caoKhung(); setTimeout(caoKhung, 0);
    },
    destroy() {
      window.removeEventListener('resize', khiDoiCo);
      if (theoDau) { theoDau.disconnect(); theoDau = null; }
      if (MAP) { MAP.remove(); MAP = null; lopVe = null; }
    },
    onLang() { if (root) veDanhSach(); },
  };
})();
