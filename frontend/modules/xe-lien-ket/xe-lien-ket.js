/* Xe liên kết — danh mục chủ xe liên kết: điều khoản (phí, ngưỡng tấn, cách trả, tiền thuê) và hợp đồng thuê xe.
 * TRẢ CHỦ XE từ 01/10 (chủ dự án: tiền chi thật ở hệ kế toán anh Tune, trạng thái về bên mình): nút "Trả qua kế toán" của
 * từng chủ xe — chọn phiếu đã khoá chưa trả → đề nghị trả → phiếu chi "Chi khác" bên đó (Nợ 4022 / Có tiền); thủ quỹ chi và
 * ghi sổ ở đó; màn này hỏi lại, đã ghi sổ thì các phiếu thành "đã trả chủ xe". API: /api/owners/{id}/tra-ke-toan,
 * /api/owners/{id}/de-nghi-tra, /api/chi-chu-xe/{id}/cap-nhat|gui-lai|huy. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, chu = [], HD = [], chuHd = null, QUYEN = {};
  const OPM = { phieu: 'opm_phieu', thang: 'opm_thang', dot: 'opm_dot' };

  /* ---------------------------------------------------------------- chủ xe liên kết (C4.2 · C4.3) */
  function veChu() {
    const o = root.querySelector('#xlk-chu'); if (!o) return;
    const themDuoc = AUTH.la('acct');
    root.querySelector('#xlk-them-chu').hidden = !themDuoc;
    o.innerHTML = chu.length ? chu.map(c => {
      return `<tr class="${c.active ? '' : 'xlk-tat'}">
        <td lang="lo"><b>${esc(c.name)}</b>${c.note ? `<div class="small muted">${esc(c.note)}</div>` : ''}</td>
        <td class="mono">${esc(c.phone || '—')}</td><td class="mono">${(c.so_xe || []).map(esc).join(', ') || '—'}</td>
        <td>${EPL.hopDong.nhan(EPL.hopDong.hienHanh(HD, c.id))}</td>
        <td>${NN.h(OPM[c.pay_mode] || 'opm_phieu')}</td>
        <td class="num tien">${c.fee_pct != null ? so(c.fee_pct, 1) + ' %' : '—'}</td>
        <td class="num tien">${c.over_limit_t != null ? `${so(c.over_limit_t, 1)} t · ${EPL.tien(c.over_price, c.hire_ccy)}/t` : '—'}</td>
        <td class="mono tien">${esc(c.hire_ccy || '')}</td>
        <td class="no-print nowrap">${themDuoc ? `<button class="btn sm" data-sua-chu="${c.id}">${NN.h('edit')}</button> ` : ''}<button class="btn sm ${chuHd && chuHd.id === c.id ? 'primary' : ''}" data-hd-chu="${c.id}">${NN.h('hd_nut')}</button>${xemTra() ? ` <button class="btn sm" data-tra-chu="${c.id}">${NN.h('cx_tra_kt')}</button>` : ''}`
        + (themDuoc ? ` <button class="btn sm danger" data-xoa-chu="${c.id}">${NN.h('delete')}</button>` : '') + `</td></tr>`;
    }).join('') : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    o.querySelectorAll('[data-hd-chu]').forEach(b => b.addEventListener('click', () => moHd(chu.find(x => x.id === b.dataset.hdChu))));
    o.querySelectorAll('[data-sua-chu]').forEach(b => b.addEventListener('click', () => suaChu(chu.find(x => x.id === b.dataset.suaChu))));
    o.querySelectorAll('[data-tra-chu]').forEach(b => b.addEventListener('click', () => traKeToan(chu.find(x => x.id === b.dataset.traChu))));
    o.querySelectorAll('[data-xoa-chu]').forEach(b => b.addEventListener('click', () => xoaChu(chu.find(x => x.id === b.dataset.xoaChu))));
  }
  /** 09/10 (anh Khampla: "có chỗ xoá không"): xoá chủ xe nhập nhầm. Máy chủ chặn khi chủ xe đã có xe / phiếu / hợp đồng / đề nghị trả
   *  (409, câu nói rõ vì sao và bảo dùng Sửa → Ngưng dùng). */
  async function xoaChu(c) {
    if (!c || !await EPL.hoi(NN.t('delete') + ' · ' + c.name, '<p>' + NN.h('cx_xoa_hoi', { ten: c.name }) + '</p>', NN.t('delete'))) return;
    try { await API.del('/api/owners/' + c.id); EPL.toast(NN.t('cx_da_xoa', { ten: c.name }), 'ok'); }
    catch (e) { return EPL.baoLoi(e); }
    if (chuHd && chuHd.id === c.id) { chuHd = null; root.querySelector('#xlk-hd').hidden = true; }
    await tai().catch(EPL.baoLoi);
  }

  /* ---------------------------------------------------------------- trả chủ xe qua hệ kế toán (01/10) */
  // tiền thuê xe liên kết là tiền bán — Bãi, tài xế, thủ kho, tổ sửa không thấy; lập đề nghị: KT Thu/Chi VC và Sếp
  const xemTra = () => AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel');
  const lapTra = () => AUTH.la('acct');
  const TT_TRA = { da_gui: ['partial', 'ck_cho_chi'], da_chi: ['paid', 'ck_da_chi_ngan'], loi: ['unpaid', 'ck_loi_ngan'], huy: ['plain', 'cx_da_bo'] };
  async function traKeToan(c) {
    let d;
    try { d = await API.get('/api/owners/' + c.id + '/tra-ke-toan'); } catch (e) { return EPL.baoLoi(e); }
    const dn = d.de_nghi || [], cho = d.cho || [];
    const dongDn = dn.length ? `<h4>${NN.h('cx_de_nghi')}</h4><table class="tbl tbl-compact"><tbody>${dn.map(r => {
      const t = TT_TRA[r.status] || TT_TRA.loi;
      return `<tr><td class="mono small">${esc(r.ref_no)}</td><td>${EPL.tag(t[0], t[1])} <span class="mono small">${esc(r.document_no || '')}</span>
        ${r.status === 'loi' ? `<div class="small neg">${esc(r.error_message || '')}</div>` : ''}${r.status === 'da_chi' ? `<div class="small" lang="lo">${esc(r.post_by || '')} · ${EPL.ngayGio(r.post_at)}</div>` : ''}</td>
        <td class="num">${r.trip_ids.length} ${NN.h('cx_phieu')}</td><td class="num">${EPL.tien(r.amount, r.currency)}</td>
        <td class="nowrap">${r.status === 'da_gui' ? `<button class="btn sm" type="button" data-cx="cap-nhat" data-id="${esc(r.id)}">${NN.h('ck_cap_nhat')}</button>` : ''}
          ${lapTra() && r.status === 'loi' ? `<button class="btn sm warn" type="button" data-cx="gui-lai" data-id="${esc(r.id)}">${NN.h('ck_gui_lai')}</button>` : ''}
          ${lapTra() && ['da_gui', 'loi'].includes(r.status) ? `<button class="btn sm" type="button" data-cx="huy" data-id="${esc(r.id)}">${NN.h('cx_bo')}</button>` : ''}</td></tr>`;
    }).join('')}</tbody></table>` : '';
    const dongCho = cho.length ? `<h4>${NN.h('cx_cho_tra')}</h4><table class="tbl tbl-compact"><thead><tr><th></th><th>${NN.h('doc_no')}</th>
        <th>${NN.h('c_truck')}</th><th class="num">${NN.h('ton')}</th><th class="num">${NN.h('cx_tra')}</th></tr></thead>
      <tbody>${cho.map(x => `<tr><td><input type="checkbox" class="cx-chon" value="${esc(x.id)}" data-ccy="${esc(x.hire_ccy || 'LAK')}" data-tien="${x.tra_chu_xe || 0}" ${lapTra() ? 'checked' : 'disabled'}></td>
        <td><span class="mono">${esc(x.doc_no)}</span><div class="small muted">${EPL.ngay(x.doc_date)}</div></td><td>${esc(x.truck_no || '')}</td><td class="num">${so(x.tan_tinh, 2)}</td>
        <td class="num"><b>${EPL.tien(x.tra_chu_xe, x.hire_ccy)}</b><div class="small muted">${NN.h('cx_tien_thue')} ${EPL.tien(x.tien_thue, x.hire_ccy)} − ${EPL.tien((x.phi || 0) + (x.tru_vuot || 0) + (x.ung_truoc || 0), x.hire_ccy)}</div></td></tr>`).join('')}</tbody></table>
      ${lapTra() ? `<div class="field"><label>${NN.h('cx_cach_tra')}</label><select id="cx-pt"><option value="cash">${NN.h('cx_tien_mat')}</option><option value="bank">${NN.h('cx_chuyen_khoan')}</option></select></div>
        <div class="small" id="cx-tong"></div>` : ''}` : `<p class="muted">${NN.h('cx_khong_cho')}</p>`;
    const hoi = EPL.hoi(NN.t('cx_tra_kt') + ' · ' + c.name, `<div class="cx-tra"><p class="small muted">${NN.h('cx_giai_thich')}</p>${dongDn}${dongCho}</div>`,
      NN.t(lapTra() && cho.length ? 'cx_lap' : 'close'));
    const hop = document.getElementById('ht-noi-dung');
    const tong = () => {
      const chon = [...hop.querySelectorAll('.cx-chon:checked')], tien = [...new Set(chon.map(x => x.dataset.ccy))];
      const o = hop.querySelector('#cx-tong'); if (!o) return;
      o.innerHTML = tien.length > 1 ? `<span class="neg">${NN.h('cx_khac_tien')}</span>`
        : NN.h('cx_tong', { n: chon.length, tien: EPL.tien(chon.reduce((a, x) => a + (+x.dataset.tien || 0), 0), tien[0] || '') });
    };
    hop.querySelectorAll('.cx-chon').forEach(x => x.addEventListener('change', tong)); tong();
    hop.querySelectorAll('[data-cx]').forEach(b => b.addEventListener('click', async () => {
      try { const r = await API.post(`/api/chi-chu-xe/${b.dataset.id}/${b.dataset.cx}`, {}); EPL.toast(NN.t((TT_TRA[r.status] || TT_TRA.loi)[1]), r.status === 'loi' ? 'loi' : 'ok'); }
      catch (e) { EPL.baoLoi(e); }
      document.getElementById('hop-thoai').close(); traKeToan(c);
    }));
    if (!await hoi || !lapTra() || !cho.length) return;
    const ids = [...hop.querySelectorAll('.cx-chon:checked')].map(x => x.value);
    if (!ids.length) return EPL.toast(NN.t('cx_chua_chon'), 'loi');
    const pt = (hop.querySelector('#cx-pt') || {}).value || 'cash';
    try {
      const r = await API.post('/api/owners/' + c.id + '/de-nghi-tra', { trip_ids: ids, phuong_thuc: pt });
      EPL.toast(NN.t('cx_da_lap', { so: r.document_no || r.ref_no }), 'ok');
    } catch (e) { EPL.baoLoi(e); }
    traKeToan(c);
  }
  /** Hộp thêm / sửa chủ xe — 09/10 (anh Khampla: "thêm xe ngoài không có chỗ đánh sổ tài khoản"): hai cột, thêm TK Nợ / Có chọn từ
   *  sổ tài khoản (trống = 621 thuê xe / 4022 phải trả chủ xe). Máy chủ chặn → mở lại hộp, giữ chữ đã gõ, đánh dấu ô lỗi. */
  async function suaChu(c, nhap, loi) {
    const acc = await EPL.accCodes();
    const g = (k, md = '') => nhap && k in nhap ? nhap[k] : (c && c[k] != null ? c[k] : md);
    const loiO = (k) => (loi && loi.o === k ? loi.chu : null);
    const chung = !!(QUYEN.gls && c && c.obj_id);     // đã gắn danh mục nhà cung cấp chung: tên · điện thoại · địa chỉ sửa ở đó
    const v = await EPL.hopNhap(c ? NN.t('edit') + ' · ' + c.name : NN.t('owner_add'), [
      { type: 'nhom', label: 'ncc_nhom_chung' },
      { id: 'name', label: 'owner', value: g('name'), lo: true, bat_buoc: true, chi_doc: chung, loi: loiO('name'), goi_y: chung ? 'o_chung_goi_y' : null },
      { id: 'phone', label: 'phone', type: 'tel', value: g('phone'), chi_doc: chung },
      { id: 'address', label: 'address', value: g('address'), lo: true, rong: true, chi_doc: chung },
      { type: 'nhom', label: 'cx_nhom_dieu_khoan' },
      { id: 'pay_mode', label: 'owner_pay_mode', type: 'select', value: g('pay_mode', 'phieu'), loi: loiO('pay_mode'), options: Object.entries(OPM).map(([k, t]) => [k, NN.t(t)]) },
      { id: 'hire_ccy', label: 'ccy_hire', type: 'select', value: g('hire_ccy', 'USD'), options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'fee_pct', label: 'fee_pct', type: 'number', value: g('fee_pct', 2), loi: loiO('fee_pct') },
      { id: 'over_limit_t', label: 'limit_t', type: 'number', value: g('over_limit_t', 40) },
      { id: 'over_price', label: 'over_p', type: 'number', value: g('over_price', 1) },
      ...(c ? [{ id: 'active', label: 'status', type: 'bat', value: g('active', true) }] : []),
      { type: 'nhom', label: 'tk_nhom' },
      { id: 'acct_no', label: 'acct_debit', type: 'select', tim: 'tk_tim', value: g('acct_no'), loi: loiO('acct_no'), goi_y: 'cx_tk_no_goi_y',
        options: EPL.dsTaiKhoan(acc, '6', g('acct_no'), NN.t('cx_tk_no_md')) },
      { id: 'acct_co', label: 'acct_credit', type: 'select', tim: 'tk_tim', value: g('acct_co'), loi: loiO('acct_co'), goi_y: 'cx_tk_co_goi_y',
        options: EPL.dsTaiKhoan(acc, '4', g('acct_co'), NN.t('cx_tk_co_md')) },
      { id: 'note', label: 'note', type: 'textarea', dong: 2, value: g('note'), lo: true, rong: true },
    ], NN.t('save'), { cot: 2 });
    if (!v) return;
    if (!v.name.trim()) return suaChu(c, v, { o: 'name', chu: NN.t('owner') + '?' });
    const body = { name: v.name, phone: v.phone, address: v.address, pay_mode: v.pay_mode, hire_ccy: v.hire_ccy, fee_pct: v.fee_pct, over_limit_t: v.over_limit_t,
      over_price: v.over_price, note: v.note, acct_no: v.acct_no, acct_co: v.acct_co };
    if (chung) ['name', 'phone', 'address'].forEach(k => delete body[k]);
    if (c) body.active = v.active;
    try { await (c ? API.put('/api/owners/' + c.id, body) : API.post('/api/owners', body)); }
    catch (e) {
      if (e.ma === 'HUY') return;
      EPL.baoLoi(e);
      return suaChu(c, v, { o: Array.isArray(e.o) ? e.o[0] : e.o, chu: e.message });
    }
    EPL.toast(NN.t('saved'), 'ok');
    await tai().catch(EPL.baoLoi);
  }
  async function taiHd() { try { HD = await API.get('/api/hop-dong?kind=thue_xe'); } catch (e) { HD = []; EPL.baoLoi(e); } }   // lỗi thì báo — cột hợp đồng trống mà im lặng là tưởng chủ xe chưa có hợp đồng
  async function moHd(c) {
    chuHd = c; veChu();
    await EPL.hopDong.mo(root.querySelector('#xlk-hd'), { kind: 'thue_xe', doiTacId: c.id, ten: c.name, suaDuoc: AUTH.la('acct'),
      onDoi: async () => { await taiHd(); if (root.querySelector('#xlk-hd').hidden) chuHd = null; veChu(); } });
  }
  async function tai() {
    // lỗi máy chủ KHÔNG nuốt thành danh sách rỗng (rà 01/10): bảng "chưa có dữ liệu" trong khi chủ xe vẫn còn đó — lúc mở
    // màn thì khung hiện lỗi, sau khi lưu thì nơi gọi báo lỗi; mọi vai đều đọc được /api/owners. Hai câu hỏi song song.
    [, chu] = await Promise.all([taiHd(), API.get('/api/owners')]);
    veChu();
  }
  EPL.modules['xe-lien-ket'] = {
    async init(r) {
      root = r; chuHd = null;          // HTML mới: khối hợp đồng đóng — đừng để nút "Hợp đồng" của lần trước còn sáng
      r.querySelector('#xlk-them-chu').addEventListener('click', () => suaChu(null));
      QUYEN = await API.get('/api/suppliers/quyen').catch(() => ({}));     // cờ danh mục chung (gls) — chủ xe cùng danh mục nhà cung cấp
      await tai();
    },
    // khối hợp đồng đang mở (js/hop_dong.js) dựng chữ lúc mở — đổi tiếng thì dựng lại, không để tiêu đề / nút còn tiếng cũ
    onLang() { if (root) { veChu(); if (chuHd && !root.querySelector('#xlk-hd').hidden) moHd(chuHd); } },
  };
})();
