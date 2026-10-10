/* Nhà cung cấp — DANH MỤC: hồ sơ (mã, mã số thuế, liên hệ, đơn vị tiền), dịch vụ + khoản mục, TK Nợ / Có từ sổ tài khoản (09/10), kỳ trả,
 * khách được cấn trừ, số dòng chi trên phiếu.
 * Danh mục ở lại đây vì phiếu (dầu ghi nợ tại trạm) và tất toán tài xế cần nó, và Bãi xem danh sách · số dòng · kỳ trả
 * (không có tiền, chốt 23/09).
 *
 * TRẢ NHÀ CUNG CẤP từ 01/10 (bỏ phần tiền trang kế toán tạm — số thử, cắt sổ): tiền chi thật ở hệ kế toán anh Tune. Cột
 * Phát sinh · Đã trả · Chờ chi · Còn nợ (LAK) và nút "Trả qua kế toán" từng nhà cung cấp — cùng kiểu hộp ở màn Xe liên kết:
 * KT Chi phí VC (và Sếp) gõ số tiền trả theo đợt → đề nghị trả → phiếu chi "Chi khác" bên đó (Nợ 4021 / Có tiền, đứng tên nhà
 * cung cấp); thủ quỹ chi và ghi sổ ở đó; màn này hỏi lại trạng thái. KT Thu/Chi, KT kho xăng dầu, KT Doanh thu, hai quỹ xem.
 * API: /api/suppliers/cong-no · /api/suppliers/{id}/tra-ke-toan · /api/suppliers/{id}/de-nghi-tra ·
 * /api/chi-ncc/{id}/cap-nhat|gui-lai|huy (routes/nha_cung_cap.py, services/chi_tat_toan_tune.py). */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], KH = [], NO = {}, KM = {}, QUYEN = {};
  // khoản mục dự phòng khi chưa đọc được danh mục cấu hình (/api/khoan-muc)
  const KHOAN = ['x_chip_lao', 'x_chip_vn', 'x_tire', 'x_toll', 'x_bridge', 'x_border', 'x_parking', 'x_oil', 'x_brake', 'x_tow', 'x_air', 'x_misc'];
  const HAN = ['t_monthly', 't_prepaid', 'pm_on_dispatch'];
  // quyền — chép services/chi_tat_toan_tune.py (XEM_NCC · DE_NGHI_NCC); máy chủ vẫn là nơi quyết
  const xemTra = () => AUTH.la('acct', 'expacct', 'fuel', 'rev', 'treasury', 'cash');
  const lapTra = () => AUTH.la('expacct');
  // trạng thái đề nghị trả (cùng bảng màn Xe liên kết) · phiếu chi bên kế toán bị xoá tay: lỗi PHIEU_CHI_MAT
  const TT_TRA = { da_gui: ['partial', 'ck_cho_chi'], da_chi: ['paid', 'ck_da_chi_ngan'], loi: ['unpaid', 'ck_loi_ngan'], huy: ['plain', 'cx_da_bo'] };
  const ttTra = (r) => (r.status === 'loi' && r.error_code === 'PHIEU_CHI_MAT' ? ['unpaid', 'ncc_phieu_mat'] : (TT_TRA[r.status] || TT_TRA.loi));
  const lak = (v) => (v == null ? '—' : so(v) + ' LAK');

  function ve() {
    const tien = xemTra();
    root.querySelector('#ncc-bang').classList.toggle('ncc-co-tien', tien);
    root.querySelector('#ncc-than').innerHTML = ds.length ? ds.map(s => {
      const n = NO[s.id];
      return `<tr>
      <td lang="lo"><b>${esc(s.name)}</b>${s.code || s.phone ? `<div class="small muted">${esc([s.code, s.phone].filter(Boolean).join(' · '))}</div>` : ''}</td>
      <td>${s.dich_vu ? `<span lang="lo">${esc(s.dich_vu)}</span>` + (s.item_key ? `<div class="small muted">${NN.h(s.item_key)}</div>` : '') : s.item_key ? NN.h(s.item_key) : '—'}</td>
      <td class="tien-chi"><span class="acct nowrap">${tkHien(s)}</span></td>
      <td class="num">${s.so_dong}</td>
      <td class="tien" lang="lo">${esc(s.customer_name || '') || '—'}</td>
      <td>${NN.h(s.payment_term || 't_monthly')}</td>
      <td class="num ncc-tien">${n ? so(n.phat_sinh_lak) : '—'}</td><td class="num ncc-tien">${n ? so(n.da_tra_lak) : '—'}</td>
      <td class="num ncc-tien">${n && n.cho_chi_lak ? `<span class="ncc-cho">${so(n.cho_chi_lak)}</span>` : n ? '0' : '—'}</td>
      <td class="num ncc-tien"><b class="${n && n.con_no_lak > 0 ? 'neg' : ''}">${n ? so(n.con_no_lak) : '—'}</b></td>
      <td class="no-print nowrap">${AUTH.la('expacct') ? `<button class="btn sm" data-sua="${s.id}">${NN.h('edit')}</button> ` : ''}${tien ? `<button class="btn sm" data-tra="${s.id}">${NN.h('cx_tra_kt')}</button>` : ''}</td></tr>`;
    }).join('')
      : `<tr><td colspan="11" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
    root.querySelectorAll('[data-tra]').forEach(b => b.addEventListener('click', () => traKeToan(ds.find(x => x.id === b.dataset.tra))));
  }
  /** Hộp thêm / sửa nhà cung cấp — 09/10 (anh Khampla, so với phần mềm kế toán của họ): đủ hồ sơ (mã, mã số thuế, điện thoại, thư
   *  điện tử, địa chỉ, trang web, đơn vị tiền, đang dùng), DỊCH VỤ GÕ ĐƯỢC (trước là ô chọn cứng 12 khoản), khoản mục chi để khớp dòng
   *  chi trên phiếu (danh mục cấu hình được, có ô tìm), và TK Nợ / Có CHỌN TỪ SỔ TÀI KHOẢN (thay 4 cặp mã ghi cứng). Trống = máy theo
   *  mặc định (Nợ theo khoản mục 625 / 614, Có 4021). Máy chủ chặn (TK sai nhóm, thư điện tử sai…) → mở lại hộp, giữ chữ đã gõ,
   *  đánh dấu ô lỗi. `nhap`: giá trị lần trước · `loi`: {o, chu}. */
  async function sua(s, nhap, loi) {
    const acc = await EPL.accCodes();
    const g = (k, md = '') => nhap && k in nhap ? nhap[k] : (s && s[k] != null ? s[k] : md);
    const loiO = (k) => (loi && loi.o === k ? loi.chu : null);
    // nhà cung cấp đã gắn danh mục chung (cờ bật): tên · mã · điện thoại · địa chỉ sửa ở đó — máy chủ chặn 409 SUA_O_GLS
    const chung = !!(QUYEN.gls && s && s.obj_id);
    const khoan = khoanNcc(g('item_key'));
    const f = [
      { type: 'nhom', label: 'ncc_nhom_chung' },
      { id: 'name', label: 'supplier', value: g('name'), lo: true, bat_buoc: true, chi_doc: chung, loi: loiO('name'), goi_y: chung ? 'o_chung_goi_y' : null },
      { id: 'code', label: 'ncc_ma', value: g('code'), chi_doc: chung, placeholder: 'EPLNCC-…' },
      { id: 'tax_no', label: 'tax_no', value: g('tax_no') },
      { id: 'currency', label: 'ncc_tien_te', type: 'select', value: g('currency', s ? '' : 'LAK'), loi: loiO('currency'),
        options: [['', '—']].concat(EPL.TIEN_TE.map(m => [m, m])) },
      { id: 'phone', label: 'phone', type: 'tel', value: g('phone'), chi_doc: chung },
      { id: 'email', label: 'email', value: g('email'), loi: loiO('email'), placeholder: 'name@company.la' },
      { id: 'address', label: 'address', value: g('address'), lo: true, rong: true, chi_doc: chung },
      { id: 'website', label: 'website', value: g('website'), placeholder: 'https://' },
      { id: 'active', label: 'status', type: 'bat', value: g('active', true) },
      { type: 'nhom', label: 'ncc_nhom_dich_vu' },
      { id: 'dich_vu', label: 'service', value: g('dich_vu'), lo: true, goi_ds: khoan.slice(1).map(x => x[1]), goi_y: 'ncc_dich_vu_goi_y', placeholder: NN.t('ncc_dich_vu_ph') },
      { id: 'item_key', label: 'ncc_khoan_muc', type: 'select', tim: 'search', value: g('item_key'), options: khoan, goi_y: 'ncc_khoan_muc_goi_y' },
      { id: 'payment_term', label: 'terms', type: 'select', value: g('payment_term', 't_monthly'), options: HAN.map(k => [k, NN.t(k)]) },
      // Trạm dầu bên Việt Nam ghi nợ: cuối tháng trừ vào cước của khách nào (C5.1).
      { id: 'customer_id', label: 'ncc_can_tru_kh', type: 'select', tim: 'search', value: g('customer_id'),
        options: [['', '—']].concat(KH.map(k => [k.id, k.name, false, k.code || ''])) },
      { type: 'nhom', label: 'tk_nhom' },
      { id: 'acct_no', label: 'acct_debit', type: 'select', tim: 'tk_tim', value: g('acct_no'), loi: loiO('acct_no'), goi_y: 'ncc_tk_no_goi_y',
        options: EPL.dsTaiKhoan(acc, '6', g('acct_no'), NN.t('ncc_tk_no_md')) },
      { id: 'acct_co', label: 'acct_credit', type: 'select', tim: 'tk_tim', value: g('acct_co'), loi: loiO('acct_co'), goi_y: 'ncc_tk_co_goi_y',
        options: EPL.dsTaiKhoan(acc, '4', g('acct_co'), NN.t('ncc_tk_co_md')) },
      { id: 'note', label: 'note', type: 'textarea', dong: 2, value: g('note'), lo: true, rong: true },
    ];
    const v = await EPL.hopNhap((s ? NN.t('edit') + ' · ' + s.name : NN.t('add') + ' · ' + NN.t('supplier')), f, NN.t('save'), { cot: 2 });
    if (!v) return;
    if (!v.name.trim()) return sua(s, v, { o: 'name', chu: NN.t('supplier') + '?' });
    const than = { ...v, customer_id: v.customer_id || null };
    if (chung) ['name', 'code', 'phone', 'address'].forEach(k => delete than[k]);
    try { await (s ? API.put('/api/suppliers/' + s.id, than) : API.post('/api/suppliers', than)); }
    catch (e) {
      if (e.ma === 'HUY') return;
      EPL.baoLoi(e);
      return sua(s, v, { o: Array.isArray(e.o) ? e.o[0] : e.o, chu: e.message });
    }
    EPL.toast(NN.t('saved'), 'ok');
    await tai().catch(EPL.baoLoi);
  }
  /** Khoản mục chi chọn được cho nhà cung cấp: mục IV đi đường · V sửa chữa · VI khác (không có dầu mục III — dầu là kho). Khoản
   *  đang lưu mà nay ngưng / ngoài danh sách (vd "diesel" của trạm dầu Việt Nam) vẫn giữ để thấy. */
  function khoanNcc(dang) {
    const ds = [...new Set(['travel', 'repair', 'other'].flatMap(m => (KM.items || {})[m] || []))];
    if (!ds.length) ds.push(...KHOAN);
    if (dang && !ds.includes(dang)) ds.unshift(dang);
    return [['', NN.t('ncc_khong_khoan')]].concat(ds.map(k => [k, NN.t(k)]));
  }
  /** TK Nợ / Có đang áp cho nhà cung cấp (cột danh sách): mã riêng in đậm; trống thì mã mặc định, chữ nhạt. */
  function tkHien(s) {
    const sua_ = ((KM.items || {}).repair || []).includes(s.item_key);
    const md = (ma) => `<span class="muted" title="${esc(NN.t('tk_mac_dinh'))}">${ma}</span>`;
    return (s.acct_no ? `<b>${esc(s.acct_no)}</b>` : md(s.item_key ? (sua_ ? '614' : '625') : '625·614')) + ' / '
      + (s.acct_co ? `<b>${esc(s.acct_co)}</b>` : md('4021'));
  }

  /* ---------------------------------------------------------------- trả nhà cung cấp qua hệ kế toán (01/10) */
  /** Đóng hộp chung rồi CHỜ sự kiện close chạy xong mới mở hộp khác. dialog.close() bắn "close" về sau: mở ngay hộp hỏi
   *  "Bỏ đề nghị?" thì chính sự kiện cũ đó trả lời luôn hộp mới là "không" — rà 01/10: hộp hỏi biến mất, hộp trả hiện lại, bấm
   *  Đồng ý là lập thêm một đề nghị với số gợi ý. */
  const dongHop = () => new Promise(res => {
    const d = document.getElementById('hop-thoai');
    if (!d.open) return res();
    d.addEventListener('close', () => setTimeout(res, 0), { once: true });
    d.close();
  });
  async function traKeToan(s) {
    if (!s) return;
    let d;
    try { d = await API.get('/api/suppliers/' + s.id + '/tra-ke-toan'); } catch (e) { return EPL.baoLoi(e); }
    const n = d.ncc || {}, dn = d.de_nghi || [];
    const tom = `<div class="ncc-tom">
        <div><span>${NN.h('owed_lak')}</span><b>${lak(n.phat_sinh_lak)}</b></div><div><span>${NN.h('paid_lak')}</span><b>${lak(n.da_tra_lak)}</b></div>
        <div><span>${NN.h('ncc_cho_chi')}</span><b>${lak(n.cho_chi_lak)}</b></div><div class="${n.con_no_lak > 0 ? 'neg' : ''}"><span>${NN.h('balance_lak')}</span><b>${lak(n.con_no_lak)}</b></div></div>`;
    const dongDn = `<h4>${NN.h('cx_de_nghi')}</h4>` + (dn.length ? `<table class="tbl tbl-compact"><tbody>${dn.map(r => {
      const t = ttTra(r);
      return `<tr class="${r.status === 'huy' ? 'ncc-mo' : ''}"><td><span class="mono small">${esc(r.ref_no)}</span><div class="small muted">${EPL.ngayGio(r.created_at)}${r.created_by ? ' · <span lang="lo">' + esc(r.created_by) + '</span>' : ''}</div></td>
        <td>${EPL.tag(t[0], t[1])} <span class="mono small">${esc(r.document_no || '')}</span>
          ${r.status === 'loi' && r.error_message ? `<div class="small neg">${esc(r.error_message)}</div>` : ''}${r.status === 'da_chi' ? `<div class="small" lang="lo">${esc(r.post_by || '')} · ${EPL.ngayGio(r.post_at)}</div>` : ''}
          ${r.dien_giai ? `<div class="small muted" lang="lo">${esc(r.dien_giai)}</div>` : ''}</td>
        <td class="num"><b>${EPL.tien(r.amount, r.currency)}</b>${r.currency !== 'LAK' && r.amount_lak != null ? `<div class="small muted">≈ ${lak(r.amount_lak)}</div>` : ''}<div class="small muted">${NN.h(r.phuong_thuc === 'bank' ? 'cx_chuyen_khoan' : 'cx_tien_mat')}</div></td>
        <td class="nowrap">${r.status === 'da_gui' ? `<button class="btn sm" type="button" data-cx="cap-nhat" data-id="${esc(r.id)}">${NN.h('ck_cap_nhat')}</button>` : ''}
          ${lapTra() && r.status === 'loi' ? `<button class="btn sm warn" type="button" data-cx="gui-lai" data-id="${esc(r.id)}">${NN.h('ck_gui_lai')}</button>` : ''}
          ${lapTra() && ['da_gui', 'loi'].includes(r.status) ? `<button class="btn sm" type="button" data-cx="huy" data-id="${esc(r.id)}" data-so="${esc(r.document_no || r.ref_no)}">${NN.h('cx_bo')}</button>` : ''}</td></tr>`;
    }).join('')}</tbody></table>` : `<p class="small muted">${NN.h('ncc_chua_de_nghi')}</p>`);
    // Trả theo đợt nên số gõ tay; gợi ý sẵn số còn nợ. Tiền khác Kíp thì gõ tỷ giá của lần trả (trống: máy lấy tỷ giá đang dùng).
    // Ô lập đặt TRÊN danh sách đề nghị cũ: nhà cung cấp nhiều lần trả thì danh sách dài, ô lập bị đẩy khuất dưới đáy hộp (1366).
    const form = lapTra() ? `<h4>${NN.h('cx_lap')}</h4><div class="ncc-form">
        <div class="field"><label>${NN.h('ncc_so_tien_tra')}</label><input id="ncc-tra-tien" class="num" inputmode="decimal" value="${n.con_no_lak > 0 ? esc(n.con_no_lak) : ''}"></div>
        <div class="field"><label>${NN.h('cur')}</label><select id="ncc-tra-tt">${EPL.TIEN_TE.map(m => `<option value="${m}">${m}</option>`).join('')}</select></div>
        <div class="field" id="ncc-tra-tg-o" hidden><label>${NN.h('rate_to_lak')}</label><input id="ncc-tra-tg" class="num" inputmode="decimal"></div>
        <div class="field"><label>${NN.h('cx_cach_tra')}</label><select id="ncc-tra-pt"><option value="cash">${NN.h('cx_tien_mat')}</option><option value="bank">${NN.h('cx_chuyen_khoan')}</option></select></div>
        <div class="field ncc-form-rong"><label>${NN.h('note')}</label><input id="ncc-tra-ghi" lang="lo"></div></div>` : '';
    const hoi = EPL.hoi(NN.t('cx_tra_kt') + ' · ' + s.name, `<div class="ncc-tra"><p class="small muted">${NN.h('ncc_tra_giai_thich')}</p>${tom}${form}${dongDn}</div>`,
      NN.t(lapTra() ? 'cx_lap' : 'close'));
    const hop = document.getElementById('ht-noi-dung');
    const oTt = hop.querySelector('#ncc-tra-tt');
    if (oTt) oTt.addEventListener('change', () => { hop.querySelector('#ncc-tra-tg-o').hidden = oTt.value === 'LAK'; });
    hop.querySelectorAll('[data-cx]').forEach(b => b.addEventListener('click', async () => {
      const viec = b.dataset.cx, id = b.dataset.id, soPhieu = b.dataset.so;
      await dongHop();
      // Bỏ = rút phiếu chi chưa chi bên hệ kế toán — hỏi lại bằng hộp trong ứng dụng, không dùng confirm() của trình duyệt
      if (viec === 'huy' && !await EPL.hoi(NN.t('cx_bo'), '<p>' + NN.h('ncc_bo_hoi', { so: soPhieu }) + '</p>', NN.t('cx_bo'))) return traKeToan(s);
      try { const r = await API.post(`/api/chi-ncc/${id}/${viec}`, {}); EPL.toast(NN.t(ttTra(r)[1]), r.status === 'loi' ? 'loi' : 'ok'); }
      catch (e) { EPL.baoLoi(e); }
      await tai().catch(EPL.baoLoi);
      traKeToan(s);
    }));
    if (!await hoi || !lapTra()) return;
    const than = { so_tien: hop.querySelector('#ncc-tra-tien').value.trim(), tien_te: oTt.value, phuong_thuc: hop.querySelector('#ncc-tra-pt').value,
      ghi_chu: hop.querySelector('#ncc-tra-ghi').value.trim() };
    if (than.tien_te !== 'LAK' && hop.querySelector('#ncc-tra-tg').value.trim()) than.ty_gia = hop.querySelector('#ncc-tra-tg').value.trim();
    if (!(EPL.doc(than.so_tien) > 0)) { EPL.toast(NN.t('ncc_so_tien_tra') + '?', 'loi'); return traKeToan(s); }
    let r;
    try { r = await API.post('/api/suppliers/' + s.id + '/de-nghi-tra', than); }
    catch (e) {
      // trả vượt số còn nợ (trừ nhà cung cấp trả trước): máy chủ chặn 409 TRA_QUA_NO — hỏi rồi gửi lại kèm xac_nhan
      if (e.ma !== 'TRA_QUA_NO') { EPL.baoLoi(e); return traKeToan(s); }
      if (!await EPL.hoi(NN.t('ncc_qua_no'), '<p>' + NN.h('ncc_qua_no_hoi', { tra: EPL.tien(EPL.doc(than.so_tien), than.tien_te), no: so(n.con_no_lak) }) + '</p>', NN.t('cx_lap'))) return traKeToan(s);
      try { r = await API.post('/api/suppliers/' + s.id + '/de-nghi-tra', { ...than, xac_nhan: true }); } catch (e2) { EPL.baoLoi(e2); return traKeToan(s); }
    }
    // gửi sang kế toán hỏng thì máy chủ vẫn giữ đề nghị (status loi) — báo lỗi, bấm Gửi lại trong hộp
    if (r.status === 'loi') EPL.toast(NN.t('ck_loi_ngan') + (r.error_message ? ': ' + r.error_message : ''), 'loi');
    else EPL.toast(NN.t('cx_da_lap', { so: r.document_no || r.ref_no }), 'ok');
    await tai().catch(EPL.baoLoi);
    traKeToan(s);
  }

  async function tai() {
    ds = await API.get('/api/suppliers');
    // tiền của mọi nhà cung cấp một lượt; lỗi thì báo — cột tiền hiện "—", danh mục vẫn dùng được
    if (xemTra()) {
      try { NO = Object.fromEntries((await API.get('/api/suppliers/cong-no')).map(x => [x.id, x])); }
      catch (e) { NO = {}; EPL.baoLoi(e); }
    }
    ve();
  }
  EPL.modules['nha-cung-cap'] = {
    async init(r) {
      root = r; NO = {};
      const t = r.querySelector('#ncc-them'); t.hidden = !AUTH.la('expacct'); t.addEventListener('click', () => sua(null));
      // khách (ô cấn trừ) · khoản mục cấu hình · quyền (cờ danh mục chung) — thiếu cái nào thì hộp dùng dự phòng, không chặn màn
      [KH, KM, QUYEN] = await Promise.all([API.get('/api/customers').catch(() => []), API.get('/api/khoan-muc').catch(() => ({})),
        API.get('/api/suppliers/quyen').catch(() => ({}))]);
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();
