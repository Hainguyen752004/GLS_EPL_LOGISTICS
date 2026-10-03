/* Tất toán đối tác — trả chủ xe liên kết (xe thuê) theo kỳ, dạng BẢNG TÍNH từng chuyến (chủ dự án 02/10/2026).
 *
 *   Trả đối tác = tiền thuê − phí quản lý − cắt quá tải − tạm ứng EPL đưa − nợ NCC EPL trả thay − SO nhiên liệu còn nợ.
 * Lập đề nghị: máy tự cấn trừ SO nhiên liệu (TKN bên hệ kế toán anh Tune) rồi lập phiếu chi "Chi khác" phần còn lại đứng tên đối
 * tác; thủ quỹ chi và ghi sổ ở đó, màn này đọc lại. Đối tác tự mua tự trả hết thì trả đủ tiền thuê. Số tính ở máy chủ, không gõ tay.
 *
 * Trái: đối tác của kỳ (tổng, trạng thái). Phải: một đối tác — công thức bằng số, bảng tính từng chuyến (mở từng chuyến xem dòng
 * tạm ứng · nợ NCC · dầu bán), dòng tổng; tích chuyến → "Lập đề nghị trả". Tab Lịch sử đề nghị: TCX, cấn trừ TKN, phiếu chi.
 * API: GET /api/tat-toan-doi-tac?ky=YYYY-MM[&owner_id=] (chưa có → "chưa có dữ liệu", màn không vỡ) · lập: POST
 * /api/owners/{id}/de-nghi-tra {trip_ids, phuong_thuc} · bỏ / hỏi lại: POST /api/chi-chu-xe/{id}/huy | cap-nhat (cùng đường
 * màn Xe liên kết → "Trả qua kế toán"). Lập / bỏ: KT Thu/Chi VC và Sếp (routes/chu_xe.DE_NGHI_TRA).
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, BANG = null, CHUA_CO = false, CHON = null, loc = '', tim = '', hen = null, LUOT = 0, tab = 'bang';
  const CT = {};                  // owner_id → bảng tính của đối tác (có chi_tiet)
  const MO = new Set();           // trip_id đang mở ra
  const TICH = new Set();         // trip_id đã tích để lập đề nghị
  const q = (s) => root.querySelector(s);
  const lapDuoc = () => AUTH.la('acct');                 // Sếp luôn qua (AUTH.la)
  const LOC = ['', 'chua_lap', 'cho_so_nhien_lieu', 'cho_thu_quy', 'da_tra', 'loi'];
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');
  const t$ = (v, ma) => (v == null || v === '' ? '—' : EPL.tien(v, ma));
  const lak = (v) => (v == null || v === '' ? '—' : so(v) + ' LAK');
  const tagTT = (k, pre) => `<span class="tag ttd-${esc(k || 'chua_lap')}">${NN.h(pre + (k || 'chua_lap'))}</span>`;
  const TT_DN = { da_gui: 'tt_cho_chi', da_chi: 'ck_da_chi_ngan', loi: 'ck_loi_ngan', huy: 'cx_da_bo' };
  const tagDN = (s) => `<span class="tag ttd-${esc(s)}">${NN.h(TT_DN[s] || 'tt_cho_chi')}</span>`;
  const NL_TT = { chua_tao: 'hs_nl_chua_tao', da_tao: 'hs_nl_da_tao', da_thu: 'dt_st_da_thu', can_tru: 'hs_nl_can_tru' };
  const tagNL = (s) => `<span class="tag ttd-${esc(s || 'chua_tao')}">${NN.h(NL_TT[s] || 'hs_nl_chua_tao')}</span>`;
  const tong = (ds, f) => ds.reduce((a, x) => a + (Number(f(x)) || 0), 0);
  /** Tên khoản theo tiếng đang xem: có item_key thì dịch theo từ điển; có tên Lào (khoan_lo / name_lo) thì dùng khi xem tiếng Lào;
   *  không thì tên máy chủ gửi (UAT 03/10: máy chủ mới gửi tên Việt). */
  const tenKhoan = (d, k) => (d.item_key && (window.EPL_TU_DIEN || {})[d.item_key] ? NN.t(d.item_key)
    : (NN.lang === 'lo' && (d[k + '_lo'] || d.name_lo)) || d[k] || '');


  /* ---------------------------------------------------------------- lọc + dải tổng */
  function dsLoc() {
    const t = tim.toLowerCase();
    return ((BANG && BANG.doi_tac) || []).filter(d => (!loc || d.trang_thai === loc)
      && (!t || [(d.ten || ''), (d.ma_ke_toan || '')].join(' ').toLowerCase().includes(t)));
  }
  function veLoc() {
    const ds = (BANG && BANG.doi_tac) || [];
    q('#ttd-loc').innerHTML = LOC.map(k => `<button type="button" data-loc="${k}" class="${loc === k ? 'on' : ''}">
      <span>${NN.h(k === 'loi' ? 'hs_loc_loi' : k ? 'ttd_st_' + k : 'all')}</span><b>${k ? ds.filter(d => d.trang_thai === k).length : ds.length}</b></button>`).join('');
    q('#ttd-loc').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veHet(); }));
  }
  function veGioiThieu() {
    const b = (k, kq) => `<b class="${kq ? 'kq' : ''}">${NN.h(k)}</b>`;
    q('#ttd-gt').innerHTML = `<span class="ct">${b('ttd_c_thue')}<i>−</i>${b('ttd_c_phi')}<i>−</i>${b('ttd_c_qua_tai')}<i>−</i>${b('ttd_c_tam_ung')}<i>−</i>${b('ttd_c_no_ncc')}<i>−</i>${b('ttd_c_nhien_lieu')}<i>=</i>${b('ttd_c_con_tra', true)}</span>
      <span class="them">${NN.h('ttd_gioi_thieu')}</span>`;
  }
  function veTong() {
    const t = (BANG && BANG.tong) || {};
    const o = (k, v, c) => `<div class="o ${c || ''}"><div class="l">${NN.h(k)}</div><div class="v">${v}</div></div>`;
    const l = (v) => (v == null ? '—' : `${so(v)}<small>LAK</small>`);
    q('#ttd-tong').innerHTML = CHUA_CO || !BANG ? '' : [
      o('ttd_so_doi_tac', t.so_doi_tac != null ? so(t.so_doi_tac) : so(((BANG && BANG.doi_tac) || []).length)),
      o('ttd_c_thue', l(t.tien_thue_lak)), o('ttd_c_phi', l(t.phi_lak), 'tru'), o('ttd_c_qua_tai', l(t.qua_tai_lak), 'tru'),
      o('ttd_c_tam_ung', l(t.tam_ung_lak), 'tru'), o('ttd_c_no_ncc', l(t.no_ncc_lak), 'tru'),
      o('ttd_c_nhien_lieu_no', l(t.nhien_lieu_con_no_lak != null ? t.nhien_lieu_con_no_lak : t.nhien_lieu_lak), 'tru'),
      o('ttd_c_con_tra', l(t.con_tra_lak), 'kq'), o('ttd_da_tra', l(t.da_tra_lak)),
    ].join('');
  }

  /* ---------------------------------------------------------------- danh sách đối tác */
  function veDs() {
    const o = q('#ttd-ds');
    if (CHUA_CO) { o.innerHTML = `<div class="ttd-trong">${NN.h('ttd_chua_co')}</div>`; return; }
    const ds = dsLoc();
    o.innerHTML = ds.length ? ds.map(d => `<button type="button" class="ttd-o st-${esc(d.trang_thai || 'chua_lap')} ${CHON === d.owner_id ? 'chon' : ''}" data-id="${esc(d.owner_id)}">
        <span class="ten" lang="lo">${esc(d.ten || '—')}</span>
        <span class="tien">${t$(d.con_tra, d.tien_te)}</span>
        <span class="phu">${d.ma_ke_toan ? esc(d.ma_ke_toan) + ' · ' : ''}${so(d.so_phieu || 0)} ${esc(NN.t('cx_phieu'))}${d.tien_te && d.tien_te !== 'LAK' && d.con_tra_lak != null ? ' · ≈ ' + so(d.con_tra_lak) + ' LAK' : ''}</span>
        <span class="tt">${tagTT(d.trang_thai, 'ttd_st_')}</span></button>`).join('')
      : `<div class="ttd-trong">${NN.h(BANG && (BANG.doi_tac || []).length ? 'loc_trong' : 'ttd_trong_ky')}</div>`;
    o.querySelectorAll('[data-id]').forEach(b => b.addEventListener('click', () => { CHON = b.dataset.id; TICH.clear(); MO.clear(); veDs(); veXem(); }));
  }

  /* ---------------------------------------------------------------- một đối tác */
  function ghiDiaChi() {
    if (!root || !root.isConnected) return;
    const ts = new URLSearchParams({ ky: q('#ttd-ky').value || '', owner_id: CHON || '' });
    [...ts.keys()].forEach(k => { if (!ts.get(k)) ts.delete(k); });
    const moi = '#/tat-toan-doi-tac' + (ts.toString() ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }
  const chuyenCua = (oid) => {
    const r = CT[oid];
    const ds = (r && r.chi_tiet) || [];
    return ds.filter(c => !c.owner_id || c.owner_id === oid);
  };
  const tichDuoc = (c) => lapDuoc() && (c.trang_thai_tra || 'chua_tra') === 'chua_tra';

  function khoiMo(c) {
    const tu = c.tam_ung || {}, ncc = c.no_ncc || [], nl = c.nhien_lieu || {};
    const tuDong = (tu.dong || []).map(d => `<tr><td lang="lo">${esc(tenKhoan(d, 'khoan'))}</td><td class="num">${so(d.sl, Number.isInteger(+d.sl) ? 0 : 2)} × ${t$(d.don_gia, d.tien_te)}</td><td class="num">${lak(d.tien_lak)}</td></tr>`).join('');
    const nccDong = ncc.map(d => `<tr><td lang="lo">${esc(tenKhoan(d, 'khoan'))}<div class="muted" lang="lo">${esc(d.nha_cung_cap || '')}</div></td><td class="num">${lak(d.tien_lak)}</td>
      <td class="mono">${esc(d.but_toan || '—')}</td></tr>`).join('');
    const nlDong = (nl.dong || []).map(d => `<tr><td lang="lo">${esc(tenKhoan(d, 'mat_hang'))}</td><td class="num">${so(d.lit, 0)} L × ${so(d.gia_ban)}</td><td class="num">${lak(d.tien_lak)}</td>
      <td class="num muted">${d.gia_von_lak != null ? NN.h('ttd_gia_von') + ' ' + so(d.gia_von_lak) : ''}</td></tr>`).join('');
    return `<tr class="ttd-mo"><td colspan="10"><div class="ttd-mo-boc"><div class="ttd-ba">
      <div class="ttd-khoi"><h5>${NN.h('ttd_c_tam_ung')}<span class="grow"></span>${tu.so_ptu ? `<span class="mono">${esc(tu.so_ptu)}</span>` : ''}</h5>
        ${tu.phieu_chi ? `<div class="rong">${NN.h('ttd_phieu_chi')}: <span class="mono">${esc(tu.phieu_chi)}</span></div>` : ''}
        ${tuDong ? `<table><tbody>${tuDong}</tbody></table>` : `<div class="rong">${NN.h(tu.tien_lak ? 'ttd_khong_dong' : 'ttd_khong_tam_ung')}</div>`}</div>
      <div class="ttd-khoi"><h5>${NN.h('ttd_c_no_ncc')}<span class="grow"></span>${ncc.length ? lak(tong(ncc, d => d.tien_lak)) : ''}</h5>
        ${nccDong ? `<table><tbody>${nccDong}</tbody></table>` : `<div class="rong">${NN.h('ttd_khong_no_ncc')}</div>`}</div>
      <div class="ttd-khoi"><h5>${NN.h('ttd_dau_ban')}<span class="grow"></span>${nl.order_code ? `<span class="mono">${esc(nl.order_code)}</span> ` : ''}${nl.trang_thai ? tagNL(nl.trang_thai) : ''}</h5>
        ${nlDong ? `<table><tbody>${nlDong}</tbody></table>` : `<div class="rong">${NN.h('ttd_khong_dau')}</div>`}
        ${nl.tien_lak ? `<div class="rong">${NN.h('collected')} ${lak(nl.da_thu_lak || 0)} · ${NN.h('hs_nl_con_no')} <b>${lak(nl.con_no_lak || 0)}</b></div>` : ''}</div>
    </div></div></td></tr>`;
  }

  function bangChuyen(d, ds) {
    const ma = d.tien_te || 'LAK';
    const coTich = ds.some(tichDuoc);
    const rows = ds.map(c => {
      const tu = c.tam_ung || {}, nl = c.nhien_lieu || {}, ncc = c.no_ncc || [];
      const nccLak = tong(ncc, x => x.tien_lak), m$ = c.tien_te || ma;
      const mo = MO.has(c.trip_id);
      return `<tr class="dong-chuyen ${mo ? 'mo' : ''} ${esc(c.trang_thai_tra || '')}" data-trip="${esc(c.trip_id)}">
        <td class="no-print">${tichDuoc(c) ? `<input type="checkbox" data-tich="${esc(c.trip_id)}" ${TICH.has(c.trip_id) ? 'checked' : ''} aria-label="✓">`
          : lapDuoc() && c.trang_thai_tra === 'trong_de_nghi' ? `<input type="checkbox" disabled class="ttd-tich-khoa" title="${esc(NN.t('ttd_khoa_tich', { so: c.so_de_nghi || '' }))}" aria-label="${esc(NN.t('ttd_khoa_tich', { so: c.so_de_nghi || '' }))}">` : ''}</td>
        <td><span class="mui">▸</span> <span class="mono">${esc(c.doc_no || '')}</span><span class="phu">${EPL.ngay(c.ngay)}</span></td>
        <td class="tuyen" lang="lo">${esc(c.tuyen || '—')}<span class="phu">${esc(c.xe || '')}${c.tai_xe ? ' · ' + esc(c.tai_xe) : ''}</span></td>
        <td class="num">${t$(c.tien_thue, m$)}<span class="phu">${so(c.tan_tinh, 2)} t × ${t$(c.gia_thue, m$)}</span></td>
        <td class="num tru">${c.phi ? '− ' + t$(c.phi, m$) : '—'}${c.phi_pct != null ? `<span class="phu">${so(c.phi_pct, 1)} %</span>` : ''}</td>
        <td class="num tru">${c.qua_tai ? '− ' + t$(c.qua_tai, m$) : '—'}${c.qua_tai_t ? `<span class="phu">${so(c.qua_tai_t, 2)} t</span>` : ''}</td>
        <td class="num tru">${tu.tien || tu.tien_lak ? '− ' + (tu.tien ? t$(tu.tien, m$) : lak(tu.tien_lak)) : '—'}${tu.tien != null && m$ !== 'LAK' && tu.tien_lak ? `<span class="phu">${lak(tu.tien_lak)}</span>` : ''}</td>
        <td class="num tru">${nccLak ? '− ' + lak(nccLak) : '—'}</td>
        <td class="num tru">${nl.con_no_lak ? '− ' + lak(nl.con_no_lak) : nl.tien_lak ? lak(0) : '—'}${nl.tien_lak ? `<span class="phu">${nl.order_code ? esc(nl.order_code) + ' · ' : ''}${NN.h(NL_TT[nl.trang_thai] || 'hs_nl_chua_tao')}</span>` : ''}</td>
        <td class="num kq">${t$(c.con_tra, m$)}${m$ !== 'LAK' && c.con_tra_lak != null ? `<span class="phu">≈ ${lak(c.con_tra_lak)}</span>` : ''}${c.can_tru_lak ? `<span class="phu">${NN.h('ttd_da_can_tru', { tien: lak(c.can_tru_lak) })}</span>` : ''}
          <span class="phu tt">${tagTT(c.trang_thai_tra || 'chua_tra', 'ttd_tr_')}${c.so_de_nghi ? ` <span class="mono">${esc(c.so_de_nghi)}</span>` : ''}</span></td></tr>`
        + (mo ? khoiMo(c) : '');
    }).join('');
    const tt = (f) => tong(ds, f);
    const foot = ds.length ? `<tfoot><tr><td class="no-print"></td><td>${NN.h('total')}</td><td>${so(ds.length)} ${esc(NN.t('cx_phieu'))} · ${so(tt(c => c.tan_tinh), 2)} t</td>
      <td class="num">${t$(tt(c => c.tien_thue), ma)}</td>
      <td class="num tru">− ${t$(tt(c => c.phi), ma)}</td><td class="num tru">− ${t$(tt(c => c.qua_tai), ma)}</td>
      <td class="num tru">− ${t$(tt(c => (c.tam_ung || {}).tien), ma)}</td><td class="num tru">− ${lak(tt(c => tong(c.no_ncc || [], x => x.tien_lak)))}</td>
      <td class="num tru">− ${lak(tt(c => (c.nhien_lieu || {}).con_no_lak))}</td><td class="num kq">${t$(tt(c => c.con_tra), ma)}</td></tr></tfoot>` : '';
    return `<div class="tbl-wrap ttd-bang"><table class="tbl tbl-compact ttd-co-dinh"><colgroup><col class="c-chk no-print"><col class="c-so"><col class="c-tuyen">
        <col class="c-thue"><col class="c-phi"><col class="c-qt"><col class="c-tu"><col class="c-ncc"><col class="c-nl"><col class="c-tra"></colgroup><thead><tr>
        <th class="no-print">${coTich ? `<input type="checkbox" id="ttd-tich-het" aria-label="✓" ${ds.filter(tichDuoc).every(c => TICH.has(c.trip_id)) && TICH.size ? 'checked' : ''}>` : ''}</th>
        <th>${NN.h('doc_no')}<span class="phu">${NN.h('c_date')}</span></th><th>${NN.h('route')} · ${NN.h('truck_no')}</th>
        <th class="num">${NN.h('ttd_c_thue')}<span class="phu">${NN.h('ton')} × ${NN.h('ttd_gia_thue')}</span></th><th class="num">${NN.h('ttd_c_phi')}</th>
        <th class="num">${NN.h('ttd_c_qua_tai')}</th><th class="num">${NN.h('ttd_c_tam_ung')}</th><th class="num">${NN.h('ttd_c_no_ncc')}</th>
        <th class="num">${NN.h('ttd_nl_cot')}</th><th class="num">${NN.h('ttd_c_con_tra')}<span class="phu">${NN.h('status')}</span></th></tr></thead>
      <tbody>${rows || `<tr><td colspan="10" class="empty">${NN.h(CT[d.owner_id] ? 'ttd_khong_chuyen' : 'loading')}</td></tr>`}</tbody>${foot}</table></div>`;
  }

  function bangLichSu(d) {
    const dn = d.de_nghi || [];
    return `<div class="tbl-wrap ttd-bang"><table class="tbl tbl-compact" style="min-width:0"><thead><tr><th>${NN.h('ttd_so_dn')}</th><th>${NN.h('c_date')}</th>
        <th class="num">${NN.h('amount')}</th><th>${NN.h('ttd_can_tru')}</th><th>${NN.h('ttd_phieu_chi')}</th><th>${NN.h('status')}</th><th class="no-print"></th></tr></thead>
      <tbody>${dn.length ? dn.map((r, i) => `<tr><td class="mono">${esc(r.so || '')}</td><td>${EPL.ngay(r.ngay)}</td><td class="num">${t$(r.tien, r.tien_te || d.tien_te)}</td>
        <td class="ttd-ls-ct">${(r.can_tru || []).length ? r.can_tru.map(x => `<div><span class="mono">${esc(x.order_code || '')}</span>${x.so_tkn ? ` → <span class="mono">${esc(x.so_tkn)}</span>` : ''} · ${lak(x.tien)}${x.trang_thai && (NL_TT[x.trang_thai] || TT_DN[x.trang_thai]) ? ' · ' + esc(NN.t(NL_TT[x.trang_thai] || TT_DN[x.trang_thai])) : ''}</div>`).join('') : '<span class="muted">—</span>'}</td>
        <td class="mono">${esc(r.phieu_chi || '—')}</td><td class="ttd-ls-tt">${tagDN(r.trang_thai)}${r.loi ? `<div class="small neg ttd-ls-loi" title="${esc(r.loi)}">${esc(r.loi)}</div>` : ''}</td>
        <td class="no-print ttd-ls-nut">${r.trang_thai === 'da_gui' ? `<button type="button" class="btn sm" data-dn="cap-nhat" data-i="${i}">${NN.h('ck_cap_nhat')}</button>` : ''}
          ${lapDuoc() && r.trang_thai === 'loi' ? `<button type="button" class="btn sm warn" data-dn="gui-lai" data-i="${i}">${NN.h('ck_gui_lai')}</button>` : ''}
          ${lapDuoc() && ['da_gui', 'loi'].includes(r.trang_thai) ? `<button type="button" class="btn sm" data-dn="huy" data-i="${i}">${NN.h('cx_bo')}</button>` : ''}</td></tr>`).join('')
        : `<tr><td colspan="7" class="empty">${NN.h('ttd_chua_dn')}</td></tr>`}</tbody></table></div>`;
  }

  function veXem() {
    const o = q('#ttd-xem');
    ghiDiaChi();
    if (CHUA_CO) { o.innerHTML = `<div class="ttd-trong">${NN.h('ttd_chua_co_chi_tiet')}</div>`; return; }
    const d = ((BANG && BANG.doi_tac) || []).find(x => x.owner_id === CHON);
    if (!d) { o.innerHTML = `<div class="ttd-trong">${NN.h(BANG ? 'ttd_chon' : 'loading')}</div>`; return; }
    const ds = chuyenCua(d.owner_id), ma = d.tien_te || 'LAK';
    // chỉ giữ chuyến CÒN tích được: sau một lần lập hỏng, hai chuyến đã nằm trong đề nghị lỗi không được đếm vào nút «Lập đề nghị trả (n)»
    ds.forEach(c => { if (TICH.has(c.trip_id) && !tichDuoc(c)) TICH.delete(c.trip_id); });
    const chon = ds.filter(c => TICH.has(c.trip_id));
    const khoa = lapDuoc() ? ds.filter(c => c.trang_thai_tra === 'trong_de_nghi') : [];
    const soKhoa = [...new Set(khoa.map(c => c.so_de_nghi).filter(Boolean))].join(', ');
    const cong = [['ttd_c_thue', d.tien_thue], ['ttd_c_phi', d.phi], ['ttd_c_qua_tai', d.qua_tai], ['ttd_c_tam_ung', d.tam_ung], ['ttd_c_no_ncc', d.no_ncc],
      ['ttd_c_nhien_lieu', d.nhien_lieu_con_no != null ? d.nhien_lieu_con_no : d.nhien_lieu]];
    o.innerHTML = `<div class="ttd-dau">
        <div><h3 lang="lo">${esc(d.ten || '—')}</h3><div class="small muted">${d.ma_ke_toan ? esc(d.ma_ke_toan) + ' · ' : ''}${NN.h('ccy_hire')} ${esc(ma)} · ${NN.h('tt_period')} ${nhanThang(BANG.ky)}</div></div>
        <div class="grow"></div>${tagTT(d.trang_thai, 'ttd_st_')}
        ${lapDuoc() ? `<button type="button" class="btn primary no-print" id="ttd-lap" ${chon.length ? '' : 'disabled'}>${NN.h('ttd_lap', { n: chon.length })}</button>` : ''}
        ${EPL.manCuaVai(AUTH.role).some(m => m.id === 'xe-lien-ket') ? `<button type="button" class="btn no-print" id="ttd-xlk">${NN.h('nav_joint')}</button>` : ''}</div>
      <div class="ttd-cong">${cong.map(([k, v], i) => `${i ? '<i>−</i>' : ''}<span>${NN.h(k)} <b>${t$(v || 0, ma)}</b></span>`).join('')}<i>=</i>
        <span class="kq">${NN.h('ttd_c_con_tra')} ${t$(d.con_tra, ma)}</span>${ma !== 'LAK' && d.con_tra_lak != null ? `<span class="muted">≈ ${lak(d.con_tra_lak)}</span>` : ''}</div>
      <div class="ttd-tab no-print"><button type="button" data-tab="bang" class="${tab === 'bang' ? 'on' : ''}">${NN.h('ttd_tab_bang')}<b>${ds.length}</b></button>
        <button type="button" data-tab="ls" class="${tab === 'ls' ? 'on' : ''}">${NN.h('ttd_tab_ls')}<b>${(d.de_nghi || []).length}</b></button>
        <span class="grow"></span>
        ${tab === 'bang' && ds.length ? `<button type="button" class="btn sm quiet" id="ttd-mo-het">${NN.h(MO.size ? 'ttd_thu_het' : 'ttd_mo_het')}</button>` : ''}
        ${chon.length ? `<span class="chon">${NN.h('ttd_da_chon', { n: chon.length, tien: t$(tong(chon, c => c.con_tra), ma) })}</span>` : ''}</div>
      ${tab === 'bang' && khoa.length ? `<div class="ttd-khoa-dem no-print">${NN.h('ttd_khoa_dem', { n: khoa.length, so: soKhoa || '—' })}</div>` : ''}
      ${tab === 'bang' ? bangChuyen(d, ds) : bangLichSu(d)}
      ${tab === 'bang' ? `<div class="ttd-chu no-print"><span>${NN.h('ttd_goi_y_mo')}</span></div>` : ''}`;
    o.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; veXem(); }));
    o.querySelectorAll('tr.dong-chuyen').forEach(tr => tr.addEventListener('click', (e) => {
      if (e.target.closest('input, a, button')) return;
      const id = tr.dataset.trip; if (MO.has(id)) MO.delete(id); else MO.add(id); veXem();
    }));
    o.querySelectorAll('[data-tich]').forEach(c => c.addEventListener('change', () => { if (c.checked) TICH.add(c.dataset.tich); else TICH.delete(c.dataset.tich); veXem(); }));
    const het = o.querySelector('#ttd-tich-het');
    if (het) het.addEventListener('change', () => { ds.filter(tichDuoc).forEach(c => { if (het.checked) TICH.add(c.trip_id); else TICH.delete(c.trip_id); }); veXem(); });
    const moHet = o.querySelector('#ttd-mo-het');
    if (moHet) moHet.addEventListener('click', () => { if (MO.size) MO.clear(); else ds.forEach(c => MO.add(c.trip_id)); veXem(); });
    const lap = o.querySelector('#ttd-lap'); if (lap) lap.addEventListener('click', () => lapDeNghi(d, chon));
    const xlk = o.querySelector('#ttd-xlk'); if (xlk) xlk.addEventListener('click', () => EPL.di('xe-lien-ket'));
    o.querySelectorAll('[data-dn]').forEach(b => b.addEventListener('click', () => viecDN(d, (d.de_nghi || [])[+b.dataset.i], b.dataset.dn, b)));
    datCao();
    if (!CT[d.owner_id]) taiMot(d.owner_id);
  }

  /* ---------------------------------------------------------------- lập / bỏ đề nghị (đường của màn Xe liên kết) */
  async function lapDeNghi(d, chon) {
    if (!chon.length) return EPL.toast(NN.t('cx_chua_chon'), 'loi');
    const ma = d.tien_te || 'LAK';
    const nlNo = tong(chon, c => (c.nhien_lieu || {}).con_no_lak);
    const html = `<p>${NN.h('ttd_hoi_lap', { n: chon.length, ten: d.ten || '' })}</p>
      <div class="ttd-cong" style="margin:8px 0">${[['ttd_c_thue', tong(chon, c => c.tien_thue)], ['ttd_c_phi', tong(chon, c => c.phi)], ['ttd_c_qua_tai', tong(chon, c => c.qua_tai)],
        ['ttd_c_tam_ung', tong(chon, c => (c.tam_ung || {}).tien)]].map(([k, v], i) => `${i ? '<i>−</i>' : ''}<span>${NN.h(k)} <b>${t$(v, ma)}</b></span>`).join('')}
        <i>−</i><span>${NN.h('ttd_c_no_ncc')} <b>${lak(tong(chon, c => tong(c.no_ncc || [], x => x.tien_lak)))}</b></span>
        <i>−</i><span>${NN.h('ttd_c_nhien_lieu')} <b>${lak(nlNo)}</b></span><i>=</i><span class="kq">${t$(tong(chon, c => c.con_tra), ma)}</span></div>
      ${nlNo ? `<p class="small">${NN.h('ttd_hoi_can_tru', { tien: lak(nlNo) })}</p>` : ''}
      <div class="field"><label>${NN.h('cx_cach_tra')}</label><select id="ttd-pt"><option value="cash">${NN.h('cx_tien_mat')}</option><option value="bank">${NN.h('cx_chuyen_khoan')}</option></select></div>`;
    if (!await EPL.hoi(NN.t('cx_lap'), html, NN.t('cx_lap'))) return;
    const pt = (document.getElementById('ttd-pt') || {}).value || 'cash';
    const ids = chon.map(c => c.trip_id);
    const nut = document.getElementById('ttd-lap'); if (nut) nut.disabled = true;     // không bấm hai lần khi máy chủ đang làm
    try {
      let r;
      // đường mới (cấn trừ SO nhiên liệu rồi phiếu chi phần còn lại); máy chủ cũ chưa có thì đường màn Xe liên kết
      try { r = await API.post('/api/tat-toan-doi-tac/de-nghi', { owner_id: d.owner_id, trip_ids: ids, cach_tra: pt }); }
      catch (e) { if (e.status !== 404 || e.ma !== 'THIEU_DUONG_API') throw e; r = await API.post('/api/owners/' + encodeURIComponent(d.owner_id) + '/de-nghi-tra', { trip_ids: ids, phuong_thuc: pt }); }
      const soPc = r && ((r.phieu_chi && r.phieu_chi.so) || r.document_no);
      EPL.toast(soPc ? NN.t('cx_da_lap', { so: soPc }) : NN.t('ttd_da_lap_dn', { so: (r && (r.so || r.ref_no)) || '' }), r && r.trang_thai === 'loi' ? 'loi' : 'ok');
    } catch (e) { EPL.baoLoi(e); }
    // xong hay hỏng đều xoá lựa chọn rồi nạp lại: chuyến đã vào đề nghị (kể cả đề nghị lỗi) không còn tích được nữa
    TICH.clear();
    delete CT[d.owner_id];
    await tai(true);
  }
  /** Mã bản ghi đề nghị (ChiChuXeTune.id) — máy chủ gửi `id` thì dùng; không thì tra theo số TCX ở danh sách của màn Xe liên kết. */
  async function maDN(d, r) {
    if (r.id) return r.id;
    const g = await API.get('/api/owners/' + encodeURIComponent(d.owner_id) + '/tra-ke-toan');
    const x = ((g && g.de_nghi) || []).find(y => y.ref_no === r.so);
    return x ? x.id : null;
  }
  async function viecDN(d, r, viec, nut) {
    if (!r) return;
    if (viec === 'huy' && !await EPL.hoi(NN.t('cx_bo'), `<p>${NN.h('ttd_hoi_bo', { so: r.so || '' })}</p>`, NN.t('cx_bo'))) return;
    if (nut) nut.disabled = true;
    try {
      let x;
      try { x = await API.post(`/api/tat-toan-doi-tac/de-nghi/${encodeURIComponent(r.so)}/${viec === 'huy' ? 'bo' : viec}`, {}); }
      catch (e) {
        if (e.status !== 404 || e.ma !== 'THIEU_DUONG_API') throw e;
        const id = await maDN(d, r);
        if (!id) throw new Error(NN.t('ttd_khong_thay_dn'));
        x = await API.post(`/api/chi-chu-xe/${encodeURIComponent(id)}/${viec}`, {});
      }
      const st = x && (x.trang_thai || x.status);
      EPL.toast(NN.t(TT_DN[st || ''] || 'saved'), st === 'loi' ? 'loi' : 'ok');
    } catch (e) { EPL.baoLoi(e); }
    delete CT[d.owner_id];
    await tai(true);
  }

  /* ---------------------------------------------------------------- cao vừa cửa sổ */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.ttd-ds');
    if (!ds || !ds.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--ttd-cao', Math.max(320, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  function veHet() {
    const ds = dsLoc();
    if (!ds.some(d => d.owner_id === CHON)) { CHON = ds[0] ? ds[0].owner_id : null; TICH.clear(); MO.clear(); }
    veLoc(); veTong(); veDs(); veXem();
    datCao();
  }

  /** Bảng của kỳ. 404 (máy chủ chưa có đường này) → "chưa có dữ liệu", không báo lỗi đỏ. */
  async function tai(giu) {
    const luot = ++LUOT, ky = q('#ttd-ky').value || EPL.thangNay();
    let b = null, chua = false;
    try { b = await API.get('/api/tat-toan-doi-tac?ky=' + encodeURIComponent(ky)); }
    catch (e) { if (e.status === 404) chua = true; else if (luot === LUOT) EPL.baoLoi(e); b = { ky, tong: {}, doi_tac: [] }; }
    if (luot !== LUOT) return;
    CHUA_CO = chua;
    BANG = { ky, tong: {}, doi_tac: [], ...(b || {}) };
    if (!giu) { Object.keys(CT).forEach(k => delete CT[k]); TICH.clear(); MO.clear(); }
    // máy chủ gửi luôn chi_tiet của cả kỳ (mỗi dòng có owner_id) thì khỏi hỏi từng đối tác
    if (Array.isArray(BANG.chi_tiet) && BANG.chi_tiet.length && BANG.chi_tiet.every(c => c.owner_id)) {
      BANG.doi_tac.forEach(d => { CT[d.owner_id] = { chi_tiet: BANG.chi_tiet.filter(c => c.owner_id === d.owner_id) }; });
    }
    veHet();
  }
  async function taiMot(oid) {
    const ky = BANG && BANG.ky;
    try {
      const r = await API.get('/api/tat-toan-doi-tac?ky=' + encodeURIComponent(ky) + '&owner_id=' + encodeURIComponent(oid));
      if (!BANG || BANG.ky !== ky) return;
      CT[oid] = r || { chi_tiet: [] };
      // bản một đối tác có thể mới hơn (vừa hỏi lại kế toán): cập nhật dòng tổng của đối tác đó
      const moi = ((r && r.doi_tac) || []).find(x => x.owner_id === oid);
      if (moi) BANG.doi_tac = BANG.doi_tac.map(x => (x.owner_id === oid ? moi : x));
    } catch (e) { CT[oid] = { chi_tiet: [] }; if (e.status !== 404) EPL.baoLoi(e); }
    if (CHON === oid && root && root.isConnected) { veDs(); veXem(); }
  }

  EPL.modules['tat-toan-doi-tac'] = {
    async init(r, ctx) {
      root = r; BANG = null; CHUA_CO = false; CHON = null; loc = ''; tim = ''; tab = 'bang';
      Object.keys(CT).forEach(k => delete CT[k]); MO.clear(); TICH.clear();
      const h = document.getElementById('pageTitle'); if (h) h.innerHTML = NN.h('title_tat_toan_doi_tac');
      const t = (ctx && ctx.tham) || {};
      if (t.ky) q('#ttd-ky').value = t.ky;
      if (t.owner_id) CHON = t.owner_id;
      veGioiThieu();
      q('#ttd-ky').addEventListener('change', () => { CHON = null; tai(); });
      q('#ttd-lam-moi').addEventListener('click', () => { if (CHON) delete CT[CHON]; tai(true); });
      q('#ttd-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); veHet(); }, 200); });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      await tai();
    },
    onLang() { if (root) { const h = document.getElementById('pageTitle'); if (h) h.innerHTML = NN.h('title_tat_toan_doi_tac'); veGioiThieu(); veHet(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      const T = NN.t, ky = BANG ? nhanThang(BANG.ky) : '';
      const sh = [EPL.xuatSheet(T('nav_tt_doi_tac') + ' ' + ky, [T('owner'), T('acct_code'), T('ccy_hire'), T('cx_phieu'), T('ttd_c_thue'), T('ttd_c_phi'),
        T('ttd_c_qua_tai'), T('ttd_c_tam_ung'), T('ttd_c_no_ncc'), T('ttd_c_nhien_lieu'), T('ttd_c_con_tra'), T('ttd_c_con_tra') + ' (LAK)', T('status')],
        dsLoc().map(d => [d.ten || '', d.ma_ke_toan || '', d.tien_te || '', d.so_phieu || 0, EPL.oTien(d.tien_thue, d.tien_te), EPL.oTien(d.phi, d.tien_te),
          EPL.oTien(d.qua_tai, d.tien_te), EPL.oTien(d.tam_ung, d.tien_te), EPL.oTien(d.no_ncc, d.tien_te),
          EPL.oTien(d.nhien_lieu_con_no != null ? d.nhien_lieu_con_no : d.nhien_lieu, d.tien_te), EPL.oTien(d.con_tra, d.tien_te), EPL.oTien(d.con_tra_lak, 'LAK'),
          T('ttd_st_' + (d.trang_thai || 'chua_lap'))]))];
      const d = ((BANG && BANG.doi_tac) || []).find(x => x.owner_id === CHON), ds = d ? chuyenCua(d.owner_id) : [];
      if (d && ds.length) {
        sh.push(EPL.xuatSheet(d.ten || 'DO', [T('doc_no'), T('c_date'), T('route'), T('truck_no'), T('ton'), T('ttd_gia_thue'), T('ttd_c_thue'), T('ttd_phi_pct'),
          T('ttd_c_phi'), T('ttd_c_qua_tai'), T('ttd_c_tam_ung'), T('ttd_c_no_ncc') + ' (LAK)', T('ttd_c_nhien_lieu') + ' (LAK)', T('ttd_c_con_tra'), T('status')],
          ds.map(c => [c.doc_no || '', EPL.oNgay(c.ngay), c.tuyen || '', c.xe || '', EPL.oSo(c.tan_tinh, 2), EPL.oTien(c.gia_thue, c.tien_te), EPL.oTien(c.tien_thue, c.tien_te),
            c.phi_pct == null ? null : EPL.oSo(c.phi_pct, 1, '%'), EPL.oTien(c.phi, c.tien_te), EPL.oTien(c.qua_tai, c.tien_te),
            EPL.oTien((c.tam_ung || {}).tien, c.tien_te), EPL.oTien(tong(c.no_ncc || [], x => x.tien_lak), 'LAK'), EPL.oTien((c.nhien_lieu || {}).con_no_lak, 'LAK'),
            EPL.oTien(c.con_tra, c.tien_te), T('ttd_tr_' + (c.trang_thai_tra || 'chua_tra'))])));
      }
      return sh;
    },
  };
})();
