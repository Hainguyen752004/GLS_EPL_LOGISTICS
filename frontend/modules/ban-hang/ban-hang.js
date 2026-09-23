/* Bán hàng — EPL bán phụ tùng, dầu cho bên ngoài. Lập phiếu = xuất kho + hoá đơn; sau đó ghi thu.
 * Số liệu từ /api/ban-hang. Ai lập: kế toán, kế toán doanh thu, kho nhiên liệu. Ai ghi thu: doanh thu, quỹ. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], KH = [], CX = [], PT = [], DIEM = [], dong = [];
  const q = (s) => root.querySelector(s);
  const lapDuoc = () => AUTH.la('acct', 'rev', 'fuel');
  const thuDuoc = () => AUTH.la('rev', 'cash', 'treasury');

  /* ---------------------------------------------------------------- danh sách */
  function ve() {
    q('#bh-than').innerHTML = DS.ds.length ? DS.ds.map(s => `<tr class="${s.status === 'paid' ? 'bh-da-thu' : ''}">
      <td class="mono"><b>${esc(s.doc_no)}</b></td><td>${EPL.ngay(s.sale_date)}</td><td lang="lo">${esc(s.customer_name)}</td>
      <td class="bh-dong-ct">${s.lines.map(d => `<b>${so(d.qty)}</b> ${esc(d.unit ? NN.t(d.unit) : '')} ${esc(d.name || '')}`).join('<br>')}</td>
      <td class="num">${so(s.total, s.currency === 'USD' ? 2 : 0)} ${esc(s.currency)}</td><td class="num">${so(s.total_lak)}</td>
      <td>${s.owner_id ? tag(s.owner_payment_id ? 'paid' : 'partial', s.owner_payment_id ? 'sale_da_tru' : 'sale_cho_tru') : tag(s.status === 'paid' ? 'paid' : 'unpaid', s.status === 'paid' ? 'sale_paid' : 'sale_issued')}${s.owner_id ? `<div class="small muted">${NN.h('sale_tru_cx')}</div>` : ''}</td>
      <td class="small" lang="lo">${esc(s.by_user || '')}${s.paid_by ? `<div class="muted">${NN.h('sale_collect')}: ${esc(s.paid_by)}</div>` : ''}</td>
      <td class="no-print">${s.status !== 'paid' && !s.owner_id && thuDuoc() ? `<button class="btn sm ok" data-thu="${s.id}">${NN.h('sale_collect')}</button> ` : ''}${s.status === 'issued' && !s.owner_payment_id && lapDuoc() ? `<button class="btn sm danger" data-bo="${s.id}">${NN.h('delete')}</button> ` : ''}<button class="btn sm quiet" data-ct="${s.doc_no}">${NN.h('ct_so')}</button></td>
    </tr>`).join('') : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    q('#bh-tong').textContent = `${DS.ds.length} · ${so(DS.tong_lak)} LAK · ${NN.t('sale_unpaid')}: ${so(DS.chua_thu_lak)} LAK${DS.cho_tru_chu_xe_lak ? ` · ${NN.t('sale_cho_tru')}: ${so(DS.cho_tru_chu_xe_lak)} LAK` : ''}`;
    root.querySelectorAll('[data-thu]').forEach(b => b.addEventListener('click', () => thu(b.dataset.thu)));
    root.querySelectorAll('[data-bo]').forEach(b => b.addEventListener('click', () => bo(b.dataset.bo)));
    root.querySelectorAll('[data-ct]').forEach(b => b.addEventListener('click', () => EPL.di('chung-tu', { tab: 'so', loai: 'HD_BAN,PT_BAN,PXK_BAN' })));
  }
  async function thu(id) {
    const s = DS.ds.find(x => x.id === id);
    const ok = await EPL.hoi(NN.t('sale_collect'), `<p><b class="mono">${esc(s.doc_no)}</b> · <span lang="lo">${esc(s.customer_name)}</span></p><p class="hi">${so(s.total, s.currency === 'USD' ? 2 : 0)} ${esc(s.currency)}</p><p class="small muted">${NN.h('sale_collect_hint')}</p>`, NN.t('sale_collect'));
    if (!ok) return;
    try { await API.post(`/api/ban-hang/${id}/thu`); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function bo(id) {
    const s = DS.ds.find(x => x.id === id);
    const ok = await EPL.hoi(NN.t('delete'), `<p><b class="mono">${esc(s.doc_no)}</b></p><p class="small muted">${NN.h('sale_delete_hint')}</p>`, NN.t('delete'));
    if (!ok) return;
    try { await API.goi(`/api/ban-hang/${id}`, { method: 'DELETE' }); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- lập phiếu */
  function veDong() {
    q('#bh-dong').innerHTML = dong.length ? dong.map((d, i) => `<tr data-i="${i}">
      <td>${i + 1}</td>
      <td>${NN.h(d.item_type === 'part' ? 'it_part' : 'it_fuel')}</td>
      <td>${d.item_type === 'part'
        ? `<select data-i="${i}" data-f="part_id">${PT.map(p => `<option value="${p.id}" ${p.id === d.part_id ? 'selected' : ''}>${esc(p.name)} · ${NN.t('stock')} ${so(p.qty)}</option>`).join('')}</select>`
        : `<select data-i="${i}" data-f="place_id">${DIEM.filter(x => x.owner_type === 'epl').map(x => `<option value="${x.id}" ${x.id === d.place_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select><div class="small muted">${NN.h('sale_fuel_l')}</div>`}</td>
      <td class="num"><input class="num" inputmode="decimal" data-i="${i}" data-f="qty" value="${esc(d.qty)}"></td>
      <td class="num"><input class="num" inputmode="decimal" data-i="${i}" data-f="unit_price" value="${esc(d.unit_price)}"></td>
      <td class="num amt">${so(EPL.doc(d.qty) * EPL.doc(d.unit_price), 2)}</td>
      <td><button type="button" class="x" data-xoa="${i}" title="${esc(NN.t('delete'))}">×</button></td></tr>`).join('')
      : `<tr><td colspan="7" class="empty small">${NN.h('sale_no_lines')}</td></tr>`;
    const tong = dong.reduce((a, d) => a + EPL.doc(d.qty) * EPL.doc(d.unit_price), 0);
    q('#bh-chan').innerHTML = `<tr><td colspan="5">${NN.h('total')}</td><td class="num"><b>${so(tong, 2)} ${esc(q('#bh-tien-te').value)}</b></td><td></td></tr>`;
    root.querySelectorAll('#bh-dong [data-f]').forEach(el => el.addEventListener('input', () => {
      const d = dong[+el.dataset.i]; d[el.dataset.f] = el.value;
      if (el.dataset.f === 'part_id') { const p = PT.find(x => x.id === el.value); if (p && !EPL.doc(d.unit_price)) d.unit_price = p.unit_price || 0; }
      veDong();
    }));
    root.querySelectorAll('#bh-dong [data-xoa]').forEach(b => b.addEventListener('click', () => { dong.splice(+b.dataset.xoa, 1); veDong(); }));
  }
  function themDong(loai) {
    if (loai === 'part') { const p = PT[0]; if (!p) return EPL.toast(NN.t('no_data'), 'loi'); dong.push({ item_type: 'part', part_id: p.id, qty: 1, unit_price: p.unit_price || 0 }); }
    else { const k = DIEM.find(x => x.owner_type === 'epl'); dong.push({ item_type: 'fuel', place_id: k ? k.id : '', qty: 0, unit_price: 0 }); }
    veDong();
  }
  // Người mua là CHỦ XE LIÊN KẾT → không thu tiền mặt, đợt trả chủ xe kế tiếp tự trừ (deal 1tr6, mua 3 trăm → trả 1tr3)
  function veLoaiMua() {
    const cx = q('#bh-loai-mua').value === 'cx';
    root.querySelectorAll('.bh-o-cx').forEach(e => { e.hidden = !cx; });
    root.querySelectorAll('.bh-o-kh').forEach(e => { e.hidden = cx; });
  }
  function moLap(mo) {
    q('#bh-lap').hidden = !mo;
    if (mo) { dong = []; q('#bh-ngay').value = EPL.homNay(); q('#bh-khach-ten').value = ''; q('#bh-ghi-chu').value = ''; q('#bh-loai-mua').value = 'kh'; q('#bh-chu-xe').value = ''; veLoaiMua(); veDong(); }
  }
  async function luu() {
    const cx = q('#bh-loai-mua').value === 'cx';
    if (cx && !q('#bh-chu-xe').value) return EPL.toast(NN.t('owner') + '?', 'loi');
    const body = { sale_date: q('#bh-ngay').value, owner_id: cx ? q('#bh-chu-xe').value : null,
      customer_id: cx ? null : (q('#bh-khach').value || null), customer_name: cx ? '' : q('#bh-khach-ten').value.trim(),
      currency: q('#bh-tien-te').value, note: q('#bh-ghi-chu').value,
      lines: dong.map(d => ({ ...d, qty: EPL.doc(d.qty), unit_price: EPL.doc(d.unit_price) })) };
    try { await API.post('/api/ban-hang', body); EPL.toast(NN.t('saved'), 'ok'); moLap(false); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  async function tai() {
    const th = q('#bh-thang').value;
    DS = await API.get('/api/ban-hang' + (th ? '?thang=' + th : ''));
    ve();
  }
  EPL.modules['ban-hang'] = {
    async init(r) {
      root = r;
      [KH, PT, DIEM, CX] = await Promise.all([API.get('/api/customers'), API.get('/api/parts'), API.get('/api/fuel-places').catch(() => []), API.get('/api/owners').catch(() => [])]);
      q('#bh-chu-xe').innerHTML = `<option value="">—</option>` + CX.filter(c => c.active !== false).map(c => `<option value="${c.id}">${esc(c.name)}${(c.so_xe || []).length ? ' · ' + esc(c.so_xe.join(', ')) : ''}</option>`).join('');
      q('#bh-loai-mua').addEventListener('change', veLoaiMua);
      q('#bh-khach').innerHTML = `<option value="">—</option>` + KH.filter(k => k.active !== false).map(k => `<option value="${k.id}">${esc(k.name)}</option>`).join('');
      q('#bh-moi').hidden = !lapDuoc();
      q('#bh-moi').addEventListener('click', () => moLap(true));
      q('#bh-huy').addEventListener('click', () => moLap(false));
      q('#bh-luu').addEventListener('click', luu);
      q('#bh-them-pt').addEventListener('click', () => themDong('part'));
      q('#bh-them-dau').addEventListener('click', () => themDong('fuel'));
      q('#bh-tien-te').addEventListener('change', veDong);
      q('#bh-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      await tai();
    },
    onLang() { if (root) { ve(); if (!q('#bh-lap').hidden) veDong(); } },
  };
})();
