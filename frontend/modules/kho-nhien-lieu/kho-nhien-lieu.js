/* Kho nhiên liệu — sổ nhập/xuất/chuyển THEO TỪNG KHO (anh Khampla C5.2), giá vốn bình quân (C5.3).
 * Tồn và giá bình quân tính ở máy chủ. Bãi xem số lít, không thấy giá (A2) — máy chủ không gửi giá cho Bãi.
 * Dầu mua bên Việt Nam (A3): nhập vào "kho xe" → phiếu xuất xe lấy từ kho đó → phần dư CHUYỂN KHO về Thà Bốc. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, d, NCC = [], chon = '';
  const q = (s) => root.querySelector(s);
  const suaDuoc = () => AUTH.la('fuel', 'acct');
  const khoOpt = (ds) => ds.map(k => [k.id, k.name]);

  function ve() {
    const rows = d.rows, thang = EPL.thangNay(), coGia = d.gia_bq !== undefined;
    const xuatThang = rows.filter(r => r.kind === 'out' && !r.transfer_no && r.move_date.startsWith(thang)).reduce((a, r) => a + r.qty_out, 0);
    q('#knl-ton').textContent = so(d.ton_lit, 1);
    q('#knl-xuat').textContent = so(xuatThang, 1);
    q('#knl-gia').textContent = coGia ? (chon ? so(d.gia_bq) + ' LAK/L' : '—') : '—';
    q('#knl-gia-o').hidden = !coGia;
    q('#knl-ds-kho').innerHTML = d.kho.filter(k => k.active || k.ton_lit).map(k => `<tr class="${k.id === chon ? 'knl-chon' : ''}" data-kho="${k.id}">
      <td lang="lo">${esc(k.name)}</td><td class="mono small">${esc(k.code || '')}</td><td class="num"><b>${so(k.ton_lit, 1)}</b></td>
      ${coGia ? `<td class="num">${k.gia_bq ? so(k.gia_bq) : '—'}</td>` : ''}</tr>`).join('');
    q('#knl-cot-gia').hidden = !coGia;
    q('#knl-than').innerHTML = rows.length ? rows.map(r => `<tr>
      <td>${EPL.ngay(r.move_date)}</td><td class="mono">${esc(r.doc_no) || '—'}</td>
      <td>${r.transfer_no ? EPL.tag('plain', 'fuel_transfer') : EPL.tag('plain', r.kind === 'in' ? 'fs_in' : 'fs_out')}</td>
      <td lang="lo" class="small">${esc(r.place_name || '')}</td><td>${esc(r.truck_no) || (r.note ? `<span class="small muted" lang="lo">${esc(r.note)}</span>` : '—')}</td>
      <td class="num knl-in">${r.qty_in ? so(r.qty_in) : ''}</td><td class="num knl-out">${r.qty_out ? so(r.qty_out) : ''}</td><td class="num"><b>${so(r.balance, 1)}</b></td>
      <td class="num">${r.unit_price ? so(r.unit_price) + ' ' + esc(r.currency) : '—'}</td><td lang="lo">${esc(r.by_user) || '—'}</td></tr>`).join('')
      : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-kho]').forEach(tr => tr.addEventListener('click', () => { chon = tr.dataset.kho === chon ? '' : tr.dataset.kho; q('#knl-kho').value = chon; tai().catch(EPL.baoLoi); }));
  }
  const khoMacDinh = () => chon || (d.kho.find(k => k.code === 'KHO-TB') || d.kho[0] || {}).id;
  async function ghi(kind) {
    const khoHoatDong = d.kho.filter(k => k.active);
    const v = await EPL.hopNhap(NN.t(kind === 'in' ? 'fuel_in' : 'fuel_out'), [
      { id: 'place_id', label: 'fuel_kho', type: 'select', value: khoMacDinh(), options: khoOpt(khoHoatDong) },
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'doc_no', label: kind === 'in' ? 'po_no' : 'ref', value: '' },
      ...(kind === 'in' ? [{ id: 'supplier_id', label: 'supplier', type: 'select', value: '', options: [['', '—'], ...NCC.filter(s => s.active !== false).map(s => [s.id, s.name])] }] : []),
      ...(kind === 'out' ? [{ id: 'truck_no', label: 'truck_no', value: '' }] : []),
      { id: 'qty_l', label: 'qty_l', type: 'number', value: '' },
      ...(kind === 'in' ? [
        { id: 'unit_price', label: 'unit_price', type: 'number', value: '' },
        { id: 'currency', label: 'cur', type: 'select', value: 'LAK', options: [['LAK', 'LAK'], ['VND', 'VND'], ['THB', 'THB'], ['USD', 'USD']] },
        { id: 'rate_to_lak', label: 'fuel_rate_in', type: 'number', value: '' },
      ] : []),
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    try { await API.post('/api/fuel-moves', { kind, ...v }); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function chuyen() {
    const kho = d.kho.filter(k => k.active);
    const tu = khoMacDinh(), den = (kho.find(k => k.id !== tu && k.code === 'KHO-TB') || kho.find(k => k.id !== tu) || {}).id;
    const v = await EPL.hopNhap(NN.t('fuel_transfer'), [
      { id: 'from_place_id', label: 'fuel_from', type: 'select', value: tu, options: kho.map(k => [k.id, `${k.name} · ${so(k.ton_lit, 1)} L`]) },
      { id: 'to_place_id', label: 'fuel_to', type: 'select', value: den, options: khoOpt(kho) },
      { id: 'move_date', label: 'c_date', type: 'date', value: EPL.homNay() },
      { id: 'qty_l', label: 'qty_l', type: 'number', value: '' },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('fuel_transfer'));
    if (!v) return;
    try { const r = await API.post('/api/fuel-transfers', v); EPL.toast(`${NN.t('fuel_transfer_done')} · ${r.transfer_no}`, 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() {
    d = await API.get('/api/fuel-moves' + (chon ? '?place_id=' + encodeURIComponent(chon) : ''));
    const s = q('#knl-kho');
    s.innerHTML = `<option value="">${esc(NN.t('fuel_all_kho'))}</option>` + d.kho.filter(k => k.active || k.ton_lit).map(k => `<option value="${k.id}" ${k.id === chon ? 'selected' : ''}>${esc(k.name)}</option>`).join('');
    ve();
  }
  EPL.modules['kho-nhien-lieu'] = {
    async init(r) {
      root = r; chon = '';
      ['#knl-nhap', '#knl-xuat-nut', '#knl-chuyen'].forEach(id => { q(id).hidden = !suaDuoc(); });
      q('#knl-nhap').addEventListener('click', () => ghi('in'));
      q('#knl-xuat-nut').addEventListener('click', () => ghi('out'));
      q('#knl-chuyen').addEventListener('click', chuyen);
      q('#knl-kho').addEventListener('change', (e) => { chon = e.target.value; tai().catch(EPL.baoLoi); });
      NCC = suaDuoc() ? await API.get('/api/suppliers').catch(() => []) : [];
      await tai();
    },
    onLang() { if (d) ve(); },
  };
})();
