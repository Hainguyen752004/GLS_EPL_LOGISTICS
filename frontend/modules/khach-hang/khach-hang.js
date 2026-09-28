/* Khách hàng — xem · thêm · sửa · ngưng dùng. Không xoá cứng: phiếu cũ còn trỏ tới. */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [], tuyen = [], khGia = null, dsGia = [], khNo = null, NO = null, HD = [], khHd = null;
  const suaHd = () => AUTH.la('acct', 'rev');         // hợp đồng vận chuyển: KT Thu/Chi, KT Doanh thu (Sếp luôn được)
  const suaDuoc = () => AUTH.la('yard', 'acct');
  // Giá là tiền: Bãi không thấy; KT Thu/Chi VC (kiểm mục II) và Sếp được sửa; các vai tiền khác xem
  const xemGia = () => AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash', 'admin');
  const suaGia = () => AUTH.la('acct', 'admin');
  const so = (v, d = 2) => v == null || v === '' ? '—' : EPL.doc(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  function ve() {
    const q = root.querySelector('#kh-q').value.trim().toLowerCase();
    const rows = ds.filter(c => !q || [c.name, c.phone, c.address].join(' ').toLowerCase().includes(q));
    root.querySelector('#kh-than').innerHTML = rows.length ? rows.map((c, i) => `<tr class="${c.active ? '' : 'kh-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(c.name)}</b></td><td>${esc(c.phone) || '—'}</td><td lang="lo">${esc(c.address) || '—'}</td><td class="small muted">${esc(c.note) || ''}</td>
      <td>${EPL.tag(c.invoice_mode === 'thang' ? 'dispatched' : 'plain', c.invoice_mode === 'thang' ? 'inv_thang_s' : 'inv_phieu_s')}</td>
      <td>${EPL.hopDong.nhan(EPL.hopDong.hienHanh(HD, c.id))}</td>
      <td>${EPL.tag(c.active ? 'ok' : 'plain', c.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${c.id}">${NN.h('edit')}</button>` : ''} <button class="btn sm ${khHd && khHd.id === c.id ? 'primary' : ''}" data-hd="${c.id}">${NN.h('hd_nut')}</button> ${xemGia() ? `<button class="btn sm ${khGia && khGia.id === c.id ? 'primary' : ''}" data-gia="${c.id}">${NN.h('kh_bang_gia')}</button> <button class="btn sm ${khNo && khNo.id === c.id ? 'primary' : ''}" data-no="${c.id}">${NN.h('kh_cong_no')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-hd]').forEach(b => b.addEventListener('click', () => moHd(ds.find(x => x.id === b.dataset.hd))));
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
    root.querySelectorAll('[data-gia]').forEach(b => b.addEventListener('click', () => moGia(ds.find(x => x.id === b.dataset.gia))));
    root.querySelectorAll('[data-no]').forEach(b => b.addEventListener('click', () => moNo(ds.find(x => x.id === b.dataset.no))));
  }

  /* ---------------------------------------------------------------- công nợ khách: còn nợ EPL bao nhiêu */
  async function moNo(c) {
    khNo = c;
    try { NO = await API.get(`/api/customers/${c.id}/cong-no`); } catch (e) { NO = null; return EPL.baoLoi(e); }
    veNo(); ve();
    const k = root.querySelector('#kh-no'); if (k.scrollIntoView) k.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function veNo() {
    const kh = root.querySelector('#kh-no'); kh.hidden = !khNo || !NO; if (!khNo || !NO) return;
    root.querySelector('#kh-no-ten').textContent = NN.t('kh_no_cua').replace('{n}', khNo.name);
    const conTien = Object.entries(NO.con_no_tien || {}).map(([m, v]) => EPL.tien(v, m)).join(' · ') || '0';
    root.querySelector('#kh-no-tong').innerHTML = `<div class="kh-no-tong">
      <div><span>${NN.h('kh_no_so_to')}</span><b>${NO.so_to} · ${NO.so_to_no} ${NN.t('kh_no_con')}</b></div>
      <div><span>${NN.h('kh_no_tong')}</span><b>${EPL.tienGop(NO.tong_tien)}</b></div>
      <div><span>${NN.h('collected')}</span><b>${so(NO.da_thu_lak, 0)} LAK</b></div>
      <div><span>${NN.h('kh_no_con_no')}</span><b class="${NO.con_no_lak > 0 ? 'neg' : 'pos'}">${conTien}<small> ≈ ${so(NO.con_no_lak, 0)} LAK</small></b></div>
    </div>`;
    root.querySelector('#kh-no-than').innerHTML = (NO.dong || []).length ? NO.dong.map(x => `<tr class="${x.con_lai_lak > 0 ? '' : 'kh-tat'}">
      <td>${NN.h(x.loai === 'gop' ? 'kh_no_gop' : 'kh_no_phieu')}${x.loai === 'gop' ? ` <span class="small muted">· ${x.so_phieu} ${NN.t('hg_so_phieu').toLowerCase()}</span>` : ''}</td>
      <td class="mono">${x.loai === 'gop' ? `<a href="" data-kt-gop="${esc(x.id)}" data-thang="${esc(String(x.ngay || '').slice(0, 7))}">${esc(x.so)} ↗</a>` : `<a href="#/phieu-xuat-xe?id=${esc(x.id)}">${esc(x.so)}</a>`}</td>
      <td>${EPL.ngay(x.ngay)}</td><td class="mono">${esc(x.ccy)}</td>
      <td class="num"><b>${EPL.tien(x.tien, x.ccy)}</b></td><td class="num">${so(x.tien_lak, 0)}</td>
      <td class="num">${so(x.da_thu_lak, 0)}</td><td class="num ${x.con_lai_lak > 0 ? 'neg' : ''}">${so(x.con_lai_lak, 0)}</td>
      <td>${EPL.tag(x.finance_status)}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('kh_no_trong')}</td></tr>`;
    // tờ gộp tháng ở trang kế toán từ 28/09 (đợt 7a) — mở bên đó
    root.querySelectorAll('#kh-no-than [data-kt-gop]').forEach(a => a.addEventListener('click', (e) => {
      e.preventDefault(); EPL.moKeToan('hoa-don-gop', { thang: a.dataset.thang, id: a.dataset.ktGop }); }));
  }

  /* ---------------------------------------------------------------- bảng giá khách × tuyến */
  async function moGia(c) {
    khGia = c; if (!tuyen.length) tuyen = await API.get('/api/routes');
    dsGia = await API.get(`/api/customers/${c.id}/bang-gia`); veGia(); ve();
    const kg = root.querySelector('#kh-gia'); if (kg.scrollIntoView) kg.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function veGia() {
    const kh = root.querySelector('#kh-gia'); kh.hidden = !khGia; if (!khGia) return;
    root.querySelector('#kh-gia-ten').textContent = NN.t('kh_gia_cua').replace('{n}', khGia.name);
    root.querySelector('#kh-gia-them').hidden = !suaGia();
    root.querySelector('#kh-gia-than').innerHTML = dsGia.length ? dsGia.map(r => `<tr class="${r.active ? '' : 'kh-tat'}">
      <td lang="lo"><b>${esc(r.route_name || '')}</b></td><td>${NN.h(r.goods_type === 'iron_ore' ? 'iron_ore' : 'other_goods')}</td>
      <td class="mono small">${esc(r.price_ccy || 'USD')}</td><td class="num"><b>${so(r.price, EPL.leTien(r.price_ccy))}</b><span class="small muted"> ${NN.h(r.price_mode === 'chuyen' ? 'pm_chuyen_s' : 'pm_ton_s')}</span></td><td class="num">${r.hire_price == null ? '—' : EPL.tien(r.hire_price, r.hire_ccy || r.price_ccy)}</td>
      <td>${r.valid_from ? EPL.ngay(r.valid_from) : '—'}</td><td class="small muted">${esc(r.note) || ''}</td>
      <td>${EPL.tag(r.active ? 'ok' : 'plain', r.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaGia() ? `<button class="btn sm" data-sua-gia="${r.id}">${NN.h('edit')}</button> <button class="btn sm danger" data-xoa-gia="${r.id}">${NN.h('delete')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('kh_gia_trong')}</td></tr>`;
    root.querySelectorAll('[data-sua-gia]').forEach(b => b.addEventListener('click', () => suaGiaDong(dsGia.find(x => x.id === b.dataset.suaGia))));
    root.querySelectorAll('[data-xoa-gia]').forEach(b => b.addEventListener('click', () => xoaGia(dsGia.find(x => x.id === b.dataset.xoaGia))));
  }
  async function suaGiaDong(r) {
    const v = await EPL.hopNhap(NN.t('kh_bang_gia') + ' · ' + khGia.name, [
      { id: 'route_id', label: 'route', type: 'select', value: r ? r.route_id : (tuyen[0] || {}).id, options: tuyen.filter(t => t.active || (r && t.id === r.route_id)).map(t => [t.id, t.name]) },
      { id: 'goods_type', label: 'goods_type', type: 'select', value: r ? r.goods_type : 'iron_ore', options: [['iron_ore', NN.t('iron_ore')], ['other_goods', NN.t('other_goods')]] },
      { id: 'price_ccy', label: 'ccy_price', type: 'select', value: r ? (r.price_ccy || 'USD') : 'USD', options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'price_mode', label: 'price_mode', type: 'select', value: r ? (r.price_mode || 'ton') : 'ton', options: [['ton', NN.t('pm_ton')], ['chuyen', NN.t('pm_chuyen')]] },
      { id: 'price', label: 'price_usd', type: 'number', value: r ? r.price : '' },
      { id: 'hire_ccy', label: 'ccy_hire', type: 'select', value: r ? (r.hire_ccy || '') : '', options: [['', '—']].concat(EPL.TIEN_TE.map(m => [m, m])) },
      { id: 'hire_price', label: 'hire_pt', type: 'number', value: r ? (r.hire_price ?? '') : '' },
      { id: 'valid_from', label: 'valid_from', type: 'date', value: r ? (r.valid_from || '') : EPL.homNay() },
      { id: 'note', label: 'note', type: 'textarea', value: r ? r.note : '' },
      ...(r ? [{ id: 'active', label: 'status', type: 'select', value: r.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!(EPL.doc(v.price) > 0)) return EPL.toast(NN.t('price_usd') + '?', 'loi');
    try {
      const body = { route_id: v.route_id, goods_type: v.goods_type, price: v.price, price_ccy: v.price_ccy, price_mode: v.price_mode,
        hire_price: v.hire_price === '' ? null : v.hire_price, hire_ccy: v.hire_ccy || null, valid_from: v.valid_from || null, note: v.note };
      if (r) body.active = v.active === '1';
      await (r ? API.put('/api/bang-gia/' + r.id, body) : API.post(`/api/customers/${khGia.id}/bang-gia`, body));
      EPL.toast(NN.t('saved'), 'ok'); dsGia = await API.get(`/api/customers/${khGia.id}/bang-gia`); veGia();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function xoaGia(r) {
    if (!await EPL.hoi(NN.t('delete'), `<p>${esc(r.route_name || '')} · ${EPL.tien(r.price, r.price_ccy)}/t</p>`, NN.t('delete'))) return;
    try { await API.del('/api/bang-gia/' + r.id); dsGia = dsGia.filter(x => x.id !== r.id); veGia(); EPL.toast(NN.t('saved'), 'ok'); } catch (e) { EPL.baoLoi(e); }
  }
  async function sua(c) {
    const v = await EPL.hopNhap(c ? NN.t('edit') : NN.t('add'), [
      { id: 'name', label: 'name', value: c ? c.name : '', lo: true },
      { id: 'phone', label: 'phone', value: c ? c.phone : '' },
      { id: 'address', label: 'address', value: c ? c.address : '', lo: true },
      // Cách xuất hoá đơn (C8.2): khách hợp đồng nhận MỘT tờ cuối tháng; khách vãng lai mỗi phiếu một tờ.
      { id: 'invoice_mode', label: 'inv_mode', type: 'select', value: c ? (c.invoice_mode || 'phieu') : 'phieu',
        options: [['phieu', NN.t('inv_phieu')], ['thang', NN.t('inv_thang')]] },
      { id: 'note', label: 'note', type: 'textarea', value: c ? c.note : '' },
      ...(c ? [{ id: 'active', label: 'status', type: 'select', value: c.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    try {
      const body = { name: v.name, phone: v.phone, address: v.address, note: v.note, invoice_mode: v.invoice_mode };
      if (c) body.active = v.active === '1';
      await (c ? API.put('/api/customers/' + c.id, body) : API.post('/api/customers', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function taiHd() { try { HD = await API.get('/api/hop-dong?kind=khach'); } catch (e) { HD = []; } }
  async function moHd(c) {
    khHd = c; ve();
    await EPL.hopDong.mo(root.querySelector('#kh-hd'), { kind: 'khach', doiTacId: c.id, ten: c.name, suaDuoc: suaHd(),
      onDoi: async () => { await taiHd(); if (root.querySelector('#kh-hd').hidden) khHd = null; ve(); } });
  }
  async function tai() { ds = await API.get('/api/customers'); await taiHd(); ve(); }
  EPL.modules['khach-hang'] = {
    async init(r) {
      root = r; r.querySelector('#kh-q').addEventListener('input', ve);
      const them = r.querySelector('#kh-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null));
      r.querySelector('#kh-gia-them').addEventListener('click', () => suaGiaDong(null));
      r.querySelector('#kh-gia-dong').addEventListener('click', () => { khGia = null; veGia(); ve(); });
      r.querySelector('#kh-no-dong').addEventListener('click', () => { khNo = null; NO = null; veNo(); ve(); });
      await tai();
    },
    onLang() { if (root) { ve(); veGia(); veNo(); } },
  };
})();
