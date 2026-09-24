/* Xe & rơ-moóc — đầu kéo + rơ-moóc, lắp/tháo, giấy tờ, lịch xe, sửa chữa & chi phí (mục V).
   Bản thiết kế anh gửi, nối vào API THẬT của dự án:
     GET /api/vehicles · GET /api/vehicles/{id}        (kèm lịch sử rơ-moóc, chi phí mục V, phiếu gần đây)
     GET /api/trailers · GET /api/trailers/{id}        (kèm lịch sử lắp của chính rơ-moóc đó)
     GET /api/vehicles/{id}/lich?tuan=YYYY-MM-DD       (lịch tuần dựng từ phiếu và dòng sửa chữa)
     POST/PUT /api/vehicles · POST/PUT /api/trailers
     POST /api/vehicles/{id}/trailer {trailer_id, reason}   — trailer_id rỗng là tháo
   Bản mẫu viết theo một bộ API riêng (/api/xe, /api/ro-mooc). Không dựng API thứ hai cho cùng một
   dữ liệu: module đổi tên trường ngay ở ranh giới (xemXe/guiXe, xemRM/guiRM) rồi phần vẽ giữ nguyên. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  const NGUONG_GIAY_TO = 30;      // ngày — giấy tờ "sắp hết hạn"
  const NGUONG_BAO_DUONG = 500;   // km — còn ≤ 500 km tới mốc bảo dưỡng thì "đến kỳ"
  const suaDuoc = () => AUTH.la('yard', 'acct');     // chỉ Bãi và Kế toán sửa danh mục (như các màn danh mục khác)
  // Thẻ <img> không gửi header Authorization nên ảnh nhận phiên qua ?tk=… — y như tệp đính kèm phiếu.
  const urlAnh = (u) => u ? `${u}?tk=${encodeURIComponent(EPL.API.token())}` : null;
  const thayMaKT = () => AUTH.role !== 'yard';       // mã tài khoản là việc kế toán; Bãi thấy tiền chi nhưng không thấy mã
  let root, thoat = null, xe = [], rm = [], chuXe = [], ui = { mode: 'dau-keo', sel: null, tab: 'lich', chip: null, q: '', soHuu: '', bai: '', tt: '', tuan: null };

  /* ---------- đổi tên trường giữa máy chủ và bản thiết kế ----------
   * Máy chủ nói: truck_no/plate_head/owner_type/status/insurance_exp…
   * Bản thiết kế nói: so_xe/bien/so_huu/trang_thai/han.bao_hiem…
   * Chỉ dịch ở đây, không rải khắp nơi. */
  const TT_XE = { available: 'idle', on_trip: 'running', maintenance: 'repair', inactive: 'repair' };
  const TT_XE_NGUOC = { idle: 'available', running: 'on_trip', repair: 'maintenance' };
  const ngay = (v) => (v ? String(v).slice(0, 10) : null);

  function xemXe(v) {
    return {
      _id: v.id, so_xe: v.truck_no, bien: v.plate_head, hang: v.brand_model, nam_sx: v.year,
      so_huu: v.owner_type === 'joint' ? 'thue-ngoai' : 'cong-ty', chu_xe: v.owner_name, chu_xe_id: v.owner_id, bai: v.depot,
      so_may: v.engine_no, so_khung: v.chassis_no, km: v.odometer_km, km_bao_duong: v.next_service_km,
      ngay_bao_duong: ngay(v.service_date), dinh_muc: v.fuel_norm, tai_trong: v.capacity_t,
      noi_dang_kiem: v.inspection_place, dung_tich: v.engine_cap, kich_thuoc_thung: v.box_size, lop: v.tyre,
      han: { bao_hiem: ngay(v.insurance_exp), dang_kiem: ngay(v.inspection_exp), luu_hanh: ngay(v.road_permit_exp) },
      trang_thai: TT_XE[v.status] || 'idle', ro_mooc: v.trailer ? v.trailer.plate : (v.plate_trailer || null),
      ghi_chu: v.note, so_phieu: v.so_phieu, phieu_hien_tai: v.phieu_hien_tai,
      anh: v.anh_chinh ? urlAnh(v.anh_chinh) : null, anh_ds: (v.anh || []).map(a => ({ ...a, src: urlAnh(a.url) })),
      lich_su_rm: (v.lich_su_ro_mooc || []).map(h => ({ bien: h.plate, lap: ngay(h.attached_at), thao: ngay(h.detached_at), ly_do: h.reason })),
      chi_phi: (v.sua_chua || []).map(c => ({
        phieu: c.doc_no, ngay: ngay(c.doc_date), nguon: NN.t(c.source === 'kho' ? 'src_kho' : 'src_mua'),
        khoan: c.item_key ? NN.t(c.item_key) : (c.item_name || ''), tien: c.tien_lak, ma_kt: thayMaKT() ? c.acct_code : null,
      })),
      phieu_gan_day: (v.phieu_gan_day || []).map(t => ({
        doc_no: t.doc_no, ngay: ngay(t.doc_date), khach: t.customer_name, tan: t.weight,
        tt: t.finance_status === 'paid' ? 'paid' : t.transport_status === 'dispatched' ? 'planned' : t.transport_status,
      })),
      _chi_tiet: !!v.lich_su_ro_mooc,
    };
  }
  function guiXe(o) {
    return {
      truck_no: o.so_xe, plate_head: o.bien, brand_model: o.hang, year: o.nam_sx,
      owner_type: o.so_huu === 'thue-ngoai' ? 'joint' : 'EPL', owner_id: o.chu_xe_id || null, owner_name: o.chu_xe, depot: o.bai,
      engine_no: o.so_may, chassis_no: o.so_khung, odometer_km: o.km, next_service_km: o.km_bao_duong,
      service_date: o.ngay_bao_duong || null, fuel_norm: o.dinh_muc, capacity_t: o.tai_trong,
      inspection_place: o.noi_dang_kiem, engine_cap: o.dung_tich, box_size: o.kich_thuoc_thung, tyre: o.lop,
      insurance_exp: o.han.bao_hiem || null, inspection_exp: o.han.dang_kiem || null, road_permit_exp: o.han.luu_hanh || null,
      status: TT_XE_NGUOC[o.trang_thai] || 'available', note: o.ghi_chu,
    };
  }
  function xemRM(t) {
    return {
      _id: t.id, bien: t.plate, loai: t.trailer_type, tai_trong: t.capacity_t, nam_sx: t.year,
      so_khung: t.chassis_no, so_huu: t.owner_type === 'joint' ? 'thue-ngoai' : 'cong-ty', bai: t.depot,
      noi_dang_kiem: t.inspection_place, ghi_chu: t.note,
      han: { dang_kiem: ngay(t.inspection_exp), luu_hanh: ngay(t.insurance_exp) },
      lap_vao: t.dang_lap_xe ? t.dang_lap_xe.truck_no : null,
      trang_thai: t.status === 'maintenance' ? 'repair' : (t.dang_lap_xe ? 'lap' : 'roi'),
      lich_su_lap: (t.lich_su_lap || []).map(h => ({ so_xe: h.truck_no, lap: ngay(h.attached_at), thao: ngay(h.detached_at), ly_do: h.reason })),
      _chi_tiet: !!t.lich_su_lap,
    };
  }
  function guiRM(o) {
    return {
      plate: o.bien, trailer_type: o.loai, capacity_t: o.tai_trong, year: o.nam_sx,
      owner_type: o.so_huu === 'thue-ngoai' ? 'joint' : 'EPL', depot: o.bai, chassis_no: o.so_khung,
      inspection_place: o.noi_dang_kiem, note: o.ghi_chu,
      inspection_exp: o.han.dang_kiem || null, insurance_exp: o.han.luu_hanh || null,
    };
  }
  /** Nạp phần chi tiết (lịch sử rơ-moóc, chi phí mục V, phiếu gần đây) khi người dùng chọn một xe —
   *  danh sách không kèm sẵn để mở màn không phải chờ hàng chục lượt gọi. */
  async function napChiTiet(o, laRM) {
    if (!o || o._chi_tiet || !o._id) return o;
    try {
      const d = laRM ? await API.get('/api/trailers/' + o._id) : await API.get('/api/vehicles/' + o._id);
      Object.assign(o, laRM ? xemRM(d) : xemXe(d));
    } catch (e) { /* mất mạng thì vẫn xem được phần đã có */ }
    return o;
  }

  /* ---------- tiện ích ---------- */
  const today = () => EPL.homNay ? new Date(EPL.homNay()) : new Date();
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const fmt = (s) => s ? s.split('-').reverse().join('/') : '—';
  const daysTo = (s) => s ? Math.round((new Date(s + 'T00:00:00') - today()) / 864e5) : null;
  const legalLevel = (s) => { const d = daysTo(s); return d == null ? 'none' : d < 0 ? 'r' : d <= NGUONG_GIAY_TO ? 'a' : 'g'; };
  const worst = (han) => { const lv = Object.values(han || {}).map(legalLevel); return lv.includes('r') ? 'r' : lv.includes('a') ? 'a' : 'g'; };
  const denKy = (x) => x.km_bao_duong != null && x.km != null && x.km_bao_duong - x.km <= NGUONG_BAO_DUONG;
  const pill = (k, t) => `<span class="xe-pill ${k}">${esc(t)}</span>`;
  const ST = { running: ['amber', 'xe_st_running'], idle: ['green', 'xe_st_idle'], repair: ['red', 'xe_st_repair'], lap: ['green', 'xe_rm_attached'], roi: ['muted', 'xe_rm_free'] };
  const stPill = (k) => { const s = ST[k] || ST.idle; return pill(s[0], NN.t(s[1])); };
  const truck = `<svg class="xe-i" viewBox="0 0 24 24"><path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></svg>`;
  const toast = (m) => EPL.toast(m, 'ok');     // dùng hộp báo chung của khung, không dựng cái thứ hai

  /* Thẻ hồ sơ trượt ra từ mép phải; đóng bằng nút X, bấm nền mờ, hoặc phím Esc. */
  const CLOSE_BTN = `<button type="button" class="xe-close" data-close-detail aria-label="${esc(NN.t('close'))}"><svg class="xe-i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>`;
  function openDetail() { root.querySelector('#xe-detail').classList.add('open'); root.querySelector('#xe-scrim').classList.add('open'); }
  function closeDetail() { root.querySelector('#xe-detail').classList.remove('open'); root.querySelector('#xe-scrim').classList.remove('open'); }
  const trailerOf = (x) => rm.find(r => r.bien === x.ro_mooc);

  /* ---------- tải ---------- */
  async function tai() {
    const [dsXe, dsRM, dsChu] = await Promise.all([API.get('/api/vehicles'), API.get('/api/trailers'), API.get('/api/owners').catch(() => [])]);
    chuXe = dsChu;
    xe = dsXe.map(xemXe); rm = dsRM.map(xemRM);
    const bai = [...new Set(xe.map(x => x.bai).filter(Boolean))];
    const sel = root.querySelector('#xe-f-bai'); sel.innerHTML = `<option value="">${NN.h('xe_all_depot')}</option>` + bai.map(b => `<option value="${esc(b)}" class="lo">${esc(b)}</option>`).join('');
    if (!ui.sel) ui.sel = ui.mode === 'dau-keo' ? (xe[0] && xe[0].so_xe) : (rm[0] && rm[0].bien);
    ve(); chonXong();
  }
  /** Sau mỗi lần đổi lựa chọn: nạp chi tiết rồi vẽ lại đúng thẻ bên phải. */
  async function chonXong() {
    const laRM = ui.mode === 'ro-mooc';
    const o = laRM ? rm.find(v => v.bien === ui.sel) : xe.find(v => v.so_xe === ui.sel);
    if (!o || o._chi_tiet) return;
    await napChiTiet(o, laRM);
    if ((laRM ? o.bien : o.so_xe) === ui.sel) veDetail();
  }

  /* ---------- chip xem nhanh ---------- */
  function chips() {
    if (ui.mode === 'dau-keo') return [
      ['xe_q_total', xe.length, '', () => true],
      ['xe_st_running', xe.filter(x => x.trang_thai === 'running').length, 'info', x => x.trang_thai === 'running'],
      ['xe_st_idle', xe.filter(x => x.trang_thai === 'idle').length, 'good', x => x.trang_thai === 'idle'],
      ['xe_st_repair', xe.filter(x => x.trang_thai === 'repair').length, 'bad', x => x.trang_thai === 'repair'],
      ['xe_q_maint', xe.filter(denKy).length, 'warn', denKy],
      ['xe_q_legal', xe.filter(x => worst(x.han) !== 'g').length, 'bad', x => worst(x.han) !== 'g'],
      ['xe_rented', xe.filter(x => x.so_huu === 'thue-ngoai').length, 'tan', x => x.so_huu === 'thue-ngoai'],
      ['xe_q_no_trailer', xe.filter(x => !x.ro_mooc).length, 'warn', x => !x.ro_mooc],
    ];
    return [
      ['xe_q_total', rm.length, '', () => true],
      ['xe_rm_attached', rm.filter(r => r.lap_vao).length, 'good', r => !!r.lap_vao],
      ['xe_rm_free', rm.filter(r => !r.lap_vao && r.trang_thai !== 'repair').length, 'info', r => !r.lap_vao && r.trang_thai !== 'repair'],
      ['xe_st_repair', rm.filter(r => r.trang_thai === 'repair').length, 'bad', r => r.trang_thai === 'repair'],
      ['xe_q_legal', rm.filter(r => worst(r.han) !== 'g').length, 'bad', r => worst(r.han) !== 'g'],
    ];
  }
  function veQuick() {
    const C = chips();
    root.querySelector('#xe-quick').innerHTML = `<span class="lbl">${NN.h('tq_quick')}</span>` + C.map((c, i) => `<button type="button" class="xe-chip ${c[2]} ${c[1] ? '' : 'zero'} ${ui.chip === i ? 'on' : ''}" data-i="${i}"><b>${c[1]}</b>${NN.h(c[0])}</button>`).join('') +
      `<span class="right">${NN.h('tq_updated')} ${today().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</span>`;
    root.querySelectorAll('.xe-chip').forEach(el => el.addEventListener('click', () => { const i = +el.dataset.i; ui.chip = ui.chip === i || i === 0 ? null : i; ve(); }));
  }

  /* ---------- danh sách ---------- */
  function visible() {
    const q = ui.q.trim().toLowerCase(), C = chips(), test = ui.chip != null ? C[ui.chip][3] : () => true;
    if (ui.mode === 'dau-keo') return xe.filter(x => test(x) && (!ui.soHuu || x.so_huu === ui.soHuu) && (!ui.bai || x.bai === ui.bai) && (!ui.tt || x.trang_thai === ui.tt)
      && (!q || [x.so_xe, x.hang, x.bien, x.ro_mooc, x.bai, x.chu_xe, x.phieu_hien_tai].join(' ').toLowerCase().includes(q)));
    return rm.filter(r => test(r) && (!ui.tt || (ui.tt === 'repair' ? r.trang_thai === 'repair' : ui.tt === 'idle' ? !r.lap_vao : !!r.lap_vao)) && (!q || [r.bien, r.loai, r.lap_vao].join(' ').toLowerCase().includes(q)));
  }
  function veList() {
    const list = visible(), tb = root.querySelector('#xe-tbl');
    root.querySelector('#xe-n-dk').textContent = xe.length; root.querySelector('#xe-n-rm').textContent = rm.length;
    root.querySelector('#xe-list-title').textContent = NN.t(ui.mode === 'dau-keo' ? 'xe_list_tractor' : 'xe_list_trailer');
    root.querySelector('#xe-count').textContent = `${list.length} / ${ui.mode === 'dau-keo' ? xe.length : rm.length}`;
    if (!list.length) { tb.innerHTML = ''; root.querySelector('#xe-foot').innerHTML = `<span>${NN.h('xe_none')}</span>`; return; }
    if (!list.some(x => (x.so_xe || x.bien) === ui.sel)) ui.sel = list[0].so_xe || list[0].bien;
    const dots = (han, keys) => `<span class="xe-dots">${keys.map(k => `<i class="${legalLevel(han[k])}" title="${esc(NN.t('xe_h_' + k))}: ${fmt(han[k])}"></i>`).join('')}</span>`;
    if (ui.mode === 'dau-keo') {
      tb.innerHTML = `<thead><tr><th>#</th><th>${NN.h('xe_no')}</th><th>${NN.h('xe_brand')}</th><th>${NN.h('xe_plate_tractor')}</th><th>${NN.h('xe_plate_trailer')}</th><th>${NN.h('xe_owner')}</th><th class="num">${NN.h('xe_odo')}</th><th>${NN.h('xe_docs')}</th><th>${NN.h('xe_status')}</th></tr></thead><tbody>` +
        list.map((x, i) => { const pct = x.km_bao_duong ? Math.min(100, x.km / x.km_bao_duong * 100) : 0, k = denKy(x) ? (x.km >= x.km_bao_duong ? 'bad' : 'warn') : '';
          return `<tr class="${x.so_xe === ui.sel ? 'on' : ''}" data-id="${esc(x.so_xe)}"><td class="muted">${i + 1}</td><td><span class="code mono lo">${esc(x.so_xe)}</span></td><td>${esc(x.hang)}<span class="sub">${x.nam_sx || ''}</span></td><td class="lo">${esc(x.bien)}</td><td class="lo">${x.ro_mooc ? esc(x.ro_mooc) : `<span class="muted">—</span>`}</td><td>${pill(x.so_huu === 'thue-ngoai' ? 'muted' : 'green', NN.t(x.so_huu === 'thue-ngoai' ? 'xe_rented' : 'xe_company'))}</td>
            <td class="num xe-km">${x.km != null ? so(x.km) : '—'}${x.km_bao_duong ? `<div class="t"><b class="${k}" style="width:${pct}%"></b></div>${denKy(x) ? `<span class="sub" style="color:var(--xe-warn)">${NN.h('xe_q_maint')}</span>` : ''}` : ''}</td>
            <td>${dots(x.han, ['bao_hiem', 'dang_kiem', 'luu_hanh'])}</td><td>${stPill(x.trang_thai)}${x.phieu_hien_tai ? `<span class="sub mono">${esc(x.phieu_hien_tai)}</span>` : ''}</td></tr>`; }).join('') + '</tbody>';
      root.querySelector('#xe-foot').innerHTML = `<span>${xe.filter(x => x.trang_thai === 'running').length} ${NN.t('xe_st_running').toLowerCase()} · ${xe.filter(x => x.trang_thai === 'idle').length} ${NN.t('xe_st_idle').toLowerCase()} · ${xe.filter(x => x.trang_thai === 'repair').length} ${NN.t('xe_st_repair').toLowerCase()}</span><span>${NN.h('xe_legend_dots')}</span>`;
    } else {
      tb.innerHTML = `<thead><tr><th>#</th><th>${NN.h('xe_plate')}</th><th>${NN.h('xe_rm_type')}</th><th class="num">${NN.h('xe_rm_load')}</th><th>${NN.h('xe_rm_on')}</th><th>${NN.h('xe_docs')}</th><th>${NN.h('xe_status')}</th></tr></thead><tbody>` +
        list.map((r, i) => `<tr class="${r.bien === ui.sel ? 'on' : ''}" data-id="${esc(r.bien)}"><td class="muted">${i + 1}</td><td><span class="code lo">${esc(r.bien)}</span><span class="sub">${r.nam_sx || ''}</span></td><td class="lo">${esc(r.loai)}</td><td class="num">${r.tai_trong} t</td><td>${r.lap_vao ? `<span class="mono">${esc(r.lap_vao)}</span>` : `<span class="muted">—</span>`}</td><td>${dots(r.han, ['dang_kiem', 'luu_hanh'])}</td><td>${r.trang_thai === 'repair' ? stPill('repair') : stPill(r.lap_vao ? 'lap' : 'roi')}</td></tr>`).join('') + '</tbody>';
      root.querySelector('#xe-foot').innerHTML = `<span>${rm.filter(r => r.lap_vao).length} ${NN.t('xe_rm_attached').toLowerCase()} · ${rm.filter(r => !r.lap_vao).length} ${NN.t('xe_rm_free').toLowerCase()}</span><span>${NN.h('xe_legend_dots')}</span>`;
    }
    tb.querySelectorAll('tbody tr').forEach(tr => { tr.addEventListener('click', () => { ui.sel = tr.dataset.id; veList(); veDetail(); openDetail(); chonXong(); }); tr.addEventListener('dblclick', () => { const o = ui.mode === 'dau-keo' ? xe.find(v => v.so_xe === tr.dataset.id) : rm.find(v => v.bien === tr.dataset.id); if (o) openHoSo(o, ui.mode !== 'dau-keo'); }); });
  }

  /* ---------- thẻ xem nhanh (cột phải, chỉ đọc) ---------- */
  function legalRows(han, keys) {
    return `<div class="xe-legal">${keys.map(k => { const d = daysTo(han[k]), lv = legalLevel(han[k]), pct = d == null ? 0 : Math.max(0, Math.min(100, d / 365 * 100));
      return `<div class="row"><span>${NN.h('xe_h_' + k)}</span><div class="t"><b class="${lv}" style="width:${pct}%"></b></div><div class="d">${fmt(han[k])}<small>${d == null ? '' : d < 0 ? NN.t('xe_expired') + ' ' + (-d) + ' ' + NN.t('tq_days') : NN.t('xe_left') + ' ' + d + ' ' + NN.t('tq_days')}</small></div></div>`; }).join('')}</div>`;
  }
  const legalPill = (han) => { const w = worst(han); return pill(w === 'g' ? 'green' : w === 'a' ? 'amber' : 'red', NN.t(w === 'g' ? 'xe_legal_ok' : w === 'a' ? 'xe_legal_soon' : 'xe_legal_expired')); };
  const legalNotes = (han) => Object.entries(han || {}).filter(([, v]) => legalLevel(v) !== 'g').map(([k, v]) => `<div class="xe-note ${legalLevel(v) === 'r' ? 'bad' : 'warn'}">${NN.h('xe_h_' + k)}: ${NN.h(legalLevel(v) === 'r' ? 'xe_legal_expired' : 'xe_legal_soon')} · ${fmt(v)}</div>`).join('');
  function trailerBlock(x) {
    const t = trailerOf(x); if (!t) return `<div class="xe-trailer none">${NN.h('xe_no_trailer_short')}</div>`;
    const since = (x.lich_su_rm || []).find(h => h.bien === t.bien && !h.thao)?.lap;
    return `<div class="xe-trailer"><span class="p lo">${esc(t.bien)}</span><span class="m"><span class="lo">${esc(t.loai)}</span> · ${t.tai_trong} t${since ? ` · ${NN.t('xe_since')} ${fmt(since)}` : ''}</span><span class="m" style="flex:0 0 auto;text-align:right"><span class="xe-dots"><i class="${legalLevel(t.han.dang_kiem)}"></i></span> ${NN.t('xe_h_dang_kiem')} ${fmt(t.han.dang_kiem)}</span></div>`;
  }
  function veDetail() {
    const box = root.querySelector('#xe-detail');
    if (ui.mode === 'ro-mooc') return veDetailRM(box);
    const x = xe.find(v => v.so_xe === ui.sel); if (!x) { box.innerHTML = `<div class="xe-empty">${NN.h('xe_pick')}</div>`; return; }
    box.innerHTML = CLOSE_BTN + `
      <div class="xe-head"><div class="xe-photo">${x.anh ? `<img src="${esc(x.anh)}" alt="">` : truck}</div>
        <div class="t"><b class="mono lo">${esc(x.so_xe)}</b> · <span class="lo">${esc(x.bien)}</span> ${stPill(x.trang_thai)}<small>${esc(x.hang)} · ${x.nam_sx || '—'} · ${NN.t(x.so_huu === 'thue-ngoai' ? 'xe_rented' : 'xe_company')}${x.chu_xe ? ' · ' + esc(x.chu_xe) : ''}</small>
          <div class="acts"><button class="xe-btn-sm dark" data-act="open"><svg class="xe-i" viewBox="0 0 24 24"><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>${NN.h('xe_open_profile')}</button><button class="xe-btn-sm" data-act="dispatch" ${x.trang_thai !== 'idle' ? 'disabled' : ''}>${NN.h('new_dispatch')}</button></div></div></div>
      <div class="xe-kv">
        <div><span>${NN.h('xe_engine')}</span><b class="mono">${esc(x.so_may || '—')}</b></div><div><span>${NN.h('xe_chassis')}</span><b class="mono">${esc(x.so_khung || '—')}</b></div>
        <div><span>${NN.h('xe_depot')}</span><b class="lo">${esc(x.bai || '—')}</b></div><div><span>${NN.h('xe_trips_done')}</span><b>${x.so_phieu ?? 0}</b></div>
        <div><span>${NN.h('xe_odo')}</span><b>${x.km != null ? so(x.km) + ' km' : '—'}</b></div><div><span>${NN.h('xe_next_maint')}</span><b style="${denKy(x) ? 'color:var(--xe-warn)' : ''}">${x.km_bao_duong ? so(x.km_bao_duong) + ' km' : '—'}</b></div>
        <div><span>${NN.h('xe_fuel_norm')}</span><b>${x.dinh_muc ? x.dinh_muc + ' L/100km' : '—'}</b></div><div><span>${NN.h('xe_current_trip')}</span><b class="mono">${esc(x.phieu_hien_tai || '—')}</b></div>
      </div>
      <div class="xe-sec">${NN.h('xe_legal')}<span class="grow"></span>${legalPill(x.han)}</div>
      ${legalRows(x.han, ['bao_hiem', 'dang_kiem', 'luu_hanh'])}
      ${legalNotes(x.han)}
      ${denKy(x) ? `<div class="xe-note warn">${NN.h('xe_q_maint')} · ${NN.t('xe_left')} ${so(x.km_bao_duong - x.km)} km</div>` : ''}
      ${x.ghi_chu ? `<div class="xe-note" style="background:var(--xe-tan);color:var(--xe-tan-ink)">${esc(x.ghi_chu)}</div>` : ''}
      <div class="xe-sec">${NN.h('xe_trailer')}</div>
      ${trailerBlock(x)}
      <div class="xe-hint">${NN.h('xe_quick_hint')}</div>`;
    box.querySelector('[data-act="open"]').onclick = () => openHoSo(x, false, 'chung');
    box.querySelector('[data-act="dispatch"]').onclick = () => EPL.di('phieu-xuat-xe', { moi: 1, xe: x._id });
  }
  function veDetailRM(box) {
    const r = rm.find(v => v.bien === ui.sel); if (!r) { box.innerHTML = `<div class="xe-empty">${NN.h('xe_pick')}</div>`; return; }
    const host = xe.find(x => x.so_xe === r.lap_vao);
    box.innerHTML = CLOSE_BTN + `
      <div class="xe-head"><div class="xe-photo">${truck}</div><div class="t"><b class="lo">${esc(r.bien)}</b> ${r.trang_thai === 'repair' ? stPill('repair') : stPill(r.lap_vao ? 'lap' : 'roi')}<small class="lo">${esc(r.loai)} · ${r.tai_trong} t · ${r.nam_sx || '—'}</small>
        <div class="acts"><button class="xe-btn-sm dark" data-act="open">${NN.h('xe_open_profile')}</button></div></div></div>
      <div class="xe-kv"><div><span>${NN.h('xe_chassis')}</span><b class="mono">${esc(r.so_khung || '—')}</b></div><div><span>${NN.h('xe_rm_on')}</span><b class="mono">${r.lap_vao ? esc(r.lap_vao) : '—'}</b></div><div><span>${NN.h('xe_owner')}</span><b>${NN.h(r.so_huu === 'thue-ngoai' ? 'xe_rented' : 'xe_company')}</b></div><div><span>${NN.h('xe_depot')}</span><b class="lo">${esc(r.bai || (host && host.bai) || '—')}</b></div></div>
      <div class="xe-sec">${NN.h('xe_legal')}<span class="grow"></span>${legalPill(r.han)}</div>${legalRows(r.han, ['dang_kiem', 'luu_hanh'])}${legalNotes(r.han)}
      ${r.ghi_chu ? `<div class="xe-note warn">${esc(r.ghi_chu)}</div>` : ''}
      ${host ? `<div class="xe-sec">${NN.h('xe_rm_on')}</div><div class="xe-trailer"><span class="p mono">${esc(host.so_xe)}</span><span class="m"><span class="lo">${esc(host.bien)}</span> · ${esc(host.hang)}</span>${stPill(host.trang_thai)}</div>` : ''}
      <div class="xe-hint">${NN.h('xe_quick_hint')}</div>`;
    box.querySelector('[data-act="open"]').onclick = () => openHoSo(r, true, 'chung');
  }

  /* ---------- form hồ sơ (modal lớn, có tab) ---------- */
  const F = (id, label, ctrl, w) => `<div class="f ${w ? 'w' + w : ''}"><label for="${id}">${label}</label>${ctrl}</div>`;
  const I = (id, v, type, ph) => `<input id="${id}" type="${type || 'text'}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}">`;
  const close = () => { root.querySelector('#xe-modal-root').innerHTML = ''; };
  function startOfWeek(d) { const x = new Date(d); const day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); x.setHours(0, 0, 0, 0); return x; }

  function openHoSo(o, isRM, tab) {
    closeDetail();     // mở hộp hồ sơ đầy đủ thì thu ngăn trượt lại, không chồng hai lớp
    const isNew = isRM ? !o.bien : !o.so_xe;
    const TABS = isRM ? [['chung', 'xe_tab_general'], ['phaply', 'xe_tab_legal'], ['romooc', 'xe_tab_rm_history']]
      : [['chung', 'xe_tab_general'], ['phaply', 'xe_tab_legal'], ['kythuat', 'xe_tab_tech'], ['romooc', 'xe_trailer'], ['lich', 'xe_tab_schedule_full'], ['sua', 'xe_tab_repair_full'], ['phieu', 'xe_tab_trips_full']];
    let cur = tab || 'chung'; const vals = {}; let sub = null;   // sub = form phụ đang mở trong tab rơ-moóc ('attach' | 'detach')
    const rt = root.querySelector('#xe-modal-root');
    rt.innerHTML = `<div class="xe-backdrop"><div class="xe-modal xe-modal--lg">
      <div class="mh"><div><h3>${isNew ? NN.h('xe_add') : NN.h('xe_profile')}: <span class="mono lo">${esc(isRM ? o.bien : o.so_xe) || '—'}</span></h3><small>${NN.h('xe_edit_sub')}</small></div><button class="x" type="button" data-close><svg class="xe-i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
      <div class="mtop"><div class="photo"><div class="xe-photo">${!isRM && o.anh ? `<img src="${esc(o.anh)}" alt="">` : truck}</div>
        <div><b>${NN.h('xe_photo')}</b>${isRM ? `<small>${NN.h('xe_photo_rm')}</small>`
          : `<small id="m-anh-dem">${NN.h('xe_photo_n', { n: (o.anh_ds || []).length })}</small>
             ${suaDuoc() && o.id ? `<label class="xe-btn-sm" style="margin-top:4px">${NN.h('xe_photo_add')}<input type="file" id="m-anh-them" accept="image/*" hidden></label>` : ''}`}</div></div>
        <div class="st"><small>${NN.h('xe_status')}</small><b>${isRM ? NN.t(o.trang_thai === 'repair' ? 'xe_st_repair' : o.lap_vao ? 'xe_rm_attached' : 'xe_rm_free') : NN.t((ST[o.trang_thai] || ST.idle)[1])}</b><p>${NN.h('xe_status_auto')}</p></div></div>
      <div class="mtabs" id="m-tabs"></div>
      <div class="mb" id="m-body"></div>
      <div class="mf"><span class="small muted" id="m-foot-note" style="margin-right:auto"></span><button class="btn" type="button" data-close>${NN.h('cancel')}</button><button class="btn primary" type="button" id="m-save">${NN.h('xe_save')}</button></div>
    </div></div>`;
    rt.querySelectorAll('[data-close]').forEach(b => b.onclick = close);
    rt.querySelector('.xe-backdrop').addEventListener('click', e => { if (e.target.classList.contains('xe-backdrop')) close(); });
    // Ảnh xe: đưa lên đúng chỗ chứa tệp của phiếu; ảnh đầu tiên tự thành ảnh đại diện.
    const oAnh = rt.querySelector('#m-anh-them');
    if (oAnh) oAnh.addEventListener('change', async () => {
      const f = oAnh.files && oAnh.files[0]; if (!f) return;
      let nen; try { nen = await EPL.nenTep(f); } catch (e) { return EPL.baoLoi(e); }
      const fd = new FormData(); fd.append('tep', nen, nen.name);
      try {
        const ds = await EPL.API.tep(`/api/vehicles/${o.id}/anh`, fd);
        o.anh_ds = ds.map(a => ({ ...a, src: urlAnh(a.url) }));
        const c = ds.find(a => a.chinh); o.anh = c ? urlAnh(c.url) : null;
        const khung = rt.querySelector('.mtop .xe-photo');
        if (khung && o.anh) khung.innerHTML = `<img src="${esc(o.anh)}" alt="">`;
        const dem = rt.querySelector('#m-anh-dem'); if (dem) dem.textContent = NN.t('xe_photo_n').replace('{n}', ds.length);
        EPL.toast(NN.t('saved'), 'ok');
        await tai();                       // danh sách lấy lại ảnh đại diện mới
      } catch (e) { EPL.baoLoi(e); }
      oAnh.value = '';
    });
    const body = rt.querySelector('#m-body');
    const grab = () => body.querySelectorAll('[id^="f-"]').forEach(el => { vals[el.id] = el.value; });
    const g = (k) => vals[k];
    const isForm = () => ['chung', 'phaply', 'kythuat'].includes(cur);

    const formTab = () => {
      if (cur === 'chung') return isRM
        ? F('f-bien', NN.h('xe_plate'), I('f-bien', o.bien)) + F('f-loai', NN.h('xe_rm_type'), I('f-loai', o.loai)) + F('f-tai', NN.h('xe_rm_load') + ' (t)', I('f-tai', o.tai_trong, 'number')) + F('f-nam', NN.h('xe_year'), I('f-nam', o.nam_sx, 'number')) + F('f-sohuu', NN.h('xe_owner'), `<select id="f-sohuu"><option value="cong-ty" ${o.so_huu !== 'thue-ngoai' ? 'selected' : ''}>${NN.h('xe_company')}</option><option value="thue-ngoai" ${o.so_huu === 'thue-ngoai' ? 'selected' : ''}>${NN.h('xe_rented')}</option></select>`) + F('f-bai', NN.h('xe_depot'), I('f-bai', o.bai)) + F('f-ghichu', NN.h('xe_note'), `<textarea id="f-ghichu" rows="2">${esc(o.ghi_chu || '')}</textarea>`, 3)
        : F('f-soxe', NN.h('xe_no'), I('f-soxe', o.so_xe)) + F('f-bien', NN.h('xe_plate_tractor'), I('f-bien', o.bien)) + F('f-hang', NN.h('xe_brand'), I('f-hang', o.hang, 'text', 'VD: HOWO-430')) + F('f-nam', NN.h('xe_year'), I('f-nam', o.nam_sx, 'number')) + F('f-sohuu', NN.h('xe_owner'), `<select id="f-sohuu"><option value="cong-ty" ${o.so_huu !== 'thue-ngoai' ? 'selected' : ''}>${NN.h('xe_company')}</option><option value="thue-ngoai" ${o.so_huu === 'thue-ngoai' ? 'selected' : ''}>${NN.h('xe_rented')}</option></select>`) + F('f-chuxe', NN.h('xe_owner_name'), chuXe.length ? `<select id="f-chuxe"><option value="">—</option>${chuXe.filter(c => c.active || c.id === o.chu_xe_id).map(c => `<option value="${esc(c.id)}" ${c.id === o.chu_xe_id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select>` : I('f-chuxe', o.chu_xe)) + F('f-bai', NN.h('xe_depot'), I('f-bai', o.bai)) + F('f-dinhmuc', NN.h('xe_fuel_norm') + ' (L/100km)', I('f-dinhmuc', o.dinh_muc, 'number')) + F('f-taitrong', NN.h('xe_rm_load') + ' (t)', I('f-taitrong', o.tai_trong, 'number')) + F('f-ghichu', NN.h('xe_note'), `<textarea id="f-ghichu" rows="2">${esc(o.ghi_chu || '')}</textarea>`, 3);
      if (cur === 'phaply') return `<div class="sech">${NN.h('xe_legal')}</div>` + (isRM ? '' : F('f-h-bh', NN.h('xe_h_bao_hiem'), I('f-h-bh', o.han.bao_hiem, 'date'))) + F('f-h-dk', NN.h('xe_h_dang_kiem'), I('f-h-dk', o.han.dang_kiem, 'date')) + F('f-h-lh', NN.h('xe_h_luu_hanh'), I('f-h-lh', o.han.luu_hanh, 'date')) + F('f-noidk', NN.h('xe_insp_place'), I('f-noidk', o.noi_dang_kiem, 'text', 'VD: ສູນກວດກາ ວຽງຈັນ')) + `<div class="sech">${NN.h('xe_ids')}</div>` + (isRM ? '' : F('f-somay', NN.h('xe_engine'), I('f-somay', o.so_may))) + F('f-sokhung', NN.h('xe_chassis'), I('f-sokhung', o.so_khung));
      return `<div class="sech">${NN.h('xe_tab_tech')}</div>` + F('f-km', NN.h('xe_odo') + ' (km)', I('f-km', o.km, 'number')) + F('f-kmbd', NN.h('xe_next_maint') + ' (km)', I('f-kmbd', o.km_bao_duong, 'number')) + F('f-ngaybd', NN.h('xe_maint_date'), I('f-ngaybd', o.ngay_bao_duong, 'date')) + F('f-dungtich', NN.h('xe_engine_cap'), I('f-dungtich', o.dung_tich, 'text', 'VD: 9,7 L / 430 HP')) + F('f-kt', NN.h('xe_box_size'), I('f-kt', o.kich_thuoc_thung, 'text', 'VD: 12,1 × 2,4 × 2,6 m')) + F('f-lop', NN.h('xe_tyre'), I('f-lop', o.lop, 'text', 'VD: 11R22.5'));
    };

    const histRows = (list) => list.length ? `<div class="xe-rows">${list.map(h => `<div class="xe-row"><div class="k"><b class="${h.so_xe ? 'mono' : 'lo'}" style="${h.so_xe ? '' : 'font-family:inherit;font-size:13px'}">${esc(h.so_xe ? NN.t('xe_no') + ' ' + h.so_xe : h.bien)}</b><small>${NN.t('xe_attached_on')} ${fmt(h.lap)}${h.thao ? ` · ${NN.t('xe_detached_on')} ${fmt(h.thao)}` : ''}${h.ly_do ? ` · ${esc(h.ly_do)}` : ''}</small></div><div class="v">${h.thao ? pill('muted', NN.t('xe_detached')) : pill('green', NN.t('xe_rm_attached'))}</div></div>`).join('')}</div>` : `<div class="xe-empty">${NN.h('xe_no_history')}</div>`;

    const rmTab = () => {
      if (isRM) {
        const host = xe.find(x => x.so_xe === o.lap_vao), hosts = xe.filter(x => x.trang_thai !== 'repair');
        const hist = (o.lich_su_lap || []).slice().sort((a, c) => (c.lap || '').localeCompare(a.lap || ''));   // máy chủ trả sẵn lịch sử của chính rơ-moóc này
        return `<div class="xe-sec" style="padding:0 0 6px">${NN.h('xe_rm_on')}<span class="grow"></span>${o.lap_vao ? `<button class="xe-btn-sm tan" type="button" data-sub="detach">${NN.h('xe_detach')}</button>` : `<button class="xe-btn-sm dark" type="button" data-sub="attach">${NN.h('xe_attach_to')}</button>`}</div>
          ${host ? `<div class="xe-trailer" style="margin:0 0 10px"><span class="p mono">${esc(host.so_xe)}</span><span class="m"><span class="lo">${esc(host.bien)}</span> · ${esc(host.hang)}</span>${stPill(host.trang_thai)}</div>` : `<div class="xe-trailer none" style="margin:0 0 10px">${NN.h('xe_rm_free')}</div>`}
          ${sub === 'attach' ? `<div class="xe-subform"><div class="xe-form">${F('s-xe', NN.h('xe_no'), `<select id="s-xe">${hosts.map(x => `<option value="${esc(x.so_xe)}">${esc(x.so_xe)} · ${esc(x.bien)}${x.ro_mooc ? ` (${NN.t('xe_currently')} ${esc(x.ro_mooc)})` : ''}</option>`).join('')}</select>`)}${F('s-ngay', NN.h('xe_date'), I('s-ngay', iso(today()), 'date'))}${F('s-lydo', NN.h('xe_reason'), I('s-lydo', ''))}</div><div class="acts"><button class="xe-btn-sm" type="button" data-sub="">${NN.h('cancel')}</button><button class="xe-btn-sm dark" type="button" data-do="attach-rm">${NN.h('xe_attach')}</button></div></div>` : ''}
          ${sub === 'detach' ? `<div class="xe-subform"><div class="xe-form">${F('s-ngay', NN.h('xe_date'), I('s-ngay', iso(today()), 'date'))}${F('s-lydo', NN.h('xe_reason'), I('s-lydo', '', 'text', 'VD: Nứt sàn – đưa đi hàn'), 2)}</div><div class="acts"><button class="xe-btn-sm" type="button" data-sub="">${NN.h('cancel')}</button><button class="xe-btn-sm tan" type="button" data-do="detach-rm">${NN.h('xe_detach')}</button></div></div>` : ''}
          <div class="xe-sec" style="padding:8px 0 4px">${NN.h('xe_rm_log')}</div>${histRows(hist)}`;
      }
      const t = trailerOf(o), free = rm.filter(r => !r.lap_vao && r.trang_thai !== 'repair');
      return `<div class="xe-sec" style="padding:0 0 6px">${NN.h('xe_trailer')}<span class="grow"></span><button class="xe-btn-sm ${t ? '' : 'dark'}" type="button" data-sub="attach">${NN.h(t ? 'xe_swap' : 'xe_attach')}</button>${t ? `<button class="xe-btn-sm tan" type="button" data-sub="detach">${NN.h('xe_detach')}</button>` : ''}</div>
        ${trailerBlock(o).replace('class="xe-trailer', 'style="margin:0 0 10px" class="xe-trailer')}
        ${sub === 'attach' ? `<div class="xe-subform"><div class="xe-form">${F('s-rm', NN.h('xe_trailer'), free.length ? `<select id="s-rm">${free.map(r => `<option value="${esc(r.bien)}" class="lo">${esc(r.bien)} — ${esc(r.loai)} · ${r.tai_trong} t</option>`).join('')}</select>` : `<div class="xe-note warn" style="margin:0">${NN.h('xe_no_free_trailer')}</div>`)}${F('s-ngay', NN.h('xe_date'), I('s-ngay', iso(today()), 'date'))}${F('s-lydo', NN.h('xe_reason'), I('s-lydo', '', 'text', t ? 'VD: đổi rơ-moóc sau sửa sàn' : ''))}</div><div class="acts"><button class="xe-btn-sm" type="button" data-sub="">${NN.h('cancel')}</button><button class="xe-btn-sm dark" type="button" data-do="attach" ${free.length ? '' : 'disabled'}>${NN.h('xe_attach')}</button></div>${t ? `<div class="small muted" style="margin-top:6px">${NN.h('xe_attach_replace')} <span class="lo">${esc(t.bien)}</span></div>` : ''}</div>` : ''}
        ${sub === 'detach' ? `<div class="xe-subform"><div class="xe-form">${F('s-ngay', NN.h('xe_date'), I('s-ngay', iso(today()), 'date'))}${F('s-lydo', NN.h('xe_reason'), I('s-lydo', '', 'text', 'VD: Nứt sàn – đưa đi hàn'), 2)}</div><div class="acts"><button class="xe-btn-sm" type="button" data-sub="">${NN.h('cancel')}</button><button class="xe-btn-sm tan" type="button" data-do="detach">${NN.h('xe_detach')}</button></div></div>` : ''}
        <div class="xe-sec" style="padding:8px 0 4px">${NN.h('xe_rm_log')}</div>${histRows((o.lich_su_rm || []).slice().sort((a, c) => (c.lap || '').localeCompare(a.lap || '')))}`;
    };

    async function lichTab() {
      const tuan = ui.tuan || iso(startOfWeek(today()));
      let lich = null; try { lich = await API.get(`/api/vehicles/${encodeURIComponent(o._id)}/lich?tuan=${tuan}`); } catch (e) { lich = null; }
      const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(tuan + 'T00:00:00'); d.setDate(d.getDate() + i); return d; });
      const ev = (dIso) => (lich && lich.ngay || []).find(n => n.ngay === dIso);
      const cnt = { trip: 0, rep: 0, free: 0 }; days.forEach(d => { const e = ev(iso(d)); cnt[e && e.su_kien.length ? (e.su_kien.some(s => s.loai === 'rep') ? 'rep' : 'trip') : 'free']++; });
      body.innerHTML = `<div class="xe-weekhd" style="padding:0 0 6px"><button class="xe-btn-sm" data-w="-1">‹</button><b>${fmt(iso(days[0]))} – ${fmt(iso(days[6]))}</b><button class="xe-btn-sm" data-w="1">›</button><span class="grow"></span>${pill('blue', cnt.trip + ' ' + NN.t('xe_days_trip'))} ${pill('amber', cnt.rep + ' ' + NN.t('xe_days_repair'))} ${pill('green', cnt.free + ' ' + NN.t('xe_days_free'))}</div>
        <div class="xe-week xe-week--grid">${days.map(d => { const e = ev(iso(d)), isT = iso(d) === iso(today()); return `<div class="xe-day ${isT ? 'today' : ''}"><div class="d">${NN.t('xe_dow_' + d.getDay())}<b>${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}</b></div><div class="evs">${e && e.su_kien.length ? e.su_kien.map(s => `<span class="ev ${s.loai}">${esc(s.text)}</span>`).join('') : `<span class="ev">${NN.h('xe_free_all_day')}</span>`}</div></div>`; }).join('')}</div>
        <div class="small muted" style="margin-top:8px">${NN.h('xe_schedule_hint')}</div>`;
      body.querySelectorAll('[data-w]').forEach(bt => bt.onclick = () => { const d = new Date(tuan + 'T00:00:00'); d.setDate(d.getDate() + 7 * +bt.dataset.w); ui.tuan = iso(d); lichTab(); });
    }
    const suaTab = () => { const c = o.chi_phi || [], tong = c.reduce((a, v) => a + (v.tien || 0), 0);
      return `<div class="xe-sec" style="padding:0 0 6px">${NN.h('xe_tab_repair_full')}<span class="grow"></span><button class="xe-btn-sm tan" type="button" data-go="incident">+ ${NN.h('xe_incident')}</button></div>` + (c.length ? `<div class="xe-rows xe-rows--box">${c.map(v => `<div class="xe-row"><div class="k"><span style="font-weight:600">${esc(v.khoan)}</span><small>${fmt(v.ngay)} · ${esc(v.nguon)}${v.phieu && v.phieu !== '—' ? ` · <span class="mono">${esc(v.phieu)}</span>` : ''}${v.ma_kt ? ` · <span class="tien">${esc(v.ma_kt)}</span>` : ''}</small></div><div class="v"><b class="mono">${so(v.tien)}</b><small>LAK</small></div></div>`).join('')}<div class="xe-foot"><span>${NN.h('xe_total_repair')}: <b style="color:var(--xe-ink)">${so(tong)} LAK</b></span><span>${NN.h('xe_cost_source')}</span></div></div>` : `<div class="xe-empty">${NN.h('xe_no_cost')}</div>`); };
    const phieuTab = () => { const p = o.phieu_gan_day || [];
      return p.length ? `<div class="xe-rows xe-rows--box">${p.map(v => `<div class="xe-row click" data-doc="${esc(v.doc_no)}"><div class="k"><b>${esc(v.doc_no)}</b><small>${fmt(v.ngay)} · <span class="lo">${esc(v.khach)}</span>${v.tan != null ? ` · ${so(v.tan, 2)} ${NN.t('ton')}` : ''}</small></div><div class="v">${pill(v.tt === 'paid' || v.tt === 'arrived' ? 'green' : v.tt === 'transit' ? 'blue' : 'muted', NN.t('xe_tt_' + v.tt))}</div></div>`).join('')}</div>` : `<div class="xe-empty">${NN.h('xe_no_trips')}</div>`; };

    function render() {
      rt.querySelector('#m-tabs').innerHTML = TABS.map(([id, k]) => `<button type="button" class="xe-tab ${cur === id ? 'active' : ''}" data-mt="${id}">${NN.h(k)}</button>`).join('');
      rt.querySelectorAll('[data-mt]').forEach(b => b.onclick = () => { if (isForm()) grab(); cur = b.dataset.mt; sub = null; render(); });
      rt.querySelector('#m-save').style.display = isForm() && suaDuoc() ? '' : 'none'; rt.querySelector('#m-foot-note').textContent = isForm() ? '' : NN.t('xe_tab_autosave');
      if (cur === 'lich') { body.innerHTML = `<div class="xe-empty">…</div>`; lichTab(); return; }
      body.innerHTML = isForm() ? `<form class="xe-form" onsubmit="return false">${formTab()}</form>` : cur === 'romooc' ? rmTab() : cur === 'sua' ? suaTab() : phieuTab();
      if (isForm()) Object.entries(vals).forEach(([k, v]) => { const el = body.querySelector('#' + k); if (el) el.value = v; });
      if (!suaDuoc()) {          // vai chỉ xem: bỏ mọi nút sửa, lắp, tháo — hồ sơ vẫn đọc được
        body.querySelectorAll('[data-sub]').forEach(b => b.remove());
        body.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = true; });
      }
      body.querySelectorAll('[data-sub]').forEach(b => b.onclick = () => { sub = b.dataset.sub || null; render(); if (sub) setTimeout(() => body.querySelector('#s-lydo')?.focus(), 30); });
      body.querySelectorAll('.xe-row.click').forEach(el => el.onclick = () => { close(); EPL.di('theo-doi', { q: el.dataset.doc }); });
      const inc = body.querySelector('[data-go="incident"]'); if (inc) inc.onclick = () => { close(); EPL.di('theo-doi-tuyen', {}); };   // báo sự cố nằm ở màn Theo dõi tuyến
      const d = body.querySelector('[data-do]'); if (d) d.onclick = () => doSub(d.dataset.do);
    }
    async function doSub(kind) {
      const ngay = body.querySelector('#s-ngay').value, ly = (body.querySelector('#s-lydo') || {}).value?.trim() || '';
      let ok = true;
      if (kind === 'detach') { if (!ly) return body.querySelector('#s-lydo').focus(); ok = await doDetach(o, ngay, ly); if (ok) toast(NN.t('xe_detached_toast')); }
      else if (kind === 'detach-rm') { const host = xe.find(x => x.so_xe === o.lap_vao); if (!ly) return body.querySelector('#s-lydo').focus(); ok = await doDetach(host, ngay, ly); if (ok) toast(NN.t('xe_detached_toast')); }
      else if (kind === 'attach') { const bien = body.querySelector('#s-rm').value; ok = await doAttach(o, bien, ngay, ly); }
      else if (kind === 'attach-rm') { const x = xe.find(v => v.so_xe === body.querySelector('#s-xe').value); ok = await doAttach(x, o.bien, ngay, ly); }
      sub = null;
      if (ok) { await tai(); const moi = isRM ? rm.find(v => v._id === o._id) : xe.find(v => v._id === o._id); if (moi) { await napChiTiet(moi, isRM); Object.assign(o, moi); } }
      render();
    }
    /** Lưu THẬT. Bản mẫu nuốt lỗi API (`catch (e) {}`) nên màn báo đã lưu trong khi máy chủ từ chối —
     *  ở đây lỗi phải hiện ra và giữ nguyên hộp để người dùng sửa; lưu xong thì tải lại từ máy chủ. */
    async function save() {
      grab();
      if (isRM) {
        Object.assign(o, { bien: g('f-bien') || o.bien, loai: g('f-loai') ?? o.loai, tai_trong: +g('f-tai') || o.tai_trong, nam_sx: +g('f-nam') || o.nam_sx, so_huu: g('f-sohuu') || o.so_huu, bai: g('f-bai') ?? o.bai, ghi_chu: g('f-ghichu') ?? o.ghi_chu, so_khung: g('f-sokhung') ?? o.so_khung, noi_dang_kiem: g('f-noidk') ?? o.noi_dang_kiem });
        if (g('f-h-dk')) o.han.dang_kiem = g('f-h-dk'); if (g('f-h-lh')) o.han.luu_hanh = g('f-h-lh');
        if (isNew && !o.bien) return EPL.toast(NN.t('xe_need_plate'), 'loi');
      } else {
        Object.assign(o, { so_xe: g('f-soxe') || o.so_xe, bien: g('f-bien') || o.bien, hang: g('f-hang') ?? o.hang, nam_sx: +g('f-nam') || o.nam_sx, so_huu: g('f-sohuu') || o.so_huu, bai: g('f-bai') ?? o.bai, dinh_muc: g('f-dinhmuc') ? +g('f-dinhmuc') : o.dinh_muc, tai_trong: g('f-taitrong') ? +g('f-taitrong') : o.tai_trong, ghi_chu: g('f-ghichu') ?? o.ghi_chu, so_may: g('f-somay') ?? o.so_may, so_khung: g('f-sokhung') ?? o.so_khung, noi_dang_kiem: g('f-noidk') ?? o.noi_dang_kiem, km: g('f-km') ? +g('f-km') : o.km, km_bao_duong: g('f-kmbd') ? +g('f-kmbd') : o.km_bao_duong, ngay_bao_duong: g('f-ngaybd') ?? o.ngay_bao_duong, dung_tich: g('f-dungtich') ?? o.dung_tich, kich_thuoc_thung: g('f-kt') ?? o.kich_thuoc_thung, lop: g('f-lop') ?? o.lop });
        [['bh', 'bao_hiem'], ['dk', 'dang_kiem'], ['lh', 'luu_hanh']].forEach(([k, key]) => { if (g('f-h-' + k)) o.han[key] = g('f-h-' + k); });
        if (g('f-chuxe') !== undefined) {
          if (chuXe.length) { o.chu_xe_id = g('f-chuxe') || null; const c = chuXe.find(x => x.id === o.chu_xe_id); o.chu_xe = c ? c.name : null; }
          else o.chu_xe = g('f-chuxe');
        }
        if (isNew && !o.so_xe) return EPL.toast(NN.t('xe_need_no'), 'loi');
      }
      const than = isRM ? guiRM(o) : guiXe(o);
      const duong = isRM ? '/api/trailers' : '/api/vehicles';
      try {
        const d = isNew ? await API.post(duong, than) : await API.put(duong + '/' + o._id, than);
        ui.sel = isRM ? d.plate : d.truck_no;
      } catch (e) { return EPL.baoLoi(e); }
      close(); toast(`${NN.t('xe_saved')} ${isRM ? o.bien : o.so_xe}`);
      await tai();
    }
    rt.querySelector('#m-save').onclick = save;
    render();
  }

  /* Lắp / tháo đi thẳng vào máy chủ (POST /api/vehicles/{id}/trailer, trailer_id rỗng là tháo). Máy chủ
     tự tháo khỏi xe cũ nếu rơ-moóc đang lắp ở xe khác, và tự ghi lịch sử — không dựng lại luật ở đây.
     NGÀY lắp/tháo do máy chủ đóng dấu theo lúc bấm; ô ngày trong biểu mẫu chỉ để người dùng đối chiếu. */
  async function doAttach(x, bien, _ngay, ly_do) {
    const r = rm.find(v => v.bien === bien); if (!x || !r) return false;
    try { await API.post(`/api/vehicles/${encodeURIComponent(x._id)}/trailer`, { trailer_id: r._id, reason: ly_do || null }); }
    catch (e) { EPL.baoLoi(e); return false; }
    toast(`${NN.t('xe_attached_toast')} ${bien} → ${x.so_xe}`);
    return true;
  }
  async function doDetach(x, _ngay, ly_do) {
    if (!x || !x.ro_mooc) return true;
    try { await API.post(`/api/vehicles/${encodeURIComponent(x._id)}/trailer`, { trailer_id: '', reason: ly_do || null }); }
    catch (e) { EPL.baoLoi(e); return false; }
    return true;
  }

  function ve() { veQuick(); veList(); veDetail(); }

  EPL.modules['xe'] = {
    async init(r) {
      root = r;
      r.querySelectorAll('[data-i18n-ph]').forEach(el => el.placeholder = NN.t(el.dataset.i18nPh));
      r.querySelector('#xe-loai').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; ui.mode = b.dataset.v; ui.chip = null; ui.sel = null; r.querySelectorAll('#xe-loai button').forEach(x => x.classList.toggle('active', x === b)); ui.sel = ui.mode === 'dau-keo' ? xe[0]?.so_xe : rm[0]?.bien; ve(); });
      r.querySelector('#xe-q').addEventListener('input', e => { ui.q = e.target.value; veList(); veDetail(); });
      r.querySelector('#xe-f-so-huu').addEventListener('change', e => { ui.soHuu = e.target.value; veList(); veDetail(); });
      r.querySelector('#xe-f-bai').addEventListener('change', e => { ui.bai = e.target.value; veList(); veDetail(); });
      r.querySelector('#xe-f-tt').addEventListener('change', e => { ui.tt = e.target.value; veList(); veDetail(); });
      r.querySelector('#xe-refresh').addEventListener('click', () => tai().then(() => toast(NN.t('xe_refreshed'))).catch(EPL.baoLoi));
      const them = r.querySelector('#xe-them'); them.hidden = !suaDuoc();
      them.addEventListener('click', () => { if (ui.mode === 'dau-keo') openHoSo({ so_xe: '', bien: '', hang: '', so_huu: 'cong-ty', han: {}, trang_thai: 'idle', lich_su_rm: [], chi_phi: [], phieu_gan_day: [] }, false); else openHoSo({ bien: '', loai: '', tai_trong: 40, so_huu: 'cong-ty', han: {}, trang_thai: 'roi' }, true); });
      // Đóng ngăn hồ sơ: bấm nền mờ, hoặc nút X trong chính thẻ (gắn một lần, bắt theo nổi bọt).
      r.querySelector('#xe-scrim').addEventListener('click', closeDetail);
      r.querySelector('#xe-detail').addEventListener('click', e => { if (e.target.closest('[data-close-detail]')) closeDetail(); });
      // Gỡ phím Esc khi rời màn — trước đây mỗi lần mở màn lại gắn thêm một cái, không bao giờ tháo.
      // Esc đóng hộp hồ sơ trước; hộp đã đóng thì mới thu ngăn trượt.
      thoat = (e) => { if (e.key !== 'Escape') return; if (r.querySelector('#xe-modal-root').innerHTML) close(); else closeDetail(); };
      document.addEventListener('keydown', thoat);
      await tai();
    },
    onLang() { ve(); },
    destroy() { if (thoat) document.removeEventListener('keydown', thoat); thoat = null; },
  };
})();
