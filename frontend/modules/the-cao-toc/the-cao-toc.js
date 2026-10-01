/* Thẻ cao tốc — ບັດທາງດ່ວນ (anh Khampla C6.1).
 *
 * Thẻ là một "kho tiền" nhỏ: số dư cộng dồn từ các dòng nạp và các lần qua trạm. Thẻ bị trừ khi kế
 * toán GHI SỔ mục IV của phiếu — trước đó dòng chi còn sửa tới sửa lui, trừ sớm thì số dư nhảy loạn.
 *
 * Hai kiểu thẻ khác nhau ở chỗ ai bỏ tiền: khách cấp thẻ và nạp tiền (cuối tháng phần EPL tiêu trên
 * thẻ đó được cấn trừ vào cước của chính khách ấy), hay thẻ của EPL do quỹ Thà Bốc nạp.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], KH = [], TX = [], XE = [], T = null, canTru = null;

  const suaDuoc = () => AUTH.la('acct');
  const napDuoc = () => AUTH.la('acct', 'cash', 'treasury');
  const xemCanTru = () => AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash');
  const le = (ma) => EPL.leTien(ma);
  const KIEU = [['khach', 'tct_k_khach'], ['epl', 'tct_k_epl']];
  const DONG = { nap: 'tct_d_nap', chi: 'tct_d_chi', dieu_chinh: 'tct_d_dc' };

  /* ---------------------------------------------------------------- danh sách thẻ */
  function ve() {
    const q = root.querySelector('#tct-q').value.trim().toLowerCase();
    const rows = DS.filter(t => !q || [t.card_no, t.name, t.customer_name, t.driver_name, t.truck_no]
      .join(' ').toLowerCase().includes(q));
    root.querySelector('#tct-than').innerHTML = rows.length ? rows.map(t => `<tr class="${t.active ? '' : 'tct-tat'} ${T && T.id === t.id ? 'chon' : ''}">
      <td class="mono"><b>${esc(t.card_no)}</b></td>
      <td lang="lo">${esc(t.name || '')}</td>
      <td>${NN.h(t.kind === 'khach' ? 'tct_k_khach' : 'tct_k_epl')}</td>
      <td lang="lo">${esc(t.customer_name || '') || '—'}</td>
      <td lang="lo">${esc(t.driver_name || t.truck_no || '') || '—'}</td>
      <td class="mono">${esc(t.currency)}</td>
      <td class="num"><b class="${t.balance <= 0 ? 'neg' : ''}">${so(t.balance, le(t.currency))}</b></td>
      <td>${tag(t.active ? 'ok' : 'plain', t.active ? 'active' : 'inactive')}</td>
      <td class="no-print"><button class="btn sm" data-xem="${esc(t.id)}">${NN.h('hg_xem')}</button>
        ${suaDuoc() ? `<button class="btn sm" data-sua="${esc(t.id)}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#tct-dem').textContent = rows.length ? `${rows.length} ${NN.t('rows')}` : '';
    root.querySelectorAll('[data-xem]').forEach(b => b.addEventListener('click', () => xem(b.dataset.xem)));
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(DS.find(t => t.id === b.dataset.sua))));
  }

  /* ---------------------------------------------------------------- sổ của một thẻ */
  function veChiTiet() {
    const o = root.querySelector('#tct-ct');
    o.hidden = !T; if (!T) return;
    root.querySelector('#tct-ct-ten').innerHTML = `${esc(T.card_no)}${T.name ? ' · <span lang="lo">' + esc(T.name) + '</span>' : ''}`;
    root.querySelector('#tct-nap').hidden = !napDuoc() || !T.active;
    root.querySelector('#tct-dc').hidden = !suaDuoc();
    const dong = (T.moves || []).map(m => `<tr>
      <td class="nowrap">${EPL.ngay(m.move_date)}</td>
      <td class="${m.kind === 'nap' ? 'tct-nap' : m.kind === 'chi' ? 'tct-chi' : ''}">${NN.h(DONG[m.kind] || 'tct_d_dc')}</td>
      <td class="num"><b>${m.kind === 'chi' ? '−' : '+'}${so(Math.abs(m.amount), le(T.currency))}</b></td>
      <td class="num">${so(m.balance_after, le(T.currency))}</td>
      <td class="mono small">${esc(m.trip_doc_no || m.ref || '')}</td>
      <td class="small muted" lang="lo">${esc(m.note || '')}</td>
      <td class="small muted">${esc(m.by_user || '')}</td></tr>`).join('');
    root.querySelector('#tct-ct-than').innerHTML = `
      <div class="tct-dau">
        <div><span>${NN.h('tct_loai')}</span><b>${NN.h(T.kind === 'khach' ? 'tct_k_khach' : 'tct_k_epl')}</b></div>
        <div><span>${NN.h('customer')}</span><b lang="lo">${esc(T.customer_name || '') || '—'}</b></div>
        <div><span>${NN.h('tct_giu')}</span><b lang="lo">${esc(T.driver_name || '') || '—'}</b></div>
        <div><span>${NN.h('truck_no')}</span><b>${esc(T.truck_no || '') || '—'}</b></div>
        <div><span>${NN.h('tct_du')}</span><b class="${T.balance <= 0 ? 'thap' : ''}">${so(T.balance, le(T.currency))} ${esc(T.currency)}</b></div>
      </div>
      ${T.note ? `<p class="small muted" lang="lo">${esc(T.note)}</p>` : ''}
      <div class="tbl-wrap">${(T.moves || []).length ? `<table class="tbl tbl-compact"><thead><tr>
        <th>${NN.h('c_date')}</th><th>${NN.h('type')}</th><th class="num">${NN.h('pay_amount')}</th>
        <th class="num">${NN.h('tct_du_sau')}</th><th>${NN.h('doc_no')}</th><th>${NN.h('note')}</th><th>${NN.h('by_user')}</th>
      </tr></thead><tbody>${dong}</tbody></table>` : `<p class="small muted">${NN.h('tct_chua_co')}</p>`}</div>
      <p class="small muted">${NN.h('tct_tru_nhac')}</p>`;
  }

  async function xem(id) {
    try {
      T = await API.get('/api/the-cao-toc/' + id); ve(); veChiTiet();
      const o = root.querySelector('#tct-ct'); if (o.scrollIntoView) o.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- thêm · sửa · nạp */
  async function sua(t) {
    const v = await EPL.hopNhap(t ? NN.t('edit') : NN.t('tct_them'), [
      { id: 'card_no', label: 'tct_so', value: t ? t.card_no : '' },
      { id: 'name', label: 'name', value: t ? (t.name || '') : '', lo: true },
      { id: 'kind', label: 'tct_loai', type: 'select', value: t ? t.kind : 'epl', options: KIEU.map(([k, n]) => [k, NN.t(n)]) },
      { id: 'customer_id', label: 'customer', type: 'select', value: t ? (t.customer_id || '') : '',
        options: [['', '—']].concat(KH.map(k => [k.id, k.name])) },
      { id: 'driver_id', label: 'tct_giu', type: 'select', value: t ? (t.driver_id || '') : '',
        options: [['', '—']].concat(TX.map(d => [d.id, d.name])) },
      { id: 'vehicle_id', label: 'truck_no', type: 'select', value: t ? (t.vehicle_id || '') : '',
        options: [['', '—']].concat(XE.map(x => [x.id, x.truck_no])) },
      { id: 'currency', label: 'ccy', type: 'select', value: t ? t.currency : 'LAK', options: EPL.TIEN_TE.map(m => [m, m]) },
      ...(t ? [] : [{ id: 'balance', label: 'tct_du_dau', type: 'number', value: '0' }]),
      { id: 'note', label: 'note', type: 'textarea', value: t ? (t.note || '') : '' },
      ...(t ? [{ id: 'active', label: 'status', type: 'select', value: t.active ? '1' : '0',
        options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!String(v.card_no || '').trim()) return EPL.toast(NN.t('tct_so') + '?', 'loi');
    const than = { card_no: v.card_no, name: v.name, kind: v.kind, customer_id: v.customer_id || null,
      driver_id: v.driver_id || null, vehicle_id: v.vehicle_id || null, currency: v.currency, note: v.note };
    if (!t) than.balance = v.balance;
    if (t) than.active = v.active === '1';
    try {
      T = await (t ? API.put('/api/the-cao-toc/' + t.id, than) : API.post('/api/the-cao-toc', than));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function nap() {
    const v = await EPL.hopNhap(NN.t('tct_nap') + ' · ' + T.card_no, [
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'amount', label: 'pay_amount', type: 'number', value: '' },
      { id: 'ref', label: 'pay_ref', value: '' },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    if (!(EPL.doc(v.amount) > 0)) return EPL.toast(NN.t('pay_amount') + '?', 'loi');
    try { T = await API.post(`/api/the-cao-toc/${T.id}/nap`, v); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  async function dieuChinh() {
    const v = await EPL.hopNhap(NN.t('tct_dieu_chinh') + ' · ' + T.card_no, [
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'amount', label: 'tct_chenh', type: 'number', value: '' },
      { id: 'note', label: 'tct_ly_do', value: '', lo: true },
    ], NN.t('save'));
    if (!v) return;
    if (!String(v.note || '').trim()) return EPL.toast(NN.t('tct_ly_do') + '?', 'loi');
    try { T = await API.post(`/api/the-cao-toc/${T.id}/dieu-chinh`, v); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- cấn trừ cuối tháng */
  function veCanTru() {
    const card = root.querySelector('#tct-can-tru-card');
    card.hidden = !xemCanTru();
    if (!xemCanTru() || !canTru) return;
    const ds = canTru.ds || [];
    if (canTru.loi) { root.querySelector('#tct-can-tru').innerHTML = `<tr><td colspan="7" class="empty neg">${esc(canTru.loi)}</td></tr>`; return; }
    root.querySelector('#tct-can-tru').innerHTML = ds.length ? ds.map(o => `<tr>
      <td lang="lo"><b>${esc(o.customer_name)}</b></td>
      <td>${o.the.map(t => esc(t.card_no)).join(' · ')}</td>
      <td class="mono">${esc(o.currency)}</td>
      <td class="num tct-nap">${so(o.nap, le(o.currency))}</td>
      <td class="num tct-chi">${so(o.chi, le(o.currency))}</td>
      <td class="num">${o.the.reduce((n, t) => n + (t.so_luot || 0), 0)}</td>
      <td class="num"><b>${so(o.can_tru, le(o.currency))}</b></td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('tct_can_tru_trong')}</td></tr>`;
  }

  /* ---------------------------------------------------------------- nạp dữ liệu */
  // Ba câu hỏi chạy SONG SONG (rà 01/10: trước đây nối đuôi nhau — mạng chậm thì màn chờ gấp ba)
  async function tai() {
    const thang = xemCanTru() ? root.querySelector('#tct-thang').value : '';
    const [ds, t, ct] = await Promise.all([
      API.get('/api/the-cao-toc'),
      T ? API.get('/api/the-cao-toc/' + T.id).catch(() => null) : null,
      // lỗi máy chủ thì hiện ngay trong bảng (rà 01/10): trước đây canTru = null → bảng giữ số của tháng trước / trống trơn
      xemCanTru() ? API.get('/api/the-cao-toc/cong-no' + (thang ? '?thang=' + thang : '')).catch(e => ({ ds: [], loi: e.message })) : null,
    ]);
    DS = ds; T = t;
    if (xemCanTru()) canTru = ct;
    ve(); veChiTiet(); veCanTru();
  }

  EPL.modules['the-cao-toc'] = {
    async init(r) {
      root = r;
      // ô tháng mặc định là tháng này THEO GIỜ MÁY (EPL.doiOThang đã đặt) — không gán lại bằng toISOString: đó là giờ UTC,
      // 0–7 giờ sáng ngày 1 ở Lào ra tháng trước, bảng cấn trừ mở ra tháng cũ (rà 01/10)
      // khách · tài xế · xe chỉ cần cho hộp Thêm / Sửa thẻ (vai kế toán) — nạp cùng lúc với danh sách, không chờ trước
      const danhMuc = suaDuoc() ? Promise.all([API.get('/api/customers'), API.get('/api/drivers'), API.get('/api/vehicles')])
        .then(([a, b, c]) => { KH = a; TX = b; XE = c; }) : Promise.resolve();
      const them = r.querySelector('#tct-them'); them.hidden = !suaDuoc();
      them.addEventListener('click', () => sua(null));
      r.querySelector('#tct-q').addEventListener('input', ve);
      r.querySelector('#tct-nap').addEventListener('click', nap);
      r.querySelector('#tct-dc').addEventListener('click', dieuChinh);
      r.querySelector('#tct-ct-dong').addEventListener('click', () => { T = null; ve(); veChiTiet(); });
      r.querySelector('#tct-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      await Promise.all([danhMuc, tai()]);
    },
    onLang() { if (root) { ve(); veChiTiet(); veCanTru(); } },
  };
})();
