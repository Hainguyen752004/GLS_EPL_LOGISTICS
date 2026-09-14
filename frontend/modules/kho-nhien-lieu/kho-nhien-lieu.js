/* Kho nhiên liệu — sổ nhập/xuất, tồn cộng dồn tính ở máy chủ. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, d;
  const suaDuoc = () => AUTH.la('yard', 'fuel', 'acct');

  function ve() {
    const rows = d.rows, thang = EPL.thangNay();
    const xuatThang = rows.filter(r => r.kind === 'out' && r.move_date.startsWith(thang)).reduce((a, r) => a + r.qty_out, 0);
    const nhap = rows.filter(r => r.kind === 'in' && r.qty_in > 0);
    const giaBQ = nhap.length ? nhap.reduce((a, r) => a + r.qty_in * (r.unit_price || 0), 0) / nhap.reduce((a, r) => a + r.qty_in, 0) : 0;
    root.querySelector('#knl-ton').textContent = so(d.ton_lit, 1);
    root.querySelector('#knl-xuat').textContent = so(xuatThang, 1);
    root.querySelector('#knl-gia').textContent = so(giaBQ) + ' LAK/L';
    root.querySelector('#knl-than').innerHTML = rows.length ? rows.map(r => `<tr>
      <td>${EPL.ngay(r.move_date)}</td><td class="mono">${esc(r.doc_no) || '—'}</td><td>${EPL.tag('plain', r.kind === 'in' ? 'fs_in' : 'fs_out')}</td><td>${esc(r.truck_no) || '—'}</td>
      <td class="num knl-in">${r.qty_in ? so(r.qty_in) : ''}</td><td class="num knl-out">${r.qty_out ? so(r.qty_out) : ''}</td><td class="num"><b>${so(r.balance, 1)}</b></td>
      <td class="num">${r.unit_price ? so(r.unit_price) + ' ' + esc(r.currency) : '—'}</td><td lang="lo">${esc(r.by_user) || '—'}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
  }
  async function ghi(kind) {
    const v = await EPL.hopNhap(NN.t(kind === 'in' ? 'fuel_in' : 'fuel_out'), [
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'doc_no', label: 'ref', value: '' },
      ...(kind === 'out' ? [{ id: 'truck_no', label: 'truck_no', value: '' }] : []),
      { id: 'qty_l', label: 'qty_l', type: 'number', value: '' },
      { id: 'unit_price', label: 'unit_price', type: 'number', value: '' },
      { id: 'currency', label: 'cur', type: 'select', value: 'LAK', options: [['LAK', 'LAK'], ['VND', 'VND'], ['THB', 'THB'], ['USD', 'USD']] },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    try { d = await API.post('/api/fuel-moves', { kind, ...v }); EPL.toast(NN.t('saved'), 'ok'); ve(); } catch (e) { EPL.baoLoi(e); }
  }
  EPL.modules['kho-nhien-lieu'] = {
    async init(r) {
      root = r;
      r.querySelector('#knl-nhap').hidden = r.querySelector('#knl-xuat-nut').hidden = !suaDuoc();
      r.querySelector('#knl-nhap').addEventListener('click', () => ghi('in'));
      r.querySelector('#knl-xuat-nut').addEventListener('click', () => ghi('out'));
      d = await API.get('/api/fuel-moves'); ve();
    },
    onLang() { if (d) ve(); },
  };
})();
