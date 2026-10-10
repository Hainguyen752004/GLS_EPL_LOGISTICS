/* Theo dõi phiếu vận chuyển — một dòng một phiếu, đủ cột như sheet ໜ້າລາຍງານຂົນສົ່ງ.
 *
 * TIỀN TỆ. Mỗi phiếu tính theo tiền của hợp đồng phiếu đó (USD · LAK · CNY · THB), nên bảng này có
 * cột **Tiền** nói rõ từng dòng là tiền gì, và dòng tổng cộng RIÊNG TỪNG LOẠI TIỀN thay vì cộng
 * táo với cam. Ai muốn một con số duy nhất thì đổi ô "Quy đổi" sang Kíp hoặc USD — lúc đó mọi dòng
 * quy theo tỷ giá đã khoá trên chính phiếu đó, và dòng tổng còn một con số.
 * Riêng khối chi phí luôn là Kíp: dòng chi vốn đã trộn LAK · VND · THB nên quy về Kíp ngay từ máy chủ.
 */
(function () {
  const { API, NN, esc, so, tien, tag } = EPL;
  const KTG = EPL.khoangThoiGian;
  // 09/10 (anh Khampla): kỳ xem chọn ở bộ lọc thời gian dùng chung (KY: Năm · Tháng · Khoảng thời gian · nút nhanh) thay ô tháng
  let root, ds = [], tyGia = {}, TRANG = 1, TONG = {}, KY = null;
  const CO = 100;              // một trang 100 phiếu — một tháng có thể ~30.000 phiếu (nghìn chuyến / ngày)
  /* Tháng trống (chủ dự án 01/10: mở màn đầu tháng thấy "Chưa có dữ liệu", tưởng màn không tải được).
   * TU_DONG: lượt tải đầu khi vào màn KHÔNG kèm tháng — tháng này trống thì tự sang tháng gần nhất có phiếu, BAO giữ dòng báo.
   * Người dùng tự chọn tháng trống thì giữ tháng đó; GAN là tháng gần nhất có phiếu cho nút trong khung trống. */
  let TU_DONG = false, BAO = null, GAN = null;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');

  /* «Tháng gần nhất có phiếu» dùng chung: EPL.khoangThoiGian.gan (09/10 — trước đây hàm thangGan riêng ở đây, cùng cách). */

  /** Tỷ giá quy đổi của MỘT phiếu — lấy ngay trên phiếu, không lấy tỷ giá hôm nay. */
  function rate(p, ma) {
    return { USD: p.rate_usd || 22000, THB: p.rate_thb || 700, VND: p.rate_vnd || 1.2,
      CNY: p.rate_cny || 3000, LAK: 1 }[String(ma || 'LAK').toUpperCase()] || 1;
  }
  const quy = () => root.querySelector('#td-quy').value;       // '' = giữ tiền của phiếu
  /** Đổi một số tiền của phiếu p từ `tu` sang tiền đang hiển thị. */
  function ve_tien(p, v, tu) {
    const dich = quy();
    if (v == null) return { v: null, ma: tu };
    if (!dich || dich === tu) return { v, ma: tu };
    return { v: v * rate(p, tu) / rate(p, dich), ma: dich };
  }
  const oTien = (p, v, tu, dam) => {
    const t = ve_tien(p, v, tu);
    if (t.v == null) return '<span class="muted">—</span>';
    const chu = so(t.v, EPL.leTien(t.ma));
    return dam ? `<b>${chu}</b>` : chu;
  };
  /* Dữ liệu cả năm (24/09): lọc · tìm · chia trang ở MÁY CHỦ; dòng tổng lấy từ /api/bao-cao/theo-doi/tong — cộng trên
   * TOÀN BỘ phiếu khớp bộ lọc, riêng từng loại tiền (hoặc quy về một tiền theo tỷ giá khoá trên từng phiếu). */
  function thamLoc() {
    const p = KTG.thamSo(KY.giaTri);          // trọn một tháng → thang (như cũ), khoảng khác → tu + den
    const tim = root.querySelector('#td-q').value.trim(); if (tim) p.set('q', tim);
    [['td-vc', 'transport_status'], ['td-tc', 'finance_status'], ['td-cty', 'company']].forEach(([id, k]) => {
      const v = root.querySelector('#' + id).value; if (v) p.set(k, v); });
    return p;
  }
  let LUOT = 0;                // lượt tải mới nhất — gõ tìm trong lúc lượt trước (tự sang tháng) còn chờ thì lượt cũ không vẽ đè
  async function tai(trang = 1) {
    const luot = ++LUOT;
    TRANG = trang;
    const pt = thamLoc(); pt.set('trang', TRANG); pt.set('co', CO);
    const pq = thamLoc(); if (quy()) pq.set('quy', quy());
    const [a, b] = await Promise.all([API.get('/api/bao-cao/theo-doi?' + pt), API.get('/api/bao-cao/theo-doi/tong?' + pq)]);
    if (luot !== LUOT) return;
    ds = a; TONG = b; GAN = null;
    const gt = KY.giaTri;
    if (!ds.length && gt.tu) {
      // /api/trips lọc bằng cùng loc_phieu với bảng này: tìm · trạng thái · loại xe giữ nguyên, chỉ bỏ kỳ (KTG.gan thay bằng hai mép)
      const r = await KTG.gan(gt, thamLoc());
      if (luot !== LUOT) return;
      GAN = r.co ? null : r.gan;
      if (TU_DONG && GAN) { TU_DONG = false; BAO = { trong: KTG.laThang(gt) || gt.tu.slice(0, 7), xem: GAN }; KY.dat(KTG.cuaThang(GAN)); return tai(1); }
    }
    TU_DONG = false;
    locVaVe();
  }
  /** Bộ lọc ngoài tháng đang bật — khung trống nói "không khớp bộ lọc" thay vì "tháng chưa có phiếu". */
  const coLoc = () => !!root.querySelector('#td-q').value.trim() || ['td-vc', 'td-tc', 'td-cty'].some(id => root.querySelector('#' + id).value);
  /** Người dùng TỰ chọn kỳ (bộ lọc thời gian, nút tháng gần nhất ở khung trống): giữ đúng kỳ đó, bỏ dòng báo, thôi tự sang tháng khác.
   *  `v` = 'YYYY-MM' (nút ở khung trống) — không có thì kỳ đang chọn trên bộ lọc. */
  function chonThang(v) { TU_DONG = false; BAO = null; if (v) KY.dat(KTG.cuaThang(v)); return tai(1); }

  /** Dòng báo cạnh ô tháng (tự sang tháng khác) và khung trống giữa vùng đang nhìn, có nút về tháng gần nhất có phiếu. */
  function veTrong(trong) {
    const bao = root.querySelector('#td-bao');
    bao.hidden = !BAO;
    bao.innerHTML = BAO ? `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg><span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span>` : '';
    root.querySelector('.td-cuon').hidden = trong;
    const o = root.querySelector('#td-trong');
    o.hidden = !trong;
    if (!trong) { o.innerHTML = ''; return; }
    const th = KY.laThang();                  // kỳ trọn một tháng: câu cũ «Tháng 09/2026 chưa có phiếu»; khoảng khác: kèm hai ngày
    o.innerHTML = `<b>${coLoc() ? NN.h('loc_trong') : th ? NN.h('thang_trong_n', { thang: nhanThang(th) }) : NN.h('ktg_trong_n', { khoang: KY.nhan() })}</b>
      ${GAN ? `<button type="button" class="btn primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}`;
    const b = o.querySelector('[data-thang]');
    if (b) b.addEventListener('click', () => chonThang(b.dataset.thang).catch(EPL.baoLoi));
  }

  function locVaVe() {
    const rows = ds, dau = (TRANG - 1) * CO;
    const sVal = TONG.doanh_thu || {}, sThu = TONG.da_thu || {}, sCon = TONG.con_lai || {}, sNet = TONG.lai || {};
    const sExp = TONG.tong_chi_lak || 0, soPhieu = TONG.so_phieu ?? rows.length; const d = '<span class="muted">—</span>';
    root.querySelector('#td-than').innerHTML = rows.length ? rows.map((p, i) => {
      const c = p.tinh, ma = c.ccy, mh = c.hire_ccy || ma;
      const chi = c.chi || {};                 // Bãi không nhận tiền chi (anh Khampla A2) — cột đó ẩn với Bãi
      const hao = c.hao_hut_pct !== null && c.hao_hut_pct > 1.5 ? `<span class="td-hao" title="${esc(NN.t('w_loss'))}">${so(c.hao_hut_pct, 1)}%</span>` : '';
      return `<tr data-id="${p.id}">
        <td>${dau + i + 1}</td><td class="nowrap">${EPL.ngay(p.doc_date)}</td><td class="nowrap mono"><b>${esc(p.doc_no)}</b></td>
        <td class="mono">${esc(p.ore_bill_no) || d}</td><td class="nowrap" lang="lo">${p.origin || p.destination ? `${esc(p.origin) || d} → ${esc(p.destination) || d}` : d}</td>
        <td>${p.company === 'joint' ? tag('plain', 'co_joint') : 'EPL'}</td><td lang="lo" class="nowrap">${esc(p.driver_name) || d}</td>
        <td lang="lo" class="nowrap">${esc(p.plate_head) || d}</td><td lang="lo" class="nowrap">${esc(p.plate_trailer) || d}</td><td>${esc(p.truck_no) || d}</td>
        <td lang="lo">${esc(p.customer_name) || d}</td><td>${tag('ore', p.goods_type || 'iron_ore')}</td>
        <td class="num">${so(p.weight_origin, 2)}</td><td class="num">${p.weight_dest != null ? so(p.weight_dest, 2) : d}${hao}</td>
        <td class="mono tien td-ccy">${esc(quy() || ma)}</td>
        <td class="num tien">${oTien(p, p.price, ma)}${c.cach_tinh === 'chuyen' ? `<span class="td-hao" style="color:var(--muted)" title="${esc(NN.t('pm_chuyen'))}">${NN.h('pm_chuyen_s')}</span>` : ''}</td><td class="num tien">${oTien(p, c.doanh_thu, ma, true)}</td>
        <td class="num tien">${c.da_thu ? oTien(p, c.da_thu, ma) : d}</td><td class="num tien ${c.con_lai ? 'neg' : ''}">${c.con_lai ? oTien(p, c.con_lai, ma) : d}</td>
        <td class="num tien">${c.lien_ket ? oTien(p, c.tien_thue, mh) : d}</td><td class="num tien">${c.lien_ket ? oTien(p, c.phi, mh) : d}</td><td class="num tien">${c.lien_ket ? oTien(p, c.tru_vuot, mh) : d}</td>
        <td class="num tien-chi">${so(chi.fuel)}</td><td class="num tien-chi">${so(chi.travel)}</td><td class="num tien-chi">${chi.repair ? so(chi.repair) : d}</td><td class="num tien-chi">${chi.other ? so(chi.other) : d}</td><td class="num tien-chi"><b>${so(c.tong_chi_lak)}</b></td>
        <td class="num tien ${c.lai < 0 ? 'neg' : 'pos'}"><b>${oTien(p, c.lai, ma)}</b></td>
        <td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td></tr>`;
    }).join('') : `<tr><td colspan="31" class="empty">${NN.h('no_data')}</td></tr>`;
    const gop = (t) => `<span class="td-gop">${EPL.tienGop(t, '<br>')}</span>`;
    // nhãn "Tổng · n chuyến" chiếm đúng ba cột đứng yên (#, Ngày, Số phiếu) và đứng yên theo — trước đây một ô 15 cột
    // trôi theo khi cuộn ngang: nhãn mất, các ô tổng tiền lộ ra ngay dưới cột Ngày / Số phiếu (01/10)
    root.querySelector('#td-chan').innerHTML = `<tr><td colspan="3" class="td-chan-nhan">${NN.ghep([{ k: 'total' }, ' · ' + so(soPhieu) + ' ', { k: 'trips' }])}</td><td colspan="12"></td>
      <td class="tien"></td><td class="num tien">${gop(sVal)}</td><td class="num tien">${gop(sThu)}</td><td class="num tien">${gop(sCon)}</td>
      <td class="tien"></td><td class="tien"></td><td class="tien"></td><td class="tien-chi"></td><td class="tien-chi"></td><td class="tien-chi"></td><td class="tien-chi"></td>
      <td class="num tien-chi">${so(sExp)} LAK</td><td class="num tien">${gop(sNet)}</td><td colspan="2"></td></tr>`;
    const tong = ds.tong ?? rows.length, soTrang = Math.max(1, Math.ceil(tong / CO));
    root.querySelector('#td-dem').textContent = rows.length ? `${so(dau + 1)}–${so(dau + rows.length)} / ${so(tong)} ${NN.t('rows')}` : '';
    const tr = root.querySelector('#td-trang');
    tr.innerHTML = soTrang > 1 ? `<button class="btn sm" data-trang="${TRANG - 1}" ${TRANG <= 1 ? 'disabled' : ''}>${NN.h('trang_truoc')}</button>
      <span class="small muted">${NN.h('trang_n', { n: so(TRANG), tong: so(soTrang) })}</span>
      <button class="btn sm" data-trang="${TRANG + 1}" ${TRANG >= soTrang ? 'disabled' : ''}>${NN.h('trang_sau')}</button>` : '';
    tr.querySelectorAll('[data-trang]').forEach(b => b.addEventListener('click', () => tai(+b.dataset.trang).catch(EPL.baoLoi)));
    root.querySelectorAll('#td-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: tr.dataset.id })));
    veTrong(!rows.length);
    datDinhTieuDe();
    datCao();
  }

  /** Bảng cuộn trong khung cao VỪA cửa sổ: đo chỗ còn lại từ đầu bảng tới đáy cửa sổ, trừ phần nằm dưới bảng (thanh chia
   *  trang, dòng ghi chú, viền thẻ, lề đáy trang). Số cố định trong CSS chỉ đúng một kiểu: chế độ VI + ລາວ (nhãn hai dòng),
   *  hàng lọc xuống dòng, có thanh chia trang là trang lại cuộn dọc thêm 50–100px (rà 01/10). Toạ độ là điểm ảnh màn hình,
   *  max-height là px CSS bên trong .app (zoom = --ty-le) nên chia cho --ty-le. */
  function datCao() {
    const c = root && root.querySelector('.td-cuon');
    if (!c || c.hidden || !c.isConnected) return;
    // lúc mở màn còn dải "Đang tải…" (chung.js: .mod-dang-tai::before) đẩy bảng xuống ~45px — đo sau khi dải đó tắt
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const page = document.getElementById('noi-dung'), the = c.closest('.card');
    const r = c.getBoundingClientRect(), duoi = the.getBoundingClientRect().bottom - r.bottom;
    const le = (parseFloat(getComputedStyle(page).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (r.top + window.scrollY) - duoi - le) / tl;
    root.style.setProperty('--td-cao', Math.max(240, Math.floor(cao)) + 'px');   // biến CSS, không style trực tiếp: quy tắc in vẫn thắng
  }
  let henCao = null;
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };   // sau khi chung.js đặt lại --ty-le

  /** Hàng tiêu đề thứ hai dính NGAY DƯỚI hàng một. Đặt cứng top:37px thì ở chế độ VI + ລາວ (hàng một hai dòng) hàng hai
   *  đè lên nửa dưới hàng một khi cuộn dọc — đo chiều cao thật sau mỗi lần vẽ / đổi tiếng. */
  function datDinhTieuDe() {
    const bang = root.querySelector('.td-bang'), o = bang && bang.querySelector('thead tr:first-child th.grp');
    if (o && o.offsetHeight) bang.style.setProperty('--td-h1', o.offsetHeight + 'px');
  }

  function veChuThich() {
    const o = root.querySelector('#td-ty-gia');
    if (!o) return;
    const ds_ = EPL.TIEN_TE.filter(m => m !== 'LAK' && tyGia[m]).map(m => `1 ${m} = ${so(tyGia[m], m === 'VND' ? 2 : 0)} LAK`);
    o.innerHTML = ds_.length ? `<span class="small muted">${NN.h('rate_on_slip')}: ${esc(ds_.join(' · '))}</span>` : '';
  }

  // "Xuất báo cáo" (và nút cùng tên ở Tổng quan) giờ ra Excel thật .xlsx — trước đây là CSV (rà 23/09)
  const xuatBaoCao = () => EPL.xuatExcel();

  /** Excel ra ĐỦ mọi phiếu khớp bộ lọc, không chỉ trang đang xem: tải từng đợt 500 dòng, vẽ tạm cả bảng, đọc bảng
   *  bằng đúng cách xuất mặc định (cùng cột, cùng định dạng tiền), rồi vẽ lại trang đang xem. */
  async function xuatHet(r) {
    const tong = ds.tong ?? ds.length, tat = [];
    for (let t = 1; (t - 1) * 500 < tong; t++) {
      const p = thamLoc(); p.set('trang', t); p.set('co', 500);
      tat.push(...await API.get('/api/bao-cao/theo-doi?' + p));
    }
    const giu = ds, giuTrang = TRANG;
    ds = tat; TRANG = 1; locVaVe();
    try { return EPL._xlsx.sheetMacDinh(r); } finally { ds = giu; TRANG = giuTrang; locVaVe(); }
  }

  EPL.modules['theo-doi'] = {
    async init(r, ctx) {
      root = r;
      const t = ctx.tham || {};
      // Mở từ Tổng quan: mang sẵn bộ lọc và tháng đang xem sang đây.
      if (t.transport_status) r.querySelector('#td-vc').value = t.transport_status;
      if (t.finance_status) r.querySelector('#td-tc').value = t.finance_status;
      if (t.cty) r.querySelector('#td-cty').value = t.cty;
      if (t.q) r.querySelector('#td-q').value = t.q;
      // kỳ mang sang (?thang= hay ?tu=&den= — Tổng quan gửi đúng kỳ đang xem); không có thì tháng này
      const kyDc = KTG.tuDiaChi(t);
      KY = KTG(r.querySelector('#td-ky'), { cheDo: 'khoang', giaTri: kyDc || KTG.cuaThang(EPL.thangNay()), toiDaNgay: 366,
        khiDoi: () => chonThang() });          // tự chọn kỳ: bỏ dòng báo
      BAO = null; GAN = null;
      TU_DONG = !kyDc;                        // mở thẳng (menu, tìm một số phiếu từ Tổng quan): tháng này trống thì sang tháng gần nhất có
      let hen = null;
      r.querySelector('#td-q').addEventListener('input', () => { clearTimeout(hen); hen = setTimeout(() => tai(1).catch(EPL.baoLoi), 350); });
      ['td-vc', 'td-tc', 'td-cty'].forEach(id => r.querySelector('#' + id).addEventListener('change', () => tai(1).catch(EPL.baoLoi)));
      r.querySelector('#td-quy').addEventListener('change', () => tai(TRANG).catch(EPL.baoLoi));   // dòng tổng quy đổi ở máy chủ
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      r.querySelector('#td-xuat').addEventListener('click', xuatBaoCao);
      r.querySelector('#td-moi').addEventListener('click', () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      // tỷ giá chỉ cho dòng chú thích — hỏi SONG SONG với bảng, bảng không phải chờ nó (rà 01/10: 40–465 ms đứng trước bảng)
      tyGia = {};
      const nhanTyGia = API.get('/api/rates').then(d => { tyGia = d || {}; }, () => { tyGia = {}; })
        .then(() => { if (root === r) veChuThich(); });
      await Promise.all([tai(), nhanTyGia]);
      if (t.xuat) xuatBaoCao();               // nút "Xuất báo cáo" bên Tổng quan bấm thẳng sang đây
    },
    xuatExcel: (r) => xuatHet(r),
    onLang() { veChuThich(); if (ds.length) locVaVe(); else { veTrong(true); datDinhTieuDe(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); },
  };
})();
