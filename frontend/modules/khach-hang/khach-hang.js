/* Khách hàng — xem · thêm · sửa · ngưng dùng. Không xoá cứng: phiếu cũ còn trỏ tới. */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [];
  const suaDuoc = () => AUTH.la('yard', 'acct');

  function ve() {
    const q = root.querySelector('#kh-q').value.trim().toLowerCase();
    const rows = ds.filter(c => !q || [c.name, c.phone, c.address].join(' ').toLowerCase().includes(q));
    root.querySelector('#kh-than').innerHTML = rows.length ? rows.map((c, i) => `<tr class="${c.active ? '' : 'kh-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(c.name)}</b></td><td>${esc(c.phone) || '—'}</td><td lang="lo">${esc(c.address) || '—'}</td><td class="small muted">${esc(c.note) || ''}</td>
      <td>${EPL.tag(c.active ? 'ok' : 'plain', c.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${c.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
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
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();
