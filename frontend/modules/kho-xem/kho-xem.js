/* Xem kho — ເບິ່ງສາງ. Theo MẶT HÀNG, CHỈ XEM (sếp 30/09: kho dời về trang logistics; thao tác kho do bên kho — anh Toàn).
 *
 * Ba nhóm: Nhiên liệu (mỗi kho dầu EPL một dòng), Phụ tùng (mỗi phụ tùng một dòng), Kho hàng (mỗi loại hàng khách gửi ở
 * bãi một dòng). Mỗi dòng: tồn, phần đang chờ xuất theo phiếu đề nghị, phần đã khai trên phiếu mà chưa có đề nghị, còn
 * lại, nhập / xuất trong tháng. Bấm một dòng → khung phải: phiếu đề nghị đang chờ (bấm số phiếu mở phiếu xuất xe), dòng
 * trên phiếu chưa có đề nghị, lô còn hàng, 10 lần nhập / xuất gần nhất.
 *
 * API: GET /api/kho-xem?thang=YYYY-MM (số tồn hỏi bên kho; phần chờ xuất là của trang điều xe). Bãi không nhận giá.
 */
(function () {
  const { API, NN, esc, so } = EPL;
  let root, D = null, tab = 'dau', chon = { dau: null, pt: null, hang: null }, tim = '', loi = '';

  const q = (s) => root.querySelector(s);
  const L = (n, d = 0) => (n === null || n === undefined) ? '—' : so(n, d);
  const lit = (n) => L(n, 0);
  const tan = (n) => L(n, 3);
  const donVi = (u) => u ? NN.t(u) : '';
  const thangNay = () => new Date().toISOString().slice(0, 7);
  const khop = (...s) => !tim || s.some(x => String(x || '').toLowerCase().includes(tim));

  /* ---------------------------------------------------------------- dữ liệu */
  async function tai() {
    loi = '';
    try {
      D = await API.get('/api/kho-xem?thang=' + encodeURIComponent(q('#kx-thang').value || thangNay()));
    } catch (e) { D = null; loi = e.message || String(e); }
    veHet();
  }

  function dsDau() {
    return (D ? D.nhien_lieu : []).filter(k => khop(k.name, k.code, ...(k.de_nghi || []).map(x => x.doc_no + ' ' + x.voucher_no + ' ' + x.truck_no),
      ...(k.chua_de_nghi || []).map(x => x.doc_no + ' ' + x.truck_no)));
  }
  function dsPt() { return (D ? D.phu_tung : []).filter(p => khop(p.name, ...(p.tren_phieu || []).map(x => x.doc_no + ' ' + x.truck_no))); }
  function dsHang() { return (D ? D.hang : []).filter(h => khop(h.name, ...(h.lo || []).map(x => x.doc_no + ' ' + x.customer_name + ' ' + x.truck_no))); }

  /* ---------------------------------------------------------------- dải số */
  function veKpi() {
    const k = q('#kx-kpis');
    if (!D) { k.innerHTML = ''; return; }
    const dau = D.nhien_lieu.filter(x => x.active !== false || x.ton_lit);
    const tong = dau.reduce((s, x) => s + (x.ton_lit || 0), 0);
    const nCho = D.nhien_lieu.reduce((s, x) => s + (x.de_nghi || []).length, 0);
    const lCho = D.nhien_lieu.reduce((s, x) => s + (x.cho_xuat || 0), 0);
    const lChua = D.nhien_lieu.reduce((s, x) => s + (x.chua_de_nghi_l || 0), 0);
    const duoi = D.phu_tung.filter(p => p.duoi_muc && p.active !== false);
    const tHang = D.hang.reduce((s, h) => s + (h.ton_t || 0), 0);
    const nLo = D.hang.reduce((s, h) => s + (h.lo || []).length, 0);
    const o = (cls, l, v, dv, s) => `<div class="kx-kpi ${cls}"><div class="l">${l}</div><div class="v">${v}<small>${dv}</small></div><div class="s">${s}</div></div>`;
    k.innerHTML = [
      o('', NN.h('kx_ton_dau'), lit(tong), NN.h('u_l'), NN.h('kx_so_kho', { n: dau.length })),
      o(nCho ? 'canh' : '', NN.h('td_await_iss'), lit(lCho), NN.h('u_l'),
        NN.h('kx_so_phieu', { n: nCho }) + (lChua ? ' · ' + NN.h('kx_c_chua') + ' ' + lit(lChua) + ' ' + NN.h('u_l') : '')),
      o(duoi.length ? 'do' : '', NN.h('kx_pt_duoi'), String(duoi.length), '', duoi.slice(0, 3).map(p => esc(p.name)).join(' · ') || '—'),
      o('', NN.h('kx_hang_bai'), tan(tHang), NN.h('ton'), NN.h('kx_so_lo', { n: nLo })),
    ].join('');
  }

  /* ---------------------------------------------------------------- bảng trái */
  function thanh(x) {
    const ton = Math.max(x.ton_lit || 0, 0), cho = x.cho_xuat || 0, chua = x.chua_de_nghi_l || 0;
    const tong = Math.max(ton, cho + chua, 1);
    const con = Math.max(ton - cho - chua, 0);
    const pc = (v) => (100 * v / tong).toFixed(1) + '%';
    return `<div class="kx-thanh" title="${esc(NN.t('kx_c_con'))} ${lit(con)} · ${esc(NN.t('kx_c_cho'))} ${lit(cho)} · ${esc(NN.t('kx_c_chua'))} ${lit(chua)}">
      <i class="con" style="width:${pc(con)}"></i><i class="cho" style="width:${pc(cho)}"></i><i class="chua" style="width:${pc(chua)}"></i></div>`;
  }
  const soCon = (v, dv) => v === null || v === undefined ? '<span class="nhat">—</span>'
    : `<span class="${v < 0 ? 'am' : ''}">${dv(v)}</span>`;

  function veBang() {
    const b = q('#kx-bang'), g = D && D.thay_gia;
    q('#kx-n-dau').textContent = D ? D.nhien_lieu.length : '·';
    q('#kx-n-pt').textContent = D ? D.phu_tung.length : '·';
    q('#kx-n-hang').textContent = D ? D.hang.length : '·';
    root.querySelectorAll('.kx-tab').forEach(t => { t.classList.toggle('on', t.dataset.tab === tab); t.setAttribute('aria-selected', t.dataset.tab === tab); });
    if (!D) { b.innerHTML = `<tbody><tr><td class="empty">${loi ? '' : NN.h('loading')}</td></tr></tbody>`; return; }
    let dau = '', than = '', ds = [];
    if (tab === 'dau') {
      ds = dsDau();
      dau = `<tr><th>${NN.h('fuel_kho')}</th><th class="num">${NN.h('stock')}</th><th class="num">${NN.h('kx_c_cho')}</th>
        <th class="num">${NN.h('kx_c_chua')}</th><th title="${esc(NN.t('kx_c_con_h'))}">${NN.h('kx_c_con')}</th>
        <th class="num">${NN.h('kx_in_month')}</th><th class="num">${NN.h('fuel_out_month')}</th>${g ? `<th class="num">${NN.h('fuel_avg')}</th>` : ''}</tr>`;
      than = ds.map(x => `<tr data-id="${esc(x.place_id)}" class="${chon.dau === x.place_id ? 'sel' : ''}">
        <td><span class="ten">${esc(x.name)}</span>${x.country ? `<span class="kx-nuoc">${esc(x.country)}</span>` : ''}
          <span class="phu">${esc(x.code || '')}${x.active === false ? ' · ' + NN.h('inactive') : ''}</span></td>
        <td class="num">${lit(x.ton_lit)}</td>
        <td class="num ${x.cho_xuat ? 'canh' : 'nhat'}">${x.cho_xuat ? lit(x.cho_xuat) : '—'}${(x.de_nghi || []).length ? `<span class="phu">${NN.h('kx_so_phieu', { n: x.de_nghi.length })}</span>` : ''}</td>
        <td class="num ${x.chua_de_nghi_l ? 'canh' : 'nhat'}">${x.chua_de_nghi_l ? lit(x.chua_de_nghi_l) : '—'}</td>
        <td><div class="num">${soCon(x.con_dung, lit)}</div>${x.ton_lit === null ? '' : thanh(x)}</td>
        <td class="num">${x.nhap_thang ? lit(x.nhap_thang) : '<span class="nhat">—</span>'}</td>
        <td class="num">${x.xuat_thang ? lit(x.xuat_thang) : '<span class="nhat">—</span>'}</td>
        ${g ? `<td class="num">${x.gia_bq ? so(x.gia_bq, 0) + ' LAK' : '—'}</td>` : ''}</tr>`).join('');
      than += `<tr class="kx-khong-chon"><td colspan="${g ? 8 : 7}"><div class="kx-chu-thich">
        <span><i class="con"></i>${NN.h('kx_c_con')}</span><span><i class="cho"></i>${NN.h('kx_c_cho')}</span><span><i class="chua"></i>${NN.h('kx_c_chua')}</span></div></td></tr>`;
    } else if (tab === 'pt') {
      ds = dsPt();
      dau = `<tr><th>${NN.h('part')}</th><th>${NN.h('unit')}</th><th class="num">${NN.h('stock')}</th><th class="num">${NN.h('min_stock')}</th>
        <th class="num">${NN.h('kx_c_tren_phieu')}</th><th class="num">${NN.h('kx_c_con')}</th>
        <th class="num">${NN.h('kx_in_month')}</th><th class="num">${NN.h('kx_out_month')}</th>${g ? `<th class="num">${NN.h('fuel_avg')}</th>` : ''}</tr>`;
      than = ds.map(x => `<tr data-id="${esc(x.id)}" class="${chon.pt === x.id ? 'sel' : ''}">
        <td><span class="ten">${esc(x.name)}</span>${x.active === false ? `<span class="phu">${NN.h('inactive')}</span>` : ''}</td>
        <td>${esc(donVi(x.unit))}</td>
        <td class="num ${x.duoi_muc ? 'am' : ''}">${L(x.ton, 2)}</td>
        <td class="num">${x.min_qty ? L(x.min_qty, 2) : '<span class="nhat">—</span>'}${x.duoi_muc ? `<span class="phu am">${NN.h('kx_duoi_muc')}</span>` : ''}</td>
        <td class="num ${x.cho_xuat ? 'canh' : 'nhat'}">${x.cho_xuat ? L(x.cho_xuat, 2) : '—'}</td>
        <td class="num">${soCon(x.con_dung, (v) => L(v, 2))}</td>
        <td class="num">${x.nhap_thang ? L(x.nhap_thang, 2) : '<span class="nhat">—</span>'}</td>
        <td class="num">${x.xuat_thang ? L(x.xuat_thang, 2) : '<span class="nhat">—</span>'}</td>
        ${g ? `<td class="num">${x.gia_bq ? so(x.gia_bq, 0) + ' LAK' : '—'}</td>` : ''}</tr>`).join('');
    } else {
      ds = dsHang();
      dau = `<tr><th>${NN.h('goods_type')}</th><th class="num">${NN.h('kx_ton_t')}</th><th class="num">${NN.h('kx_k_lo')}</th>
        <th class="num">${NN.h('kx_in_month')}</th><th class="num">${NN.h('kx_out_month')}</th></tr>`;
      than = ds.map(x => `<tr data-id="${esc(x.name)}" class="${chon.hang === x.name ? 'sel' : ''}">
        <td><span class="ten">${esc(x.name)}</span></td><td class="num">${tan(x.ton_t)}</td><td class="num">${(x.lo || []).length}</td>
        <td class="num">${x.nhap_thang ? tan(x.nhap_thang) : '<span class="nhat">—</span>'}</td>
        <td class="num">${x.xuat_thang ? tan(x.xuat_thang) : '<span class="nhat">—</span>'}</td></tr>`).join('');
    }
    if (!ds.length) than = `<tr><td class="empty" colspan="9">${NN.h('no_data')}</td></tr>`;
    b.innerHTML = `<thead>${dau}</thead><tbody>${than}</tbody>`;
    b.querySelectorAll('tbody tr[data-id]').forEach(tr => tr.addEventListener('click', () => { chon[tab] = tr.dataset.id; veBang(); veCt(); }));
  }

  /* ---------------------------------------------------------------- khung phải */
  const moPhieu = (id, chu) => `<a data-mo="${esc(id)}">${esc(chu)}</a>`;
  const loai = (k, tf) => tf ? `<span class="kx-k tf">${NN.h('fuel_transfer')}</span>`
    : `<span class="kx-k ${k === 'in' ? 'in' : k === 'out' ? 'out' : 'adj'}">${NN.h(k === 'in' ? 'kh_nhap' : k === 'out' ? 'kh_xuat' : 'kh_dc')}</span>`;
  const muc = (tieuDe, n, bang) => `<div class="kx-muc"><h4>${tieuDe}<span class="dem">${n}</span></h4>${n ? bang : `<div class="kx-trong">${NN.h('no_data')}</div>`}</div>`;
  const oSo = (l, v, cls = '') => `<div><div class="l">${l}</div><div class="v ${cls}">${v}</div></div>`;

  function ganDay(ds, dv, g) {
    return muc(NN.h('kx_gan_day'), ds.length, `<table><thead><tr><th>${NN.h('c_date')}</th><th></th><th class="num">${NN.h('kx_sl')}</th>
      <th>${NN.h('doc_no')}</th><th>${NN.h('c_truck')}</th>${g ? `<th class="num">${NN.h('kx_gia')}</th>` : ''}</tr></thead><tbody>${ds.map(m => `<tr>
      <td>${EPL.ngay(m.ngay)}</td><td>${loai(m.kind, m.chuyen_kho)}</td><td class="num">${dv(m.qty)}</td>
      <td class="mono">${esc(m.doc_no || '—')}</td><td>${esc(m.truck_no || m.customer_name || '—')}</td>
      ${g ? `<td class="num">${m.gia ? so(m.gia, 0) + ' LAK' : '—'}</td>` : ''}</tr>`).join('')}</tbody></table>`);
  }

  function veCt() {
    const ct = q('#kx-ct'), g = D && D.thay_gia;
    if (!D) { ct.innerHTML = loi ? `<div class="kx-chon">${NN.h('kx_loi', { loi: esc(loi) })}</div>` : ''; return; }
    let x = null;
    if (tab === 'dau') x = D.nhien_lieu.find(k => k.place_id === chon.dau);
    else if (tab === 'pt') x = D.phu_tung.find(p => p.id === chon.pt);
    else x = D.hang.find(h => h.name === chon.hang);
    if (!x) { ct.innerHTML = `<div class="kx-chon">${NN.h('kx_chon')}</div>`; return; }
    let dau = '', than = '';
    if (tab === 'dau') {
      dau = `<h3>${esc(x.name)} ${x.country ? `<span class="kx-nuoc">${esc(x.country)}</span>` : ''}</h3>
        <div class="phu">${esc(x.code || '')}${g && x.gia_bq ? ' · ' + NN.h('fuel_avg') + ' ' + so(x.gia_bq, 0) + ' LAK/' + NN.h('u_l') : ''}</div>
        <div class="kx-ct-so">${oSo(NN.h('stock') + ' (L)', lit(x.ton_lit))}${oSo(NN.h('kx_c_cho') + ' (L)', lit(x.cho_xuat), x.cho_xuat ? 'canh' : '')}
          ${oSo(NN.h('kx_c_con') + ' (L)', lit(x.con_dung), x.con_dung < 0 ? 'am' : '')}</div>`;
      than = muc(NN.h('td_await_iss'), x.de_nghi.length, `<table><thead><tr><th>${NN.h('kx_v_no')}</th><th>${NN.h('doc_no')}</th>
          <th>${NN.h('c_truck')}</th><th>${NN.h('c_driver')}</th><th class="num">${NN.h('qty_l')}</th><th>${NN.h('c_date')}</th></tr></thead>
          <tbody>${x.de_nghi.map(v => `<tr><td class="mono">${esc(v.voucher_no)}</td><td>${moPhieu(v.trip_id, v.doc_no)}${v.company === 'joint' ? `<span class="phu">${NN.h('ht_xuat_xuat_ban')}</span>` : ''}</td>
            <td>${esc(v.truck_no || '—')}</td><td>${esc(v.driver_name || '—')}</td><td class="num">${lit(v.qty_l)}</td><td>${EPL.ngay(v.ngay)}</td></tr>`).join('')}</tbody></table>`)
        + muc(NN.h('kx_chua_de_nghi_h'), x.chua_de_nghi.length, `<table><thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('c_truck')}</th>
          <th>${NN.h('c_driver')}</th><th class="num">${NN.h('qty_l')}</th><th>${NN.h('c_date')}</th></tr></thead>
          <tbody>${x.chua_de_nghi.map(v => `<tr><td>${moPhieu(v.trip_id, v.doc_no)}</td><td>${esc(v.truck_no || '—')}</td>
            <td>${esc(v.driver_name || '—')}</td><td class="num">${lit(v.qty_l)}</td><td>${EPL.ngay(v.ngay)}</td></tr>`).join('')}</tbody></table>`)
        + ganDay(x.gan_day || [], lit, g);
    } else if (tab === 'pt') {
      const dv = (v) => L(v, 2) + ' ' + esc(donVi(x.unit));
      dau = `<h3>${esc(x.name)}</h3><div class="phu">${NN.h('min_stock')} ${x.min_qty ? dv(x.min_qty) : '—'}${g && x.gia_bq ? ' · ' + NN.h('fuel_avg') + ' ' + so(x.gia_bq, 0) + ' LAK' : ''}</div>
        <div class="kx-ct-so">${oSo(NN.h('stock'), L(x.ton, 2), x.duoi_muc ? 'am' : '')}${oSo(NN.h('kx_c_tren_phieu'), L(x.cho_xuat, 2), x.cho_xuat ? 'canh' : '')}
          ${oSo(NN.h('kx_c_con'), L(x.con_dung, 2), x.con_dung < 0 ? 'am' : '')}</div>`;
      than = muc(NN.h('kx_tren_phieu_h'), x.tren_phieu.length, `<table><thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('c_truck')}</th>
          <th class="num">${NN.h('kx_sl')}</th><th>${NN.h('c_date')}</th></tr></thead>
          <tbody>${x.tren_phieu.map(v => `<tr><td>${moPhieu(v.trip_id, v.doc_no)}</td><td>${esc(v.truck_no || '—')}</td>
            <td class="num">${L(v.qty, 2)}</td><td>${EPL.ngay(v.ngay)}</td></tr>`).join('')}</tbody></table>`)
        + ganDay(x.gan_day || [], (v) => L(v, 2), g);
    } else {
      dau = `<h3>${esc(x.name)}</h3>
        <div class="kx-ct-so">${oSo(NN.h('kx_ton_t'), tan(x.ton_t))}${oSo(NN.h('kx_k_lo'), String((x.lo || []).length))}
          ${oSo(NN.h('kx_out_month') + ' (' + NN.h('ton') + ')', tan(x.xuat_thang))}</div>`;
      than = muc(NN.h('kx_lo_con'), x.lo.length, `<table><thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('c_customer')}</th>
          <th>${NN.h('kx_origin')}</th><th class="num">${NN.h('kx_nhap_t')}</th><th class="num">${NN.h('kx_con_t')}</th><th>${NN.h('c_date')}</th></tr></thead>
          <tbody>${x.lo.map(o => `<tr><td class="mono">${esc(o.doc_no || '—')}<span class="phu">${esc(o.truck_no || '')}</span></td><td>${esc(o.customer_name || '—')}</td>
            <td>${esc(o.origin || '—')}</td><td class="num">${tan(o.nhap_t)}</td><td class="num"><b>${tan(o.con_t)}</b></td><td>${EPL.ngay(o.ngay)}</td></tr>`).join('')}</tbody></table>`)
        + ganDay(x.gan_day || [], tan, false);
    }
    ct.innerHTML = `<div class="kx-ct-dau">${dau}</div><div class="kx-ct-cuon">${than}</div>`;
    ct.querySelectorAll('a[data-mo]').forEach(a => a.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: a.dataset.mo })));
  }

  function veLoi() {
    const k = q('#kx-kpis');
    if (loi) k.innerHTML = `<div class="kx-loi" style="grid-column:1/-1">${NN.h('kx_loi', { loi: esc(loi) })}</div>`;
  }

  function veHet() {
    if (!root) return;
    // chưa chọn gì thì chọn sẵn dòng đầu (dòng có phiếu chờ trước) — khung phải không trống lúc mở màn
    if (D) {
      const dau = dsDau(), pt = dsPt(), hang = dsHang();
      if (!dau.some(x => x.place_id === chon.dau)) chon.dau = ((dau.find(x => (x.de_nghi || []).length) || dau[0]) || {}).place_id || null;
      if (!pt.some(x => x.id === chon.pt)) chon.pt = ((pt.find(x => x.duoi_muc) || pt[0]) || {}).id || null;
      if (!hang.some(x => x.name === chon.hang)) chon.hang = (hang[0] || {}).name || null;
    }
    veKpi(); veLoi(); veBang(); veCt();
  }

  EPL.modules['kho-xem'] = {
    async init(r, { tham }) {
      root = r; D = null; tim = '';
      if (tham && ['dau', 'pt', 'hang'].includes(tham.tab)) tab = tham.tab;
      q('#kx-thang').value = thangNay();
      q('#kx-thang').addEventListener('change', tai);
      q('#kx-tim').addEventListener('input', (e) => { tim = e.target.value.trim().toLowerCase(); veHet(); });
      root.querySelectorAll('.kx-tab').forEach(t => t.addEventListener('click', () => { tab = t.dataset.tab; veBang(); veCt(); }));
      await tai();
    },
    onLang() { if (root) veHet(); },
    xuatExcel() {
      const T = NN.t, S = [];
      if (!D) return [];
      S.push(EPL.xuatSheet(T('e_fuel'), [T('fuel_kho'), 'Mã', T('stock'), T('kx_c_cho'), T('kx_c_chua'), T('kx_c_con'), T('kx_in_month'), T('fuel_out_month')]
        .concat(D.thay_gia ? [T('fuel_avg')] : []),
        D.nhien_lieu.map(x => [x.name, x.code || '', EPL.oSo(x.ton_lit, 0, 'L'), EPL.oSo(x.cho_xuat, 0, 'L'), EPL.oSo(x.chua_de_nghi_l, 0, 'L'),
          EPL.oSo(x.con_dung, 0, 'L'), EPL.oSo(x.nhap_thang, 0, 'L'), EPL.oSo(x.xuat_thang, 0, 'L')].concat(D.thay_gia ? [EPL.oSo(x.gia_bq, 0, 'LAK')] : []))));
      S.push(EPL.xuatSheet(T('part'), [T('part'), T('unit'), T('stock'), T('min_stock'), T('kx_c_tren_phieu'), T('kx_c_con'), T('kx_in_month'), T('kx_out_month')]
        .concat(D.thay_gia ? [T('fuel_avg')] : []),
        D.phu_tung.map(x => [x.name, donVi(x.unit), EPL.oSo(x.ton, 2), EPL.oSo(x.min_qty, 2), EPL.oSo(x.cho_xuat, 2), EPL.oSo(x.con_dung, 2),
          EPL.oSo(x.nhap_thang, 2), EPL.oSo(x.xuat_thang, 2)].concat(D.thay_gia ? [EPL.oSo(x.gia_bq, 0, 'LAK')] : []))));
      S.push(EPL.xuatSheet(T('nav_goods'), [T('goods_type'), T('doc_no'), T('c_customer'), T('kx_origin'), T('kx_nhap_t'), T('kx_con_t'), T('c_date')],
        D.hang.flatMap(h => h.lo.map(o => [h.name, o.doc_no || '', o.customer_name || '', o.origin || '', EPL.oSo(o.nhap_t, 3), EPL.oSo(o.con_t, 3), EPL.oNgay(o.ngay)]))));
      return S;
    },
  };
})();
