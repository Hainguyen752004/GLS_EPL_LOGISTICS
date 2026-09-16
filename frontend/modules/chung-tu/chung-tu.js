/* Chứng từ — Phiếu chi tạm ứng (in cho tài xế) và Phiếu thu (thu tiền khách). Số liệu từ /api/trips/{id}/phieu-chi|phieu-thu. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, tab = 'chi', DS = [], P = null, ACC = {};
  const q = (s) => root.querySelector(s);

  function tenTK(ma) {
    // "625/402" → hai nửa, mỗi nửa tra danh mục anh Khang; nửa không có thì nói thẳng
    return String(ma || '').split('/').map(m => { const x = ACC[m]; return `<span class="ct-acc" title="${esc(x ? (x.description || x.name) : NN.t('acct_not_in_catalogue'))}">${esc(m)}</span>`; }).join(' / ');
  }
  function chuSo(n) { return so(n) + ' LAK'; }

  function veChi(d) {
    q('#ct-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(d.so_phieu_chi)}</b>${EPL.ngay(d.doc_date)}`;
    const tt = d.trang_thai === 'wait' ? 'stt_wait2' : 'stt_' + d.trang_thai;
    if (!d.dong.length) { q('#ct-than').innerHTML = `<div class="ct-tieu-de">${NN.h('voucher_payment')}</div><div class="ct-trong">${NN.h('no_advance_lines')}</div>`; return; }
    q('#ct-than').innerHTML = `
      <div class="ct-tieu-de">${NN.h('voucher_payment')}</div>
      <div class="ct-phu">ໃບຈ່າຍເງິນລ່ວງໜ້າ · Advance payment voucher</div>
      <div class="ct-meta">
        <div><span>${NN.h('payee')}</span><span lang="lo"><b>${esc(d.driver_name || '—')}</b></span></div><div><span>${NN.h('doc_no')}</span><span class="mono"><b>${esc(d.doc_no)}</b></span></div>
        <div><span>${NN.h('truck_no')}</span><span>${esc(d.truck_no)} · <span lang="lo">${esc(d.plate_head)} / ${esc(d.plate_trailer)}</span></span></div><div><span>${NN.h('truck_type')}</span><span>${d.company === 'joint' ? NN.h('co_joint') + ' · ' + esc(d.owner_name || '') : NN.h('co_epl')}</span></div>
        <div style="grid-column:1/-1"><span>${NN.h('purpose')}</span><span lang="lo">${NN.h('purpose_advance', { doc_no: d.doc_no, tuyen: (d.origin || '') + ' → ' + (d.destination || '') })}</span></div>
      </div>
      <table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h('qty')}</th><th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th><th>${NN.h('acct_pair')}</th></tr></thead>
        <tbody>${d.dong.map((x, i) => `<tr><td>${i + 1}</td><td lang="lo">${esc(x.item_key ? NN.t(x.item_key) : x.item_name)}</td><td class="num">${so(x.qty)}</td><td class="num">${so(x.unit_price)}${x.currency !== 'LAK' ? ' ' + esc(x.currency) : ''}</td><td class="num">${so(x.tien_lak)}</td><td>${tenTK(x.acct_code)}</td></tr>`).join('')}</tbody></table>
      <div class="ct-tong"><div><span>${NN.h('total')}</span><span>${chuSo(d.tong_lak)}</span></div></div>
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.trang_thai === 'paid' ? 'paid' : d.trang_thai === 'wait' ? 'plain' : 'partial', tt)} ${d.tra_tien_xong ? '· ' + NN.h('advance_received') : ''}</div>
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_receiver')}<div class="small muted" lang="lo">${esc(d.driver_name || '')}</div></div><div><div class="line"></div>${NN.h('sg_cashier')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }
  function veThu(d) {
    q('#ct-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(d.so_phieu_thu)}</b>${EPL.ngay(d.doc_date)}`;
    if (!d.invoiced) { q('#ct-than').innerHTML = `<div class="ct-tieu-de">${NN.h('voucher_receipt')}</div><div class="ct-trong">${NN.h('not_invoiced_yet')}<br><span class="small">${NN.h('sec2')}: ${NN.h(d.trans_status === 'wait' ? 'stt_wait2' : 'stt_' + d.trans_status)}</span></div>`; return; }
    q('#ct-than').innerHTML = `
      <div class="ct-tieu-de">${NN.h('voucher_receipt')}</div>
      <div class="ct-phu">ໃບຮັບເງິນ · Receipt voucher</div>
      <div class="ct-meta">
        <div><span>${NN.h('payer_name')}</span><span lang="lo"><b>${esc(d.customer_name || '—')}</b></span></div><div><span>${NN.h('doc_no')}</span><span class="mono"><b>${esc(d.doc_no)}</b></span></div>
        <div><span>${NN.h('c_w_dest')}</span><span>${so(d.tan_tinh, 2)} ${NN.h('ton')} × ${so(d.price_usd, 2)} USD</span></div><div><span>${NN.h('acct_pair')}</span><span>${tenTK(d.acct_code)}</span></div>
        <div style="grid-column:1/-1"><span>${NN.h('purpose')}</span><span lang="lo">${NN.h('purpose_receipt', { doc_no: d.doc_no, tuyen: (d.origin || '') + ' → ' + (d.destination || '') })}</span></div>
      </div>
      <div class="ct-tong"><div><span>${NN.h('amount')}</span><span>${so(d.doanh_thu_usd, 2)} USD</span></div></div>
      <div class="ct-chu">≈ ${so(d.doanh_thu_lak)} LAK (1 USD = ${so(d.rate_usd)} LAK)</div>
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.finance_status, 'fin_' + d.finance_status)}</div>
      <div class="ct-ky"><div><div class="line"></div>${NN.h('payer_name')}</div><div><div class="line"></div>${NN.h('sg_cashier')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }
  async function ve() {
    if (!P) { q('#ct-than').innerHTML = `<div class="ct-trong">${NN.h('no_data')}</div>`; return; }
    try {
      if (tab === 'chi') veChi(await API.get(`/api/trips/${P.id}/phieu-chi`));
      else veThu(await API.get(`/api/trips/${P.id}/phieu-thu`));
    } catch (e) { q('#ct-than').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; }
  }
  EPL.modules['chung-tu'] = {
    async init(r, ctx) {
      root = r;
      const [ds, acc] = await Promise.all([API.get('/api/trips'), API.get('/api/acc-codes').catch(() => ({ data: [], source: 'error' }))]);
      DS = ds; ACC = {}; (acc.data || []).forEach(x => { ACC[x.code] = x; });
      q('#ct-acc-nguon').innerHTML = NN.h(acc.source === 'remote' || acc.source === 'cached' ? 'acct_source_remote' : 'acct_source_fallback');
      q('#ct-chon').innerHTML = DS.map(p => `<option value="${p.id}">${esc(p.doc_no)} · ${esc(p.driver_name || '')}</option>`).join('');
      q('#ct-chon').addEventListener('change', e => { P = DS.find(p => p.id === e.target.value); ve(); });
      q('#ct-mo-phieu').addEventListener('click', () => P && EPL.di('phieu-xuat-xe', { id: P.id }));
      root.querySelectorAll('.ct-tab button').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; root.querySelectorAll('.ct-tab button').forEach(x => x.classList.toggle('active', x === b)); ve(); }));
      if (AUTH.role === 'driver') root.querySelector('.ct-tab button[data-tab="thu"]').hidden = true;
      const t = ctx.tham || {}; P = DS.find(p => p.id === t.id) || DS[0] || null;
      if (P) q('#ct-chon').value = P.id;
      await ve();
    },
    onLang() { if (root) ve(); },
  };
})();
