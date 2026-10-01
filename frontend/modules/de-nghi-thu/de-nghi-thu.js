/* Phiếu đề nghị thu — ໃບສະເໜີຮັບເງິນ (sếp 30/09).
 *
 * DO xong (xe về, có biên bản giao nhận, kế toán Viêng Chăn KHOÁ phiếu) → máy lập tờ đề nghị thu cước (loại PDT) — gửi bên
 * công nợ (anh Tune) lập SO, xuất hoá đơn, thu tiền khách. Bên mình không thu tiền: màn này xem trạng thái bên đó chép sang
 * (chờ khoá · chưa lập · chờ gửi · đã tạo SO · thu một phần · đã thu đủ), in tờ. Số tiền theo ĐÚNG tiền tệ cước của phiếu.
 * 01/10 (bỏ trang kế toán tạm): "đã tạo SO" theo lần gửi SO, thu tiền là bản ĐỌC LẠI công nợ khách bên hệ anh Tune (chỉ xem) —
 * nút Cập nhật đọc lại cả tháng (POST /api/de-nghi-thu/cap-nhat). Không còn cờ hoá đơn trang tạm (invoiced · inv_no).
 * 01/10 (bỏ trang kế toán tạm phần tiền): tờ không còn đẩy sang trang tạm — bỏ nút "Gửi bên công nợ" (dt_gui), lời gọi
 * /api/ke-toan/trang-thai, mã phiếu và lỗi đẩy bên trang tạm. Đường sang hệ kế toán (anh Tune) là nút Tạo SO bên dưới.
 *
 * API: GET /api/de-nghi-thu?thang=&q= · GET/POST /api/trips/{id}/de-nghi-thu.
 * Tạo SO ở hệ kế toán (anh Tune, hợp đồng mục 3.2): GET /api/trips/{id}/tao-so (xem trước, không gọi mạng) → hỏi xác nhận →
 * POST /api/trips/{id}/tao-so. Chỉ KT Thu/Chi Viêng Chăn và Sếp; máy chủ cũng chặn vai khác.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  const TT = ['chua_lap', 'cho_gui', 'da_tao_so', 'thu_mot_phan', 'da_thu', 'cho_khoa', ''];
  let root, D = { ds: [] }, tt = '', tim = '', chonId = null, hen = null;
  const q = (s) => root.querySelector(s);
  const tagTT = (s) => `<span class="tag dt_${esc(s)}">${NN.h('dt_st_' + s)}</span>`;
  const tien = (n, ma) => EPL.tien(n, ma);
  const thangNay = () => EPL.thangNay();    // giờ máy — toISOString là giờ UTC, 0–7 giờ sáng ngày 1 ra tháng trước
  /* Tháng trống (01/10): đầu tháng chưa DO nào về nên màn mở ra trống, trông như hỏng. TU_DONG = lượt tải đầu khi vào màn
   * không kèm tháng → tháng trống thì sang tháng gần nhất có DO đã về, BAO giữ dòng báo; GAN = tháng cho nút ở khung trống. */
  let TU_DONG = false, BAO = null, GAN = null;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');

  /** Tháng `th` có phiếu không; không có thì tháng nào GẦN NHẤT có (cùng bộ lọc `loc` của /api/trips). Hỏi hai lần, mỗi lần
   *  một dòng: phiếu mới nhất tới cuối tháng `th`, phiếu cũ nhất từ đầu tháng `th` — không tải cả năm. Cách đều: tháng trước. */
  async function thangGan(th, loc) {
    const [y, m] = th.split('-').map(Number);
    const hoi = (them) => { const p = new URLSearchParams(loc); p.set('co', '1'); Object.entries(them).forEach(([k, v]) => p.set(k, v));
      return API.get('/api/trips?' + p).then(d => (d && d[0] && d[0].doc_date ? d[0].doc_date.slice(0, 7) : null), () => null); };
    const [truoc, sau] = await Promise.all([hoi({ den: th + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }), hoi({ tu: th + '-01', sap: 'cu' })]);
    if (truoc === th || sau === th) return { co: true, gan: th };
    const n = (v) => v.slice(0, 4) * 12 + +v.slice(5, 7);
    return { co: false, gan: !truoc || !sau ? truoc || sau : (n(sau) - n(th) < n(th) - n(truoc) ? sau : truoc) };
  }
  /** Người dùng TỰ chọn tháng (ô tháng, nút ở khung trống): giữ đúng tháng đó, bỏ dòng báo, thôi tự sang tháng khác. */
  function chonThang(v) { TU_DONG = false; BAO = null; q('#dnt-thang').value = v; tai(); }

  function loc() {
    return D.ds.filter(x => !tt || x.trang_thai === tt);
  }

  /* ---------------------------------------------------------------- thanh trạng thái + dải tổng */
  function veSeg() {
    const dem = {};
    D.ds.forEach(x => { dem[x.trang_thai] = (dem[x.trang_thai] || 0) + 1; });
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
      <div class="o"><span class="l">${NN.h('ncc_con_thu')}</span><span class="v">${so(conLak)}<small>LAK</small></span><span class="s">${NN.h('dt_con_lai_s')}</span></div>
      ${BAO ? `<div class="dnt-bao" id="dnt-bao" role="status"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>
        <span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span></div>` : ''}`;
  }

  /* ---------------------------------------------------------------- danh sách DO */
  function veDs() {
    const ds = loc(), o = q('#dnt-ds');
    if (!ds.length) {
      // tháng có DO mà thẻ trạng thái / chữ tìm lọc hết → nói "không khớp bộ lọc", đừng nói tháng này chưa có DO nào về
      const boLoc = D.ds.length || tim;
      o.innerHTML = `<div class="dnt-trong"><div>${NN.h(boLoc ? 'loc_trong' : 'dt_trong')}</div>
        ${D.ds.length && tt ? `<button type="button" class="btn sm" data-tat-ca="1">${NN.h('tq_view_all')}</button>` : ''}
        ${!D.ds.length && GAN ? `<button type="button" class="btn sm primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}</div>`;
      const b = o.querySelector('[data-thang]'); if (b) b.addEventListener('click', () => chonThang(b.dataset.thang));
      const h = o.querySelector('[data-tat-ca]'); if (h) h.addEventListener('click', () => { tt = ''; veHet(); });
      return;
    }
    o.innerHTML = ds.map(x => `<button type="button" class="dnt-o st-${esc(x.trang_thai)} ${x.trip_id === chonId ? 'chon' : ''}" data-id="${esc(x.trip_id)}">
      <div class="so">${esc(x.doc_no)}<span class="dnt-kind ${esc(x.kind)}">${NN.h(x.kind === 'gom' ? 'dn_gom' : 'dn_giao')}</span></div>
      <div class="tien">${tien(x.doanh_thu, x.ccy)}</div>
      <div class="kh" lang="lo">${esc(x.customer_name || '—')}</div>
      <div class="tt">${tagTT(x.trang_thai)}${x.so_ke_toan && !x.so_ke_toan.da_tao_so && x.so_ke_toan.error_message
        ? ` <span class="tag dt_so_loi" title="${esc(x.so_ke_toan.error_message)}">SO ⚠</span>` : ''}</div>
      <div class="phu"><span lang="lo">${esc(x.origin || '')} → ${esc(x.destination || '')}</span> · ${esc(x.truck_no || '')} · ${so(x.tan_tinh, 2)} ${NN.h('ton')}</div>
      <div class="phu" style="text-align:right">${x.pdt ? esc(x.pdt.so) : EPL.ngay(x.doc_date)}</div>
    </button>`).join('');
    o.querySelectorAll('.dnt-o').forEach(b => b.addEventListener('click', () => { chonId = b.dataset.id; veDs(); veTo(); }));
  }

  /* ---------------------------------------------------------------- tờ đề nghị thu */
  async function veTo() {
    const x = D.ds.find(y => y.trip_id === chonId), nut = q('#dnt-nut');
    q('#dnt-giay').scrollTop = 0;            // tờ cuộn trong khung riêng (01/10): chọn DO khác thì về đầu tờ
    // danh sách trống: khung trống bên trái đã nói lý do + nút; tờ giấy "Chọn một tờ bên trái" lúc đó chỉ gây rối
    q('#dnt-giay').hidden = !loc().length;
    if (!x) { nut.innerHTML = ''; q('#dnt-so').innerHTML = ''; q('#dnt-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    let d;
    try { d = await API.get(`/api/trips/${x.trip_id}/de-nghi-thu`); } catch (e) { q('#dnt-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; return; }
    if (chonId !== x.trip_id) return;
    const laKt = AUTH.la('acct');
    const sk = x.so_ke_toan;
    nut.innerHTML = `${tagTT(d.trang_thai)}
      ${sk && sk.da_tao_so ? `<span class="tag dt_so" title="${esc(sk.thu && sk.thu.doc_luc ? EPL.ngayGio(sk.thu.doc_luc) : '')}">${NN.h('dt_so_da', { so: sk.order_code || '' })}</span>` : ''}
      ${sk && !sk.da_tao_so && sk.error_message ? `<span class="small neg" title="${esc(sk.error_message)}">⚠ ${NN.h('dt_so_loi', { loi: sk.error_message.slice(0, 90) })}</span>` : ''}
      <span class="grow"></span>
      ${laKt && d.trang_thai === 'chua_lap' ? `<button class="btn primary" id="dnt-lap">${NN.h('dt_lap')}</button>` : ''}
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
    const soGui = q('#dnt-so-gui'); if (soGui) soGui.addEventListener('click', async () => {
      // xem trước ở máy chủ (không gọi mạng): thiếu mã khách, thiếu tuyến, cước THB… thì nói rõ, không gửi
      let v;
      try { v = await API.get(`/api/trips/${x.trip_id}/tao-so`); } catch (e) { return EPL.baoLoi(e); }
      if (v.loi) return EPL.toast(v.loi.loi || v.loi.ma, 'loi');
      const tt = v.tom_tat || {};
      const tienSo = so(tt.final_selling_price, EPL.leTien(tt.currency)) + ' ' + (tt.currency || '');
      if (!await EPL.hoi(NN.t('dt_so_hoi'), NN.h('dt_so_hoi_nd', { kh: d.customer_name || '', ma: tt.customer_code || '', tien: tienSo }) + (tt.tao_khach ? '<p class="small">' + NN.h('dt_so_tao_khach', { ma: tt.tao_khach }) + '</p>' : ''), NN.t('dt_so_nut'))) return;
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
        ${d.da_tao_so ? `<span>${NN.h('dt_so_da', { so: (d.so_ke_toan || {}).order_code || '' })}</span>` : ''}
        <span>${NN.h('collected')}: <b>${so(d.da_thu_lak)} LAK</b></span>
        <span>${NN.h('ncc_con_thu')}: <b>${so(d.con_lai_lak)} LAK</b></span>
        ${d.locked_by ? `<span>${NN.h('s_locked')}: <span lang="lo">${esc(d.locked_by)}</span> · ${esc((d.locked_at || '').replace('T', ' '))}</span>` : ''}
      </div>
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_issuer')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div>
        <div><div class="line"></div>${NN.h('dt_ben_cong_no')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }


  /* Danh sách + tờ in cao VỪA cửa sổ (01/10): đo từ đầu danh sách tới đáy cửa sổ, trừ lề đáy trang, đặt vào --dn-cao (biến
   * CSS chứ không style trực tiếp: quy tắc in vẫn thắng). Số cố định trong CSS chỉ đúng tiếng Việt — chế độ VI + ລາວ (nhãn
   * hai dòng) trang còn cuộn dọc 40–100px. Toạ độ là điểm ảnh màn hình, px CSS bên trong .app (zoom --ty-le) nên chia. */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.dnt-ds');
    if (!ds || !ds.isConnected) return;
    // lúc mở màn còn dải "Đang tải…" (chung.js: .mod-dang-tai::before) đẩy danh sách xuống — đo sau khi dải đó tắt
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--dn-cao', Math.max(300, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };   // sau khi chung.js đặt lại --ty-le

  function veHet() {
    const ds = loc();
    if (!ds.some(x => x.trip_id === chonId)) chonId = ds[0] ? ds[0].trip_id : null;
    veSeg(); veTong(); veDs(); veTo();
    datCao();                 // dải tổng / dòng báo vừa vẽ lại — đầu danh sách có thể đổi chỗ
  }

  let LUOT = 0;                // lượt tải mới nhất — lượt cũ (đang tự sang tháng) về sau thì không vẽ đè
  async function tai() {
    const luot = ++LUOT;
    const thang = q('#dnt-thang').value || thangNay();
    const th = new URLSearchParams({ thang });
    if (tim) th.set('q', tim);
    let duoc = true, ve;
    // Hỏi "tháng gần nhất" SAU khi danh sách về trống, không hỏi song song: đo 01/10, /api/trips chạy cùng lúc với
    // /api/de-nghi-thu thì máy chủ chậm hẳn (105 ms → 1 s) — nối tiếp nhanh hơn.
    try { ve = await API.get('/api/de-nghi-thu?' + th.toString()); } catch (e) { ve = { ds: [] }; duoc = false; if (luot === LUOT) EPL.baoLoi(e); }
    if (luot !== LUOT) return;
    D = ve; GAN = null;
    if (duoc && !D.ds.length) {
      // tờ đề nghị thu chỉ có ở DO đã về (khoá phiếu đòi xe về): tháng gần nhất có DO đã về, cùng chữ tìm
      const r = await thangGan(thang, tim ? { transport_status: 'arrived', q: tim } : { transport_status: 'arrived' });
      if (luot !== LUOT) return;
      GAN = r.co ? null : r.gan;
      if (TU_DONG && GAN) { TU_DONG = false; BAO = { trong: thang, xem: GAN }; q('#dnt-thang').value = GAN; return tai(); }
    }
    TU_DONG = false;
    veHet();
  }

  EPL.modules['de-nghi-thu'] = {
    async init(r, ctx) {
      root = r; D = { ds: [] }; tim = ''; tt = ''; chonId = null; BAO = null; GAN = null;
      const t = (ctx && ctx.tham) || {};
      // ô tháng mặc định là tháng này THEO GIỜ MÁY (EPL.doiOThang) — toISOString là giờ UTC, 0–7 giờ sáng ngày 1 ra tháng trước
      if (t.thang) q('#dnt-thang').value = t.thang;
      TU_DONG = !t.thang;                     // mở từ Đề nghị theo DO thì đã kèm tháng của DO — giữ nguyên
      if (t.id) chonId = t.id;
      if (TT.includes(t.tt)) tt = t.tt;
      q('#dnt-thang').addEventListener('change', (e) => chonThang(e.target.value));
      // đọc lại thu tiền mọi SO của tháng từ công nợ khách bên hệ kế toán (chỉ xem) rồi tải lại danh sách
      q('#dnt-cap-nhat').addEventListener('click', async (e) => {
        const b = e.currentTarget; b.disabled = true;
        try {
          const r = await API.post('/api/de-nghi-thu/cap-nhat', { thang: q('#dnt-thang').value || thangNay() });
          EPL.toast(`${NN.t('ck_cap_nhat')} · ${r.da_doc} SO` + (r.loi ? ' — ' + r.loi : ''), r.loi ? 'loi' : 'ok');
        } catch (er) { EPL.baoLoi(er); }
        b.disabled = false;
        await tai();
      });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      q('#dnt-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      await tai();
    },
    onLang() { if (root) veHet(); },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); },
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
