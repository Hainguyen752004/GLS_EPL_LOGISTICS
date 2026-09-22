/* Lệnh sửa chữa riêng — ໃບສັ່ງສ້ອມແປງ (anh Khampla C7.3).
 *
 * Mục V trên phiếu chỉ ghi được cái sửa TRONG một chuyến. Xe nằm bãi đại tu, hay bảo dưỡng định kỳ
 * theo số km, thì không có chuyến nào để gắn vào — tờ lệnh này là chỗ khai đúng việc đó, và đi qua
 * đúng chuỗi duyệt của mục V: tổ sửa chữa nhập → KT Chi phí kiểm → ghi sổ → Quỹ tiền mặt chi.
 *
 * Quy tắc kho giữ nguyên: có trong kho thì XUẤT KHO (trừ tồn ngay lúc khai), không có thì MUA NGOÀI.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], XE = [], PARTS = [], O = null;

  const nhapDuoc = () => AUTH.la('repair');
  const BUOC = [['entered', 'sc_b_nhap'], ['verified', 'sc_b_kiem'], ['booked', 'sc_b_ghiso'], ['paid', 'sc_b_chi']];
  const TT_TAG = { entered: 'dispatched', verified: 'transit', booked: 'ore', paid: 'paid' };
  const lamDuoc = (hd) => AUTH.la(hd === 'pay' ? 'cash' : 'expacct');

  /* ---------------------------------------------------------------- danh sách */
  function ve() {
    const xe = root.querySelector('#sc-xe').value, tt = root.querySelector('#sc-tt').value;
    const rows = DS.filter(o => (!xe || o.vehicle_id === xe) && (!tt || o.status === tt));
    root.querySelector('#sc-than').innerHTML = rows.length ? rows.map(o => `<tr class="${O && O.id === o.id ? 'chon' : ''}">
      <td class="mono"><b>${esc(o.doc_no)}</b></td>
      <td>${EPL.ngay(o.order_date)}</td>
      <td><b>${esc(o.truck_no || '')}</b>${o.plate_head ? ` <span class="small muted" lang="lo">${esc(o.plate_head)}</span>` : ''}</td>
      <td>${NN.h(o.kind === 'bao_duong' ? 'sc_bao_duong' : 'sc_sua_chua')}</td>
      <td lang="lo">${esc(o.garage || '') || `<span class="muted">${NN.h('sc_tai_bai')}</span>`}</td>
      <td class="num">${o.odo_km == null ? '—' : so(o.odo_km)}</td>
      <td class="num">${o.so_dong}</td>
      <td class="num"><b>${so(o.tong_lak)}</b></td>
      <td>${tag(TT_TAG[o.status] || 'plain', 'sc_st_' + o.status)}</td>
      <td class="no-print"><button class="btn sm" data-xem="${esc(o.id)}">${NN.h('hg_xem')}</button></td></tr>`).join('')
      : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#sc-dem').textContent = rows.length ? `${rows.length} ${NN.t('rows')}` : '';
    root.querySelectorAll('[data-xem]').forEach(b => b.addEventListener('click', () => xem(b.dataset.xem)));
  }

  /* ---------------------------------------------------------------- một tờ */
  function veChiTiet() {
    const o = root.querySelector('#sc-ct');
    o.hidden = !O; if (!O) return;
    root.querySelector('#sc-ct-ten').innerHTML = `${esc(O.doc_no)} · ${esc(O.truck_no || '')} · ${NN.h(O.kind === 'bao_duong' ? 'sc_bao_duong' : 'sc_sua_chua')}`;
    const iBuoc = BUOC.findIndex(b => b[0] === O.status);
    const dong = (O.lines || []).map((d, i) => `<tr>
      <td>${i + 1}</td>
      <td lang="lo">${esc(d.item_key ? NN.t(d.item_key) : (d.item_name || ''))}${d.note ? ` <span class="small muted">${esc(d.note)}</span>` : ''}</td>
      <td class="${d.source === 'kho' ? 'sc-kho' : 'sc-mua'}">${NN.h(d.source === 'kho' ? 'src_kho' : 'src_mua')}</td>
      <td class="num">${so(d.qty, 2)}</td>
      <td class="num">${EPL.tien(d.unit_price, d.currency)}</td>
      <td class="num"><b>${so(d.tien_lak)}</b></td>
      <td class="mono small">${esc(d.acct_code || '')}</td></tr>`).join('');
    const nut = [];
    const keTiep = { entered: 'verify', verified: 'book', booked: 'pay' }[O.status];
    if (keTiep && lamDuoc(keTiep)) nut.push(`<button class="btn sm ok" data-hd="${keTiep}">${NN.h('a_' + (keTiep === 'verify' ? 'verify' : keTiep === 'book' ? 'book' : 'pay'))}</button>`);
    if (['verified', 'booked'].includes(O.status) && AUTH.la('expacct')) nut.push(`<button class="btn sm warn" data-hd="return">${NN.h('a_return')}</button>`);
    if (O.status === 'entered' && nhapDuoc()) {
      nut.push(`<button class="btn sm primary" data-them-dong>+ ${NN.h('sc_them_dong')}</button>`);
      nut.push(`<button class="btn sm" data-sua>${NN.h('edit')}</button>`);
      nut.push(`<button class="btn sm danger" data-xoa>${NN.h('delete')}</button>`);
    }
    root.querySelector('#sc-ct-than').innerHTML = `
      <div class="sc-dau">
        <div><span>${NN.h('c_date')}</span><b>${EPL.ngay(O.order_date)}</b></div>
        <div><span>${NN.h('truck_no')}</span><b>${esc(O.truck_no || '')}</b></div>
        <div><span>${NN.h('odo_km')}</span><b>${O.odo_km == null ? '—' : so(O.odo_km) + ' km'}</b></div>
        <div><span>${NN.h('sc_gara')}</span><b lang="lo">${esc(O.garage || '') || NN.t('sc_tai_bai')}</b></div>
        <div><span>${NN.h('sc_tong_kho')}</span><b>${so(O.tong_kho_lak)} LAK</b></div>
        <div><span>${NN.h('sc_tong_mua')}</span><b>${so(O.tong_mua_lak)} LAK</b></div>
        <div><span>${NN.h('in_lak')}</span><b>${so(O.tong_lak)} LAK</b></div>
        <div><span>${NN.h('voucher_no')}</span><b class="mono">${esc(O.chung_tu || '—')}</b></div>
      </div>
      <div class="sc-buoc">${BUOC.map(([ma, khoa], i) => `<span class="b ${i < iBuoc ? 'xong' : i === iBuoc ? 'gio' : ''}">${NN.h(khoa)}</span>`).join('<span class="muted">›</span>')}</div>
      ${O.note ? `<p class="small muted" lang="lo">${esc(O.note)}</p>` : ''}
      <div class="sc-sec">${NN.h('sc_dong')}</div>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr>
        <th>#</th><th>${NN.h('item')}</th><th>${NN.h('source')}</th><th class="num">${NN.h('qty')}</th>
        <th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('in_lak')}</th><th>${NN.h('acct_code')}</th>
      </tr></thead><tbody>${dong}</tbody></table></div>
      <p class="small muted">${NN.h('sc_kho_nhac')}</p>
      <div class="no-print" style="display:flex;gap:8px;margin-top:10px">${nut.join('')}</div>`;
    root.querySelectorAll('[data-hd]').forEach(b => b.addEventListener('click', () => buoc(b.dataset.hd)));
    const td = root.querySelector('[data-them-dong]'); if (td) td.addEventListener('click', themDong);
    const s = root.querySelector('[data-sua]'); if (s) s.addEventListener('click', () => lap(O));
    const x = root.querySelector('[data-xoa]'); if (x) x.addEventListener('click', xoa);
  }

  async function xem(id) {
    try {
      O = await API.get('/api/lenh-sua-chua/' + id); ve(); veChiTiet();
      const o = root.querySelector('#sc-ct'); if (o.scrollIntoView) o.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } catch (e) { EPL.baoLoi(e); }
  }

  async function buoc(hd) {
    try { O = await API.post(`/api/lenh-sua-chua/${O.id}/${hd}`, {}); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  async function xoa() {
    if (!await EPL.hoi(NN.t('delete'), `<p>${esc(O.doc_no)}</p>`, NN.t('delete'))) return;
    try { await API.goi('/api/lenh-sua-chua/' + O.id, { method: 'DELETE' }); O = null; EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- lập / sửa
   * Một tờ lệnh thường chỉ vài dòng, nên nhập từng dòng một qua hộp nhỏ — không dựng bảng sửa
   * tại chỗ cho một màn mà tổ sửa chữa mở vài lần một tuần.
   */
  async function lap(cu) {
    const xeCon = XE.filter(x => x.active !== false);
    if (!xeCon.length) return EPL.toast(NN.t('no_data'), 'loi');
    const v = await EPL.hopNhap(cu ? NN.t('edit') : NN.t('sc_them'), [
      { id: 'vehicle_id', label: 'truck_no', type: 'select', value: cu ? cu.vehicle_id : xeCon[0].id,
        options: xeCon.map(x => [x.id, `${x.truck_no}${x.plate_head ? ' · ' + x.plate_head : ''}`]) },
      { id: 'kind', label: 'sc_loai', type: 'select', value: cu ? cu.kind : 'sua_chua',
        options: [['sua_chua', NN.t('sc_sua_chua')], ['bao_duong', NN.t('sc_bao_duong')]] },
      { id: 'order_date', label: 'c_date', type: 'date', value: cu ? cu.order_date : EPL.homNay() },
      { id: 'odo_km', label: 'odo_km', type: 'number', value: cu && cu.odo_km != null ? cu.odo_km : '' },
      { id: 'garage', label: 'sc_gara', value: cu ? (cu.garage || '') : '', lo: true },
      { id: 'note', label: 'note', type: 'textarea', value: cu ? (cu.note || '') : '' },
    ], NN.t('save'));
    if (!v) return;
    const than = { vehicle_id: v.vehicle_id, kind: v.kind, order_date: v.order_date, garage: v.garage, note: v.note };
    if (v.odo_km !== '') than.odo_km = v.odo_km;
    try {
      O = cu ? await API.put('/api/lenh-sua-chua/' + cu.id, than) : await API.post('/api/lenh-sua-chua', than);
      EPL.toast(NN.t('saved'), 'ok');
      await tai();
      if (!cu) await themDong();          // tờ mới thì hỏi ngay dòng đầu tiên, khỏi để tờ rỗng
    } catch (e) { EPL.baoLoi(e); }
  }

  async function themDong() {
    if (!O) return;
    const conKho = PARTS.filter(p => p.qty > 0);
    const v = await EPL.hopNhap(NN.t('sc_them_dong'), [
      { id: 'source', label: 'source', type: 'select', value: conKho.length ? 'kho' : 'mua',
        options: [['kho', NN.t('src_kho')], ['mua', NN.t('src_mua')]] },
      { id: 'part_id', label: 'pick_part', type: 'select', value: '',
        options: [['', '—']].concat(conKho.map(p => [p.id, `${p.name} · ${NN.t('stock_left')} ${so(p.qty)}`])) },
      { id: 'item_name', label: 'item', value: '', lo: true },
      { id: 'qty', label: 'qty', type: 'number', value: '1' },
      { id: 'unit_price', label: 'unit_price', type: 'number', value: '' },
      { id: 'currency', label: 'cur', type: 'select', value: 'LAK', options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    if (v.source === 'kho' && !v.part_id) return EPL.toast(NN.t('pick_part') + '?', 'loi');
    if (v.source !== 'kho' && !String(v.item_name || '').trim()) return EPL.toast(NN.t('item') + '?', 'loi');
    const lines = (O.lines || []).map(d => ({ id: d.id, item_key: d.item_key, item_name: d.item_name, qty: d.qty,
      unit_price: d.unit_price, currency: d.currency, source: d.source, part_id: d.part_id, note: d.note }));
    lines.push({ source: v.source, part_id: v.part_id || null, item_name: v.item_name, qty: v.qty,
      unit_price: v.unit_price === '' ? null : v.unit_price, currency: v.currency, note: v.note });
    try {
      O = await API.put('/api/lenh-sua-chua/' + O.id, { lines });
      PARTS = await API.get('/api/parts');
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- nạp */
  async function tai() {
    const thang = root.querySelector('#sc-thang').value;
    DS = await API.get('/api/lenh-sua-chua' + (thang ? '?thang=' + thang : ''));
    if (O && !DS.some(o => o.id === O.id)) O = null;
    if (O) { try { O = await API.get('/api/lenh-sua-chua/' + O.id); } catch (e) { O = null; } }
    ve(); veChiTiet();
  }

  EPL.modules['sua-chua'] = {
    async init(r, ctx) {
      root = r;
      r.querySelector('#sc-thang').value = (ctx.tham && ctx.tham.thang) || '';
      [XE, PARTS] = await Promise.all([API.get('/api/vehicles'), API.get('/api/parts')]);
      r.querySelector('#sc-xe').innerHTML = `<option value="">${NN.t('all')}</option>` +
        XE.map(x => `<option value="${esc(x.id)}">${esc(x.truck_no)}</option>`).join('');
      r.querySelector('#sc-tt').innerHTML = `<option value="">${NN.t('all')}</option>` +
        BUOC.map(([ma, khoa]) => `<option value="${ma}">${NN.t('sc_st_' + ma)}</option>`).join('');
      const them = r.querySelector('#sc-them'); them.hidden = !nhapDuoc();
      them.addEventListener('click', () => lap(null));
      ['#sc-thang', '#sc-xe', '#sc-tt'].forEach(s => r.querySelector(s).addEventListener('change', () => {
        if (s === '#sc-thang') tai().catch(EPL.baoLoi); else ve();
      }));
      r.querySelector('#sc-ct-dong').addEventListener('click', () => { O = null; ve(); veChiTiet(); });
      r.querySelector('#sc-ct-in').addEventListener('click', () => window.print());
      await tai();
      if (ctx.tham && ctx.tham.id) await xem(ctx.tham.id);
    },
    onLang() { if (root) { ve(); veChiTiet(); } },
  };
})();
