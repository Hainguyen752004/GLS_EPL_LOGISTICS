/* Đề nghị theo DO — HỒ SƠ DO HAI BÊN (chủ dự án 02/10/2026).
 *
 * Chủ dự án hỏi "trang này có chức năng gì, có phải để xem qua lại giữa bên mình và anh Tune không" — đúng: mỗi DO, bên điều
 * xe (trang này) đề nghị chi / xuất kho / thu những gì, và bên kế toán (hệ anh Tune) đã lập chứng từ nào, trạng thái ra sao.
 * Bảy nhóm, mỗi nhóm một cặp "bên điều xe ↔ bên kế toán":
 *   tam_ung  Tạm ứng           PTU                     ↔ phiếu chi «Chi trước» CTR
 *   chi_muc  Chi mục V / VI     mục V · VI quỹ trả ngay  ↔ phiếu chi «Chi khác» CKH
 *   xuat_kho Xuất kho           PLNL · phụ tùng kho     ↔ bút toán xuất nội bộ (625 · 614/1371) · xuất bán (4022/707 + 607/1371)
 *   but_toan Thuê xe · nợ NCC   khoá phiếu              ↔ bút toán 621/4022 · …/4021 (GL…)
 *   thu      Đề nghị thu        PDT                     ↔ SO dịch vụ vận chuyển TK-… · đã thu bao nhiêu
 *   so_nl    SO nhiên liệu      xe thuê lấy dầu kho EPL ↔ SO nhiên liệu ghi công nợ đối tác (đường mới — sắp có)
 *   tra_dt   Trả đối tác        đề nghị TCX             ↔ phiếu chi «Chi khác»
 * Mỗi nhóm một chữ trạng thái (máy chủ tính): khong · chua (bên điều xe chưa xong) · cho_gui · cho_kt (kế toán đã lập, chờ chi /
 * thu / ghi sổ) · xong · loi. Trái: DO của tháng, bảy ô màu mỗi DO. Phải: một DO — tab "Hai bên theo nhóm" (bảy thẻ) và tab
 * "Từng dòng tiền" (settlement của gói DO: dòng nào đã vào chứng từ nào).
 * API: GET /api/ho-so-do?thang=&q= · GET /api/ho-so-do/{trip_id} (routes/ho_so_do.py, chỉ đọc) · sổ: /api/chung-tu,
 * POST /api/chung-tu/{id}/da-day · hai mã: GET/PUT /api/kho-tam/cau-hinh (máy chủ trước 52f673c: /api/ke-toan/cau-hinh).
 * SO nhiên liệu xe thuê: đọc thêm GET /api/tat-toan-doi-tac?ky=&owner_id= (nếu máy chủ có) — không có thì "sắp có".
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, tab = 'do', D = { ds: [] }, loc = '', tim = '', chonId = null, hen = null, tabCt = 'nhom';
  let SO_LOAI = [], soLoaiChon = '';
  const CT = {};                     // trip_id → hồ sơ đầy đủ (GET /api/ho-so-do/{id})
  const NL = {};                     // trip_id → dòng tất toán đối tác (SO nhiên liệu) | null
  const XEM_SO = ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'depot', 'admin'];
  // loại đối tượng của tờ (services/chung_tu.py) → nhãn đã dịch; trước đây hiện mã thô "tai_xe", "khach"… dưới tên
  const DOI_TUONG = { khach: 'customer', tai_xe: 'driver', chu_xe: 'owner', kho: 'fuel_kho', ncc: 'supplier' };
  const NHOM = ['tam_ung', 'chi_muc', 'xuat_kho', 'but_toan', 'thu', 'so_nl', 'tra_dt'];
  const MUC = ['xong', 'cho_kt', 'cho_gui', 'chua', 'loi', 'khong'];
  const LOC = ['', 'em', 'kt', 'loi', 'xong'];
  const q = (s) => root.querySelector(s);
  const thangNay = () => EPL.thangNay();    // giờ máy — toISOString là giờ UTC, 0–7 giờ sáng ngày 1 ra tháng trước
  const duocVao = (id) => EPL.manCuaVai(AUTH.role).some(m => m.id === id);
  /** Tên loại chứng từ theo tiếng đang xem — từ điển `ctl_<mã>` (rà 02/10: máy chủ chỉ gửi tên Việt / Lào, tiếng Anh hiện chữ
   *  Việt). Loại mới chưa có khoá thì lấy tên máy chủ gửi. `tho` = chữ thuần (cho <option>). */
  function tenLoai(ma, vi, lo, tho) {
    const k = 'ctl_' + String(ma || '').toLowerCase();
    if ((window.EPL_TU_DIEN || {})[k]) return tho ? esc(NN.t(k)) : NN.h(k);
    return esc(NN.lang === 'lo' ? lo || vi : vi || lo);
  }
  const veOLoai = () => {
    q('#ct-so-loai').innerHTML = `<option value="">${esc(NN.t('all'))}</option>` + SO_LOAI.map(l => `<option value="${l.ma}">${esc(l.ma)} · ${tenLoai(l.ma, l.ten, l.ten_lo, true)}</option>`).join('');
    q('#ct-so-loai').value = soLoaiChon;
  };
  /* Tháng trống (01/10): mở màn đầu tháng thấy "Chưa có dữ liệu", tưởng hỏng. TU_DONG = lượt tải đầu khi vào màn không kèm
   * tháng → tháng trống thì sang tháng gần nhất có DO, BAO giữ dòng báo; GAN = tháng cho nút ở khung trống. */
  let TU_DONG = false, BAO = null, GAN = null, GIU_CT = null;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');

  /** Tháng `th` có phiếu không; không có thì tháng nào GẦN NHẤT có (cùng bộ lọc `loc` của /api/trips). Hỏi hai lần, mỗi lần
   *  một dòng: phiếu mới nhất tới cuối tháng `th`, phiếu cũ nhất từ đầu tháng `th` — không tải cả năm. Cách đều: tháng trước. */
  async function thangGan(th, loc) {
    const [y, m] = th.split('-').map(Number);
    const hoi = (them) => { const p = new URLSearchParams(loc); p.set('co', '1'); Object.entries(them).forEach(([k, v]) => p.set(k, v));
      return API.get('/api/trips?' + p).then(d => (d && d[0] && d[0].doc_date ? d[0].doc_date.slice(0, 7) : null), () => null); };
    const [truoc, sau] = await Promise.all([hoi({ den: th + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }), hoi({ tu: th + '-01', sap: 'cu' })]);
    if (truoc === th || sau === th) return { co: true, gan: th };
    const n = (v) => v.slice(0, 4) * 12 + +v.slice(5, 7);
    return { co: false, gan: !truoc || !sau ? truoc || sau : (n(sau) - n(th) < n(th) - n(truoc) ? sau : truoc) };
  }
  /** Người dùng TỰ chọn tháng (ô tháng, nút ở khung trống): giữ đúng tháng đó, bỏ dòng báo, thôi tự sang tháng khác. */
  function chonThang(v) { TU_DONG = false; BAO = null; q('#ct2-thang').value = v; taiDo(); }
  function veBao() {
    const o = q('#ct2-bao');
    o.hidden = !BAO;
    o.innerHTML = BAO ? `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg><span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span>` : '';
  }
  /** Bảng trống: lý do đúng (tháng chưa có DO · chữ tìm / thẻ lọc không khớp) + nút về tháng gần nhất hoặc xem tất cả. */
  function oTrong() {
    const boLoc = D.ds.length || tim;
    return `<div class="ct2-trong-bang"><div>${boLoc ? NN.h('loc_trong') : NN.h('thang_trong_n', { thang: nhanThang(q('#ct2-thang').value) })}</div>
      ${D.ds.length && loc ? `<button type="button" class="btn sm" data-tat-ca="1">${NN.h('tq_view_all')}</button>` : ''}
      ${!D.ds.length && GAN ? `<button type="button" class="btn sm primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}</div>`;
  }

  /* ---------------------------------------------------------------- lọc theo trạng thái hai bên */
  const mucCua = (x, k) => ((x.nhom || {})[k] || {}).muc || 'khong';
  const coMuc = (x, ...m) => NHOM.some(k => m.includes(mucCua(x, k)));
  const xongHet = (x) => NHOM.some(k => mucCua(x, k) !== 'khong') && NHOM.every(k => ['khong', 'xong'].includes(mucCua(x, k)));
  const KHOP = { '': () => true, em: (x) => coMuc(x, 'chua'), kt: (x) => coMuc(x, 'cho_gui', 'cho_kt'), loi: (x) => coMuc(x, 'loi'), xong: xongHet };
  const NHAN_LOC = { '': 'all', em: 'hs_loc_em', kt: 'hs_loc_kt', loi: 'hs_loc_loi', xong: 'hs_loc_xong' };
  function dsLoc() { return D.ds.filter(KHOP[loc] || KHOP['']); }
  function veLoc() {
    q('#ct2-loc').innerHTML = LOC.map(k => `<button type="button" data-loc="${k}" class="${loc === k ? 'on' : ''}">
      <span>${NN.h(NHAN_LOC[k])}</span><b>${D.ds.filter(KHOP[k]).length}</b></button>`).join('');
    q('#ct2-loc').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veBang(); veCt(); }));
  }

  /* ---------------------------------------------------------------- nhãn */
  const tagMuc = (m) => `<span class="tag hs-tm-${esc(m)}">${NN.h('hs_m_' + m)}</span>`;
  const tag = (mau, khoa) => EPL.tag(mau, khoa);
  const PC = { da_gui: ['transit', 'tt_cho_chi'], da_chi: ['paid', 'ck_da_chi_ngan'], loi: ['unpaid', 'ck_loi_ngan'], phieu_mat: ['unpaid', 'ck_phieu_mat'] };
  const SO_TT = { chua_thu: ['dispatched', 'hs_so_chua_thu'], thu_mot_phan: ['partial', 'dt_st_thu_mot_phan'], da_thu: ['paid', 'dt_st_da_thu'],
    khong_thay: ['unpaid', 'hs_so_khong_thay'], failed: ['unpaid', 'ck_loi_ngan'], conflict: ['unpaid', 'hs_so_trung'] };
  const STT = { wait: 'plain', entered: 'dispatched', verified: 'dispatched', booked: 'transit', paid: 'paid' };
  const tagPC = (tt) => tag(...(PC[tt] || ['plain', 'v_' + tt]));
  function tagGL(it) {
    if (it.tt === 'can_dao') return tag('unpaid', 'btc_can_dao');
    if (it.loi) return tag('unpaid', 'ck_loi_ngan');
    if (it.tt === 'cho_gui') return tag('transit', 'dt_st_cho_gui');
    return it.chinh_thuc ? tag('paid', 'hs_gl_chinh_thuc') : tag('dispatched', 'hs_gl_so_tam');
  }
  const tienLak = (v) => (v == null ? '' : `<span class="tien">${so(v)} LAK</span>`);
  const tienCcy = (v, ma) => (v == null ? '' : `<span class="tien">${EPL.tien(v, ma)}</span>`);
  const mono = (s) => `<span class="mono">${esc(s)}</span>`;
  const rong = (k, thay) => `<div class="t"><span class="rong">${NN.h(k, thay)}</span></div>`;
  const dongT = (...p) => `<div class="t">${p.filter(Boolean).join(' ')}</div>`;

  /** Một tờ / chứng từ trong một bên của thẻ. */
  function oTo(it) {
    switch (it.loai) {
      case 'ptu': return dongT(mono(it.so), tag(it.tt === 'da_cap' ? 'paid' : 'transit', 'v_' + it.tt), tienLak(it.tien_lak));
      case 'ctr': case 'ckh':
        return dongT(it.so ? mono(it.so) : `<span class="rong">${NN.h('hs_chua_co_so')}</span>`, tagPC(it.tt), tienLak(it.tien_lak),
          it.ref && it.ref !== it.so ? `<span class="small muted">${esc(it.ref)}</span>` : '')
          + (it.loi ? `<div class="t"><span class="small neg">${esc(it.loi)}</span></div>` : '');
      case 'muc': return dongT(`<b>${NN.h('hs_muc', { m: it.muc })}</b>`, tag(STT[it.tt] || 'plain', 'stt_' + it.tt),
        it.so ? mono(it.so) : '', tienLak(it.tien_lak));
      case 'plnl': return dongT(mono(it.so), tag(it.tt === 'da_cap' ? 'paid' : 'transit', 'v_' + it.tt), `<span class="tien">${so(it.lit, 0)} L</span>`,
        it.kho ? `<span class="small muted" lang="lo">${esc(it.kho)}</span>` : '');
      case 'pt_kho': return dongT(NN.h('hs_pt_kho', { da: it.da_xuat, n: it.n }));
      case 'khoa': return dongT(tag(it.tt === 'da_khoa' ? 'paid' : 'plain', it.tt === 'da_khoa' ? 's_locked' : 'hs_chua_khoa'),
        `<span class="small muted">${[it.thue ? NN.h('hs_kt_thue') : '', it.ncc ? NN.h('hs_kt_ncc') : ''].filter(Boolean).join(' · ')}</span>`);
      case 'gl': return dongT(it.so ? mono(it.so) : `<span class="rong">${NN.h('hs_chua_co_so')}</span>`, tagGL(it),
        `<span class="small muted">${NN.h('btc_nguon_' + it.nguon)}</span>`, tienCcy(it.tien, it.ccy),
        it.id && duocVao('but-toan-cho') ? `<a data-bt="${esc(it.id)}">${NN.h('hs_xem_but_toan')}</a>` : '');
      case 'pdt': return dongT(it.so ? mono(it.so) : '', tag('dt_' + it.tt, 'dt_st_' + it.tt), tienCcy(it.tien, it.ccy));
      case 'so': return dongT(it.so ? mono(it.so) : '', tag(...(SO_TT[it.tt] || ['plain', 'hs_so_chua_thu'])),
        it.tong != null ? `<span class="tien">${NN.h('collected')} ${EPL.tien(it.da_thu || 0, it.ccy)} / ${EPL.tien(it.tong, it.ccy)}</span>` : '')
        + (it.loi ? `<div class="t"><span class="small neg">${esc(it.loi)}</span></div>` : '');
      case 'tcx': return dongT(mono(it.so), tagPC(it.tt), tienCcy(it.tien, it.ccy), it.so_phieu ? `<span class="small muted">${it.so_phieu} ${NN.h('cx_phieu')}</span>` : '');
      case 'nl_em': return dongT(`<b>${NN.h('hs_nl_dau_ban')}</b>`, it.so_dong ? `<span class="small muted">${NN.h('ct_so_dong', { n: it.so_dong })}</span>` : '', tienLak(it.tien_lak));
      case 'nl_so': return dongT(it.so ? mono(it.so) : '', tag(...({ chua_tao: ['plain', 'hs_nl_chua_tao'], da_tao: ['dispatched', 'hs_nl_da_tao'],
        da_thu: ['paid', 'dt_st_da_thu'], can_tru: ['paid', 'hs_nl_can_tru'], loi: ['unpaid', 'ck_loi_ngan'] }[it.tt] || ['plain', 'hs_nl_chua_tao'])),
        it.con_no_lak ? `<span class="tien">${NN.h('hs_nl_con_no')} ${so(it.con_no_lak)} LAK</span>` : '')
        + (it.loi ? `<div class="t"><span class="small neg">${esc(it.loi)}</span></div>` : '');
      case 'tkn': return dongT(it.so ? mono(it.so) : `<span class="rong">${NN.h('hs_chua_co_so')}</span>`,
        tag(...({ da_gui: ['paid', 'hs_nl_can_tru'], loi: ['unpaid', 'ck_loi_ngan'] }[it.tt] || ['plain', 'hs_nl_can_tru'])),
        `<span class="small muted">${NN.h('hs_tkn')}${it.ref ? ' · ' + esc(it.ref) : ''}</span>`, tienLak(it.tien_lak))
        + (it.loi ? `<div class="t"><span class="small neg">${esc(it.loi)}</span></div>` : '');
      default: return '';
    }
  }

  /** Thẻ một nhóm: tên + trạng thái cả nhóm, câu giải thích, cặp "bên điều xe → bên kế toán", ghi chú. */
  function theNhom(k, g) {
    // 06/10: nhóm bút toán khoá phiếu có thêm phí quản lý 4022/715 và cắt quá tải 4022/758 (cùng chứng từ thuê xe) — câu khoá mới
    const giai = k === 'tam_ung' || k === 'xuat_kho' ? 'hs_d_' + k + '_' + (g.hinh_thuc || 'noi_bo') : k === 'but_toan' ? 'hs_d_but_toan_phi' : 'hs_d_' + k;
    const em = g.em.length ? g.em.map(oTo).join('') : rong(k === 'so_nl' ? 'hs_sap_co' : 'hs_em_chua');
    const kt = g.kt.length ? g.kt.map(oTo).join('') : rong(k === 'so_nl' ? 'hs_sap_co' : 'hs_kt_chua');
    const chu = g.ghi_chu && !(k === 'so_nl' && g.kt.length) ? `<div class="hs-chu ${g.muc === 'loi' ? 'loi' : g.muc === 'xong' || k === 'so_nl' ? 'nhe' : ''}">${NN.h('hs_c_' + g.ghi_chu)}</div>` : '';
    return `<div class="hs-the hs-b-${esc(g.muc)}">
      <div class="hs-the-dau"><h4>${NN.h('hs_g_' + k)}</h4>${tagMuc(g.muc)}</div>
      <div class="hs-giai">${NN.h(giai)}</div>
      <div class="hs-cap"><span class="hs-nhan">${NN.h('hs_ben_em')}</span><div class="hs-ben">${em}</div>
        <span class="hs-nhan kt"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v14M6 12l6 6 6-6"/></svg>${NN.h('hs_ben_kt')}</span><div class="hs-ben kt">${kt}</div></div>${chu}</div>`;
  }

  /* ---------------------------------------------------------------- bảng DO */
  function o7(x) {
    return `<div class="hs-o7">${NHOM.map(k => { const m = mucCua(x, k);
      return `<i class="hs-m-${m}" title="${esc(NN.t('hs_g_' + k))} · ${esc(NN.t('hs_m_' + m))}">${NN.h('hs_k_' + k)}</i>`; }).join('')}</div>`;
  }
  function veBang() {
    const b = q('#ct2-bang'), ds = dsLoc();
    veLoc();
    b.innerHTML = `<thead><tr><th>DO</th><th>${NN.h('truck_no')} · ${NN.h('driver')}<span class="lo-sub" style="display:block;font-weight:500">${NN.h('customer')} · ${NN.h('route')}</span></th>
      <th>${NN.h('hs_c_hai_ben')}<div class="hs-o7 dau" style="margin-top:4px">${NHOM.map(k => `<i>${NN.h('hs_k_' + k)}</i>`).join('')}</div></th></tr></thead>
      <tbody>${ds.length ? ds.map(x => `<tr data-id="${esc(x.trip_id)}" class="${x.trip_id === chonId ? 'sel' : ''}">
        <td><span class="so">${esc(x.doc_no)}</span>
          <span class="phu">${EPL.ngay(x.doc_date)}<span class="ct2-k ${esc(x.kind)}">${NN.h(x.kind === 'gom' ? 'dn_gom' : 'dn_giao')}</span>${x.company === 'joint' ? `<span class="ct2-k joint">${NN.h('dn_xe_thue')}</span>` : ''}${x.locked ? `<span class="ct2-k khoa">${NN.h('s_locked')}</span>` : ''}</span></td>
        <td>${esc(x.truck_no || '—')} · <span lang="lo">${esc(x.driver_name || '')}</span>
          <span class="phu" lang="lo">${esc(x.customer_name || '—')}${x.origin || x.destination ? ` · ${esc(x.origin || '—')} → ${esc(x.destination || '—')}` : ''}</span></td>
        <td>${o7(x)}</td></tr>`).join('')
        : `<tr><td class="empty" colspan="3">${oTrong()}</td></tr>`}</tbody>`;
    b.querySelectorAll('tbody tr[data-id]').forEach(tr => tr.addEventListener('click', () => { chonId = tr.dataset.id; veBang(); veCt(); }));
    const nutThang = b.querySelector('[data-thang]'); if (nutThang) nutThang.addEventListener('click', () => chonThang(nutThang.dataset.thang));
    const nutHet = b.querySelector('[data-tat-ca]'); if (nutHet) nutHet.addEventListener('click', () => { loc = ''; chonId = D.ds[0] ? D.ds[0].trip_id : null; veBang(); veCt(); });
    // bảng trống: bỏ khung "Chọn một dòng" bên phải, bảng (và khung trống của nó) chiếm cả bề ngang
    q('#ct2-do').classList.toggle('trong', !ds.length); q('#ct2-ct').hidden = !ds.length;
    veBao();
    // chú thích sáu màu — ngay dưới bảng, không chiếm hàng riêng trên đầu
    let chu = root.querySelector('.ct2-chu');
    if (!chu) { chu = document.createElement('div'); chu.className = 'ct2-chu'; q('.ct2-trai').appendChild(chu); }
    chu.innerHTML = MUC.map(m => `<span><i class="hs-m-${m}"></i>${NN.h('hs_m_' + m)}</span>`).join('');
    datCao();
  }

  /* ---------------------------------------------------------------- khung phải: một DO */
  /** Tờ / tháng đang xem ghi vào địa chỉ (rà 01/10): bấm "Mở phiếu" sang Phiếu xuất xe rồi Quay lại, hay tải lại trang, là về
   *  đúng tờ đó. replaceState: không thêm bước lịch sử, không bắn hashchange; màn đã bị rời (gốc tháo khỏi trang) thì thôi. */
  function ghiDiaChi(ts) {
    if (!root || !root.isConnected) return;
    [...ts.keys()].forEach(k => { if (!ts.get(k)) ts.delete(k); });
    const moi = '#/chung-tu' + (ts.toString() ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }

  /** SO nhiên liệu của một chuyến xe thuê — dòng chi tiết màn Tất toán đối tác (GET /api/tat-toan-doi-tac). Máy chủ chưa có
   *  đường đó (404) hay vai không xem được thì null: thẻ giữ chữ "sắp có". Hỏi một lần mỗi chuyến. */
  async function taiNL(x) {
    if (x.trip_id in NL) return NL[x.trip_id];
    NL[x.trip_id] = null;
    if (x.company !== 'joint' || !x.owner_id || !duocVao('tat-toan-doi-tac')) return null;
    try {
      const r = await API.get('/api/tat-toan-doi-tac?ky=' + encodeURIComponent((x.doc_date || '').slice(0, 7)) + '&owner_id=' + encodeURIComponent(x.owner_id) + '&cap_nhat=0');
      NL[x.trip_id] = ((r && r.chi_tiet) || []).find(c => c.trip_id === x.trip_id) || null;
    } catch (e) { NL[x.trip_id] = null; }
    return NL[x.trip_id];
  }
  /** Ghép SO nhiên liệu (nếu đọc được) vào nhóm so_nl của hồ sơ. */
  function ghepNL(nhom, c) {
    const n = c && c.nhien_lieu;
    if (!n || !nhom.so_nl || !nhom.so_nl.sap_co || !n.tien_lak) return nhom;      // máy chủ đã đọc SO nhiên liệu thì giữ         // chuyến không lấy dầu kho EPL: giữ nhóm như máy chủ tính
    const g = { ...nhom.so_nl, em: [{ loai: 'nl_em', tien_lak: n.tien_lak }],
      kt: n.trang_thai && n.trang_thai !== 'chua_tao' ? [{ loai: 'nl_so', so: n.order_code, tt: n.trang_thai, con_no_lak: n.con_no_lak }] : [] };
    g.muc = n.trang_thai === 'da_thu' || n.trang_thai === 'can_tru' ? 'xong' : n.trang_thai === 'da_tao' ? 'cho_kt' : 'chua';
    g.ghi_chu = g.kt.length ? null : 'nl_cho_tao';
    return { ...nhom, so_nl: g };
  }

  const KIND = { sales_order: 'hs_x_sales_order', fuel_so: 'hs_x_fuel_so', journal: 'hs_x_journal', advance: 'hs_x_advance', pay_now: 'hs_x_pay_now',
    driver_settlement: 'hs_x_driver_settlement', owner_payment: 'hs_x_owner_payment', owner_paid: 'hs_x_owner_paid',
    payroll: 'hs_x_payroll', toll_card: 'hs_x_toll_card' };
  const MUC_LA = { III: 'III', IV: 'IV', V: 'V', VI: 'VI' };
  /** Bảng từng dòng tiền của DO: mỗi dòng đã vào chứng từ nào (settlement), xếp theo mục. */
  function bangDong(h) {
    const coTien = h.thay_tien_chi;
    const st = (s) => `<span class="tag hs-${esc(s.state)}" ${NN.lang === 'vi' || NN.lang === 'both' ? `title="${esc(s.label || '')}"` : ''}>${NN.h('hs_s_' + s.state)}</span>`;
    // mã nguồn bút toán (EPLLAO-<nguồn>-<mã máy>) là khoá máy, không phải số người đọc — chỉ hiện số tờ người dùng (PTU-, PCSC-, TCX-…)
    const ref = (r) => (r && !/^EPLLAO-/.test(r) ? r : '');
    const ma = (s) => `${st(s)}${s.doc_no ? `<b>${esc(s.doc_no)}</b>` : ''}${ref(s.ref_no) && s.ref_no !== s.doc_no ? `<span class="phu">${esc(s.ref_no)}</span>` : ''}`;
    const dongTr = (cls, muc, ten, sl, tien, s) => `<tr class="hs-s-${esc(s.state)} ${cls}"><td>${muc}</td><td lang="lo">${ten}</td><td class="num">${sl}</td>
      ${coTien ? `<td class="num">${tien}</td>` : ''}<td>${NN.h(KIND[s.kind] || 'hs_x_khac')}</td><td class="ma">${ma(s)}</td></tr>`;
    // SO nhiên liệu của DO xe thuê (header.fuel_so gói DO) — một dòng trên đầu, như tiền thuê
    const fs = h.fuel_so;
    // cột "Thành tiền (LAK)": số Kíp, tiền gốc (nếu khác Kíp) ở dòng phụ — như dòng cước
    const kip = (lak, v, ma) => `${lak != null ? so(lak) : '—'}${ma && ma !== 'LAK' && v != null ? `<span class="phu">${EPL.tien(v, ma)}</span>` : ''}`;
    const soNl = fs ? dongTr('hs-dong-thue', '—', NN.h('hs_so_nl_dong'), '', (fs.currency || 'LAK') === 'LAK' ? (fs.total != null ? so(fs.total) : '—') : kip(null, fs.total, fs.currency),
      { state: fs.order_code ? 'has_voucher' : 'pending', kind: 'fuel_so', doc_no: fs.order_code, ref_no: null }) : '';
    const thue = h.thue ? [h.thue.settlement && dongTr('hs-dong-thue', '—', NN.h('hs_tien_thue_dt'), '', kip(h.thue.amount_lak, h.thue.amount, h.thue.currency), h.thue.settlement),
      h.thue.journal && dongTr('hs-dong-thue', '—', NN.h('hs_bt_thue_xe'), '', kip(h.thue.amount_lak, h.thue.amount, h.thue.currency), h.thue.journal)].filter(Boolean).join('') : '';
    const rows = (h.dong || []).map(d => {
      const s = d.settlement || { state: 'open' };
      const ten = d.kind === 'thu' ? NN.h('hs_cuoc') : esc(NN.lang === 'lo' ? d.name_lo || d.name : d.name || d.name_lo || '');
      const sl = d.unit_price != null ? `${so(d.qty, EPL.leTien(d.currency) ? 2 : (Number.isInteger(+d.qty) ? 0 : 2))} × ${EPL.tien(d.unit_price, d.currency)}` : so(d.qty, Number.isInteger(+d.qty) ? 0 : 2);
      const tien = d.kind === 'thu' ? `${d.amount_lak != null ? so(d.amount_lak) : '—'}${d.currency && d.currency !== 'LAK' ? `<span class="phu">${EPL.tien(d.actual_amount, d.currency)}</span>` : ''}`
        : (d.amount_lak != null ? so(d.amount_lak) : '—');
      const phu = [d.source === 'kho' ? NN.h(d.sale_to_owner ? 'hs_xuat_ban_ngan' : 'hs_xuat_noi_bo_ngan') : '', d.ghi_no ? NN.h('ncc_ghi_no') : '',
        d.paid_by === 'chu_xe' ? NN.h('pay_own') : ''].filter(Boolean).join(' · ');
      // dòng xuất bán (kind sales_order trên dòng chi): phần bán là SO nhiên liệu, giá vốn 607/1371 — không hiện như "cước → SO"
      const s2 = d.kind !== 'thu' && s.kind === 'sales_order' ? { ...s, kind: 'fuel_so' } : s;
      return dongTr('', d.kind === 'thu' ? NN.h('hs_thu_ngan') : MUC_LA[d.section] || '—', ten + (phu ? `<span class="phu">${phu}</span>` : ''), sl, tien, s2);
    }).join('');
    const dem = {}; (h.dong || []).forEach(d => { const k = (d.settlement || {}).state || 'open'; dem[k] = (dem[k] || 0) + 1; });
    return `<div class="tbl-wrap hs-dong"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('hs_cot_muc')}</th><th>${NN.h('item')}</th>
        <th class="num">${NN.h(coTien ? 'hs_cot_sl_gia' : 'qty')}</th>${coTien ? `<th class="num">${NN.h('amount_lak')}</th>` : ''}<th>${NN.h('hs_cot_xu_ly')}</th>
        <th>${NN.h('hs_cot_chung_tu')}</th></tr></thead>
      <tbody>${soNl + thue + rows || `<tr><td colspan="6" class="empty">${h.loi_dong ? `<span class="neg">${NN.h('hs_loi_dong')}</span>` : NN.h('no_data')}</td></tr>`}</tbody></table></div>
      <div class="hs-chu-dong">${['has_voucher', 'pending', 'open', 'not_payable'].map(k => `<span><span class="tag hs-${k}">${NN.h('hs_s_' + k)} · ${dem[k] || 0}</span> ${NN.h('hs_sg_' + k)}</span>`).join('')}</div>`;
  }

  async function veCt() {
    const ct = q('#ct2-ct'), x = D.ds.find(y => y.trip_id === chonId);
    if (tab === 'do') ghiDiaChi(new URLSearchParams({ thang: q('#ct2-thang').value || '', id: x ? x.trip_id : '' }));
    if (!x) { ct.innerHTML = `<div class="ct2-chon">${NN.h('kx_chon')}</div>`; return; }
    const h = CT[x.trip_id];
    const nhom = ghepNL(h ? h.nhom : x.nhom, NL[x.trip_id]);
    const coDong = h && h.dong ? h.dong.length + (h.thue ? 1 : 0) : null;
    const nut = [
      duocVao('phieu-xuat-xe') ? `<button type="button" class="btn sm" data-mo="phieu">${NN.h('open_slip')}</button>` : '',
      duocVao('but-toan-cho') ? `<button type="button" class="btn sm" data-mo="bt">${NN.h('hs_bt_cua_phieu')}</button>` : '',
      x.company === 'joint' && duocVao('tat-toan-doi-tac') ? `<button type="button" class="btn sm" data-mo="ttdt">${NN.h('nav_tt_doi_tac')}</button>` : '',
    ].join('');
    const coNhom = NHOM.filter(k => nhom[k] && nhom[k].muc !== 'khong'), khong = NHOM.filter(k => !nhom[k] || nhom[k].muc === 'khong');
    const dem = {}; coNhom.forEach(k => { dem[nhom[k].muc] = (dem[nhom[k].muc] || 0) + 1; });
    const than = tabCt === 'dong'
      ? (h ? bangDong(h) : `<div class="ct2-chon">${NN.h('loading')}</div>`)
      : `<div class="hs-luoi">${coNhom.map(k => theNhom(k, nhom[k])).join('')}
          ${khong.length ? `<div class="hs-khong"><span>${NN.h('hs_khong_phat_sinh')}:</span>${khong.map(k => `<span class="tag">${NN.h('hs_g_' + k)}</span>`).join('')}</div>` : ''}</div>`;
    ct.innerHTML = `<div class="ct2-dau"><div><h3>${esc(x.doc_no)}</h3>
        <div class="phu"><span lang="lo">${esc(x.customer_name || '')}</span>${x.origin || x.destination ? ` · <span lang="lo">${esc(x.origin || '—')} → ${esc(x.destination || '—')}</span>` : ''}</div>
        <div class="phu">${esc(x.truck_no || '')} · <span lang="lo">${esc(x.driver_name || '')}</span>${x.company === 'joint' ? ' · ' + NN.h('co_joint') + ' <span lang="lo">' + esc(x.owner_name || '') + '</span>' : ' · ' + NN.h('co_epl')}
          · ${x.locked ? NN.h('s_locked') + (x.locked_at ? ' ' + EPL.ngay(x.locked_at) : '') : NN.h('hs_chua_khoa')}</div></div>
        <div class="nut no-print">${nut}</div></div>
      <div class="hs-tab no-print"><button type="button" data-tct="nhom" class="${tabCt === 'nhom' ? 'on' : ''}">${NN.h('hs_tab_nhom')}<b>${coNhom.length}</b></button>
        <button type="button" data-tct="dong" class="${tabCt === 'dong' ? 'on' : ''}">${NN.h('hs_tab_dong')}${coDong != null ? `<b>${coDong}</b>` : ''}</button>
        <span class="grow"></span><span class="tom">${MUC.filter(m => dem[m]).map(m => `${dem[m]} ${esc(NN.t('hs_m_' + m).toLowerCase())}`).join(' · ')}</span></div>
      <div class="ct2-cuon">${than}</div>`;
    ct.querySelectorAll('[data-tct]').forEach(b => b.addEventListener('click', () => { tabCt = b.dataset.tct; veCt(); }));
    ct.querySelectorAll('[data-mo]').forEach(b => b.addEventListener('click', () => {
      const m = b.dataset.mo;
      if (m === 'phieu') EPL.di('phieu-xuat-xe', { id: x.trip_id });
      else if (m === 'bt') EPL.di('but-toan-cho', { trip_id: x.trip_id, doc: x.doc_no });
      else EPL.di('tat-toan-doi-tac', { ky: (x.doc_date || '').slice(0, 7), owner_id: x.owner_id || '' });
    }));
    ct.querySelectorAll('a[data-bt]').forEach(a => a.addEventListener('click', () => EPL.di('but-toan-cho', { trip_id: x.trip_id, doc: x.doc_no, id: a.dataset.bt })));
    datCao();
    // nạp hồ sơ đầy đủ (từng dòng tiền) và SO nhiên liệu — xong thì vẽ lại nếu vẫn đang xem DO này
    const id = x.trip_id;
    const viec = [];
    if (!h) viec.push(API.get('/api/ho-so-do/' + encodeURIComponent(id)).then(r => { CT[id] = r; }, e => { EPL.baoLoi(e); CT[id] = { nhom: x.nhom, dong: [], thay_tien_chi: D.thay_tien_chi }; }));
    if (!(id in NL) && x.company === 'joint' && ((x.nhom || {}).so_nl || {}).sap_co) viec.push(taiNL(x));
    if (!viec.length) return;
    await Promise.all(viec);
    if (chonId === id && root && root.isConnected && tab === 'do') veCt();
  }

  /* Bảng cao VỪA cửa sổ (rà 01/10): đo từ đầu khung bảng của tab đang mở tới đáy cửa sổ, trừ lề đáy trang và dòng chú thích
   * dưới bảng, đặt vào --ct-cao (bảng) và --ct-cao-phai (khung phải). Toạ độ là px màn hình, px CSS bên trong .app (zoom
   * --ty-le) nên chia. */
  let henCao = null;
  function datCao() {
    const w = root && root.querySelector(tab === 'so' ? '#ct-so-ct .tbl-wrap' : '.ct2-trai .tbl-wrap');
    if (!w || !w.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const chu = tab === 'so' ? null : root.querySelector('.ct2-chu');
    const duoi = chu ? chu.getBoundingClientRect().height + 8 * tl : 0;
    const dinh = w.getBoundingClientRect().top + window.scrollY;
    const cao = (window.innerHeight - dinh - le - duoi) / tl;
    root.style.setProperty('--ct-cao', Math.max(260, Math.floor(cao)) + 'px');
    const p = root.querySelector('.ct2-phai');
    if (p && tab === 'do') {
      const top = p.getBoundingClientRect().top + window.scrollY;
      p.style.maxHeight = Math.max(300, Math.floor((window.innerHeight - top - le) / tl)) + 'px';
    }
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  let LUOT = 0;                // lượt tải mới nhất — lượt cũ (đang tự sang tháng) về sau thì không vẽ đè
  async function taiDo() {
    const luot = ++LUOT;
    const thang = q('#ct2-thang').value || thangNay();
    const th = new URLSearchParams({ thang });
    if (tim) th.set('q', tim);
    let duoc = true, ve;
    try { ve = await API.get('/api/ho-so-do?' + th.toString()); } catch (e) { ve = { ds: [] }; duoc = false; if (luot === LUOT) EPL.baoLoi(e); }
    if (luot !== LUOT) return;
    D = ve; GAN = null;
    Object.keys(CT).forEach(k => { if (k !== GIU_CT) delete CT[k]; });   // tải lại là đọc lại — trừ hồ sơ vừa nạp lúc vào màn
    GIU_CT = null;
    if (duoc && !D.ds.length) {
      const r = await thangGan(thang, tim ? { q: tim } : {});
      if (luot !== LUOT) return;
      GAN = r.co ? null : r.gan;
      if (TU_DONG && GAN) { TU_DONG = false; BAO = { trong: thang, xem: GAN }; q('#ct2-thang').value = GAN; return taiDo(); }
    }
    TU_DONG = false;
    const ds = dsLoc();
    if (!ds.some(x => x.trip_id === chonId)) chonId = ds[0] ? ds[0].trip_id : null;
    veBang(); veCt();
  }

  /* ---------------------------------------------------------------- Sổ chứng từ (in / xem / định khoản, đối chiếu tay) */
  function veSoTong(tong) {
    q('#ct-so-tong').innerHTML = Object.keys(tong).length ? SO_LOAI.filter(l => tong[l.ma]).map(l => {
      const t = tong[l.ma];
      return `<button type="button" class="o ${soLoaiChon === l.ma ? 'chon' : ''}" data-loai="${l.ma}"><b>${esc(l.ma)}</b>${tenLoai(l.ma, l.ten, l.ten_lo)}
        <div><span class="n">${t.so_to}</span> ${NN.h('ct_so_to').toLowerCase()} · <span class="n">${so(t.tien_lak)}</span> LAK${t.chua_day ? ` · <span class="c">${t.chua_day} ${NN.h('ct_chua_day').toLowerCase()}</span>` : ''}</div></button>`;
    }).join('') : '';
    q('#ct-so-tong').querySelectorAll('[data-loai]').forEach(b => b.addEventListener('click', () => { soLoaiChon = soLoaiChon === b.dataset.loai ? '' : b.dataset.loai; q('#ct-so-loai').value = soLoaiChon; veSo(); }));
  }
  /** Hai mã bên kế toán cấp (hàng khách gửi · giá vốn hàng bán) — gõ ở đây là mọi tờ sinh từ đó mang mã, không sửa mã nguồn.
   *  Địa chỉ / khoá trang kế toán tạm đã bỏ (01/10). Đường mới /api/kho-tam/cau-hinh; máy chủ cũ chỉ có /api/ke-toan/cau-hinh. */
  async function goiCauHinh(phuong, than) {
    const goi = (d) => (phuong === 'put' ? API.put(d, than) : API.get(d));
    try { return await goi('/api/kho-tam/cau-hinh'); } catch (e) { if (e.status !== 404 && e.status !== 405) throw e; }
    return goi('/api/ke-toan/cau-hinh');
  }
  async function moCauHinh() {
    let hien = {}; try { hien = await goiCauHinh('get'); } catch (e) { hien = {}; }
    const v = await EPL.hopNhap(NN.t('ct_cau_hinh'), [
      { id: 'ma_hang_khach_gui', label: 'ct_ma_hang_gui', value: hien.ma_hang_khach_gui || '' },
      { id: 'ma_gia_von', label: 'ct_ma_gia_von', value: hien.ma_gia_von || '' },
    ], NN.t('save'));
    if (!v) return;
    try { await goiCauHinh('put', { ma_hang_khach_gui: v.ma_hang_khach_gui, ma_gia_von: v.ma_gia_von }); EPL.toast(NN.t('saved'), 'ok'); }
    catch (e) { EPL.baoLoi(e); }
  }

  async function veSo() {
    const th = new URLSearchParams();
    if (soLoaiChon) th.set('loai', soLoaiChon);
    if (q('#ct-so-tu').value) th.set('tu', q('#ct-so-tu').value);
    if (q('#ct-so-den').value) th.set('den', q('#ct-so-den').value);
    if (q('#ct-so-chua').checked) th.set('chua_day', '1');
    let r;
    try { r = await API.get('/api/chung-tu?' + th.toString()); } catch (e) { q('#ct-so-than').innerHTML = `<tr><td colspan="10" class="empty neg">${esc(e.message)}</td></tr>`; return; }
    veSoTong(r.tong);
    datCao();
    const tk = (ma, ten) => ma ? `<span class="acct" title="${esc(ten || '')}">${esc(ma)}</span>` : `<span class="muted small" title="${esc(ten || '')}">?</span>`;
    const suaDuoc = AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash');   // đánh dấu đối chiếu tay
    q('#ct-so-than').innerHTML = r.ds.length ? r.ds.map(c => `<tr class="${c.da_day && c.loai !== 'PDT' ? 'da-day' : ''}" data-id="${c.id}">
      <td class="mono">${esc(c.so)}</td><td>${EPL.ngay(c.ngay)}</td>
      <td><b>${esc(c.loai)}</b><div class="small muted">${tenLoai(c.loai, c.loai_ten, c.loai_ten_lo)}</div></td>
      <td>${c.trip_id ? `<a href="#/phieu-xuat-xe?id=${esc(c.trip_id)}" class="mono">${esc(c.trip_doc_no || '')}</a>` : '<span class="muted">—</span>'}</td>
      <td lang="lo">${esc(c.doi_tuong_ten || '')}<div class="small muted">${DOI_TUONG[c.doi_tuong_loai] ? NN.h(DOI_TUONG[c.doi_tuong_loai]) : esc(c.doi_tuong_loai || '')}</div></td>
      <td class="num">${c.tien == null ? '—' : EPL.tien(c.tien, c.tien_te)}</td>
      <td class="num">${c.tien_lak == null ? '—' : so(c.tien_lak)}</td>
      <td>${c.no || c.co || c.no_ten ? `${tk(c.no, c.no_ten)} / ${tk(c.co, c.co_ten)}` : '<span class="muted">—</span>'}</td>
      <td class="small">${esc(c.mo_ta || '')}<div class="muted">${esc(c.by_user || '')}</div></td>
      <td class="small">${c.loai === 'PDT' ? '<span class="muted">—</span>' : c.da_day ? `✓ ${NN.h('ct_da_day')}` : `<span class="muted">${NN.h('ct_chua_day')}</span>`}</td>
      <td class="no-print">${c.loai === 'PDT' ? '' : suaDuoc ? `<button type="button" class="btn sm ${c.da_day ? 'quiet' : ''}" data-day="${c.id}" data-gia-tri="${c.da_day ? 0 : 1}">${NN.h(c.da_day ? 'ct_mo_lai' : 'ct_danh_dau')}</button>` : (c.da_day ? '✓' : '')}</td>
    </tr>`).join('') : `<tr><td colspan="11" class="empty small">${NN.h('ct_khong_co')}</td></tr>`;
    q('#ct-so-than').querySelectorAll('[data-day]').forEach(b => b.addEventListener('click', async () => {
      try { await API.post(`/api/chung-tu/${b.dataset.day}/da-day`, { da_day: b.dataset.giaTri === '1' }); await veSo(); } catch (e) { EPL.baoLoi(e); }
    }));
  }

  /* ---------------------------------------------------------------- hai tab */
  async function doiTab(t) {
    tab = t === 'so' && XEM_SO.includes(AUTH.role) ? 'so' : 'do';
    root.querySelectorAll('#ct2-tab button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    root.querySelectorAll('.ct2-khi-do').forEach(el => { el.hidden = tab !== 'do'; });
    q('#ct2-do').hidden = tab !== 'do'; q('#ct-so-ct').hidden = tab !== 'so';
    if (tab === 'so') {
      ghiDiaChi(new URLSearchParams({ tab: 'so', loai: soLoaiChon || '' }));
      // danh mục loại nạp một lần trong phiên, nhưng ô chọn thì của GỐC MÀN MỚI mỗi lần vào màn — luôn vẽ lại
      if (!SO_LOAI.length) SO_LOAI = await API.get('/api/chung-tu/loai').catch(() => []);
      veOLoai();
      await veSo();
    } else await taiDo();
  }

  /** Chữ thuần của một nhóm cho tệp Excel: "PTU-… · Đã cấp → 1368-CTR-… · Đã chi". */
  function chuNhom(g) {
    if (!g || g.muc === 'khong') return '';
    const t = (it) => [it.so || '', it.loai === 'gl' ? NN.t('btc_nguon_' + it.nguon) : ''].filter(Boolean).join(' ');
    const em = g.em.map(t).filter(Boolean).join('; '), kt = g.kt.map(t).filter(Boolean).join('; ');
    return NN.t('hs_m_' + g.muc) + (em || kt ? ` · ${em || '—'} → ${kt || '—'}` : '');
  }

  EPL.modules['chung-tu'] = {
    async init(r, ctx) {
      root = r; D = { ds: [] }; tim = ''; loc = ''; chonId = null; tabCt = 'nhom';
      Object.keys(CT).forEach(k => delete CT[k]); Object.keys(NL).forEach(k => delete NL[k]);
      const t = (ctx && ctx.tham) || {};
      // đường cũ ?tab=chi / ?tab=linh (tờ in) → màn Phiếu đề nghị chi
      if (t.tab === 'chi') return EPL.di('de-nghi-chi', { id: t.id || '', v: t.v || '' });
      if (t.tab === 'linh') return EPL.di('de-nghi-xuat-kho', { id: t.id || '', v: t.v || '' });
      // mở từ màn khác chỉ kèm mã phiếu (Bút toán chờ gửi, Tất toán…): hỏi hồ sơ trước để biết DO thuộc tháng nào
      if (t.id && !t.thang) {
        try { const h = await API.get('/api/ho-so-do/' + encodeURIComponent(t.id)); CT[t.id] = h; GIU_CT = t.id; if (h && h.do && h.do.doc_date) t.thang = h.do.doc_date.slice(0, 7); }
        catch (e) { /* không có thì vào như thường */ }
      }
      if (t.thang) q('#ct2-thang').value = t.thang;
      BAO = null; GAN = null; TU_DONG = !t.thang;
      if (t.id) chonId = t.id;
      if (!XEM_SO.includes(AUTH.role)) q('#ct2-tab button[data-tab="so"]').hidden = true;
      q('#ct-cau-hinh').hidden = AUTH.role !== 'admin';
      q('#ct-cau-hinh').addEventListener('click', moCauHinh);
      root.querySelectorAll('#ct2-tab button').forEach(b => b.addEventListener('click', () => doiTab(b.dataset.tab)));
      q('#ct2-thang').addEventListener('change', (e) => chonThang(e.target.value));
      q('#ct2-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); taiDo(); }, 300); });
      q('#ct-so-loai').addEventListener('change', e => { soLoaiChon = e.target.value; veSo(); });
      ['ct-so-tu', 'ct-so-den', 'ct-so-chua'].forEach(id => q('#' + id).addEventListener('change', veSo));
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      if (t.loai) soLoaiChon = String(t.loai).toUpperCase();
      await doiTab(t.tab === 'so' ? 'so' : 'do');
    },
    onLang() { if (root) { if (SO_LOAI.length) veOLoai(); if (tab === 'so') veSo(); else { veBang(); veCt(); } } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      if (tab === 'so') return EPL._xlsx.sheetMacDinh(root);
      const T = NN.t;
      const sh = [EPL.xuatSheet(T('hs_tab'), ['DO', T('do_kind'), T('c_date'), T('truck_no'), T('driver'), T('customer'), T('route'),
        ...NHOM.map(k => T('hs_g_' + k))],
        dsLoc().map(x => [x.doc_no, T(x.kind === 'gom' ? 'dn_gom' : 'dn_giao'), EPL.oNgay(x.doc_date), x.truck_no || '', x.driver_name || '', x.customer_name || '',
          (x.origin || '') + ' → ' + (x.destination || ''), ...NHOM.map(k => chuNhom((x.nhom || {})[k]))]))];
      const h = CT[chonId], x = D.ds.find(y => y.trip_id === chonId);
      if (h && x && (h.dong || []).length) {
        sh.push(EPL.xuatSheet(x.doc_no, [T('hs_cot_muc'), T('item'), T('qty'), T('unit_price'), T('cur'), T('amount_lak'), T('hs_cot_xu_ly'), T('hs_cot_chung_tu'), T('status')],
          h.dong.map(d => { const s = d.settlement || {}; return [d.kind === 'thu' ? T('hs_thu_ngan') : d.section || '', d.kind === 'thu' ? T('hs_cuoc') : (d.name || ''),
            EPL.oSo(d.qty, 2), d.unit_price == null ? null : EPL.oSo(d.unit_price, 2), d.currency || '', d.amount_lak == null ? null : EPL.oSo(d.amount_lak),
            T(KIND[s.kind] || 'hs_x_khac'), [s.doc_no, s.ref_no].filter(Boolean).join(' · '), T('hs_s_' + (s.state || 'open'))]; })));
      }
      return sh;
    },
  };
})();
