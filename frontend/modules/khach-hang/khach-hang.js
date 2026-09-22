/* Khách hàng — xem · thêm · sửa · ngưng dùng. Không xoá cứng: phiếu cũ còn trỏ tới. */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [], tuyen = [], khGia = null, dsGia = [];
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
      <td>${EPL.tag(c.active ? 'ok' : 'plain', c.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${c.id}">${NN.h('edit')}</button>` : ''} ${xemGia() ? `<button class="btn sm ${khGia && khGia.id === c.id ? 'primary' : ''}" data-gia="${c.id}">${NN.h('kh_bang_gia')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
    root.querySelectorAll('[data-gia]').forEach(b => b.addEventListener('click', () => moGia(ds.find(x => x.id === b.dataset.gia))));
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
      { id: 'note', label: 'note', type: 'textarea', value: c ? c.note : '' },
      ...(c ? [{ id: 'active', label: 'status', type: 'select', value: c.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    try {
      const body = { name: v.name, phone: v.phone, address: v.address, note: v.note };
      if (c) body.active = v.active === '1';
      await (c ? API.put('/api/customers/' + c.id, body) : API.post('/api/customers', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/customers'); ve(); }
  EPL.modules['khach-hang'] = {
    async init(r) {
      root = r; r.querySelector('#kh-q').addEventListener('input', ve);
      const them = r.querySelector('#kh-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null));
      r.querySelector('#kh-gia-them').addEventListener('click', () => suaGiaDong(null));
      r.querySelector('#kh-gia-dong').addEventListener('click', () => { khGia = null; veGia(); ve(); });
      await tai();
    },
    onLang() { if (root) { ve(); veGia(); } },
  };
})();
