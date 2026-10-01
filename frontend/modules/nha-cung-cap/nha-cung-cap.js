/* Nhà cung cấp — DANH MỤC: tên, dịch vụ (khoản mục), mã kế toán, kỳ trả, khách được cấn trừ, số dòng chi trên phiếu.
 * Phần tiền (phát sinh, đã trả, còn nợ, trả nhà cung cấp) KHÔNG còn ở trang kế toán tạm (01/10: bỏ phần tiền bên đó — số thử,
 * cắt sổ): trả nhà cung cấp là phiếu chi bên hệ kế toán anh Tune. Nút "Công nợ · trả nhà cung cấp ↗" sang trang tạm đã gỡ.
 * Danh mục ở lại đây vì phiếu (dầu ghi nợ tại trạm) và tất toán tài xế cần nó, và Bãi xem danh sách · số dòng · kỳ trả
 * (không có tiền, chốt 23/09). */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [], KH = [];
  const KHOAN = ['x_chip_lao', 'x_chip_vn', 'x_tire', 'x_toll', 'x_bridge', 'x_border', 'x_parking', 'x_oil', 'x_brake', 'x_tow', 'x_air', 'x_misc'];
  const TK = ['625/4021', '614/4021', '614/1371', '625/1371'];
  const HAN = ['t_monthly', 't_prepaid', 'pm_on_dispatch'];

  function ve() {
    root.querySelector('#ncc-than').innerHTML = ds.length ? ds.map(s => `<tr>
      <td lang="lo"><b>${esc(s.name)}</b></td><td>${s.item_key ? NN.h(s.item_key) : '—'}</td><td class="tien-chi"><span class="acct">${esc(s.acct_code) || '—'}</span></td>
      <td class="num">${s.so_dong}</td>
      <td class="tien" lang="lo">${esc(s.customer_name || '') || '—'}</td>
      <td>${NN.h(s.payment_term || 't_monthly')}</td>
      <td class="no-print">${AUTH.la('expacct') ? `<button class="btn sm" data-sua="${s.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
  }
  async function sua(s) {
    const v = await EPL.hopNhap(s ? NN.t('edit') : NN.t('add'), [
      { id: 'name', label: 'supplier', value: s ? s.name : '', lo: true },
      { id: 'item_key', label: 'service', type: 'select', value: s ? s.item_key : 'x_chip_lao', options: KHOAN.map(k => [k, NN.t(k)]) },
      { id: 'acct_code', label: 'acct_code', type: 'select', value: s ? s.acct_code : '625/4021', options: TK.map(k => [k, k]) },
      { id: 'payment_term', label: 'terms', type: 'select', value: s ? s.payment_term : 't_monthly', options: HAN.map(k => [k, NN.t(k)]) },
      // Trạm dầu bên Việt Nam ghi nợ: cuối tháng trừ vào cước của khách nào (C5.1).
      { id: 'customer_id', label: 'ncc_can_tru_kh', type: 'select', value: s ? (s.customer_id || '') : '',
        options: [['', '—']].concat(KH.map(k => [k.id, k.name])) },
      { id: 'note', label: 'note', value: s ? s.note : '' },
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('supplier') + '?', 'loi');
    const than = { ...v, customer_id: v.customer_id || null };
    try { await (s ? API.put('/api/suppliers/' + s.id, than) : API.post('/api/suppliers', than)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  async function tai() { ds = await API.get('/api/suppliers'); ve(); }
  EPL.modules['nha-cung-cap'] = {
    async init(r) {
      root = r; const t = r.querySelector('#ncc-them'); t.hidden = !AUTH.la('expacct'); t.addEventListener('click', () => sua(null));
      try { KH = await API.get('/api/customers'); } catch (e) { KH = []; }
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();
