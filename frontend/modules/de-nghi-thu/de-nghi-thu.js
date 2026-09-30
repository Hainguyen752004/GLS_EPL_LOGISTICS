/* Phiếu đề nghị thu — ໃບສະເໜີຮັບເງິນ (sếp 30/09).
 *
 * DO xong (xe về, có biên bản giao nhận, kế toán Viêng Chăn KHOÁ phiếu) → máy lập tờ đề nghị thu cước (loại PDT) — gửi bên
 * công nợ (anh Tune) lập SO, xuất hoá đơn, thu tiền khách. Bên mình không thu tiền: màn này xem trạng thái bên đó chép sang
 * (chờ gửi · đã gửi · đã xuất hoá đơn · đã thu đủ), in tờ, gửi tờ còn chờ. Số tiền theo ĐÚNG tiền tệ cước của phiếu.
 *
 * API: GET /api/de-nghi-thu?thang=&q= · GET/POST /api/trips/{id}/de-nghi-thu · POST /api/chung-tu/{id}/day (gửi một tờ).
 * Tạo SO bên kế toán (anh Tune, hợp đồng mục 3.2): GET /api/trips/{id}/tao-so (xem trước, không gọi mạng) → hỏi xác nhận →
 * POST /api/trips/{id}/tao-so. Chỉ KT Thu/Chi Viêng Chăn và Sếp; máy chủ cũng chặn vai khác.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  const TT = ['cho_gui', 'da_gui', 'da_hoa_don', 'da_thu', 'cho_khoa', ''];
  let root, D = { ds: [] }, tt = '', tim = '', chonId = null, KET_NOI = { cau_hinh: false }, hen = null;
  const q = (s) => root.querySelector(s);
  const tagTT = (s) => `<span class="tag dt_${esc(s)}">${NN.h('dt_st_' + s)}</span>`;
  const tien = (n, ma) => EPL.tien(n, ma);
  const thangNay = () => new Date().toISOString().slice(0, 7);

  function loc() {
    return D.ds.filter(x => !tt || x.trang_thai === tt || (tt === 'cho_gui' && x.trang_thai === 'chua_lap'));
  }

  /* ---------------------------------------------------------------- thanh trạng thái + dải tổng */
  function veSeg() {
    const dem = {};
    D.ds.forEach(x => { const k = x.trang_thai === 'chua_lap' ? 'cho_gui' : x.trang_thai; dem[k] = (dem[k] || 0) + 1; });
    q('#dnt-tt').innerHTML = TT.map(k => `<button data-tt="${k}" class="${tt === k ? 'on' : ''}">
      <span>${NN.h(k ? 'dt_st_' + k : 'all')}</span><b>${k ? (dem[k] || 0) : D.ds.length}</b></button>`).join('');
    root.querySelectorAll('#dnt-tt button').forEach(b => b.addEventListener('click', () => { tt = b.dataset.tt; veHet(); }));
  }
  function veTong() {
    // cộng theo TIỀN TỆ của cước — không quy đổi thầm về một tiền rồi gắn nhãn (chủ dự án: hiện đúng tiền của chứng từ)
    const de = {}, cho = {};
    D.ds.filter(x => x.locked).forEach(x => { de[x.ccy] = (de[x.ccy] || 0) + (x.doanh_thu || 0); });
    D.ds.filter(x => ['cho_gui', 'chua_lap'].includes(x.trang_thai)).forEach(x => { cho[x.ccy] = (cho[x.ccy] || 0) + (x.doanh_thu || 0); });
    const nCho = D.ds.filter(x => ['cho_gui', 'chua_lap'].includes(x.trang_thai)).length;
    const conLak = D.ds.filter(x => x.locked).reduce((s, x) => s + (x.con_lai_lak || 0), 0);
    const oTien = (m) => Object.keys(m).length ? Object.entries(m).map(([k, v]) => `${so(v, EPL.leTien(k))}<small>${esc(k)}</small>`).join(' · ') : '—';
    q('#dnt-tong').innerHTML = `
      <div class="o"><span class="l">${NN.h('dt_tong_thang')}</span><span class="v">${oTien(de)}</span><span class="s">${NN.h('dn_so_to', { n: D.ds.filter(x => x.locked).length })}</span></div>
      <div class="o ${nCho ? 'canh' : ''}"><span class="l">${NN.h('dt_st_cho_gui')}</span><span class="v">${oTien(cho)}</span><span class="s">${NN.h('dn_so_to', { n: nCho })}</span></div>
      <div class="o"><span class="l">${NN.h('ncc_con_thu')}</span><span class="v">${so(conLak)}<small>LAK</small></span><span class="s">${NN.h('dt_con_lai_s')}</span></div>`;
  }

  /* ---------------------------------------------------------------- danh sách DO */
  function veDs() {
    const ds = loc(), o = q('#dnt-ds');
    if (!ds.length) { o.innerHTML = `<div class="dnt-trong">${NN.h('dt_trong')}</div>`; return; }
    o.innerHTML = ds.map(x => `<button type="button" class="dnt-o st-${esc(x.trang_thai)} ${x.trip_id === chonId ? 'chon' : ''}" data-id="${esc(x.trip_id)}">
      <div class="so">${esc(x.doc_no)}<span class="dnt-kind ${esc(x.kind)}">${NN.h(x.kind === 'gom' ? 'dn_gom' : 'dn_giao')}</span></div>
      <div class="tien">${tien(x.doanh_thu, x.ccy)}</div>
      <div class="kh" lang="lo">${esc(x.customer_name || '—')}</div>
      <div class="tt">${tagTT(x.trang_thai)}${x.so_ke_toan && x.so_ke_toan.da_tao_so ? ` <span class="tag dt_so">SO</span>`
        : x.so_ke_toan && x.so_ke_toan.error_message ? ` <span class="tag dt_so_loi" title="${esc(x.so_ke_toan.error_message)}">SO ⚠</span>` : ''}</div>
      <div class="phu"><span lang="lo">${esc(x.origin || '')} → ${esc(x.destination || '')}</span> · ${esc(x.truck_no || '')} · ${so(x.tan_tinh, 2)} ${NN.h('ton')}</div>
      <div class="phu" style="text-align:right">${x.pdt ? esc(x.pdt.so) : EPL.ngay(x.doc_date)}</div>
    </button>`).join('');
    o.querySelectorAll('.dnt-o').forEach(b => b.addEventListener('click', () => { chonId = b.dataset.id; veDs(); veTo(); }));
  }

  /* ---------------------------------------------------------------- tờ đề nghị thu */
  async function veTo() {
    const x = D.ds.find(y => y.trip_id === chonId), nut = q('#dnt-nut');
    if (!x) { nut.innerHTML = ''; q('#dnt-so').innerHTML = ''; q('#dnt-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    let d;
    try { d = await API.get(`/api/trips/${x.trip_id}/de-nghi-thu`); } catch (e) { q('#dnt-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; return; }
    if (chonId !== x.trip_id) return;
    const laKt = AUTH.la('acct');
    const sk = x.so_ke_toan;
    nut.innerHTML = `${tagTT(d.trang_thai)}
      ${sk && sk.da_tao_so ? `<span class="tag dt_so">${NN.h('dt_so_da', { so: sk.order_code || '' })}</span>` : ''}
      ${sk && !sk.da_tao_so && sk.error_message ? `<span class="small neg" title="${esc(sk.error_message)}">⚠ ${NN.h('dt_so_loi', { loi: sk.error_message.slice(0, 90) })}</span>` : ''}
      ${d.pdt && d.pdt.da_day && d.pdt.ma_ben_ke_toan ? `<span class="small muted">${NN.h('ct_ma_kt')}: <b class="mono">${esc(d.pdt.ma_ben_ke_toan)}</b></span>` : ''}
      ${d.pdt && d.pdt.loi_day ? `<span class="small neg" title="${esc(d.pdt.loi_day)}">⚠ ${esc(d.pdt.loi_day.slice(0, 80))}</span>` : ''}
      <span class="grow"></span>
      ${laKt && d.trang_thai === 'chua_lap' ? `<button class="btn primary" id="dnt-lap">${NN.h('dt_lap')}</button>` : ''}
      ${laKt && d.pdt && !d.pdt.da_day && KET_NOI.cau_hinh ? `<button class="btn primary" id="dnt-gui">${NN.h('dt_gui')}</button>` : ''}
      ${laKt && d.locked && !(sk && sk.da_tao_so) ? `<button class="btn primary" id="dnt-so-gui">${NN.h('dt_so_nut')}</button>` : ''}
      <button class="btn" id="dnt-mo">${NN.h('open_slip')}</button>
      <button class="btn ${d.pdt ? '' : 'quiet'}" id="dnt-in">${NN.h('print')}</button>`;
    q('#dnt-mo').addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: x.trip_id }));
    q('#dnt-in').addEventListener('click', () => window.print());
    const lap = q('#dnt-lap'); if (lap) lap.addEventListener('click', async () => {
      lap.disabled = true;
      try { await API.post(`/api/trips/${x.trip_id}/de-nghi-thu`, {}); EPL.toast(NN.t('saved'), 'ok'); } catch (e) { EPL.baoLoi(e); }
      await tai();
    });
    const gui = q('#dnt-gui'); if (gui) gui.addEventListener('click', async () => {
      gui.disabled = true;
      try { await API.post(`/api/chung-tu/${d.pdt.id}/day`, {}); EPL.toast(NN.t('ct_day_xong'), 'ok'); } catch (e) { EPL.baoLoi(e); }
      await tai();
    });
    const soGui = q('#dnt-so-gui'); if (soGui) soGui.addEventListener('click', async () => {
      // xem trước ở máy chủ (không gọi mạng): thiếu mã khách, thiếu tuyến, cước THB… thì nói rõ, không gửi
      let v;
      try { v = await API.get(`/api/trips/${x.trip_id}/tao-so`); } catch (e) { return EPL.baoLoi(e); }
      if (v.loi) return EPL.toast(v.loi.loi || v.loi.ma, 'loi');
      const tt = v.tom_tat || {};
      const tienSo = so(tt.final_selling_price, EPL.leTien(tt.currency)) + ' ' + (tt.currency || '');
      if (!await EPL.hoi(NN.t('dt_so_hoi'), NN.h('dt_so_hoi_nd', { kh: d.customer_name || '', ma: tt.customer_code || '', tien: tienSo }), NN.t('dt_so_nut'))) return;
      soGui.disabled = true;
      try { const r = await API.post(`/api/trips/${x.trip_id}/tao-so`, {}); EPL.toast(NN.t('dt_so_xong', { so: (r.trang_thai || {}).order_code || '' }), 'ok'); }
      catch (e) { EPL.baoLoi(e); }
      await tai();
    });

    q('#dnt-so').innerHTML = d.pdt ? `${NN.h('voucher_no')}<b>${esc(d.pdt.so)}</b>${EPL.ngay(d.pdt.ngay)}` : `<span class="muted">${NN.h('dt_ban_nhap')}</span>`;
    const o = (k, val, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${val == null || val === '' ? '—' : val}</span></div>`;
    const khoan = d.cach_tinh === 'chuyen';
    q('#dnt-to').innerHTML = `
      <div class="ct-tieu-de">${NN.h('dt_tieu_de')}</div>
      <div class="ct-phu">ໃບສະເໜີຮັບເງິນ · Collection request</div>
      <div class="ct-meta">
        ${o('customer', `<b>${esc(d.customer_name || '—')}</b>`, true)}${o('doc_no', `<b class="mono">${esc(d.doc_no)}</b> · ${NN.h(d.kind === 'gom' ? 'do_gom' : 'do_giao')}`)}
        ${o('hd_van_chuyen', esc(d.contract_no || ''))}${o('route', `${esc(d.origin || '')} → ${esc(d.destination || '')}`, true)}
        ${o('truck_no', `${esc(d.truck_no || '')} · <span lang="lo">${esc(d.plate_head || '')} / ${esc(d.plate_trailer || '')}</span>`)}${o('driver', esc(d.driver_name || ''), true)}
        ${o('d_out', EPL.ngay(d.out_date))}${o('d_back', EPL.ngay(d.back_date))}
        ${o('pod_no', `${esc(d.pod_no || '')}${d.pod_signed ? ' · ✓ ' + NN.h('dt_ky_may') : ''}`)}${o('pod_receiver', `${esc(d.pod_receiver || '')}${d.pod_date ? ' · ' + EPL.ngay(d.pod_date) : ''}`, true)}
        ${d.company === 'joint' ? o('truck_type', NN.h('co_joint') + ' · ' + esc(d.owner_name || '')) : ''}${o('ore_bill_no', esc(d.ore_bill_no || ''))}
      </div>
      <table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('dt_noi_dung')}</th><th class="num">${NN.h('col_tons')}</th>
        <th class="num">${NN.h(khoan ? 'pm_chuyen' : 'price_t')}</th><th class="num">${NN.h('amount')} (${esc(d.ccy)})</th></tr></thead>
        <tbody><tr><td>1</td><td lang="lo">${NN.h('dt_noi_dung')} · ${esc(d.goods_type ? NN.t(d.goods_type) : '')}</td>
          <td class="num">${so(d.tan_tinh, 3)}</td><td class="num">${so(d.don_gia, EPL.leTien(d.ccy))}</td><td class="num"><b>${so(d.doanh_thu, EPL.leTien(d.ccy))}</b></td></tr></tbody></table>
      <div class="ct-tong"><div><span>${NN.h('total')}</span><span>${tien(d.doanh_thu, d.ccy)}</span></div></div>
      ${d.ccy !== 'LAK' ? `<div class="dnt-quy">≈ ${so(d.doanh_thu_lak)} LAK · ${NN.h('rate_on_slip')} 1 ${esc(d.ccy)} = ${so(d.rate_to_lak, 2)} LAK</div>` : ''}
      <div class="dnt-ben">
        <span>${NN.h('status')}: ${tagTT(d.trang_thai)}</span>
        ${d.invoiced ? `<span>${NN.h('dt_st_da_hoa_don')}${d.inv_no ? `: <b class="mono">${esc(d.inv_no)}</b>` : ' ✓'}</span>` : ''}
        <span>${NN.h('collected')}: <b>${so(d.da_thu_lak)} LAK</b></span>
        <span>${NN.h('ncc_con_thu')}: <b>${so(d.con_lai_lak)} LAK</b></span>
        ${d.locked_by ? `<span>${NN.h('s_locked')}: <span lang="lo">${esc(d.locked_by)}</span> · ${esc((d.locked_at || '').replace('T', ' '))}</span>` : ''}
      </div>
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_issuer')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div>
        <div><div class="line"></div>${NN.h('dt_ben_cong_no')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }

  function veHet() {
    const ds = loc();
    if (!ds.some(x => x.trip_id === chonId)) chonId = ds[0] ? ds[0].trip_id : null;
    veSeg(); veTong(); veDs(); veTo();
  }

  async function tai() {
    const th = new URLSearchParams({ thang: q('#dnt-thang').value || thangNay() });
    if (tim) th.set('q', tim);
    try { D = await API.get('/api/de-nghi-thu?' + th.toString()); } catch (e) { D = { ds: [] }; EPL.baoLoi(e); }
    veHet();
  }

  EPL.modules['de-nghi-thu'] = {
    async init(r, ctx) {
      root = r; D = { ds: [] }; tim = ''; tt = ''; chonId = null;
      const t = (ctx && ctx.tham) || {};
      q('#dnt-thang').value = t.thang || thangNay();
      if (t.id) chonId = t.id;
      if (TT.includes(t.tt)) tt = t.tt;
      q('#dnt-thang').addEventListener('change', tai);
      q('#dnt-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      if (AUTH.la('acct')) { try { KET_NOI = await API.get('/api/ke-toan/trang-thai'); } catch (e) { KET_NOI = { cau_hinh: false }; } }
      await tai();
    },
    onLang() { if (root) veHet(); },
    xuatExcel() {
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_de_nghi_thu'), [T('doc_no'), T('do_kind'), T('customer'), T('route'), T('truck_no'), T('col_tons'), T('amount'), T('ccy'),
        T('amount_lak'), T('voucher_no'), T('status'), T('collected'), T('ncc_con_thu')],
        loc().map(x => [x.doc_no, T(x.kind === 'gom' ? 'dn_gom' : 'dn_giao'), x.customer_name || '', (x.origin || '') + ' → ' + (x.destination || ''), x.truck_no || '',
          EPL.oSo(x.tan_tinh, 3), EPL.oSo(x.doanh_thu, EPL.leTien(x.ccy), x.ccy), x.ccy, EPL.oSo(x.doanh_thu_lak, 0, 'LAK'), x.pdt ? x.pdt.so : '',
          T('dt_st_' + x.trang_thai), EPL.oSo(x.da_thu_lak, 0, 'LAK'), EPL.oSo(x.con_lai_lak, 0, 'LAK')]))];
    },
  };
})();
