/* Tất toán tài xế theo tháng — đối tiền ứng với tiền chi thật, chênh thì bù hoặc thu lại (dựng lại 01/10).
 *
 * Chênh lệch = đã chi thật − đã ứng.  Dương: công ty chi bù (phiếu chi "Chi khác" TT_CHI bên kế toán anh Tune).
 * Âm: tài xế nộp lại (phiếu thu "Thu khác" TT_THU).  Dưới 1 Kíp: không lập phiếu, chốt xong ngay.
 * Chốt cũng ghi quyết toán QT_TU (Nợ 625 / Có 1601 = đã chi thật) thành bút toán chờ gửi. Thủ quỹ bên đó chi / thu rồi GHI
 * SỔ; máy chủ hỏi lại → bản chốt "xong". Số tính và luật ở routes/tat_toan.py, tiền ở services/chi_tat_toan_tune.py.
 *
 * Ai làm gì (bảng Nhiệm Vụ, bước 19): KT Chi phí VC (và Sếp) chốt · bỏ chốt · gửi lại; quỹ tiền mặt / ngân hàng xem, cập nhật.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, BANG = { dong: [] }, CHON = null, CT = {}, loc = '', tim = '', hen = null, LUOT = 0, TU_DONG = false, BAO = null;
  const MO = new Set();               // phiếu đang mở ra trong bảng tính (từng dòng tiền)
  const q = (s) => root.querySelector(s);
  const chotDuoc = () => AUTH.la('expacct');          // Sếp luôn qua (AUTH.la)
  const LOC = ['', 'chua', 'cho', 'loi', 'xong'];
  const lak = (v) => `${so(v)} <small>LAK</small>`;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');
  const thangTruoc = (v) => { const [y, m] = v.split('-').map(Number); const d = new Date(y, m - 2, 1);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); };

  /* ---------------------------------------------------------------- trạng thái một dòng */
  /** {k: khoá lọc, nhan: khoá dịch, mau: lớp nhãn} — chưa chốt · chờ chi · lỗi · xong. */
  function trangThai(d) {
    const t = d.tat_toan;
    if (!d.da_tat_toan || !t) return { k: 'chua', nhan: 'tt_chua_chot', mau: 'plain' };
    if (t.status === 'xong') return { k: 'xong', nhan: 'tt_xong', mau: 'paid' };
    const p = t.phieu_ke_toan || {};
    if (p.status === 'loi') return { k: 'loi', nhan: p.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan', mau: 'unpaid' };
    return { k: 'cho', nhan: 'tt_cho_chi', mau: 'transit' };
  }
  const chieu = (ch) => (Math.abs(ch) < 1 ? 'tt_even' : ch > 0 ? 'tt_pay_more' : 'tt_give_back');
  const lop = (ch) => (Math.abs(ch) < 1 ? '' : ch > 0 ? 'pos' : 'neg');

  function locDs() {
    const t = tim.toLowerCase();
    return BANG.dong.filter(d => (!loc || trangThai(d).k === loc)
      && (!t || ((d.driver_name || '') + ' ' + (d.driver_latin || '') + ' ' + (d.driver_code || '')).toLowerCase().includes(t)));
  }

  /* ---------------------------------------------------------------- thanh lọc + dải tổng */
  function veLoc() {
    const dem = {}; BANG.dong.forEach(d => { const k = trangThai(d).k; dem[k] = (dem[k] || 0) + 1; });
    const nhan = { '': 'all', chua: 'tt_chua_chot', cho: 'tt_cho_chi', loi: 'ck_loi_ngan', xong: 'tt_xong' };
    q('#tt2-loc').innerHTML = LOC.map(k => `<button type="button" data-loc="${k}" class="${loc === k ? 'on' : ''}">
      <span>${NN.h(nhan[k])}</span><b>${k ? (dem[k] || 0) : BANG.dong.length}</b></button>`).join('');
    q('#tt2-loc').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veHet(); }));
  }
  function veTong() {
    const ds = BANG.dong;
    const bu = ds.filter(d => d.chenh_lech_lak >= 1).reduce((a, d) => a + d.chenh_lech_lak, 0);
    const lai = ds.filter(d => d.chenh_lech_lak <= -1).reduce((a, d) => a - d.chenh_lech_lak, 0);
    const cho = ds.filter(d => trangThai(d).k === 'cho').length, loi = ds.filter(d => trangThai(d).k === 'loi').length;
    q('#tt2-tong').innerHTML = [
      ['tt_advanced', lak(BANG.tong_ung_lak), ''],
      ['tt_spent', lak(BANG.tong_chi_lak), ''],
      ['tt_pay_more', lak(bu), 'pos'],
      ['tt_give_back', lak(lai), 'neg'],
      ['tt_cho_chi', `${cho}${loi ? ` <small class="neg">· ${loi} ${esc(NN.t('ck_loi_ngan').toLowerCase())}</small>` : ''}`, cho || loi ? 'canh' : ''],
    ].map(([k, v, c]) => `<div class="o ${c}"><div class="l">${NN.h(k)}</div><div class="v">${v}</div></div>`).join('')
      + (BAO ? `<div class="tt2-bao"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>
        <span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span></div>` : '')
      + `<p class="small muted tt2-note">${NN.h('tt_note')}</p>`;
  }

  /* ---------------------------------------------------------------- danh sách tài xế */
  function veDs() {
    const ds = locDs();
    q('#tt2-ds').innerHTML = ds.length ? ds.map(d => {
      const s = trangThai(d), ch = d.chenh_lech_lak, lech = d.tat_toan && d.tat_toan.lech;
      return `<button type="button" class="tt2-o st-${s.k} ${CHON === d.driver_id ? 'chon' : ''}" data-tx="${esc(d.driver_id)}">
        <span class="ten" lang="lo">${esc(d.driver_name)}</span>
        <span class="tien ${lop(ch)}">${so(Math.abs(ch))}</span>
        <span class="phu">${esc((d.driver_latin ? d.driver_latin + ' · ' : '') + (d.driver_code ? d.driver_code + ' · ' : ''))}${d.so_phieu} ${esc(NN.t('tt_slips').toLowerCase())}</span>
        <span class="tt">${EPL.tag(s.mau, s.nhan)}${lech ? ' ' + EPL.tag('partial', 'tt_lech') : ''}</span>
        <span class="phu">${NN.h(chieu(ch))}</span></button>`;
    }).join('') : `<div class="tt2-trong">${NN.h('no_data')}</div>`;
    q('#tt2-ds').querySelectorAll('[data-tx]').forEach(b => b.addEventListener('click', () => { if (CHON !== b.dataset.tx) MO.clear(); CHON = b.dataset.tx; veDs(); veXem(); }));
  }

  /* ---------------------------------------------------------------- một tài xế */
  /** Câu máy chủ (loi · loi_lo · loi_en) theo tiếng đang xem (06/10). */
  const chuMay = (x) => (!x ? '' : NN.lang === 'lo' && x.loi_lo ? x.loi_lo : NN.lang === 'en' && x.loi_en ? x.loi_en
    : NN.lang === 'both' && x.loi_lo ? x.loi + ' / ' + x.loi_lo : x.loi || '');
  function nutCua(d) {
    const s = trangThai(d), t = d.tat_toan || {}, p = t.phieu_ke_toan, qt = t.quyet_toan || {};
    const nut = [];
    if (s.k === 'chua') {
      if (chotDuoc() && d.so_phieu) {
        const cho = d.tam_ung_cho || [];       // có ở bản đầy đủ (CT) — máy chủ chặn chốt 409 TAM_UNG_CHUA_CHI_XONG khi còn
        const con = d.chan_chot || [];         // G4 06/10: DO chưa khoá / khai báo chưa duyệt / dòng tiền mặt giá 0 — máy chủ chặn 409
        nut.push(['chot', 'primary', 'tt_chot', con.length ? NN.t('tt_cc_khoa', { n: con.length }) : cho.length
          ? NN.t('tt_chot_khoa', { so: cho.map(u => u.document_no || u.doc_no || '').filter(Boolean).join(', ') }) : '', con.length ? 'tt_cc_ngan' : 'tt_chot_khoa_ngan']);
      }
    } else {
      if (p && p.status === 'da_gui') nut.push(['cap-nhat', '', 'ck_cap_nhat']);
      if (p && p.status === 'loi' && chotDuoc()) nut.push(['gui-lai', 'warn', 'tt_gui_lai']);
      // bỏ chốt chỉ khi phiếu bên kế toán chưa ghi sổ và QT_TU chưa gửi — máy chủ vẫn chặn lại lần nữa. Không bỏ được thì nút xám
      // kèm lý do (06/10 — câu máy chủ ở khối "Không bỏ chốt được" bên dưới), không giấu nút như trước
      const khongBo = (p && p.status === 'da_chi') || qt.status === 'da_gui';
      if (chotDuoc()) nut.push(['bo', 'danger', 'tt_bo_chot', khongBo ? chuMay(d.bo_chot_chan) || NN.t('tt_bo_khong_duoc') : '', 'tt_bo_khong_duoc']);
    }
    return nut.map(([v, c, k, khoa, ngan]) => khoa
      ? `<span class="tt2-khoa"><button type="button" class="btn ${c}" data-viec="${v}" disabled title="${esc(khoa)}">${NN.h(k)}</button><small>${NN.h(ngan || 'tt_chot_khoa_ngan')}</small></span>`
      : `<button type="button" class="btn ${c}" data-viec="${v}">${NN.h(k)}</button>`).join('');
  }

  /** Tờ / tháng đang xem ghi vào địa chỉ (rà 01/10): bấm "Mở phiếu" sang Phiếu xuất xe rồi Quay lại, hay tải lại trang, là về
   *  đúng tờ đó — trước đây màn mở lại từ đầu, tờ vừa xem như biến mất. init đã đọc sẵn các tham số này. replaceState: không
   *  thêm bước lịch sử, không bắn hashchange (khung không nạp lại màn); màn đã bị rời (gốc tháo khỏi trang) thì thôi. */
  function ghiDiaChi(ts) {
    if (!root || !root.isConnected) return;
    [...ts.keys()].forEach(k => { if (!ts.get(k)) ts.delete(k); });
    const moi = '#/tat-toan' + (ts.toString() ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }

  function veXem() {
    const o = q('#tt2-xem');
    const d = BANG.dong.find(x => x.driver_id === CHON);
    ghiDiaChi(new URLSearchParams({ ky: BANG.ky || q('#tt2-ky').value || '', tx: d ? d.driver_id : '' }));
    if (!d) { o.innerHTML = `<div class="tt2-trong">${NN.h('no_data')}</div>`; return; }
    const c = CT[d.driver_id];                 // bản đầy đủ (phiếu trong kỳ, tạm ứng chờ, QT_TU) — tải riêng
    const x = c || d, t = x.tat_toan, ch = x.chenh_lech_lak, s = trangThai(x);
    const canh = [];
    if (t && t.lech) canh.push(`<div class="tt2-canh">${NN.h('tt_lech')}</div>`);
    if (c && c.tam_ung_cho && c.tam_ung_cho.length) {
      canh.push(`<div class="tt2-canh">${NN.h('tt_tam_ung_cho')}: ${c.tam_ung_cho.map(u =>
        `<a href="#/phieu-xuat-xe?id=${esc(u.trip_id)}" class="mono">${esc(u.doc_no || u.trip_id)}</a>${u.document_no ? ` (${esc(u.document_no)})` : ''}`).join(', ')}</div>`);
    }
    // G4 (06/10): còn DO dở trong kỳ — máy chủ chặn chốt; liệt kê từng DO (bấm sang phiếu) và việc còn thiếu
    if (c && c.chan_chot && c.chan_chot.length) {
      canh.push(`<div class="tt2-canh tt2-cc"><b>${NN.h('tt_cc_tieu_de', { n: c.chan_chot.length })}</b><ul>${c.chan_chot.map(z =>
        `<li><a href="#/phieu-xuat-xe?id=${esc(z.trip_id)}" class="mono">${esc(z.doc_no)}</a>: ${esc(chuMay(z).replace(z.doc_no + ': ', ''))}</li>`).join('')}</ul>
        <small>${NN.h('tt_cc_goi_y')}</small></div>`);
    }
    // bỏ chốt không được (phiếu chênh đã ghi sổ / QT_TU đã gửi) — nói vì sao, ngay trên khối bản chốt
    if (c && c.bo_chot_chan) canh.push(`<div class="tt2-canh tt2-cc">${esc(chuMay(c.bo_chot_chan))}</div>`);
    o.innerHTML = `<div class="tt2-dau">
        <div><h3 lang="lo">${esc(x.driver_name)}</h3><div class="small muted">${esc((x.driver_latin ? x.driver_latin + ' · ' : '') + (x.driver_code ? x.driver_code + ' · ' : ''))}${NN.h('tt_period')} ${nhanThang(x.period)}</div></div>
        <div class="grow"></div>${EPL.tag(s.mau, s.nhan)}<div class="tt2-nut no-print">${nutCua(x)}</div></div>
      ${canh.join('')}
      <div class="tt2-so">
        <div><span>${NN.h('tt_slips')}</span><b>${x.so_phieu}</b></div>
        <div><span>${NN.h('tt_advanced')}</span><b>${lak(x.tong_ung_lak)}</b>${choUng(c) ? `<small class="tt2-cho">${NN.h('tt_ung_cho', { tien: so(choUng(c)) })}</small>` : ''}</div>
        <div><span>${NN.h('tt_spent')}</span><b>${lak(x.tong_chi_lak)}</b></div>
        <div class="${lop(ch)}"><span>${NN.h('tt_diff')} · ${NN.h(chieu(ch))}</span><b>${lak(Math.abs(ch))}</b>${choUng(c) ? `<small class="tt2-cho">${NN.h('tt_chenh_tam')}</small>` : ''}</div>
      </div>
      ${t ? veChot(t) : ''}
      <div class="tt2-bt-dau no-print"><b>${NN.h('tt_bang_tinh')}</b><span class="small muted">${NN.h('tt_bang_tinh_d')}</span><span class="grow"></span>
        ${c && c.phieu.length ? `<button type="button" class="btn sm quiet" id="tt2-mo-het">${NN.h(MO.size ? 'ttd_thu_het' : 'ttd_mo_het')}</button>` : ''}</div>
      <div class="tbl-wrap tt2-phieu">${bangTinh(c)}</div>`;
    o.querySelectorAll('[data-viec]').forEach(b => b.addEventListener('click', () => lam(x, b.dataset.viec, b)));
    o.querySelectorAll('tr.tt2-p').forEach(tr => tr.addEventListener('click', (e) => {
      if (e.target.closest('a, button, input')) return;
      const id = tr.dataset.p; if (MO.has(id)) MO.delete(id); else MO.add(id); veXem();
    }));
    const moHet = o.querySelector('#tt2-mo-het');
    if (moHet) moHet.addEventListener('click', () => { if (MO.size) MO.clear(); else (c.phieu || []).forEach(p => MO.add(p.trip_id)); veXem(); });
    if (!c) taiMot(d.driver_id);
  }

  /* ---------------------------------------------------------------- bảng tính chi tiết (02/10) */
  /* Mỗi phiếu một dòng: đã ứng · đã chi thật · chênh của phiếu, ba cột cộng dồn; mở phiếu ra là từng dòng tiền — mục, khoản,
   * SL × đơn giá, cách trả, NGUỒN (trong tạm ứng · tài xế tự chi · cùng lương · nợ NCC · thẻ · kho), số PTU, số phiếu chi bên kế
   * toán. "Đã chi thật" chỉ gồm hai nguồn trong tạm ứng và tài xế tự chi (đúng luật routes/tat_toan.py). Máy chủ chưa gửi khoá
   * chi tiết thì ô hiện "—", không vỡ. */
  const NGUON_TT = { tam_ung: ['paid', 'tt_ng_tam_ung'], tu_chi: ['transit', 'tt_ng_tu_chi'], cung_luong: ['plain', 'tt_ng_cung_luong'],
    ncc: ['dispatched', 'tt_ng_ncc'], the: ['plain', 'tt_ng_the'], kho: ['plain', 'tt_ng_kho'] };
  const CACH_TT = { tien_mat: 'pm_on_dispatch', luong: 'pm_trip_salary', ncc: 'pm_supplier', the: 'tt_ct_the', kho: 'tt_ct_kho' };
  /** Tên khoản theo tiếng đang xem: có item_key thì dịch theo từ điển; có tên Lào (khoan_lo / name_lo) thì dùng khi xem tiếng Lào;
   *  không thì tên máy chủ gửi (UAT 03/10: máy chủ mới gửi tên Việt). */
  const tenKhoan = (d, k) => (d.item_key && (window.EPL_TU_DIEN || {})[d.item_key] ? NN.t(d.item_key)
    : (NN.lang === 'lo' && (d[k + '_lo'] || d.name_lo)) || d[k] || '');
  const vaoChi = (n) => n === 'tam_ung' || n === 'tu_chi';
  /** Tạm ứng của phiếu `p` mà phiếu chi bên kế toán CHƯA ghi sổ (máy chủ liệt kê ở tam_ung_cho): Σ dòng nguồn "trong tạm ứng". Số
   *  này chưa vào "Đã ứng" (đúng luật — tài xế chưa nhận tiền), hiện riêng để ô chênh lệch không bị đọc thành "công ty chi bù". */
  const ungChoPhieu = (c, p) => (c && (c.tam_ung_cho || []).some(u => u.trip_id === p.trip_id) && Array.isArray(p.dong)
    ? p.dong.filter(d => d.nguon === 'tam_ung').reduce((a, d) => a + (Number(d.tien_lak) || 0), 0) : 0);
  const choUng = (c) => (c ? (c.phieu || []).reduce((a, p) => a + ungChoPhieu(c, p), 0) : 0);
  const soP = (p, k) => (p[k] === undefined || p[k] === null ? null : Number(p[k]));
  const chiP = (p) => (soP(p, 'da_chi_that_lak') != null ? soP(p, 'da_chi_that_lak') : soP(p, 'chi_lak'));
  const chenhP = (p) => (soP(p, 'chenh_lak') != null ? soP(p, 'chenh_lak') : soP(p, 'da_ung_lak') != null && chiP(p) != null ? chiP(p) - soP(p, 'da_ung_lak') : null);
  const oLak = (v, cls) => (v == null ? '<span class="muted">—</span>' : `<span class="${cls || ''}">${so(v)}</span>`);
  const oChenh = (v) => (v == null ? '<span class="muted">—</span>' : `<span class="${lop(v)}">${v > 0 ? '+' : v < 0 ? '−' : ''}${so(Math.abs(v))}</span>`);
  function bangDongTien(p) {
    if (!Array.isArray(p.dong)) return `<div class="tt2-rong">${NN.h('tt_chua_dong')}</div>`;
    if (!p.dong.length) return `<div class="tt2-rong">${NN.h('no_data')}</div>`;
    const MUC = { III: 'III', IV: 'IV', V: 'V', VI: 'VI', fuel: 'III', travel: 'IV', repair: 'V', other: 'VI' };
    const cong = p.dong.filter(d => vaoChi(d.nguon)).reduce((a, d) => a + (Number(d.tien_lak) || 0), 0);
    return `<table class="tbl tbl-compact tt2-dong-tien"><thead><tr><th>${NN.h('hs_cot_muc')}</th><th>${NN.h('item')}</th><th class="num">${NN.h('hs_cot_sl_gia')}</th>
        <th class="num">${NN.h('amount_lak')}</th><th>${NN.h('tt_nguon')} · ${NN.h('tt_cach_tra')}</th><th>${NN.h('tt_so_ptu')} · ${NN.h('tt_phieu_chi_kt')}</th>
        <th class="num">${NN.h('tt_vao_chi')}</th></tr></thead>
      <tbody>${p.dong.map(d => { const ng = NGUON_TT[d.nguon] || ['plain', 'tt_ng_khac'];
        return `<tr class="${vaoChi(d.nguon) ? '' : 'ngoai'}"><td>${esc(MUC[d.muc] || d.muc || '—')}</td><td lang="lo">${esc(tenKhoan(d, 'khoan') || '—')}</td>
          <td class="num">${d.sl == null ? '—' : so(d.sl, Number.isInteger(+d.sl) ? 0 : 2)} × ${d.don_gia == null ? '—' : EPL.tien(d.don_gia, d.tien_te || 'LAK')}</td>
          <td class="num">${oLak(d.tien_lak)}</td>
          <td>${EPL.tag(ng[0], ng[1])}${d.cach_tra ? `<span class="phu">${NN.h(CACH_TT[d.cach_tra] || 'tt_ng_khac')}</span>` : ''}</td>
          <td class="mono">${d.so_ptu || d.phieu_chi ? `${d.so_ptu ? esc(d.so_ptu) : ''}${d.phieu_chi ? `<span class="phu">${esc(d.phieu_chi)}</span>` : ''}` : '<span class="muted">—</span>'}</td>
          <td class="num">${vaoChi(d.nguon) ? oLak(d.tien_lak) : '<span class="muted">—</span>'}</td></tr>`; }).join('')}</tbody>
      <tfoot><tr><td colspan="6">${NN.h('tt_cong_chi_that')}</td><td class="num">${so(cong)}</td></tr></tfoot></table>`;
  }
  function bangTinh(c) {
    if (!c) return `<table class="tbl tbl-compact"><tbody><tr><td class="empty">${NN.h('loading')}</td></tr></tbody></table>`;
    let cu = 0, cc = 0, coU = true, coC = true;
    const rows = (c.phieu || []).map(p => {
      const u = soP(p, 'da_ung_lak'), ch = chiP(p), ce = chenhP(p), cho = ungChoPhieu(c, p);
      if (u == null) coU = false; else cu += u;
      if (ch == null) coC = false; else cc += ch;
      const mo = MO.has(p.trip_id);
      return `<tr class="tt2-p ${mo ? 'mo' : ''}" data-p="${esc(p.trip_id)}">
          <td class="so-p"><span class="mui">▸</span> <a href="#/phieu-xuat-xe?id=${esc(p.trip_id)}" class="mono">${esc(p.doc_no)}</a>
            <span class="phu">${EPL.ngay(p.out_date)}${p.truck_no ? ' · ' + esc(p.truck_no) : ''}</span></td>
          <td lang="lo" class="tuyen">${p.origin || p.destination ? esc((p.origin || '') + ' → ' + (p.destination || '')) : '—'}</td>
          <td class="num">${oLak(u)}${cho ? `<span class="phu tt2-cho">${NN.h('tt_ung_cho_ngan', { tien: so(cho) })}</span>` : ''}</td><td class="num">${oLak(ch)}</td><td class="num">${oChenh(ce)}</td>
          <td class="num cd">${coU ? so(cu) : '—'}</td><td class="num cd">${coC ? so(cc) : '—'}</td><td class="num cd">${coU && coC ? oChenh(cc - cu) : '—'}</td></tr>`
        + (mo ? `<tr class="tt2-mo"><td colspan="8"><div class="tt2-mo-boc">${bangDongTien(p)}</div></td></tr>` : '');
    }).join('');
    const tu = (c.phieu || []).every(p => soP(p, 'da_ung_lak') != null) ? (c.phieu || []).reduce((a, p) => a + soP(p, 'da_ung_lak'), 0) : null;
    const tc = (c.phieu || []).every(p => chiP(p) != null) ? (c.phieu || []).reduce((a, p) => a + chiP(p), 0) : null;
    return `<table class="tbl tbl-compact tt2-bang"><colgroup><col class="c-so"><col class="c-tuyen"><col class="c-n"><col class="c-n"><col class="c-n">
        <col class="c-n cd"><col class="c-n cd"><col class="c-n cd"></colgroup><thead><tr><th>${NN.h('doc_no')}<span class="lo-sub" style="display:block;font-weight:500">${NN.h('d_out')} · ${NN.h('truck_no')}</span></th><th>${NN.h('route')}</th>
        <th class="num">${NN.h('tt_advanced')}</th><th class="num">${NN.h('tt_spent')}</th><th class="num">${NN.h('tt_diff')}</th>
        <th class="num cd">${NN.h('tt_cd_ung')}</th><th class="num cd">${NN.h('tt_cd_chi')}</th><th class="num cd">${NN.h('tt_cd_chenh')}</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="8" class="empty">${NN.h('no_data')}</td></tr>`}</tbody>
      ${(c.phieu || []).length ? `<tfoot><tr><td colspan="2">${NN.h('total')} · ${so(c.phieu.length)} ${esc(NN.t('tt_slips').toLowerCase())}</td>
        <td class="num">${oLak(tu)}</td><td class="num">${oLak(tc)}</td><td class="num">${oChenh(tu != null && tc != null ? tc - tu : null)}</td>
        <td class="num cd">${NN.h('tt_theo_chot')}</td><td class="num cd">${so(c.tong_ung_lak)} / ${so(c.tong_chi_lak)}</td><td class="num cd">${oChenh(c.chenh_lech_lak)}</td></tr></tfoot>` : ''}</table>`;
  }

  /** Khối bản chốt: ai chốt, phiếu chi / thu bên kế toán (số phiếu, trạng thái, lỗi), quyết toán QT_TU. */
  function veChot(t) {
    const p = t.phieu_ke_toan, qt = t.quyet_toan;
    const ttQt = qt ? ({ cho_gui: 'dt_st_cho_gui', da_gui: 'dt_st_da_gui', huy: 'v_huy' }[qt.status] || qt.status) : null;
    const ttP = p ? ({ da_gui: 'tt_cho_chi', da_chi: 'ck_da_chi_ngan', huy: 'v_huy',
      loi: p.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan' }[p.status] || p.status) : null;
    return `<div class="tt2-chot">
      <div><span>${NN.h('tt_done')}</span><b>${esc(t.settled_by || '')}</b> <span class="muted">${EPL.ngayGio(t.settled_at)}</span>
        ${t.note ? `<div class="small muted">${esc(t.note)}</div>` : ''}</div>
      ${p ? `<div><span>${NN.h(p.loai === 'TT_THU' ? 'tt_thu_hoan' : 'tt_chi_bu')}</span>
        <b class="mono">${esc(p.document_no || '—')}</b>
        <span class="tt2-dong">${lak(p.amount)} · ${NN.h(p.phuong_thuc === 'bank' ? 'pm_bank' : 'pm_cash')}</span>
        <div>${EPL.tag(p.status === 'da_chi' ? 'paid' : p.status === 'loi' ? 'unpaid' : p.status === 'huy' ? 'plain' : 'transit', ttP)}
          ${p.post_by ? `<span class="small muted">${esc(p.post_by)} · ${EPL.ngayGio(p.post_at)}</span>` : ''}</div>
        ${p.error_message ? `<div class="small neg">${esc(p.error_message)}</div>` : ''}</div>` : `<div><span>${NN.h('tt_even')}</span></div>`}
      ${qt ? `<div><span>QT_TU · ${esc(NN.t('tt_qt_tu'))}</span><b>${lak(qt.tong)}</b>
        <div>${EPL.tag(qt.status === 'da_gui' ? 'paid' : qt.status === 'huy' ? 'plain' : 'transit', ttQt)}</div></div>` : ''}
    </div>`;
  }

  async function taiMot(id) {
    const ky = BANG.ky;
    try {
      const x = await API.get('/api/tat-toan/' + encodeURIComponent(id) + '?ky=' + encodeURIComponent(ky));
      if (BANG.ky !== ky) return;
      CT[id] = x; if (CHON === id) veXem();
    } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- việc: chốt · cập nhật · gửi lại · bỏ chốt */
  async function lam(d, viec, nut) {
    const id = d.driver_id, ky = BANG.ky, duong = '/api/tat-toan/' + encodeURIComponent(id);
    if (viec === 'chot') {
      const ch = d.chenh_lech_lak, co = Math.abs(ch) >= 1;
      const html = `<p>${NN.h('tt_confirm', { ky: nhanThang(ky), ten: d.driver_name })}</p>
        <p><b>${NN.h(chieu(ch))}${co ? ': ' + so(Math.abs(ch)) + ' LAK' : ''}</b>${co ? ` — ${NN.h(ch > 0 ? 'tt_chi_bu' : 'tt_thu_hoan')}` : ''}</p>
        ${co ? `<div class="field"><label>${NN.h('tt_cach')}</label><select id="tt2-hn-cach">
          <option value="cash">${NN.h('pm_cash')}</option><option value="bank">${NN.h('pm_bank')}</option></select></div>` : ''}
        <div class="field"><label>${NN.h('note')}</label><textarea id="tt2-hn-note" rows="2"></textarea></div>`;
      if (!await EPL.hoi(NN.t('tt_chot'), html, NN.t('tt_chot'))) return;
      const cach = document.getElementById('tt2-hn-cach'), note = document.getElementById('tt2-hn-note');
      const body = { driver_id: id, period: ky, note: note ? note.value.trim() || undefined : undefined };
      if (cach) body.phuong_thuc = cach.value;
      return chay(nut, id, () => API.post('/api/tat-toan', body));
    }
    if (viec === 'bo') {
      if (!await EPL.hoi(NN.t('tt_bo_chot'), `<p>${NN.h('tt_bo_hoi', { ky: nhanThang(ky), ten: d.driver_name })}</p>`, NN.t('tt_bo_chot'))) return;
      return chay(nut, id, () => API.del(duong + '?ky=' + encodeURIComponent(ky)), true);
    }
    return chay(nut, id, () => API.post(duong + '/' + viec + '?ky=' + encodeURIComponent(ky), {}));
  }
  /** Gọi máy chủ, rồi tải lại bảng tháng (số, trạng thái, dải tổng) và bản đầy đủ của tài xế. Lỗi hiện ngay trên màn. */
  async function chay(nut, id, goi, xoaBan) {
    if (nut) nut.disabled = true;
    try {
      const x = await goi();
      if (!xoaBan && x && x.driver_id === id) CT[id] = x; else delete CT[id];
      EPL.toast(NN.t('saved'), 'ok');
    } catch (e) { EPL.baoLoi(e); delete CT[id]; }
    await tai(true);
  }

  /* ---------------------------------------------------------------- cao vừa cửa sổ */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.tt2-ds');
    if (!ds || !ds.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--tt-cao', Math.max(300, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  function veHet() {
    const ds = locDs();
    if (!ds.some(d => d.driver_id === CHON)) CHON = ds[0] ? ds[0].driver_id : null;
    veLoc(); veTong(); veDs(); veXem();
    datCao();
  }

  /** Tải bảng tháng. `giu` = giữ tài xế đang chọn (sau một việc). Lần đầu vào màn không kèm kỳ: tháng này trống thì xem
   *  tháng trước (đầu tháng là lúc tất toán tháng vừa qua), kèm dòng báo. */
  async function tai(giu) {
    const luot = ++LUOT, ky = q('#tt2-ky').value || EPL.thangNay();
    let b;
    try { b = await API.get('/api/tat-toan?ky=' + encodeURIComponent(ky)); } catch (e) { if (luot === LUOT) EPL.baoLoi(e); b = { ky, dong: [] }; }
    if (luot !== LUOT) return;
    if (TU_DONG && !b.dong.length) {
      TU_DONG = false;
      const truoc = thangTruoc(ky);
      BAO = { trong: ky, xem: truoc }; q('#tt2-ky').value = truoc;
      return tai();
    }
    TU_DONG = false;
    if (!giu || (BANG.ky && BANG.ky !== b.ky)) CT = {};
    BANG = b;
    veHet();
  }

  EPL.modules['tat-toan'] = {
    async init(r, ctx) {
      root = r; BANG = { dong: [] }; CT = {}; CHON = null; loc = ''; tim = ''; BAO = null; MO.clear();
      const t = (ctx && ctx.tham) || {};
      if (t.ky) q('#tt2-ky').value = t.ky;
      TU_DONG = !t.ky;
      if (t.tx) CHON = t.tx;
      q('#tt2-ky').addEventListener('change', () => { TU_DONG = false; BAO = null; CHON = null; tai(); });
      q('#tt2-lam-moi').addEventListener('click', () => tai(true));
      q('#tt2-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); veHet(); }, 200); });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      await tai();
    },
    onLang() { if (root) veHet(); },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      const T = NN.t;
      const sh = [EPL.xuatSheet(T('nav_settle') + ' ' + nhanThang(BANG.ky), [T('driver'), T('tt_slips'), T('tt_advanced'), T('tt_spent'), T('tt_diff'),
        T('status'), T('tt_chi_bu') + ' / ' + T('tt_thu_hoan')],
        locDs().map(d => { const p = (d.tat_toan || {}).phieu_ke_toan || {};
          return [d.driver_name, d.so_phieu, d.tong_ung_lak, d.tong_chi_lak, d.chenh_lech_lak, T(trangThai(d).nhan), p.document_no || '']; }))];
      // bảng tính của tài xế đang xem: mỗi phiếu một dòng, kèm từng dòng tiền (nếu máy chủ gửi)
      const c = CT[CHON];
      if (c && (c.phieu || []).length) {
        const rows = [];
        c.phieu.forEach(p => {
          rows.push([p.doc_no, EPL.oNgay(p.out_date), p.truck_no || '', (p.origin || '') + ' → ' + (p.destination || ''), '', '', null, '', '', '', '', '',
            EPL.oSo(soP(p, 'da_ung_lak')), EPL.oSo(chiP(p)), EPL.oSo(chenhP(p))]);
          (p.dong || []).forEach(d => rows.push(['', '', '', '', d.muc || '', d.khoan || '', EPL.oSo(d.sl, 2), d.don_gia == null ? null : EPL.oSo(d.don_gia, EPL.leTien(d.tien_te || 'LAK')), d.don_gia == null ? '' : (d.tien_te || 'LAK'),
            d.cach_tra ? T(CACH_TT[d.cach_tra] || 'tt_ng_khac') : '', T((NGUON_TT[d.nguon] || [0, 'tt_ng_khac'])[1]), [d.so_ptu, d.phieu_chi].filter(Boolean).join(' · '),
            '', vaoChi(d.nguon) ? EPL.oSo(d.tien_lak) : null, EPL.oSo(d.tien_lak)]));
        });
        sh.push(EPL.xuatSheet(c.driver_name || T('driver'), [T('doc_no'), T('d_out'), T('truck_no'), T('route'), T('hs_cot_muc'), T('item'), T('qty'), T('unit_price'), T('ccy'),
          T('tt_cach_tra'), T('tt_nguon'), T('tt_so_ptu') + ' · ' + T('tt_phieu_chi_kt'), T('tt_advanced'), T('tt_spent'), T('tt_diff') + ' / ' + T('amount_lak')], rows));
      }
      return sh;
    },
  };
})();
