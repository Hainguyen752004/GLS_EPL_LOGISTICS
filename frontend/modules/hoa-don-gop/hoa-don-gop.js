/* Hoá đơn gộp tháng — ໃບເກັບເງິນລວມເດືອນ (anh Khampla C8.2).
 *
 * Khách có cờ "gộp tháng" thì không xuất hoá đơn từng phiếu. Cuối tháng vào đây:
 *   1. Bảng "Chờ gộp" liệt kê từng khách × từng loại tiền còn phiếu đã khoá chưa lên hoá đơn.
 *   2. Bấm "Gộp hoá đơn tháng" → một tờ HDT nhiều dòng phiếu.
 *   3. Thu tiền ghi ở TỜ, máy chủ tự rải xuống từng phiếu theo thứ tự ngày — nên trạng thái
 *      "đã thu" của từng phiếu vẫn đúng, báo cáo theo phiếu không treo sai.
 * Mọi con số lấy từ máy chủ, màn này không tự cộng lại.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, thang = '', cho = [], ds = [], HD = null;

  const lapDuoc = () => AUTH.la('rev');
  const PT_CACH = [['bank', 'pm_bank'], ['cash', 'pm_cash'], ['offset', 'pm_offset'], ['other', 'pm_other']];
  const tenCach = (m) => NN.h((PT_CACH.find(c => c[0] === m) || ['', 'pm_other'])[1]);

  /* ---------------------------------------------------------------- chờ gộp */
  function veCho() {
    root.querySelector('#hg-cho').innerHTML = cho.length ? cho.map(o => `<tr>
      <td lang="lo"><b>${esc(o.customer_name)}</b></td>
      <td class="mono">${esc(o.ccy)}</td>
      <td class="num">${o.so_phieu}</td>
      <td class="num"><b>${EPL.tien(o.tong, o.ccy)}</b></td>
      <td class="num">${so(o.tong_lak)}</td>
      <td class="hg-phieu">${o.phieu.map(p => esc(p.doc_no)).join(' · ')}</td>
      <td class="no-print">${lapDuoc() ? `<button class="btn sm ok" data-gop="${esc(o.customer_id)}" data-ccy="${esc(o.ccy)}">${NN.h('hg_gop')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('hg_cho_trong')}</td></tr>`;
    root.querySelectorAll('[data-gop]').forEach(b => b.addEventListener('click',
      () => gop(cho.find(o => o.customer_id === b.dataset.gop && o.ccy === b.dataset.ccy))));
  }

  /* ---------------------------------------------------------------- danh sách hoá đơn gộp */
  function veDs() {
    root.querySelector('#hg-than').innerHTML = ds.length ? ds.map(h => `<tr class="${HD && HD.id === h.id ? 'chon' : ''}">
      <td class="mono"><b>${esc(h.inv_no)}</b></td>
      <td lang="lo">${esc(h.customer_name)}</td>
      <td>${esc(h.period)}</td>
      <td>${EPL.ngay(h.inv_date)}</td>
      <td class="num">${h.so_phieu}</td>
      <td class="num"><b>${EPL.tien(h.amount, h.currency)}</b><div class="hg-cach">${so(h.amount_lak)} LAK</div></td>
      <td class="num">${so(h.da_thu_lak)}</td>
      <td class="num ${h.con_lai_lak > 0 ? 'neg' : 'pos'}">${so(h.con_lai_lak)}</td>
      <td>${tag(h.finance_status)}</td>
      <td class="no-print"><button class="btn sm" data-xem="${esc(h.id)}">${NN.h('view')}</button></td></tr>`).join('')
      : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#hg-dem').textContent = ds.length ? `${ds.length} ${NN.t('rows')}` : '';
    root.querySelectorAll('[data-xem]').forEach(b => b.addEventListener('click', () => xem(b.dataset.xem)));
  }

  /* ---------------------------------------------------------------- một tờ: dòng phiếu + sổ thu */
  function veChiTiet() {
    const o = root.querySelector('#hg-chi-tiet');
    o.hidden = !HD;
    if (!HD) return;
    root.querySelector('#hg-ct-ten').innerHTML = `${esc(HD.inv_no)} · <span lang="lo">${esc(HD.customer_name)}</span> · ${esc(HD.period)}`;
    const dongPhieu = (HD.phieu || []).map((p, i) => `<tr>
      <td>${i + 1}</td>
      <td class="mono"><a href="#/phieu-xuat-xe?id=${esc(p.id)}">${esc(p.doc_no)}</a></td>
      <td>${EPL.ngay(p.doc_date)}</td>
      <td>${esc(p.truck_no || '')}</td>
      <td class="mono small">${esc(p.ore_bill_no || '')}</td>
      <td class="num">${so(p.tan_tinh, 2)}</td>
      <td class="num">${EPL.tien(p.price, p.ccy)}<div class="hg-cach">${NN.h(p.cach_tinh === 'chuyen' ? 'pm_chuyen_s' : 'pm_ton_s')}</div></td>
      <td class="num"><b>${EPL.tien(p.doanh_thu, p.ccy)}</b></td>
      <td class="num">${so(p.da_thu_lak)}</td>
      <td>${tag(p.finance_status)}</td></tr>`).join('');
    const dongThu = (HD.thu_tien || []).map(x => `<tr>
      <td class="nowrap">${EPL.ngay(x.pay_date)}</td>
      <td class="num"><b>${EPL.tien(x.amount, x.currency)}</b></td>
      <td class="num">${x.currency === 'LAK' ? '—' : so(x.rate_to_lak, x.currency === 'VND' ? 2 : 0)}</td>
      <td class="num">${so(x.amount_lak)}</td>
      <td>${tenCach(x.method)}</td>
      <td class="mono small">${esc(x.ref || '')}</td>
      <td class="small muted">${esc(x.by_user || '')}</td>
      <td class="no-print">${lapDuoc() ? `<button class="btn xs danger" data-xoa-thu="${esc(x.id)}" title="${esc(NN.t('pay_del'))}">×</button>` : ''}</td></tr>`).join('');
    root.querySelector('#hg-ct-than').innerHTML = `
      <div class="hg-tong">
        <div><span>${NN.h('c_value')}</span><b>${EPL.tien(HD.amount, HD.currency)}</b></div>
        <div><span>${NN.h('in_lak')}</span><b>${so(HD.amount_lak)}</b></div>
        <div><span>${NN.h('collected')}</span><b>${so(HD.da_thu_lak)} LAK</b></div>
        <div><span>${NN.h('remaining')}</span><b class="${HD.con_lai_lak > 0 ? 'neg' : 'pos'}">${so(HD.con_lai_lak)} LAK</b></div>
        <div><span>${NN.h('hg_so_phieu')}</span><b>${HD.so_phieu}</b></div>
        <div><span>${NN.h('voucher_no')}</span><b class="mono">${esc(HD.chung_tu || '—')}</b></div>
      </div>
      <div class="hg-sec">${NN.h('hg_dong_phieu')}</div>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr>
        <th>#</th><th>${NN.h('doc_no')}</th><th>${NN.h('c_date')}</th><th>${NN.h('c_truck')}</th><th>${NN.h('ore_bill_no')}</th>
        <th class="num">${NN.h('c_w_dest')}</th><th class="num">${NN.h('c_price')}</th><th class="num">${NN.h('c_value')}</th>
        <th class="num">${NN.h('collected')}</th><th>${NN.h('c_st_f')}</th>
      </tr></thead><tbody>${dongPhieu}</tbody></table></div>
      <div class="hg-sec">${NN.h('collect_log')}</div>
      <div class="tbl-wrap">${(HD.thu_tien || []).length ? `<table class="tbl tbl-compact"><thead><tr>
        <th>${NN.h('pay_date')}</th><th class="num">${NN.h('pay_amount')}</th><th class="num">${NN.h('rate_day')}</th>
        <th class="num">${NN.h('in_lak')}</th><th>${NN.h('pay_method')}</th><th>${NN.h('pay_ref')}</th><th>${NN.h('by_user')}</th><th class="no-print"></th>
      </tr></thead><tbody>${dongThu}</tbody></table>` : `<p class="small muted">${NN.h('pay_none')}</p>`}</div>
      <p class="small muted">${NN.h('hg_phan_bo')}</p>
      <div class="no-print" style="display:flex;gap:8px;margin-top:10px">
        ${lapDuoc() && HD.con_lai_lak > 0 ? `<button class="btn sm ok" id="hg-thu">${NN.h('collect_new')}</button>` : ''}
        ${lapDuoc() && !(HD.thu_tien || []).length ? `<button class="btn sm danger" id="hg-huy">${NN.h('hg_huy')}</button>` : ''}
      </div>`;
    const bThu = root.querySelector('#hg-thu'); if (bThu) bThu.addEventListener('click', ghiThu);
    const bHuy = root.querySelector('#hg-huy'); if (bHuy) bHuy.addEventListener('click', huy);
    root.querySelectorAll('[data-xoa-thu]').forEach(b => b.addEventListener('click', () => xoaThu(b.dataset.xoaThu)));
  }

  /* ---------------------------------------------------------------- hành động */
  async function gop(o) {
    if (!o) return;
    const v = await EPL.hopNhap(NN.t('hg_gop'), [
      { id: 'inv_date', label: 'hg_inv_date', type: 'date', value: EPL.homNay() },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('hg_gop'));
    if (!v) return;
    try {
      HD = await API.post('/api/hoa-don-gop', { customer_id: o.customer_id, period: thang, currency: o.ccy, inv_date: v.inv_date, note: v.note });
      EPL.toast(NN.t('saved'), 'ok');
      await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function xem(id) {
    try { HD = await API.get('/api/hoa-don-gop/' + id); veDs(); veChiTiet();
      const o = root.querySelector('#hg-chi-tiet'); if (o.scrollIntoView) o.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } catch (e) { EPL.baoLoi(e); }
  }

  async function ghiThu() {
    const v = await EPL.hopNhap(NN.t('collect_new'), [
      { id: 'pay_date', label: 'pay_date', type: 'date', value: EPL.homNay() },
      { id: 'currency', label: 'ccy', type: 'select', value: HD.currency, options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'amount', label: 'pay_amount', type: 'number', value: '' },
      { id: 'rate_to_lak', label: 'rate_day', type: 'number', value: '' },
      { id: 'method', label: 'pay_method', type: 'select', value: 'bank', options: PT_CACH.map(([x, t]) => [x, NN.t(t)]) },
      { id: 'ref', label: 'pay_ref', value: '' },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    if (!(EPL.doc(v.amount) > 0)) return EPL.toast(NN.t('pay_amount') + '?', 'loi');
    const than = { pay_date: v.pay_date, amount: v.amount, currency: v.currency, method: v.method, ref: v.ref, note: v.note };
    if (v.rate_to_lak !== '' && v.rate_to_lak != null) than.rate_to_lak = v.rate_to_lak;
    try {
      HD = await API.post(`/api/hoa-don-gop/${HD.id}/thu-tien`, than);
    } catch (e) {
      if (!/THU_QUA_HOA_DON/.test(e.ma || '') && !/THU_QUA_HOA_DON/.test(String(e.message))) return EPL.baoLoi(e);
      if (!await EPL.hoi(NN.t('pay_over'), `<p>${esc(e.message)}</p>`, NN.t('pay_over_ok'))) return;
      than.cho_thu_du = true;
      try { HD = await API.post(`/api/hoa-don-gop/${HD.id}/thu-tien`, than); } catch (e2) { return EPL.baoLoi(e2); }
    }
    EPL.toast(NN.t('saved'), 'ok');
    await tai();
  }

  async function xoaThu(id) {
    if (!await EPL.hoi(NN.t('pay_del'), `<p>${NN.h('confirm_delete')}</p>`, NN.t('delete'))) return;
    try { HD = await API.goi('/api/hoa-don-thu/' + id, { method: 'DELETE' }); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  async function huy() {
    if (!await EPL.hoi(NN.t('hg_huy'), `<p>${NN.h('hg_huy_hoi')}</p>`, NN.t('hg_huy'))) return;
    try { await API.goi('/api/hoa-don-gop/' + HD.id, { method: 'DELETE' }); HD = null; EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- nạp */
  async function tai() {
    thang = root.querySelector('#hg-thang').value || new Date().toISOString().slice(0, 7);
    const [c, d] = await Promise.all([API.get('/api/hoa-don-gop/cho-gop?period=' + thang), API.get('/api/hoa-don-gop?period=' + thang)]);
    cho = c.ds || []; ds = d || [];
    if (HD && !ds.some(h => h.id === HD.id)) HD = null;
    if (HD) { try { HD = await API.get('/api/hoa-don-gop/' + HD.id); } catch (e) { HD = null; } }
    veCho(); veDs(); veChiTiet();
  }

  EPL.modules['hoa-don-gop'] = {
    async init(r, ctx) {
      root = r;
      const t = r.querySelector('#hg-thang');
      t.value = (ctx.tham && ctx.tham.thang) || new Date().toISOString().slice(0, 7);
      t.addEventListener('change', () => tai().catch(EPL.baoLoi));
      r.querySelector('#hg-ct-dong').addEventListener('click', () => { HD = null; veDs(); veChiTiet(); });
      r.querySelector('#hg-ct-in').addEventListener('click', () => window.print());
      await tai();
      if (ctx.tham && ctx.tham.id) await xem(ctx.tham.id);
    },
    onLang() { if (root) { veCho(); veDs(); veChiTiet(); } },
  };
})();
