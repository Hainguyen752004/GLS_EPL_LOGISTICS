/* Xe liên kết — danh mục chủ xe liên kết: điều khoản (phí, ngưỡng tấn, cách trả, tiền thuê) và hợp đồng thuê xe.
 * Chờ trả, trả gộp, trả từng phiếu và bảng xe liên kết theo tháng (lãi chuyến) ở TRANG KẾ TOÁN từ 28/09 (đợt 7b) —
 * nút trên thanh công cụ mở màn đó. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, chu = [], HD = [], chuHd = null;
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
        <td class="no-print">${themDuoc ? `<button class="btn sm" data-sua-chu="${c.id}">${NN.h('edit')}</button> ` : ''}<button class="btn sm ${chuHd && chuHd.id === c.id ? 'primary' : ''}" data-hd-chu="${c.id}">${NN.h('hd_nut')}</button></td></tr>`;
    }).join('') : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    o.querySelectorAll('[data-hd-chu]').forEach(b => b.addEventListener('click', () => moHd(chu.find(x => x.id === b.dataset.hdChu))));
    o.querySelectorAll('[data-sua-chu]').forEach(b => b.addEventListener('click', () => suaChu(chu.find(x => x.id === b.dataset.suaChu))));
  }
  async function suaChu(c) {
    const v = await EPL.hopNhap(c ? NN.t('edit') + ' · ' + c.name : NN.t('owner_add'), [
      { id: 'name', label: 'owner', value: c ? c.name : '', lo: true },
      { id: 'phone', label: 'phone', value: c ? c.phone : '' },
      { id: 'address', label: 'address', value: c ? c.address : '', lo: true },
      { id: 'pay_mode', label: 'owner_pay_mode', type: 'select', value: c ? c.pay_mode : 'phieu', options: Object.entries(OPM).map(([k, t]) => [k, NN.t(t)]) },
      { id: 'hire_ccy', label: 'ccy_hire', type: 'select', value: c ? (c.hire_ccy || 'USD') : 'USD', options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'fee_pct', label: 'fee_pct', type: 'number', value: c ? c.fee_pct : 2 },
      { id: 'over_limit_t', label: 'limit_t', type: 'number', value: c ? c.over_limit_t : 40 },
      { id: 'over_price', label: 'over_p', type: 'number', value: c ? c.over_price : 1 },
      { id: 'note', label: 'note', type: 'textarea', value: c ? c.note : '' },
      ...(c ? [{ id: 'active', label: 'status', type: 'select', value: c.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('owner') + '?', 'loi');
    const body = { name: v.name, phone: v.phone, address: v.address, pay_mode: v.pay_mode, hire_ccy: v.hire_ccy, fee_pct: v.fee_pct, over_limit_t: v.over_limit_t, over_price: v.over_price, note: v.note };
    if (c) body.active = v.active === '1';
    try { await (c ? API.put('/api/owners/' + c.id, body) : API.post('/api/owners', body)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function taiHd() { try { HD = await API.get('/api/hop-dong?kind=thue_xe'); } catch (e) { HD = []; } }
  async function moHd(c) {
    chuHd = c; veChu();
    await EPL.hopDong.mo(root.querySelector('#xlk-hd'), { kind: 'thue_xe', doiTacId: c.id, ten: c.name, suaDuoc: AUTH.la('acct'),
      onDoi: async () => { await taiHd(); if (root.querySelector('#xlk-hd').hidden) chuHd = null; veChu(); } });
  }
  async function tai() {
    await taiHd();
    chu = await API.get('/api/owners').catch(() => []);
    veChu();
  }
  EPL.modules['xe-lien-ket'] = {
    async init(r) {
      root = r;
      r.querySelector('#xlk-them-chu').addEventListener('click', () => suaChu(null));
      r.querySelector('#xlk-ke-toan').addEventListener('click', () => EPL.moKeToan('xe-lien-ket'));   // trả chủ xe ở trang kế toán
      await tai();
    },
    onLang() { if (root) veChu(); },
  };
})();
