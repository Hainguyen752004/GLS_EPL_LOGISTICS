/* Tuyến đường — danh sách | khung làm việc (chặng cạnh bản đồ) · chi phí gợi ý ở thẻ thứ hai.
 *
 * 16/10 làm lại theo màn cấu hình tuyến của EPL_System (anh Hải: «quá lỏ»). Trước đây: bảng danh sách + khung chi tiết xếp dọc,
 * sửa trong một hộp nổi phải gõ vĩ độ / kinh độ bằng tay. Nay:
 *   · sửa NGAY TRONG khung (không hộp nổi), chặng hiện kiểu EPL_System: Điểm đi → Điểm đến · km khai · km đường bộ đo được;
 *   · vị trí điểm chấm trên bản đồ: bấm «Chấm» rồi bấm lên bản đồ, kéo chấm, tìm theo tên, hoặc dán toạ độ «18.44, 103.15»;
 *   · km đường bộ đo bằng máy chỉ đường công khai — CHỈ để soát: km khai nuôi dầu, cước, lương nên không bị ghi đè;
 *     muốn dùng số đo thì bấm «Dùng km đo được» rồi Lưu (như EPL_System);
 *   · 16/10 (anh Hải: «anh không đi đường bộ, anh đi đường container — tính trạm thu phí để phiếu xuất xe có sẵn phí»): đường vẽ
 *     theo chế độ XE TẢI (Valhalla, đầu kéo + rơ-moóc 40 tấn) thay cho chế độ xe con (OSRM); thẻ «Trạm thu phí»: dò trạm trên đường
 *     xe đi (máy chủ: routes/tram_thu_phi.py), giá một lượt cho xe EPL, thu một chiều, lượt về — chọn tuyến trên phiếu là có mỗi trạm
 *     một dòng phí cao tốc;
 *   · mất mạng: nền bản đồ, đo đường, tìm theo tên bỏ qua và nói ra; chặng, km, dán toạ độ vẫn làm được.
 * API giữ nguyên (/api/routes) — toạ độ vẫn là lat / lng của từng điểm như màn Theo dõi tuyến đang đọc.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], chon = null, KM = null, DIEM = [];
  let che = 'xem';                  // 'xem' · 'sua' (tuyến đang chọn) · 'moi' (tuyến mới)
  let tam = null, banDau = '';      // bản đang sửa + ảnh chụp lúc bắt đầu sửa (biết có thay đổi chưa lưu)
  let the = 'chang', loc = 'dang';
  let MAP = null, lopNen = null, lopVe = null, nen = 'duong', nenLoi = false;
  let chamO = null;                 // chỉ số điểm đang chấm vị trí (null = không chấm)
  let DO = { khoa: '', legs: {} };  // kết quả đo đường bộ của bộ toạ độ đang hiện
  let henDo = null, henTen = null, theoDau = null;
  let STS = [];                     // danh mục trạm thu phí (thêm trạm vào tuyến)
  let ganTram = [], chamTram = false; // trạm gần đường (gợi ý sau lần dò) · đang chấm trạm mới trên bản đồ
  const DO_DEM = new Map();         // khoá toạ độ → kết quả đo (khỏi hỏi lại máy đo đường mỗi lần vẽ)

  const suaDuoc = () => AUTH.la('yard', 'acct');
  // Bãi không thấy tiền (anh Khampla A2): cột đơn giá gợi ý chỉ hiện với vai được thấy tiền chi
  const thayGia = () => AUTH.role !== 'yard';
  const MUC_CP = [['fuel', 'sec3'], ['travel', 'sec4'], ['other', 'sec6']];
  const CACH = [['', '—'], ['tien_mat', 'pm_on_dispatch'], ['luong', 'pm_trip_salary'], ['ncc', 'pm_supplier']];
  const NEN = {
    'duong': ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', 'Tiles © Esri'],
    've-tinh': ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 'Tiles © Esri'],
  };
  // Máy chỉ đường Valhalla công khai (FOSSGIS — máy openstreetmap.org đang dùng), chế độ xe tải. Cỡ xe: đầu kéo + rơ-moóc / container
  // 40' chở đầy — đường cấm xe tải, cầu yếu thì máy tránh.
  const VALHALLA = 'https://valhalla1.openstreetmap.de/route';
  const XE = { length: 16.5, width: 2.55, height: 4.2, weight: 40, axle_load: 10 };
  const TRAM_IC = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 14V3M2.5 6h11M5.5 6l2 3.2M9.5 6l2 3.2"/></svg>';
  /** Giải mã đường kiểu polyline6 (Valhalla) → [[lat, lng], …] */
  function giaiMa6(s) {
    const ra = []; let i = 0, la = 0, lo = 0;
    while (i < s.length) {
      for (let k = 0; k < 2; k++) {
        let sh = 0, r = 0, b;
        do { b = s.charCodeAt(i++) - 63; r |= (b & 0x1f) << sh; sh += 5; } while (b >= 0x20);
        const d = (r & 1) ? ~(r >> 1) : (r >> 1);
        if (k === 0) la += d; else lo += d;
      }
      ra.push([la / 1e6, lo / 1e6]);
    }
    return ra;
  }
  const TIM = 'https://nominatim.openstreetmap.org/search';
  const THUNG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/></svg>';
  const GHIM = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/></svg>';

  const q = (s) => root.querySelector(s);
  const boDau = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const tenDiem = (id) => { const x = DIEM.find(d => d.id === id); return x ? x.name : '—'; };
  const tenKhoan = (x) => x.item_key ? NN.t(x.item_key) : (x.item_name || '—');
  const dangSua = () => che !== 'xem';
  const diem = () => dangSua() ? tam.stops : (chon ? chon.stops : []);
  const coVT = (d) => !!d && d.lat !== '' && d.lat != null && d.lng !== '' && d.lng != null && isFinite(+d.lat) && isFinite(+d.lng);
  const vai = (i, n) => i === 0 ? 'dau' : (i === n - 1 ? 'cuoi' : 'giua');
  const nut = (i, n, d) => `<span class="tuy3-n ${vai(i, n)}${coVT(d) ? '' : ' chua'}" title="${esc(coVT(d) ? '' : NN.t('tuy_chua_cham'))}">${i + 1}</span>`;
  const kmDi = () => diem().slice(1).reduce((a, d) => a + EPL.doc(d.km_from_prev), 0);
  const coThayDoi = () => dangSua() && JSON.stringify(tam) !== banDau;

  /* ------------------------------------------------------------------ danh sách bên trái */
  function veDanhSach() {
    const tu = boDau(q('#tuy-q').value.trim());
    const dem = { dang: ds.filter(r => r.active).length, ngung: ds.filter(r => !r.active).length, tat: ds.length };
    root.querySelectorAll('#tuy-loc button').forEach(b => {
      b.classList.toggle('on', b.dataset.loc === loc); b.querySelector('b').textContent = dem[b.dataset.loc];
    });
    const rows = ds.filter(r => (loc === 'tat' || (loc === 'dang') === !!r.active)
      && (!tu || boDau([r.name, r.origin, r.destination].join(' ')).includes(tu)));
    const idChon = che === 'moi' ? null : (chon && chon.id);
    q('#tuy-than').innerHTML = rows.length ? rows.map((r, i) => `<tr data-id="${esc(r.id)}" class="${idChon === r.id ? 'sel' : ''} ${r.active ? '' : 'kh-tat'}">
      <td>${i + 1}</td>
      <td lang="lo"><b>${esc(r.name)}</b><span class="tuy3-phu">${esc(NN.t('tuy_diem_n', { n: r.so_diem }))}${r.return_km ? ' · ' + esc(NN.t('km_ve')) + ' ' + so(r.return_km, 1) : ''}${r.active ? '' : ' · ' + esc(NN.t('inactive'))}</span></td>
      <td class="num">${so(r.total_km, 1)}</td></tr>`).join('')
      : `<tr><td colspan="3" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('#tuy-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => moTuyen(tr.dataset.id).catch(EPL.baoLoi)));
  }

  async function boSuaNeuCan() {
    if (!coThayDoi()) return true;
    return EPL.hoi(NN.t('tuy_bo_thay_doi'), '', NN.t('tuy_bo'));
  }
  async function moTuyen(id) {
    if (che !== 'moi' && chon && chon.id === id && !dangSua()) return;
    if (!(await boSuaNeuCan())) return;
    chon = await API.get('/api/routes/' + id);
    che = 'xem'; tam = null; chamO = null;
    veTatCa(true);
  }

  /* ------------------------------------------------------------------ khung làm việc */
  function batDauSua(r) {
    tam = r ? {
      name: r.name, toll_lak: r.toll_lak || '', return_km: r.return_km || '', note: r.note || '', active: !!r.active,
      stops: r.stops.map(s => ({ name: s.name, km_from_prev: s.km_from_prev, lat: s.lat, lng: s.lng })),
      cost: Array.isArray(r.cost_template) ? r.cost_template.map(x => ({ ...x })) : [],
      tolls: (r.tram || []).map(saoTram),
    } : { name: '', toll_lak: '', return_km: '', note: '', active: true, stops: [{ name: '' }, { name: '', km_from_prev: '' }], cost: [], tolls: [] };
    banDau = JSON.stringify(tam);
    che = r ? 'sua' : 'moi'; chamO = null; ganTram = []; chamTram = false;
    veTatCa(true);
    const o = q('#tuy-f-name'); if (o && !r) o.focus();
  }

  function veTatCa(canhLai) {
    veDanhSach();
    const trong = !chon && che === 'xem';
    q('#tuy-trong').hidden = !trong;
    ['#tuy-dau', '#tuy-tom', '.tuy3-the'].forEach(s => { q(s).hidden = trong; });
    apThe(trong);
    q('#tuy-ws').classList.toggle('dang-sua', dangSua());
    if (trong) return;
    veDau(); veTom(); veThe(); veChang(); veTram(); veCp();
    veBanDo(canhLai);
    henDoDuong(0);
  }

  function veDau() {
    const o = q('#tuy-dau');
    if (!dangSua()) {
      o.innerHTML = `<div class="tuy3-ten"><h3 lang="lo">${esc(chon.name)}</h3>${EPL.tag(chon.active ? 'ok' : 'plain', chon.active ? 'active' : 'inactive')}</div>
        <div class="grow"></div>${suaDuoc() ? `<button type="button" class="btn" id="tuy-sua">${NN.h('edit')}</button>` : ''}`;
      const b = q('#tuy-sua'); if (b) b.addEventListener('click', () => batDauSua(chon));
      return;
    }
    o.innerHTML = `<label class="tuy3-o-ten"><span>${NN.h(che === 'moi' ? 'tuy_them_tuyen' : 'route_name')}</span>
        <input id="tuy-f-name" lang="lo" value="${esc(tam.name)}" placeholder="${esc(NN.t('route_name'))}"></label>
      ${che === 'sua' ? `<label class="tuy3-o-tt"><span>${NN.h('status')}</span><select id="tuy-f-active"><option value="1" ${tam.active ? 'selected' : ''}>${esc(NN.t('active'))}</option><option value="0" ${tam.active ? '' : 'selected'}>${esc(NN.t('inactive'))}</option></select></label>` : ''}
      <div class="grow"></div>
      <button type="button" class="btn" id="tuy-huy">${NN.h('cancel')}</button>
      <button type="button" class="btn primary" id="tuy-luu">${NN.h('save')}</button>`;
    q('#tuy-f-name').addEventListener('input', e => { tam.name = e.target.value; });
    const st = q('#tuy-f-active'); if (st) st.addEventListener('change', e => { tam.active = e.target.value === '1'; });
    q('#tuy-huy').addEventListener('click', huySua);
    q('#tuy-luu').addEventListener('click', () => luu().catch(EPL.baoLoi));
  }

  /** Dải số tóm tắt dưới tên tuyến. Lúc sửa: chiều về, BOT, ghi chú, trạng thái là ô nhập; tổng km tự tính. */
  function veTom() {
    const o = q('#tuy-tom');
    const f = (nhan, gt, lop) => `<div class="tuy3-f ${lop || ''}"><span>${NN.h(nhan)}</span>${gt}</div>`;
    if (!dangSua()) {
      o.innerHTML = f('tuy_chieu_di', `<b>${so(chon.total_km, 1)} km</b>`)
        + f('km_ve', `<b>${chon.return_km ? so(chon.return_km, 1) + ' km' : '—'}</b>`)
        + f('km_ca_chuyen', `<b>${so(chon.round_km, 1)} km</b>`)
        + ((chon.tram || []).length ? f('tuy_phi_tram', `<b id="tuy-phi-tram">${phiTramHtml()}</b>`) : f('toll_bot', `<b>${so(chon.toll_lak)} LAK</b>`))
        + f('trips_count', `<b>${so(chon.so_phieu)}</b>`)
        + (chon.note ? f('note', `<b class="tuy3-ghi" lang="lo">${esc(chon.note)}</b>`, 'rong') : '');
      return;
    }
    const di = kmDi();
    o.innerHTML = f('tuy_chieu_di', `<b id="tuy-km-di">${so(di, 1)} km</b>`)
      + f('km_ve', `<div class="tuy3-f-o"><input id="tuy-f-ve" class="num" inputmode="decimal" value="${esc(tam.return_km ?? '')}" title="${esc(NN.t('km_ve_hint'))}">
          <button type="button" class="btn sm quiet" id="tuy-f-ve-bang" title="${esc(NN.t('km_ve_hint'))}">= ${so(di, 1)} km</button></div>`)
      + f('km_ca_chuyen', `<b id="tuy-km-ca">${so(di + EPL.doc(tam.return_km), 1)} km</b>`)
      + (tam.tolls.length ? f('tuy_phi_tram', `<b id="tuy-phi-tram">${phiTramHtml()}</b>`)
        : f('toll_bot', `<div class="tuy3-f-o"><input id="tuy-f-toll" class="num" inputmode="numeric" value="${esc(tam.toll_lak ?? '')}"><small>LAK</small></div>`))
      + f('note', `<input id="tuy-f-note" lang="lo" value="${esc(tam.note || '')}">`, 'rong');
    q('#tuy-f-ve').addEventListener('input', e => { tam.return_km = e.target.value; capNhatTong(); });
    q('#tuy-f-ve-bang').addEventListener('click', () => { tam.return_km = Math.round(kmDi() * 10) / 10; q('#tuy-f-ve').value = tam.return_km; capNhatTong(); });
    const bot = q('#tuy-f-toll'); if (bot) bot.addEventListener('input', e => { tam.toll_lak = e.target.value; });
    q('#tuy-f-note').addEventListener('input', e => { tam.note = e.target.value; });
  }
  // gõ km thì chỉ sửa mấy con số tổng, không vẽ lại ô đang gõ
  function capNhatTong() {
    const di = kmDi();
    const a = q('#tuy-km-di'), b = q('#tuy-km-ca'), c = q('#tuy-f-ve-bang'), t = q('#tuy-chang-tong');
    if (a) a.textContent = so(di, 1) + ' km';
    if (b) b.textContent = so(di + EPL.doc(tam.return_km), 1) + ' km';
    if (c) c.textContent = '= ' + so(di, 1) + ' km';
    if (t) t.textContent = so(di, 1);
    veDo();
    veTram(); veTomTram();
  }

  function apThe(trong) {
    q('.tuy3-noi-chang').hidden = trong || the === 'cp';
    q('.tuy3-noi-cp').hidden = trong || the !== 'cp';
    root.querySelectorAll('.tuy3-trai [data-tab-noi]').forEach(o => { o.hidden = o.dataset.tabNoi !== the; });
    q('#tuy-ws').dataset.the = the;
  }
  function veThe() {
    root.querySelectorAll('#tuy-tab button').forEach(b => b.classList.toggle('on', b.dataset.tab === the));
    apThe(false);
    // bộ gợi ý chỉ xem có cả dòng phí theo trạm (máy chủ ghép vào) — đếm ở thẻ «Chi phí gợi ý» không tính các dòng đó
    const n = dangSua() ? tam.cost.length : (chon.goi_y || []).filter(x => !x.toll_station_id).length;
    q('#tuy-cp-dem').textContent = n;
    q('#tuy-tram-dem').textContent = dsTram().length;
    veThePhai();
    if (the !== 'cp' && MAP) setTimeout(() => MAP && MAP.invalidateSize(), 30);
  }

  /** Góc phải hàng thẻ: số điểm đã chấm vị trí, km đường bộ đo được cả tuyến, nút «Dùng km đo được» khi đang sửa. */
  function veThePhai() {
    const o = q('#tuy-the-phai'); if (!o) return;
    if (the === 'tram') { veThePhaiTram(o); return; }
    if (the !== 'chang') { o.innerHTML = ''; return; }
    const dd = diem(), co = dd.filter(coVT).length;
    let h = `<span class="tuy3-dem ${co === dd.length ? 'du' : ''}">${GHIM}${esc(NN.t('tuy_da_cham', { n: co, m: dd.length }))}</span>`;
    if (DO.dang) h += `<span class="tuy3-do muted">${NN.h('tuy_dang_do')}</span>`;
    else if (DO.du && DO.tong != null) {
      const khai = kmDi(), lech = khai - DO.tong;
      h += `<span class="tuy3-do">${NN.h('tuy_km_do')}: <b>${so(DO.tong, 1)} km</b>${khai ? ` <i class="${lopLech(lech, DO.tong)}">${lech > 0 ? '+' : ''}${so(lech, 1)} km · ${so(Math.abs(lech) / DO.tong * 100, 1)}%</i>` : ''}</span>`;
    }
    if (dangSua() && Object.keys(DO.legs || {}).length) h += `<button type="button" class="btn sm" id="tuy-dung-do">${NN.h('tuy_dung_km_do')}</button>`;
    o.innerHTML = h;
    const b = q('#tuy-dung-do'); if (b) b.addEventListener('click', dungKmDo);
  }
  const lopLech = (lech, goc) => { const p = goc ? Math.abs(lech) / goc : 0; return 'tuy3-lech ' + (p < 0.05 ? 'vua' : p < 0.15 ? 'lech' : 'xa'); };
  // gon: ô nhỏ dưới ô km lúc sửa — chưa đo được thì để trống, khỏi một dấu «—» dưới mỗi ô
  function oDo(i, gon) {
    if (!i) return '';
    const km = (DO.legs || {})[i];
    if (km == null) return DO.dang ? '…' : (gon ? '' : '—');
    const khai = EPL.doc(diem()[i].km_from_prev), lech = khai - km;
    return `${so(km, 1)}${khai ? `<small class="${lopLech(lech, km)}">${lech > 0 ? '+' : ''}${so(lech, 1)}</small>` : ''}`;
  }
  function veDo() {
    root.querySelectorAll('[data-do]').forEach(td => { td.innerHTML = oDo(+td.dataset.do, td.dataset.gon); });
    veThePhai();
  }
  function dungKmDo() {
    let n = 0;
    Object.entries(DO.legs || {}).forEach(([i, km]) => { if (tam.stops[+i]) { tam.stops[+i].km_from_prev = km; n++; } });
    veChang(); veTom();
    EPL.toast(NN.t('tuy_da_dung_km_do', { n }), 'ok');
  }

  /* ------------------------------------------------------------------ bảng chặng */
  function veChang() {
    const o = q('#tuy-chang'), dd = diem(), n = dd.length;
    if (!dangSua()) {
      const dong = dd.slice(1).map((d, k) => {
        const i = k + 1, a = dd[i - 1];
        return `<tr data-chang="${i}"><td>${i}</td>
          <td lang="lo"><span class="tuy3-p">${nut(i - 1, n, a)}${esc(a.name)}</span> <span class="tuy3-p"><span class="tuy3-mui">→</span>${nut(i, n, d)}${esc(d.name)}</span></td>
          <td class="num"><b>${so(d.km_from_prev, 1)}</b></td><td class="num" data-do="${i}">${oDo(i)}</td></tr>`;
      }).join('');
      const ve = chon.return_km && n ? `<tr class="tuy3-ve"><td>↩</td>
          <td lang="lo"><span class="tuy3-p">${esc(dd[n - 1].name)}</span> <span class="tuy3-p"><span class="tuy3-mui">→</span>${esc(dd[0].name)}</span> <small class="muted">${NN.h('km_ve')}</small></td>
          <td class="num"><b>${so(chon.return_km, 1)}</b></td><td class="num">—</td></tr>` : '';
      o.innerHTML = `<div class="tbl-wrap"><table class="tbl tuy3-bang-chang"><thead><tr><th>#</th><th>${NN.h('tuy_chang')}</th><th class="num">${NN.h('tuy_km_khai')}</th><th class="num">${NN.h('tuy_km_do')}</th></tr></thead>
        <tbody>${dong || `<tr><td colspan="4" class="empty">${NN.h('no_data')}</td></tr>`}${ve}</tbody>
        <tfoot><tr><td></td><td>${NN.h('tuy_chieu_di')}</td><td class="num">${so(chon.total_km, 1)}</td><td class="num">${DO.du && DO.tong != null ? so(DO.tong, 1) : '—'}</td></tr></tfoot></table></div>`;
      root.querySelectorAll('#tuy-chang tr[data-chang]').forEach(tr => tr.addEventListener('click', () => soiChang(+tr.dataset.chang)));
      return;
    }
    o.innerHTML = `<div class="tbl-wrap"><table class="tbl tbl-compact tuy3-sua"><thead><tr><th>#</th><th>${NN.h('stop')}</th><th class="num">${NN.h('km_from_prev')}<span class="tuy3-th-phu">${NN.h('tuy_km_do')}</span></th><th>${NN.h('tuy_vi_tri')}</th><th></th></tr></thead>
      <tbody>${dd.map((d, i) => `<tr class="${chamO === i ? 'cham' : ''}">
        <td>${nut(i, n, d)}</td>
        <td><input data-i="${i}" data-f="name" value="${esc(d.name || '')}" lang="lo" placeholder="${esc(NN.t(i === 0 ? 'origin' : (i === n - 1 ? 'tuy_diem_den' : 'stop')))}"></td>
        <td class="tuy3-km-o"><input class="num" data-i="${i}" data-f="km_from_prev" value="${i ? esc(d.km_from_prev ?? '') : ''}" ${i ? 'inputmode="decimal"' : 'disabled placeholder="—"'}>${i ? `<span class="tuy3-km-do" data-do="${i}" data-gon="1">${oDo(i, true)}</span>` : ''}</td>
        <td class="tuy3-vt-o"><button type="button" class="tuy3-vt ${coVT(d) ? 'co' : 'chua'} ${chamO === i ? 'on' : ''}" data-cham="${i}">${GHIM}<span>${coVT(d) ? (+d.lat).toFixed(3) + ', ' + (+d.lng).toFixed(3) : NN.h('tuy_cham')}</span></button>${coVT(d) ? `<button type="button" class="tuy3-bo-vt" data-bo-vt="${i}" title="${esc(NN.t('tuy_xoa_vi_tri'))}" aria-label="${esc(NN.t('tuy_xoa_vi_tri'))}">×</button>` : ''}</td>
        <td>${n > 2 ? `<button type="button" class="tuy3-xoa" data-xoa="${i}" title="${esc(NN.t('delete'))}" aria-label="${esc(NN.t('delete'))}">${THUNG}</button>` : ''}</td></tr>`).join('')}</tbody>
      <tfoot><tr><td></td><td>${NN.h('tuy_chieu_di')}</td><td class="num" id="tuy-chang-tong">${so(kmDi(), 1)}</td><td colspan="2"></td></tr></tfoot></table></div>
      <div class="tuy3-sua-nut"><button type="button" class="btn quiet sm" id="tuy-them-diem">+ ${NN.h('add_stop')}</button><span class="small muted">${NN.h('tuy_keo_doi')}</span></div>`;
    root.querySelectorAll('#tuy-chang input[data-f]').forEach(el => el.addEventListener('input', () => {
      const d = tam.stops[+el.dataset.i]; d[el.dataset.f] = el.value;
      if (el.dataset.f === 'km_from_prev') capNhatTong();
      else { clearTimeout(henTen); henTen = setTimeout(() => { veBanDo(false); if (chamO === +el.dataset.i) vePick(); }, 400); }
    }));
    root.querySelectorAll('#tuy-chang [data-cham]').forEach(b => b.addEventListener('click', () => batCham(+b.dataset.cham)));
    root.querySelectorAll('#tuy-chang [data-bo-vt]').forEach(b => b.addEventListener('click', () => {
      const d = tam.stops[+b.dataset.boVt]; d.lat = null; d.lng = null; doiDiem();
    }));
    root.querySelectorAll('#tuy-chang [data-xoa]').forEach(b => b.addEventListener('click', () => {
      const i = +b.dataset.xoa; tam.stops.splice(i, 1);
      if (i === 0 && tam.stops[0]) tam.stops[0].km_from_prev = '';
      if (chamO != null) chamO = chamO === i ? null : (chamO > i ? chamO - 1 : chamO);
      doiDiem(); veTom();
    }));
    q('#tuy-them-diem').addEventListener('click', () => { tam.stops.push({ name: '', km_from_prev: '' }); doiDiem(); veTom(); });
  }
  // điểm thêm / bớt / đổi vị trí: vẽ lại bảng, bản đồ, đo lại
  function doiDiem() { veChang(); veBanDo(false); vePick(); henDoDuong(); veThePhai(); }

  /** Bấm một chặng (lúc xem) → bản đồ thu vào hai đầu chặng đó. */
  function soiChang(i) {
    const dd = diem(), a = dd[i - 1], b = dd[i];
    root.querySelectorAll('#tuy-chang tr[data-chang]').forEach(tr => tr.classList.toggle('sel', +tr.dataset.chang === i));
    if (!MAP || !window.L) return;
    const p = [a, b].filter(coVT).map(d => [+d.lat, +d.lng]);
    if (p.length === 2) MAP.fitBounds(window.L.latLngBounds(p).pad(0.3), { maxZoom: 13 });
    else if (p.length === 1) MAP.setView(p[0], 11);
  }

  /* ------------------------------------------------------------------ chấm vị trí */
  function batCham(i) {
    chamO = chamO === i ? null : i; chamTram = false;
    veChang(); veBanDo(false); vePick();
    if (chamO != null) { const d = tam.stops[i]; if (coVT(d) && MAP) MAP.setView([+d.lat, +d.lng], Math.max(MAP.getZoom(), 10)); }
  }
  function datViTri(i, lat, lng, tiep) {
    const d = tam.stops[i]; if (!d) return;
    d.lat = Math.round(lat * 1e6) / 1e6; d.lng = Math.round(lng * 1e6) / 1e6;
    // chấm xong một điểm thì chuyển sang điểm kế tiếp chưa có vị trí — chấm cả tuyến một lượt
    if (tiep) { const k = tam.stops.findIndex((x, j) => j > i && !coVT(x)); chamO = k >= 0 ? k : null; }
    doiDiem();
  }
  function khiBamBanDo(e) {
    if (dangSua() && chamTram) { taoTramTai(e.latlng).catch(EPL.baoLoi); return; }
    if (!dangSua() || chamO == null) return;
    datViTri(chamO, e.latlng.lat, e.latlng.lng, true);
  }
  function vePick() {
    const o = q('#tuy-pick'); if (!o) return;
    if (chamTram && dangSua()) {
      o.hidden = false; q('#tuy-nen').hidden = true;
      const m = q('#tuy-map'); if (m) m.classList.add('dang-cham');
      o.innerHTML = `<div class="tuy3-pick-dau">${TRAM_IC}<span>${NN.h('tuy_cham_tram_hint')}</span><button type="button" class="x" id="tuy-pick-thoi" title="${esc(NN.t('cancel'))}">×</button></div>`;
      q('#tuy-pick-thoi').addEventListener('click', () => { chamTram = false; vePick(); veThePhai(); });
      return;
    }
    const d = chamO != null && tam ? tam.stops[chamO] : null;
    o.hidden = !d; q('#tuy-nen').hidden = !!d;
    const m = q('#tuy-map'); if (m) m.classList.toggle('dang-cham', !!d);
    if (!d) { o.innerHTML = ''; return; }
    o.innerHTML = `<div class="tuy3-pick-dau">${GHIM}<span>${NN.h('tuy_pick_hint', { n: chamO + 1, ten: d.name || '…' })}</span><button type="button" class="x" id="tuy-pick-thoi" title="${esc(NN.t('cancel'))}">×</button></div>
      <form class="tuy3-pick-tim" id="tuy-pick-form"><input id="tuy-pick-q" lang="lo" value="${esc(d.name || '')}" placeholder="${esc(NN.t('tuy_tim_dia_diem'))}" autocomplete="off">
        <button type="submit" class="btn sm primary">${NN.h('search')}</button></form>
      <div class="tuy3-pick-kq" id="tuy-pick-kq"></div>`;
    q('#tuy-pick-thoi').addEventListener('click', () => batCham(chamO));
    q('#tuy-pick-form').addEventListener('submit', (e) => { e.preventDefault(); timDiaDiem(q('#tuy-pick-q').value).catch(EPL.baoLoi); });
  }
  /** Dán toạ độ («18.44, 103.15» — chép từ Google Maps) thì đặt luôn, không cần mạng; còn lại tìm theo tên (cần mạng). */
  async function timDiaDiem(chu) {
    const s = String(chu || '').trim(), kq = q('#tuy-pick-kq'), i = chamO;
    if (!s || i == null) return;
    const m = s.match(/^\s*(-?\d{1,2}(?:\.\d+)?)\s*[,; ]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/);
    if (m && Math.abs(+m[1]) <= 90 && Math.abs(+m[2]) <= 180) {
      datViTri(i, +m[1], +m[2], true);
      if (MAP) MAP.setView([+m[1], +m[2]], Math.max(MAP.getZoom(), 11));
      return;
    }
    kq.innerHTML = `<div class="small muted">${NN.h('loading')}</div>`;
    let ds2 = [];
    try {
      const ng = NN.lang === 'both' ? 'vi,lo' : NN.lang;
      const r = await fetch(`${TIM}?format=json&limit=5&countrycodes=la,vn,th&accept-language=${encodeURIComponent(ng)}&q=${encodeURIComponent(s)}`);
      if (!r.ok) throw new Error('tim');
      ds2 = await r.json();
    } catch (e) {
      kq.innerHTML = `<div class="small tuy3-canh">${NN.h('tuy_can_mang')}</div>`; return;
    }
    if (chamO !== i || !root.isConnected) return;
    if (!Array.isArray(ds2) || !ds2.length) { kq.innerHTML = `<div class="small tuy3-canh">${NN.h('tuy_khong_tim_thay')}</div>`; return; }
    kq.innerHTML = ds2.map((x, k) => `<button type="button" data-k="${k}"><b lang="lo">${esc(String(x.display_name || '').split(',')[0])}</b><span lang="lo">${esc(String(x.display_name || '').split(',').slice(1, 4).join(','))}</span></button>`).join('');
    kq.querySelectorAll('button[data-k]').forEach(b => b.addEventListener('click', () => {
      const x = ds2[+b.dataset.k]; datViTri(i, +x.lat, +x.lon, true);
      if (MAP) MAP.setView([+x.lat, +x.lon], Math.max(MAP.getZoom(), 11));
    }));
  }

  /* ------------------------------------------------------------------ bản đồ */
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
  // Bản đồ là phần PHỤ: hỏng bản đồ thì chặng, km vẫn xem / sửa được.
  function veBanDo(canhLai) { veBanDoThat(canhLai).catch(() => baoBanDo()); }
  async function veBanDoThat(canhLai) {
    const o = q('#tuy-map'); if (!o) return;
    const L = await napLeaflet();
    if (!root.isConnected || !q('#tuy-map')) return;
    if (!MAP) {
      MAP = L.map(o, { zoomControl: true, attributionControl: true });
      MAP.setView([18.2, 104.0], 6);
      datNen(nen);
      MAP.on('click', khiBamBanDo);
    }
    if (lopVe) MAP.removeLayer(lopVe);
    lopVe = L.layerGroup().addTo(MAP);
    const dd = diem(), n = dd.length, co = dd.map((d, i) => [d, i]).filter(([d]) => coVT(d));
    const theoDuong = DO.path && DO.khoa === khoaDo();
    if (theoDuong) L.polyline(DO.path, { color: '#2F5D8A', weight: 5, opacity: .9 }).addTo(lopVe);
    else if (co.length > 1) L.polyline(co.map(([d]) => [+d.lat, +d.lng]), { color: '#2F5D8A', weight: 3, opacity: .8, dashArray: '6 8' }).addTo(lopVe);
    co.forEach(([d, i]) => {
      const mk = L.marker([+d.lat, +d.lng], {
        icon: L.divIcon({ className: 'tuy3-mk-o', html: `<span class="tuy3-mk ${vai(i, n)}${chamO === i ? ' on' : ''}">${i + 1}</span>`, iconSize: [28, 28], iconAnchor: [14, 14] }),
        draggable: dangSua(), keyboard: false, zIndexOffset: chamO === i ? 600 : 0,
      }).bindTooltip(`${i + 1}. ${esc(d.name || '…')}${i ? ' · +' + so(d.km_from_prev, 1) + ' km' : ''}`, { direction: 'top', offset: [0, -14] }).addTo(lopVe);
      if (dangSua()) mk.on('dragend', (e) => { const p = e.target.getLatLng(); datViTri(i, p.lat, p.lng, false); });
    });
    dsTram().filter(t => t.lat != null && t.lng != null).forEach(t => {
      L.marker([+t.lat, +t.lng], {
        icon: L.divIcon({ className: 'tuy3-mk-o', html: `<span class="tuy3-tp${coGiaTram(t) ? '' : ' chua'}">${TRAM_IC}</span>`, iconSize: [20, 20], iconAnchor: [10, 10] }),
        keyboard: false, zIndexOffset: -100,
      }).bindTooltip(`${esc(t.name)}${thayGia() && coGiaTram(t) ? ' · ' + EPL.tien(EPL.doc(t.fee), t.currency) : ''}`, { direction: 'top', offset: [0, -10] }).addTo(lopVe);
    });
    if (dangSua()) ganTram.forEach(u => {
      L.marker([u.lat, u.lng], { icon: L.divIcon({ className: 'tuy3-mk-o', html: `<span class="tuy3-tp goi-y">${TRAM_IC}</span>`, iconSize: [18, 18], iconAnchor: [9, 9] }), keyboard: false, zIndexOffset: -200 })
        .bindTooltip(`${esc(u.name || NN.t('tuy_tram'))} · ${esc(NN.t('tuy_cach_m', { m: so(u.cach_m) }))}`, { direction: 'top', offset: [0, -9] }).addTo(lopVe);
    });
    if (canhLai && co.length) MAP.fitBounds(L.latLngBounds(co.map(([d]) => [+d.lat, +d.lng])).pad(0.2), { maxZoom: 12 });
    baoBanDo(co.length, theoDuong);
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }
  /** Dòng nhắc dưới đáy bản đồ — nói thật về cái đang vẽ. */
  function baoBanDo(soCo, theoDuong) {
    const o = q('#tuy-map-bao'); if (!o) return;
    let k = '';
    if (!window.L) k = 'tuy_nen_loi';
    else if (!soCo) k = dangSua() ? 'tuy_ban_do_sua' : 'tuy_ban_do_trong';
    else if (nenLoi) k = 'tuy_nen_loi';
    else if (soCo > 1 && !theoDuong && !DO.dang) k = 'tuy_duong_thang';
    o.hidden = !k || chamO != null; o.innerHTML = k ? NN.h(k) : '';
  }
  function datNen(ma) {
    if (!MAP || !window.L) return;
    nen = ma; if (lopNen) MAP.removeLayer(lopNen);
    const [url, ghi] = NEN[ma] || NEN.duong;
    lopNen = window.L.tileLayer(url, { maxZoom: 18, attribution: ghi }).addTo(MAP);
    let henLoi = null;
    lopNen.on('tileerror', () => { clearTimeout(henLoi); henLoi = setTimeout(() => { nenLoi = true; veBaoNen(); }, 800); });
    lopNen.on('tileload', () => { clearTimeout(henLoi); if (nenLoi) { nenLoi = false; veBaoNen(); } });
    root.querySelectorAll('#tuy-nen button').forEach(b => b.classList.toggle('on', b.dataset.nen === ma));
  }
  function veBaoNen() { const dd = diem(); baoBanDo(dd.filter(coVT).length, DO.path && DO.khoa === khoaDo()); }

  /* ------------------------------------------------------------------ đo đường bộ (OSRM) */
  const khoaDo = () => diem().map(d => coVT(d) ? (+d.lat).toFixed(5) + ',' + (+d.lng).toFixed(5) : '_').join(';');
  function henDoDuong(cho) { clearTimeout(henDo); henDo = setTimeout(() => doDuong().catch(() => {}), cho == null ? 500 : cho); }
  async function doDuong() {
    if (!root || !root.isConnected || (!chon && !dangSua())) return;
    const khoa = khoaDo(), dd = diem(), co = dd.map((d, i) => [d, i]).filter(([d]) => coVT(d));
    if (DO.khoa === khoa && !DO.dang) { veDo(); return; }
    if (co.length < 2) { DO = { khoa, legs: {} }; veDo(); veBaoNen(); return; }
    if (DO_DEM.has(khoa)) { DO = DO_DEM.get(khoa); veDo(); veBanDo(false); return; }
    DO = { khoa, legs: {}, dang: true }; veDo();
    let kq;
    try {
      const ac = new AbortController(), h = setTimeout(() => ac.abort(), 15000);
      const yc = { locations: co.map(([d]) => ({ lat: +d.lat, lon: +d.lng })), costing: 'truck', costing_options: { truck: XE },
        units: 'kilometers', directions_type: 'none' };
      const r = await fetch(VALHALLA + '?json=' + encodeURIComponent(JSON.stringify(yc)), { signal: ac.signal });
      clearTimeout(h);
      const j = await r.json();
      if (!r.ok || !j.trip || j.trip.status !== 0) throw new Error('valhalla');
      const legs = {};
      // chặng i = điểm i-1 → điểm i; chỉ gán khi hai điểm liền nhau đều có vị trí (bỏ một điểm giữa thì đoạn đo gộp hai chặng)
      j.trip.legs.forEach((lg, k) => { const a = co[k][1], b = co[k + 1][1]; if (b === a + 1) legs[b] = Math.round(lg.summary.length * 10) / 10; });
      kq = { khoa, legs, tong: Math.round(j.trip.summary.length * 10) / 10, du: co.length === dd.length,
        path: j.trip.legs.reduce((a, lg) => a.concat(giaiMa6(lg.shape)), []) };
      DO_DEM.set(khoa, kq);
    } catch (e) {
      kq = { khoa, legs: {}, loi: true };
    }
    if (!root.isConnected || khoaDo() !== khoa) return;      // đã đổi điểm / rời màn trong lúc chờ
    DO = kq; veDo(); veBanDo(false);
    if (!dangSua()) veChang();
  }

  /* ------------------------------------------------------------------ trạm thu phí (thẻ thứ hai) */
  // Mỗi trạm: giá MỘT lượt cho xe EPL (anh Hải 16/10). Lượt = 1, thêm lượt về khi tuyến có km chiều về và trạm thu cả hai chiều —
  // cùng luật máy chủ (services/tram_thu_phi.luot). Bãi không thấy giá (anh Khampla A2).
  const saoTram = (t) => ({ ...t, _goc: { fee: t.fee ?? null, one_way: !!t.one_way, currency: t.currency } });
  const dsTram = () => dangSua() ? tam.tolls : ((chon && chon.tram) || []);
  const luotTram = (t) => 1 + (EPL.doc(dangSua() ? tam.return_km : (chon && chon.return_km)) > 0 && !t.one_way ? 1 : 0);
  const coGiaTram = (t) => t.fee != null && t.fee !== '';
  function tongTram() {
    const tong = {}; let chua = 0;
    dsTram().forEach(t => { if (!coGiaTram(t)) { chua++; return; } tong[t.currency] = (tong[t.currency] || 0) + EPL.doc(t.fee) * luotTram(t); });
    return { tong, chua };
  }
  function phiTramHtml() {
    const { tong, chua } = tongTram(), n = dsTram().length;
    if (!thayGia()) return esc(NN.t('tuy_n_tram', { n }));
    return (Object.keys(tong).length ? esc(EPL.tienGop(tong)) : '—') + (chua ? ` <small class="tuy3-canh">· ${esc(NN.t('tuy_n_chua_gia', { n: chua }))}</small>` : '');
  }
  function veTomTram() { const o = q('#tuy-phi-tram'); if (o) o.innerHTML = phiTramHtml(); }

  /** km của một điểm tính dọc đường xe đi đang vẽ (để xếp trạm thêm tay đúng thứ tự xe qua). Không có đường → null. */
  function kmTren(lat, lng) {
    const p = DO.path && DO.khoa === khoaDo() ? DO.path : null;
    if (!p || p.length < 2 || lat == null || lng == null) return null;
    const kx = Math.cos(lat * Math.PI / 180) * 111.32, ky = 110.54;
    let tot = null, cong = 0;
    for (let i = 1; i < p.length; i++) {
      const ax = (p[i - 1][1] - lng) * kx, ay = (p[i - 1][0] - lat) * ky, bx = (p[i][1] - lng) * kx, by = (p[i][0] - lat) * ky;
      const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy, dai = Math.sqrt(l2);
      const t = l2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0;
      const d = Math.hypot(ax + t * dx, ay + t * dy);
      if (tot == null || d < tot[0]) tot = [d, cong + t * dai];
      cong += dai;
    }
    return tot ? Math.round(tot[1] * 10) / 10 : null;
  }
  function xepTram() {
    tam.tolls.forEach(t => { if (t.km == null) t.km = kmTren(t.lat, t.lng); });
    tam.tolls.sort((a, b) => (a.km == null ? 1e9 : a.km) - (b.km == null ? 1e9 : b.km));
  }

  function veThePhaiTram(o) {
    if (!dangSua()) {
      o.innerHTML = dsTram().length ? `<span class="tuy3-do">${NN.h('tuy_phi_tram')}: <b>${phiTramHtml()}</b></span>` : '';
      return;
    }
    const co = new Set(tam.tolls.map(t => t.id));
    const them = STS.filter(s => s.active && !co.has(s.id));
    o.innerHTML = `<button type="button" class="btn sm primary tuy3-nut-tram" id="tuy-tim-tram">${TRAM_IC}<span>${NN.h('tuy_tim_tram')}</span></button>
      <button type="button" class="btn sm tuy3-nut-tram ${chamTram ? 'on' : ''}" id="tuy-cham-tram">+ <span>${NN.h('tuy_cham_tram')}</span></button>
      ${them.length ? `<select id="tuy-them-tram" class="tuy3-them-tram"><option value="">+ ${esc(NN.t('tuy_them_tram'))}</option>${them.map(s => `<option value="${esc(s.id)}">${esc(s.name)} · ${esc(s.country)}</option>`).join('')}</select>` : ''}`;
    q('#tuy-tim-tram').addEventListener('click', () => timTram().catch(EPL.baoLoi));
    q('#tuy-cham-tram').addEventListener('click', () => { chamTram = !chamTram; chamO = null; veChang(); vePick(); veThePhai(); });
    const sel = q('#tuy-them-tram');
    if (sel) sel.addEventListener('change', () => {
      const s = STS.find(x => x.id === sel.value); if (!s) return;
      tam.tolls.push(saoTram(s)); xepTram(); veTram(); veThe(); veTom(); veBanDo(false);
    });
  }

  /** Dò trạm trên đường xe tải đang vẽ: máy chủ so với trạm trong danh mục + trạm OpenStreetMap đóng gói, trạm mới thêm vào danh mục. */
  async function timTram() {
    if (!(DO.path && DO.khoa === khoaDo() && DO.path.length > 1)) { EPL.toast(NN.t(DO.dang ? 'tuy_dang_do' : 'tuy_can_duong'), 'loi'); return; }
    const b = q('#tuy-tim-tram'); if (b) b.disabled = true;
    try {
      const ra = await API.post('/api/toll-stations/doc-tuyen', { duong: DO.path, ten_tuyen: tam.name || '' });
      const kq = ra.tren || [];
      ganTram = ra.gan || [];
      const moi = kq.map(saoTram), da = new Set(moi.map(t => t.id));
      tam.tolls = moi.concat(tam.tolls.filter(t => !da.has(t.id)));      // trạm thêm tay mà không nằm trên đường: giữ, xếp cuối
      xepTram();
      STS = await API.get('/api/toll-stations').catch(() => STS);
      EPL.toast(NN.t(kq.length ? 'tuy_da_tim_tram' : 'tuy_khong_co_tram', { n: kq.length }), kq.length ? 'ok' : '');
      veTram(); veThe(); veTom(); veBanDo(false);
    } finally { if (b && b.isConnected) b.disabled = false; }
  }

  const tenTramMoi = (nuoc, km) => (nuoc === 'LA' ? 'ດ່ານເກັບຄ່າທາງ' : 'Trạm thu phí') + (km != null ? ' km ' + Math.round(km) : '');
  async function themVaoTuyen(st) {
    const t = saoTram(st); t.km = kmTren(t.lat, t.lng);
    if (!tam.tolls.some(x => x.id === t.id)) tam.tolls.push(t);
    xepTram();
    STS = await API.get('/api/toll-stations').catch(() => STS);
    veTram(); veThe(); veTom(); veBanDo(false);
  }
  /** Trạm gợi ý «gần đường»: trạm đã có trong danh mục thì dùng luôn; trạm OSM thì thêm vào danh mục (chưa có giá) rồi vào tuyến. */
  async function themGan(k) {
    const u = ganTram[k]; if (!u) return;
    const st = u.id ? STS.find(s => s.id === u.id)
      : await API.post('/api/toll-stations', { name: u.name || tenTramMoi(u.country, u.km), country: u.country, lat: u.lat, lng: u.lng, osm_ref: u.ref,
        note: tam.name ? NN.t('tuy_them_khi_do', { ten: tam.name }) : null });
    ganTram.splice(k, 1);
    if (st) await themVaoTuyen(st);
  }
  /** «Chấm trạm mới»: bấm lên bản đồ đúng chỗ có trạm (đường Lào nhiều trạm chưa có trên OpenStreetMap). */
  async function taoTramTai(ll) {
    chamTram = false; vePick(); veThePhai();
    const km = kmTren(ll.lat, ll.lng), nuoc = ll.lng > 105.0 ? 'VN' : 'LA';
    const f = [
      { id: 'name', label: 'tuy_tram', value: tenTramMoi(nuoc, km), lo: true, bat_buoc: true, rong: true },
      { id: 'country', label: 'ttp_nuoc', type: 'select', value: nuoc, options: [['LA', 'LA — Lào / ລາວ'], ['VN', 'VN — Việt Nam / ຫວຽດນາມ'], ['TH', 'TH — Thái Lan / ໄທ']] },
    ];
    if (thayGia()) f.push({ id: 'fee', label: 'tuy_gia_luot', type: 'number', value: '', goi_y: 'ttp_gia_goi_y' },
      { id: 'currency', label: 'cur', type: 'select', value: nuoc === 'VN' ? 'VND' : 'LAK', options: ['LAK', 'VND', 'THB', 'USD'].map(c => [c, c]) });
    f.push({ id: 'one_way', label: 'tuy_mot_chieu', type: 'bat', value: false, nhan_bat: 'tuy_mot_chieu' });
    const kq = await EPL.hopNhap(NN.t('ttp_them'), f, NN.t('add'), { cot: 2 });
    if (!kq) return;
    const body = { name: kq.name, country: kq.country, one_way: kq.one_way, lat: Math.round(ll.lat * 1e6) / 1e6, lng: Math.round(ll.lng * 1e6) / 1e6 };
    if (thayGia()) { body.fee = kq.fee === '' ? null : kq.fee; body.currency = kq.currency; }
    await themVaoTuyen(await API.post('/api/toll-stations', body));
  }

  function veTram() {
    const o = q('#tuy-tram'); if (!o) return;
    const dd = dsTram(), sua = dangSua(), gia = thayGia(), n = dd.length;
    const { tong, chua } = tongTram();
    const cot = 4 + (gia ? 2 : 0) + (sua ? 1 : 0);
    const dong = dd.map((t, i) => `<tr>
        <td>${i + 1}</td>
        <td lang="lo"><b>${esc(t.name)}</b><span class="tuy3-phu"><span class="tuy3-nuoc">${esc(t.country)}</span>${t.km != null ? ' · km ' + so(t.km, 1) : ''}</span></td>
        <td class="num">${luotTram(t)}</td>
        ${gia ? `<td class="num tuy3-gia-o">${sua
          ? `<div class="tuy3-f-o"><input class="num" data-i="${i}" data-f="fee" value="${esc(t.fee ?? '')}" inputmode="decimal" placeholder="${esc(NN.t('tuy_chua_gia'))}"><select data-i="${i}" data-f="currency">${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === t.currency ? 'selected' : ''}>${c}</option>`).join('')}</select></div>`
          : (coGiaTram(t) ? EPL.tien(EPL.doc(t.fee), t.currency) : `<span class="tuy3-canh">${NN.h('tuy_chua_gia')}</span>`)}</td>
        <td class="num" data-tt="${i}">${coGiaTram(t) ? EPL.tien(EPL.doc(t.fee) * luotTram(t), t.currency) : '—'}</td>` : ''}
        <td class="tuy3-mot-chieu-o">${sua ? `<label class="tuy3-mot-chieu" title="${esc(NN.t('tuy_mot_chieu'))}"><input type="checkbox" data-i="${i}" data-f="one_way" ${t.one_way ? 'checked' : ''}></label>`
          : (t.one_way ? `<span class="tuy3-co-mot" title="${esc(NN.t('tuy_mot_chieu'))}">✓</span>` : '')}</td>
        ${sua ? `<td><button type="button" class="tuy3-xoa" data-xoa-tram="${i}" title="${esc(NN.t('delete'))}" aria-label="${esc(NN.t('delete'))}">${THUNG}</button></td>` : ''}</tr>`).join('');
    o.innerHTML = `<div class="tbl-wrap"><table class="tbl tbl-compact tuy3-bang-tram"><thead><tr><th>#</th><th>${NN.h('tuy_tram')}</th><th class="num">${NN.h('tuy_luot')}</th>
        ${gia ? `<th class="num">${NN.h('tuy_gia_luot')}</th><th class="num">${NN.h('tuy_thanh_tien')}</th>` : ''}<th title="${esc(NN.t('tuy_mot_chieu'))}">${NN.h('tuy_mot_chieu_ngan')}</th>${sua ? '<th></th>' : ''}</tr></thead>
      <tbody>${dong || `<tr><td colspan="${cot}" class="empty">${NN.h(sua ? 'tuy_tram_trong_sua' : 'tuy_tram_trong')}</td></tr>`}</tbody>
      ${n ? `<tfoot><tr><td></td><td>${NN.h('tuy_tong_tram', { n })}</td><td></td>${gia ? `<td></td><td class="num" id="tuy-tram-tong">${Object.keys(tong).length ? esc(EPL.tienGop(tong)) : '—'}</td>` : ''}<td colspan="${sua ? 2 : 1}"></td></tr></tfoot>` : ''}</table></div>
      ${sua && ganTram.length ? `<div class="tuy3-gan"><div class="tuy3-gan-dau"><b>${NN.h('tuy_gan_duong')}</b><small class="muted">${NN.h('tuy_gan_duong_hint')}</small></div>
        ${ganTram.map((u, k) => `<div class="tuy3-gan-dong"><span class="tuy3-tp goi-y">${TRAM_IC}</span><span class="grow" lang="lo"><b>${esc(u.name || NN.t('tuy_tram'))}</b>
          <span class="tuy3-phu"><span class="tuy3-nuoc">${esc(u.country)}</span> · km ${so(u.km, 1)} · ${esc(NN.t('tuy_cach_m', { m: so(u.cach_m) }))}</span></span>
          <button type="button" class="btn sm" data-them-gan="${k}">+ ${NN.h('add')}</button></div>`).join('')}</div>` : ''}
      <div class="small muted tuy3-tram-chu">${NN.h('tuy_tram_hint')}${chua && gia ? ` <span class="tuy3-canh">${esc(NN.t('tuy_n_chua_gia', { n: chua }))}</span>` : ''}</div>`;
    if (!sua) return;
    o.querySelectorAll('[data-them-gan]').forEach(b => b.addEventListener('click', () => themGan(+b.dataset.themGan).catch(EPL.baoLoi)));
    o.querySelectorAll('[data-f]').forEach(el => el.addEventListener(el.type === 'checkbox' ? 'change' : 'input', () => {
      const t = tam.tolls[+el.dataset.i], f = el.dataset.f;
      t[f] = el.type === 'checkbox' ? el.checked : el.value;
      if (f === 'one_way') { veTram(); veTomTram(); return; }
      const tt = o.querySelector(`[data-tt="${el.dataset.i}"]`);
      if (tt) tt.innerHTML = coGiaTram(t) ? EPL.tien(EPL.doc(t.fee) * luotTram(t), t.currency) : '—';
      const tg = q('#tuy-tram-tong'), g = tongTram().tong; if (tg) tg.textContent = Object.keys(g).length ? EPL.tienGop(g) : '—';
      veTomTram();
    }));
    o.querySelectorAll('[data-xoa-tram]').forEach(b => b.addEventListener('click', () => {
      tam.tolls.splice(+b.dataset.xoaTram, 1); veTram(); veThe(); veTom(); veBanDo(false);
    }));
  }

  /* ------------------------------------------------------------------ chi phí gợi ý (thẻ thứ ba) */
  function veCp() {
    const o = q('#tuy-cp'); if (!o) return;
    if (!dangSua()) { veGoiY(o, chon); return; }
    o.innerHTML = `<div class="tuy3-cp-dau"><small class="muted">${NN.h('cp_goi_y_hint')}</small><div class="grow"></div>
        <button type="button" class="btn quiet sm" id="tuy-f-them-cp">+ ${NN.h('add_row')}</button><button type="button" class="btn quiet sm" id="tuy-f-chep-chung">${NN.h('cp_chep_chung')}</button></div>
      <div class="tuy-cp-bang"><table class="tbl tbl-compact" id="tuy-f-cp"><thead><tr><th>#</th><th>${NN.h('cp_muc')}</th><th>${NN.h('item')}</th><th class="num">${NN.h('cp_sl')}</th><th>${NN.h('fill_place')}</th>${thayGia() ? `<th class="num">${NN.h('gia_goi_y')}</th><th>${NN.h('cur')}</th>` : ''}<th>${NN.h('owner_pay_mode')}</th><th></th></tr></thead><tbody></tbody></table></div>`;
    q('#tuy-f-them-cp').addEventListener('click', () => { tam.cost.push({ section: 'travel', item_key: 'x_water', qty: 1, currency: 'LAK' }); veCpTam(); });
    q('#tuy-f-chep-chung').addEventListener('click', async () => {
      try { tam.cost = (await API.get('/api/tuyen-bo-chung')).map(x => ({ ...x })); veCpTam(); } catch (e) { EPL.baoLoi(e); }
    });
    veCpTam();
  }

  /** Bảng chi phí gợi ý (chỉ xem), nhóm theo mục */
  function veGoiY(o, r) {
    const coGia = (r.goi_y || []).some(x => 'unit_price' in x);
    const goi = r.goi_y || [];
    const dong = (x) => x.section === 'fuel'
      ? `<tr><td lang="lo">${esc(tenDiem(x.place_id))}</td><td class="num">${so(x.qty)} L</td>${coGia ? '<td></td>' : ''}<td></td></tr>`
      : `<tr><td lang="lo">${esc(tenKhoan(x))}</td><td class="num">${so(x.qty)}</td>${coGia ? `<td class="num">${x.unit_price != null ? so(x.unit_price) + ' ' + esc(x.currency || 'LAK') : '—'}</td>` : ''}
        <td class="small">${x.pay_channel ? NN.h((CACH.find(c => c[0] === x.pay_channel) || [])[1] || x.pay_channel) : ''}</td></tr>`;
    const nhom = MUC_CP.map(([m, k]) => [m, k, goi.filter(x => x.section === m)]).filter(g => g[2].length);
    o.innerHTML = `<div class="tuy3-cp-dau"><small class="muted">${r.goi_y_nguon === 'chung' ? NN.h('cp_nguon_chung') : NN.h('cp_goi_y_hint')}</small></div>
      <div class="tbl-wrap"><table class="tbl tbl-compact tuy-cp-xem"><thead><tr><th>${NN.h('item')} · ${NN.h('fill_place')}</th><th class="num">${NN.h('cp_sl')}</th>${coGia ? `<th class="num">${NN.h('gia_goi_y')}</th>` : ''}<th>${NN.h('owner_pay_mode')}</th></tr></thead>
      <tbody>${nhom.map(([m, k, xs]) => `<tr class="tuy-cp-nhom"><td colspan="${coGia ? 4 : 3}">${NN.h(k)}</td></tr>` + xs.map(dong).join('')).join('')
        || `<tr><td colspan="4" class="empty small">${NN.h('no_data')}</td></tr>`}</tbody></table></div>`;
  }

  /** Bảng sửa chi phí gợi ý */
  function veCpTam() {
    const tb = q('#tuy-f-cp tbody'); if (!tb) return;
    const cp = tam.cost;
    tb.innerHTML = cp.map((x, i) => {
      const khoan = (KM && KM.items[x.section]) || [];
      const tuGo = !x.item_key;
      return `<tr><td>${i + 1}</td>
        <td><select data-i="${i}" data-f="section">${MUC_CP.map(([v, k]) => `<option value="${v}" ${v === x.section ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}</select></td>
        <td><select data-i="${i}" data-f="item_key">${khoan.filter(k => k !== 'x_toll').map(k => `<option value="${k}" ${k === x.item_key ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}${x.section !== 'fuel' ? `<option value="" ${tuGo ? 'selected' : ''}>${esc(NN.t('x_custom'))}</option>` : ''}</select>
          ${tuGo && x.section !== 'fuel' ? `<input data-i="${i}" data-f="item_name" value="${esc(x.item_name || '')}" placeholder="…" style="margin-top:4px">` : ''}</td>
        <td><input class="num" data-i="${i}" data-f="qty" value="${esc(x.qty ?? '')}" inputmode="decimal"></td>
        <td>${x.section === 'fuel' ? `<select data-i="${i}" data-f="place_id"><option value="">—</option>${DIEM.map(d => `<option value="${d.id}" ${d.id === x.place_id ? 'selected' : ''}>${esc(d.name)}</option>`).join('')}</select>` : ''}</td>
        ${thayGia() ? `<td><input class="num" data-i="${i}" data-f="unit_price" value="${esc(x.unit_price ?? '')}" inputmode="decimal"></td>
        <td><select data-i="${i}" data-f="currency">${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === (x.currency || 'LAK') ? 'selected' : ''}>${c}</option>`).join('')}</select></td>` : ''}
        <td>${x.section !== 'fuel' ? `<select data-i="${i}" data-f="pay_channel">${CACH.map(([v, k]) => `<option value="${v}" ${v === (x.pay_channel || '') ? 'selected' : ''}>${esc(k === '—' ? '—' : NN.t(k))}</option>`).join('')}</select>` : ''}</td>
        <td><button type="button" class="x" data-xoa-cp="${i}">×</button></td></tr>`;
    }).join('') || `<tr><td colspan="9" class="empty small">${NN.h('cp_nguon_chung')}</td></tr>`;
    tb.querySelectorAll('[data-f]').forEach(el => el.addEventListener('input', () => {
      const x = cp[+el.dataset.i], f = el.dataset.f;
      x[f] = el.value;
      if (f === 'section') { x.item_key = x.section === 'fuel' ? 'diesel' : ((KM && KM.items[x.section]) || []).filter(k => k !== 'x_toll')[0] || null; x.item_name = null; veCpTam(); }
      if (f === 'item_key') { if (!el.value) x.item_key = null; veCpTam(); }
    }));
    tb.querySelectorAll('[data-xoa-cp]').forEach(b => b.addEventListener('click', () => { cp.splice(+b.dataset.xoaCp, 1); veCpTam(); }));
    q('#tuy-cp-dem').textContent = cp.length;
  }

  /* ------------------------------------------------------------------ lưu / huỷ */
  async function huySua() {
    if (!(await boSuaNeuCan())) return;
    che = 'xem'; tam = null; chamO = null; vePick();
    if (!chon && ds.length) chon = await API.get('/api/routes/' + ds[0].id);
    veTatCa(true);
  }
  async function luu() {
    const body = {
      name: tam.name, toll_lak: EPL.doc(tam.toll_lak), note: tam.note, return_km: EPL.doc(tam.return_km),
      stops: tam.stops.map(d => ({ name: d.name, km_from_prev: EPL.doc(d.km_from_prev),
        lat: coVT(d) ? +d.lat : null, lng: coVT(d) ? +d.lng : null })),
      // bộ chi phí gợi ý — Bãi gửi không kèm giá (máy chủ giữ giá kế toán đã đặt)
      cost_template: tam.cost.map(x => ({ section: x.section, item_key: x.item_key || null, item_name: x.item_name || null, qty: EPL.doc(x.qty),
        place_id: x.section === 'fuel' ? (x.place_id || null) : undefined, pay_channel: x.section === 'fuel' ? undefined : (x.pay_channel || null),
        ...(thayGia() ? { unit_price: x.unit_price === '' || x.unit_price == null ? null : EPL.doc(x.unit_price), currency: x.currency || 'LAK' } : {}) })),
    };
    if (che === 'sua') body.active = !!tam.active;
    body.tolls = tam.tolls.map(t => t.id);
    // giá / thu một chiều của trạm sửa ngay trên bảng trạm → ghi vào danh mục trạm trước (giá của trạm dùng chung mọi tuyến)
    for (const t of tam.tolls) {
      const g = t._goc || {}, doi = {};
      if (!!t.one_way !== !!g.one_way) doi.one_way = !!t.one_way;
      if (thayGia()) {
        if (String(t.fee ?? '') !== String(g.fee ?? '')) doi.fee = t.fee === '' || t.fee == null ? null : EPL.doc(t.fee);
        if ((t.currency || '') !== (g.currency || '')) doi.currency = t.currency;
      }
      if (Object.keys(doi).length) await API.put('/api/toll-stations/' + t.id, doi);
    }
    const moi = await (che === 'sua' ? API.put('/api/routes/' + chon.id, body) : API.post('/api/routes', body));
    EPL.toast(NN.t('saved'), 'ok');
    ds = await API.get('/api/routes');
    chon = moi; che = 'xem'; tam = null; chamO = null; vePick();
    if (!moi.active && loc === 'dang') loc = 'tat';
    veTatCa(true);
  }

  /* ------------------------------------------------------------------ chiều cao vừa một màn hình */
  function caoKhung() {
    const el = q('#tuy3'); if (!el) return;
    if ((window.innerWidth || 1600) <= 1000) { el.style.height = ''; return; }
    let tren = 0, n = el;
    while (n) { tren += n.offsetTop; n = n.offsetParent; }
    const ty = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    let cao = Math.max(460, (window.innerHeight || 900) / ty - tren - 20);
    el.style.height = cao + 'px';
    const de = document.documentElement, du = de.scrollHeight - de.clientHeight;
    if (du > 0 && cao > 460) { cao = Math.max(460, cao - du / ty); el.style.height = cao + 'px'; }
    setTimeout(() => MAP && MAP.invalidateSize(), 60);
  }
  const khiDoiCo = () => caoKhung();
  const khiPhim = (e) => {
    if (e.key !== 'Escape' || !root || !root.isConnected) return;
    if (chamTram) { chamTram = false; vePick(); veThePhai(); return; }
    if (chamO != null) batCham(chamO);
  };

  EPL.modules['tuyen-duong'] = {
    async init(r) {
      root = r; MAP = null; lopNen = lopVe = null; che = 'xem'; tam = null; chamO = null; chon = null; DO = { khoa: '', legs: {} };
      [ds, KM, DIEM, STS] = await Promise.all([API.get('/api/routes'), API.get('/api/khoan-muc'), API.get('/api/fuel-places').catch(() => []),
        API.get('/api/toll-stations').catch(() => [])]);
      q('#tuy-q').addEventListener('input', veDanhSach);
      root.querySelectorAll('#tuy-loc button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veDanhSach(); }));
      root.querySelectorAll('#tuy-tab button').forEach(b => b.addEventListener('click', () => { the = b.dataset.tab; veThe(); }));
      root.querySelectorAll('#tuy-nen button').forEach(b => b.addEventListener('click', () => datNen(b.dataset.nen)));
      const them = q('#tuy-them'); them.hidden = !suaDuoc();
      them.addEventListener('click', async () => { if (await boSuaNeuCan()) batDauSua(null); });
      window.addEventListener('resize', khiDoiCo);
      document.addEventListener('keydown', khiPhim);
      if (window.ResizeObserver) { theoDau = new ResizeObserver(khiDoiCo); ['tbar', 'topbar'].forEach(id => { const e = document.getElementById(id); if (e) theoDau.observe(e); }); }
      const dau = ds.find(x => x.active) || ds[0];
      if (dau) chon = await API.get('/api/routes/' + dau.id);
      veTatCa(true);
      caoKhung(); setTimeout(caoKhung, 0);
    },
    destroy() {
      clearTimeout(henDo); clearTimeout(henTen);
      window.removeEventListener('resize', khiDoiCo);
      document.removeEventListener('keydown', khiPhim);
      if (theoDau) { theoDau.disconnect(); theoDau = null; }
      if (MAP) { MAP.remove(); MAP = null; lopNen = lopVe = null; }
    },
    onLang() { if (root) { veTatCa(false); vePick(); } },
  };
})();
