/* Kho phụ tùng — danh mục + nhập/xuất theo xe; tồn tối thiểu tô đỏ. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [];
  const suaDuoc = () => AUTH.la('yard', 'fuel', 'acct');

  function ve() {
    root.querySelector('#kpt-than').innerHTML = ds.length ? ds.map(p => `<tr class="${p.status === 'st_low' ? 'kpt-thap' : ''}">
      <td lang="lo"><b>${esc(p.name)}</b></td><td>${NN.h(p.unit)}</td><td class="num"><b>${so(p.qty)}</b></td><td class="num">${so(p.min_qty)}</td>
      <td class="num tien">${so(p.unit_price)}</td><td>${EPL.ngay(p.last_date)}</td><td>${esc(p.last_truck) || '—'}</td><td>${EPL.tag(p.status, p.status)}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm ok" data-nhap="${p.id}">+ ${NN.h('fs_in')}</button> <button class="btn sm warn" data-xuat="${p.id}">− ${NN.h('fuel_out')}</button> <button class="btn sm" data-sua="${p.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-nhap]').forEach(b => b.addEventListener('click', () => chuyen(b.dataset.nhap, 'in')));
    root.querySelectorAll('[data-xuat]').forEach(b => b.addEventListener('click', () => chuyen(b.dataset.xuat, 'out')));
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
  }
  async function chuyen(id, kind) {
    const p = ds.find(x => x.id === id);
    const v = await EPL.hopNhap(p.name, [
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'qty', label: 'qty', type: 'number', value: '1' },
      ...(kind === 'out' ? [{ id: 'truck_no', label: 'truck_no', value: '' }, { id: 'trip_doc_no', label: 'trip_doc_no', value: '' }] : []),
      { id: 'note', label: 'note', value: '' },
    ], NN.t(kind === 'in' ? 'fs_in' : 'fuel_out'));
    if (!v) return;
    try { await API.post(`/api/parts/${id}/moves`, { kind, ...v }); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function sua(p) {
    const v = await EPL.hopNhap(p ? NN.t('edit') : NN.t('add'), [
      { id: 'name', label: 'part', value: p ? p.name : '', lo: true },
      { id: 'unit', label: 'unit', type: 'select', value: p ? p.unit : 'u_pc', options: [['u_pc', NN.t('u_pc')], ['u_set', NN.t('u_set')], ['u_l', NN.t('u_l')]] },
      ...(p ? [] : [{ id: 'qty', label: 'stock', type: 'number', value: '0' }]),
      { id: 'min_qty', label: 'min_stock', type: 'number', value: p ? p.min_qty : '0' },
      { id: 'unit_price', label: 'unit_price', type: 'number', value: p ? p.unit_price : '' },
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('part') + '?', 'loi');
    try { await (p ? API.put('/api/parts/' + p.id, v) : API.post('/api/parts', v)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/parts'); ve(); }
  EPL.modules['kho-phu-tung'] = {
    async init(r) { root = r; const t = r.querySelector('#kpt-them'); t.hidden = !suaDuoc(); t.addEventListener('click', () => sua(null)); await tai(); },
    onLang() { if (root) ve(); },
  };
})();
