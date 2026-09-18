/* Chứng từ — Phiếu chi tạm ứng (in cho tài xế) và Phiếu thu (thu tiền khách). Số liệu từ /api/trips/{id}/phieu-chi|phieu-thu. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, tab = 'chi', DS = [], P = null, ACC = {}, LINH = [], vChon = null;
  let SO_LOAI = [], soLoaiChon = '';           // sổ chứng từ: danh mục loại · loại đang lọc
  const XEM_SO = ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'depot', 'admin'];
  const q = (s) => root.querySelector(s);

  function tenTK(ma) {
    // "625/402" → hai nửa, mỗi nửa tra danh mục anh Khang; nửa không có thì nói thẳng
    return String(ma || '').split('/').map(m => { const x = ACC[m]; return `<span class="ct-acc" title="${esc(x ? (x.description || x.name) : NN.t('acct_not_in_catalogue'))}">${esc(m)}</span>`; }).join(' / ');
  }
  function chuSo(n) { return so(n) + ' LAK'; }

  /** Khối mã QR in trên phiếu. QR chỉ chứa ĐƯỜNG DẪN TRA CỨU, không nhồi số liệu:
   *  số liệu còn đổi sau lúc in, nhồi vào là tờ giấy nói một đằng hệ thống nói một nẻo.
   *  Người cấp quét ra màn "Cấp phát" với số mới nhất; mã chữ in dưới để gõ tay khi máy quét hỏng. */
  function khoiQR(v) {
    if (!v) return '';
    return `<div class="ct-qr">
      <img src="${esc(v.qr)}" alt="QR" width="132" height="132">
      <div><div class="small muted">${NN.h('v_qr_hint')}</div>
        <div class="ct-ma">${NN.h('v_code')}: <b class="mono">${esc(v.token)}</b></div>
        <div class="small muted">${EPL.tag(v.status === 'da_cap' ? 'paid' : 'plain', 'v_' + v.status)}</div></div></div>`;
  }

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
      <table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h('qty')}</th><th class="num tien">${NN.h('unit_price')}</th><th class="num tien">${NN.h('amount_lak')}</th><th class="tien">${NN.h('acct_pair')}</th></tr></thead>
        <tbody>${d.dong.map((x, i) => `<tr><td>${i + 1}</td><td lang="lo">${esc(x.item_key ? NN.t(x.item_key) : x.item_name)}</td><td class="num">${so(x.qty)}</td><td class="num tien">${so(x.unit_price)}${x.currency !== 'LAK' ? ' ' + esc(x.currency) : ''}</td><td class="num tien">${so(x.tien_lak)}</td><td class="tien">${tenTK(x.acct_code)}</td></tr>`).join('')}</tbody></table>
      <div class="ct-tong tien"><div><span>${NN.h('total')}</span><span>${chuSo(d.tong_lak)}</span></div></div>
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.trang_thai === 'paid' ? 'paid' : d.trang_thai === 'wait' ? 'plain' : 'partial', tt)} ${d.tra_tien_xong ? '· ' + NN.h('advance_received') : ''}</div>
      ${khoiQR(LINH.find(v => v.kind === 'advance'))}
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
        <div><span>${NN.h('c_w_dest')}</span><span>${so(d.tan_tinh, 2)} ${NN.h('ton')}<span class="tien"> × ${so(d.price_usd, 2)} USD</span></span></div><div class="tien"><span>${NN.h('acct_pair')}</span><span>${tenTK(d.acct_code)}</span></div>
        <div style="grid-column:1/-1"><span>${NN.h('purpose')}</span><span lang="lo">${NN.h('purpose_receipt', { doc_no: d.doc_no, tuyen: (d.origin || '') + ' → ' + (d.destination || '') })}</span></div>
      </div>
      <div class="ct-tong tien"><div><span>${NN.h('amount')}</span><span>${so(d.doanh_thu_usd, 2)} USD</span></div></div>
      <div class="ct-chu">≈ ${so(d.doanh_thu_lak)} LAK (1 USD = ${so(d.rate_usd)} LAK)</div>
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.finance_status, 'fin_' + d.finance_status)}</div>
      <div class="ct-ky"><div><div class="line"></div>${NN.h('payer_name')}</div><div><div class="line"></div>${NN.h('sg_cashier')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }
  /** PHIẾU LĨNH NHIÊN LIỆU — tài xế cầm đến đúng kho ghi ở ô Nơi đổ.
   *  Là phiếu lập LÚC XE CHƯA ĐI nên cố ý KHÔNG in: ngày về, lúc về, km chạy, cân cuối, hao hụt,
   *  thành tiền và quy đổi — những ô đó lúc này chưa ai biết, in ô trống chỉ tổ rối. */
  function veLinh(v, p) {
    if (!v) {
      q('#ct-so').innerHTML = '';
      q('#ct-than').innerHTML = `<div class="ct-tieu-de">${NN.h('v_fuel')}</div><div class="ct-trong">${NN.h('v_none')}
        <div class="small" style="margin-top:8px">${NN.h('v_make_fuel')}: ${NN.h('nav_dispatch')}</div></div>`;
      return;
    }
    q('#ct-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(v.doc_no)}</b>${EPL.ngay(v.doc_date)}`;
    const o = (k, val, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(val == null || val === '' ? '—' : val)}</span></div>`;
    q('#ct-than').innerHTML = `
      <div class="ct-tieu-de">${NN.h('v_fuel')}</div>
      <div class="ct-phu">ໃບເບີກນໍ້າມັນ · Fuel draw slip</div>
      <div class="ct-meta">
        ${o('doc_no', v.doc_no)}${o('fp_place', v.place_name, true)}
        ${o('truck_no', p.truck_no)}${o('driver', v.driver_name, true)}
        ${o('plate_head', p.plate_head, true)}${o('plate_trailer', p.plate_trailer, true)}
        ${o('customer', p.customer_name, true)}${o('goods_type', p.goods_type ? NN.t(p.goods_type) : '')}
        ${o('origin', p.origin, true)}${o('dest', p.destination, true)}
        ${o('c_w_origin', p.weight_origin != null ? so(p.weight_origin, 2) + ' ' + NN.t('ton') : '')}${o('d_out', EPL.ngay(p.out_date))}
      </div>
      <div class="ct-tong"><div><span>${NN.h('v_qty_ok')}</span><span>${so(v.qty_l, 1)} L</span></div></div>
      ${khoiQR(v)}
      ${v.status === 'da_cap' ? `<div class="ct-tt"><span class="muted">${NN.h('v_granted_by')}:</span> <b lang="lo">${esc(v.granted_by || '')}</b>
        ${v.granted_qty != null ? ' · ' + NN.h('v_qty_real') + ' <b>' + so(v.granted_qty, 1) + ' L</b>' : ''}</div>` : ''}
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_receiver')}<div class="small muted" lang="lo">${esc(v.driver_name || '')}</div></div>
        <div><div class="line"></div>${NN.h('fp_keeper')}</div>
        <div><div class="line"></div>${NN.h('sg_chief_acct')}</div>
        <div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }

  /* ---------------------------------------------------------------- sổ chứng từ */
  function veSoTong(tong) {
    q('#ct-so-tong').innerHTML = Object.keys(tong).length ? SO_LOAI.filter(l => tong[l.ma]).map(l => {
      const t = tong[l.ma];
      return `<button type="button" class="o ${soLoaiChon === l.ma ? 'chon' : ''}" data-loai="${l.ma}"><b>${esc(l.ma)}</b>${esc(NN.lang === 'lo' ? l.ten_lo : l.ten)}
        <div><span class="n">${t.so_to}</span> ${NN.h('ct_so_to').toLowerCase()} · <span class="n">${so(t.tien_lak)}</span> LAK${t.chua_day ? ` · <span class="c">${t.chua_day} ${NN.h('ct_chua_day').toLowerCase()}</span>` : ''}</div></button>`;
    }).join('') : '';
    q('#ct-so-tong').querySelectorAll('[data-loai]').forEach(b => b.addEventListener('click', () => { soLoaiChon = soLoaiChon === b.dataset.loai ? '' : b.dataset.loai; q('#ct-so-loai').value = soLoaiChon; veSo(); }));
  }
  async function veSo() {
    const th = new URLSearchParams();
    if (soLoaiChon) th.set('loai', soLoaiChon);
    if (q('#ct-so-tu').value) th.set('tu', q('#ct-so-tu').value);
    if (q('#ct-so-den').value) th.set('den', q('#ct-so-den').value);
    if (q('#ct-so-chua').checked) th.set('chua_day', '1');
    let r;
    try { r = await API.get('/api/chung-tu?' + th.toString()); } catch (e) { q('#ct-so-than').innerHTML = `<tr><td colspan="10" class="empty neg">${esc(e.message)}</td></tr>`; return; }
    veSoTong(r.tong);
    const tk = (ma, ten) => ma ? `<span class="acct" title="${esc(ten || '')}">${esc(ma)}</span>` : `<span class="muted small" title="${esc(ten || '')}">?</span>`;
    const suaDuoc = AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash');
    q('#ct-so-than').innerHTML = r.ds.length ? r.ds.map(c => `<tr class="${c.da_day ? 'da-day' : ''}" data-id="${c.id}">
      <td class="mono">${esc(c.so)}</td><td>${EPL.ngay(c.ngay)}</td>
      <td><b>${esc(c.loai)}</b><div class="small muted">${esc(NN.lang === 'lo' ? c.loai_ten_lo : c.loai_ten)}</div></td>
      <td>${c.trip_id ? `<a href="#/phieu-xuat-xe?id=${esc(c.trip_id)}" class="mono">${esc(c.trip_doc_no || '')}</a>` : '<span class="muted">—</span>'}</td>
      <td lang="lo">${esc(c.doi_tuong_ten || '')}<div class="small muted">${esc(c.doi_tuong_loai || '')}</div></td>
      <td class="num">${c.tien == null ? '—' : so(c.tien, c.tien_te === 'USD' ? 2 : 0) + ' ' + esc(c.tien_te)}</td>
      <td class="num">${c.tien_lak == null ? '—' : so(c.tien_lak)}</td>
      <td>${c.no || c.co || c.no_ten ? `${tk(c.no, c.no_ten)} / ${tk(c.co, c.co_ten)}` : '<span class="muted">—</span>'}</td>
      <td class="small">${esc(c.mo_ta || '')}<div class="muted">${esc(c.by_user || '')}</div></td>
      <td class="no-print">${suaDuoc ? `<button type="button" class="btn sm ${c.da_day ? 'quiet' : ''}" data-day="${c.id}" data-gia-tri="${c.da_day ? 0 : 1}">${NN.h(c.da_day ? 'ct_mo_lai' : 'ct_danh_dau')}</button>` : (c.da_day ? '✓' : '')}</td>
    </tr>`).join('') : `<tr><td colspan="10" class="empty small">${NN.h('ct_khong_co')}</td></tr>`;
    q('#ct-so-than').querySelectorAll('[data-day]').forEach(b => b.addEventListener('click', async () => {
      try { await API.post(`/api/chung-tu/${b.dataset.day}/da-day`, { da_day: b.dataset.giaTri === '1' }); await veSo(); } catch (e) { EPL.baoLoi(e); }
    }));
  }
  function doiTab() {
    const la = tab === 'so';
    q('#ct-so-ct').hidden = !la; q('#ct-giay').hidden = la;
    root.querySelectorAll('.ct-khi-in').forEach(el => { el.hidden = la; });
    q('#ct-o-linh').hidden = la || tab !== 'linh' || LINH.filter(v => v.kind === 'fuel').length < 2;
  }

  async function ve() {
    doiTab();
    if (tab === 'so') { await veSo(); return; }
    if (!P) { q('#ct-than').innerHTML = `<div class="ct-trong">${NN.h('no_data')}</div>`; return; }
    try {
      LINH = await API.get(`/api/trips/${P.id}/vouchers`).catch(() => []);
      const lo = LINH.filter(v => v.kind === 'fuel');
      q('#ct-o-linh').hidden = tab !== 'linh' || lo.length < 2;
      if (lo.length) {
        if (!vChon || !lo.some(v => v.id === vChon)) vChon = lo[0].id;
        q('#ct-linh').innerHTML = lo.map(v => `<option value="${v.id}" ${v.id === vChon ? 'selected' : ''}>${esc(v.doc_no)} · ${esc(v.place_name || '')}</option>`).join('');
      } else { vChon = null; q('#ct-linh').innerHTML = ''; }
      if (tab === 'chi') veChi(await API.get(`/api/trips/${P.id}/phieu-chi`));
      else if (tab === 'linh') veLinh(lo.find(v => v.id === vChon), P);
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
      if (!XEM_SO.includes(AUTH.role)) root.querySelector('.ct-tab button[data-tab="so"]').hidden = true;
      else {
        SO_LOAI = await API.get('/api/chung-tu/loai').catch(() => []);
        q('#ct-so-loai').innerHTML = `<option value="">${NN.h('all')}</option>` + SO_LOAI.map(l => `<option value="${l.ma}">${esc(l.ma)} · ${esc(NN.lang === 'lo' ? l.ten_lo : l.ten)}</option>`).join('');
        q('#ct-so-loai').addEventListener('change', e => { soLoaiChon = e.target.value; veSo(); });
        ['ct-so-tu', 'ct-so-den', 'ct-so-chua'].forEach(id => q('#' + id).addEventListener('change', veSo));
      }
      q('#ct-linh').addEventListener('change', e => { vChon = e.target.value; ve(); });
      const t = ctx.tham || {};
      if (t.tab && ['chi', 'linh', 'thu', 'so'].includes(t.tab) && !root.querySelector(`.ct-tab button[data-tab="${t.tab}"]`).hidden) {
        tab = t.tab;
        root.querySelectorAll('.ct-tab button').forEach(x => x.classList.toggle('active', x.dataset.tab === tab));
      }
      if (t.v) vChon = t.v;
      P = DS.find(p => p.id === t.id) || DS[0] || null;
      if (P) q('#ct-chon').value = P.id;
      if (t.loai) soLoaiChon = String(t.loai).toUpperCase();
      await ve();
    },
    onLang() { if (root) ve(); },
  };
})();
