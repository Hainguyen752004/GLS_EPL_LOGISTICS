/* Tài xế — xem · thêm · sửa · ngưng dùng. */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [];
  const suaDuoc = () => AUTH.la('yard', 'acct');

  function ve() {
    const q = root.querySelector('#tx-q').value.trim().toLowerCase();
    const rows = ds.filter(d => !q || [d.name, d.phone, d.license_no].join(' ').toLowerCase().includes(q));
    root.querySelector('#tx-than').innerHTML = rows.length ? rows.map((d, i) => `<tr class="${d.active ? '' : 'tx-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(d.name)}</b></td><td>${esc(d.phone) || '—'}</td><td class="mono">${esc(d.license_no) || '—'}</td><td class="small muted">${esc(d.note) || ''}</td>
      <td>${EPL.tag(d.active ? 'ok' : 'plain', d.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${d.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
  }
  async function sua(d) {
    const v = await EPL.hopNhap(d ? NN.t('edit') : NN.t('add'), [
      { id: 'name', label: 'name', value: d ? d.name : '', lo: true },
      { id: 'phone', label: 'phone', value: d ? d.phone : '' },
      { id: 'license_no', label: 'license_no', value: d ? d.license_no : '' },
      { id: 'note', label: 'note', type: 'textarea', value: d ? d.note : '' },
      ...(d ? [{ id: 'active', label: 'status', type: 'select', value: d.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    try {
      const body = { name: v.name, phone: v.phone, license_no: v.license_no, note: v.note };
      if (d) body.active = v.active === '1';
      await (d ? API.put('/api/drivers/' + d.id, body) : API.post('/api/drivers', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/drivers'); ve(); }
  EPL.modules['tai-xe'] = {
    async init(r) {
      root = r; r.querySelector('#tx-q').addEventListener('input', ve);
      const them = r.querySelector('#tx-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null));
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();
