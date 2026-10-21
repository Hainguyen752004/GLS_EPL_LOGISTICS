/* Theo dõi phiếu vận chuyển — một dòng một phiếu, đủ cột như sheet ໜ້າລາຍງານຂົນສົ່ງ.
 *
 * TIỀN TỆ. Mỗi phiếu tính theo tiền của hợp đồng phiếu đó (USD · LAK · CNY · THB), nên bảng này có
 * cột **Tiền** nói rõ từng dòng là tiền gì, và dòng tổng cộng RIÊNG TỪNG LOẠI TIỀN thay vì cộng
 * táo với cam. Ai muốn một con số duy nhất thì đổi ô "Quy đổi" sang Kíp hoặc USD — lúc đó mọi dòng
 * quy theo tỷ giá đã khoá trên chính phiếu đó, và dòng tổng còn một con số.
 * Riêng khối chi phí luôn là Kíp: dòng chi vốn đã trộn LAK · VND · THB nên quy về Kíp ngay từ máy chủ.
 *
 * 20/10 (rà điều xe D16 · D17 · D21):
 *  · bảng dựng từ MỘT danh sách cột (COT) — tiêu đề hai tầng, thân, dòng tổng cùng đọc danh sách đó. Nút «Cột» ẩn / hiện cột, nhớ
 *    trong localStorage theo vai; mặc định Bãi vừa khung 1366 không kéo ngang, kế toán chỉ khối tiền chính (phiếu quặng, đã thu, chi
 *    tiết chi phí, xe liên kết bật thêm khi cần — bảng kế toán ~1.850px thay vì 3.167px). Biển đầu · rơ-moóc · số xe gộp MỘT cột «Xe · biển số». Ba cột #, Ngày, Số phiếu ghim trái khi kéo ngang.
 *    Cột tiền của Bãi vẫn dựng như trước, CSS giấu (.vai-yard .tien) — máy chủ cũng không gửi số;
 *  · bấm tiêu đề cột để sắp (máy chủ: tham số sap — routes/bao_cao.SAP_TD), mũi tên chỉ chiều; bấm lần ba về thứ tự mặc định;
 *  · lọc nhanh Gom / Giao · khách · tuyến · xe; nút «Việc chờ tôi» — phiếu đang chờ chính người đăng nhập (tham số cho_toi);
 *  · bộ lọc (tìm, trạng thái, kỳ, trang, sắp xếp…) ghi vào địa chỉ bằng history.replaceState — mở lại địa chỉ đó là đúng bộ lọc;
 *  · bấm một dòng: ghi danh sách phiếu đang hiện (EPL.ghiDsPhieu, js/chung.js) để màn Phiếu xuất xe có ‹ trước · sau › và Quay lại.
 */
(function () {
  const { API, NN, AUTH, esc, so, tag } = EPL;
  const KTG = EPL.khoangThoiGian;
  // 09/10 (anh Khampla): kỳ xem chọn ở bộ lọc thời gian dùng chung (KY: Năm · Tháng · Khoảng thời gian · nút nhanh) thay ô tháng
  let root, ds = [], tyGia = {}, TRANG = 1, TONG = {}, KY = null;
  const CO = 100;              // một trang 100 phiếu — một tháng có thể ~30.000 phiếu (nghìn chuyến / ngày)
  /* Tháng trống (chủ dự án 01/10: mở màn đầu tháng thấy "Chưa có dữ liệu", tưởng màn không tải được).
   * TU_DONG: lượt tải đầu khi vào màn KHÔNG kèm tháng — tháng này trống thì tự sang tháng gần nhất có phiếu, BAO giữ dòng báo.
   * Người dùng tự chọn tháng trống thì giữ tháng đó; GAN là tháng gần nhất có phiếu cho nút trong khung trống. */
  let TU_DONG = false, BAO = null, GAN = null;
  /* 20/10: SAP — cột đang sắp ('' = mặc định ngày, số phiếu tăng dần; 'khoa' tăng; '-khoa' giảm). CHO_TOI — đang lọc «Việc chờ tôi»;
   * KY_GIU — kỳ trước khi bật (tắt thì trả về); DEM_CHO — gói /api/viec-cho-toi (số trên nút, ngày cũ nhất để mở rộng kỳ).
   * XUAT_DU — đang dựng bảng cho Excel: đủ mọi cột vai được xem, không theo lựa chọn ẩn / hiện. */
  let SAP = '', CHO_TOI = false, KY_GIU = null, DEM_CHO = null, XUAT_DU = false;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');
  const q = (s) => root.querySelector(s);
  const laBai = () => AUTH.role === 'yard';

  /* «Tháng gần nhất có phiếu»: dòng tổng (/api/bao-cao/theo-doi/tong?tu_tim=1) trả `gan` khi kỳ trống — máy chủ tính theo ĐỦ bộ lọc
   * (kể cả khách · tuyến · xe · Việc chờ tôi). Trước 20/10 hỏi /api/trips (EPL.khoangThoiGian.gan) — đường đó không có các lọc mới. */

  /** Tỷ giá quy đổi của MỘT phiếu — lấy ngay trên phiếu, không lấy tỷ giá hôm nay. */
  function rate(p, ma) {
    return { USD: p.rate_usd || 22000, THB: p.rate_thb || 700, VND: p.rate_vnd || 1.2,
      CNY: p.rate_cny || 3000, LAK: 1 }[String(ma || 'LAK').toUpperCase()] || 1;
  }
  const quy = () => q('#td-quy').value;       // '' = giữ tiền của phiếu
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

  /* ================================================================ cột
   * k: khoá · n: khoá chữ tiêu đề · nhom: nhóm tầng trên (NHOM) · tien: lớp tiền ('tien' bán · 'tien-chi' chi — Bãi không thấy) ·
   * sap: khoá sắp ở máy chủ · lop: lớp ô · khoa: luôn hiện · an: mặc định ẩn · an_bai: mặc định ẩn với Bãi.
   * Nhóm phải liền nhau trong danh sách (tiêu đề tầng trên gộp các cột liền nhau cùng nhóm). */
  const NHOM = { so: { n: 'c_billno' }, can: { n: 'k3_khoi_luong' }, ban: { n: 'value_amt', tien: 'tien' }, lk: { n: 'co_joint', tien: 'tien' },
    chi: { n: 'expense', tien: 'tien-chi' }, tt: { n: 'status' } };
  /* 20/10 (rà điều xe, bảng vừa khung 1366 cho kế toán): mỗi vai mở sẵn cột việc của mình — `an_vai` = vai ẨN SẴN cột đó (vẫn bật lại
   * được bằng nút «Cột», Excel vẫn đủ cột). Bên thu không cần Tổng chi / Thu – Chi; bên chi không cần đơn giá / doanh thu / còn nợ;
   * cột «Cty nhận» thay bằng nhãn «liên kết» ngay trong ô Xe. Bãi, Sếp giữ như cũ. */
  const THU = ['acct', 'rev', 'treasury', 'cash'], CHI = ['expacct', 'fuel', 'repair'];
  const COT = [
    { k: 'stt', n: '#', khoa: true, lop: 'td-g1' },
    { k: 'ngay', n: 'c_date', nhom: 'so', sap: 'ngay', khoa: true, lop: 'td-g2 nowrap' },
    { k: 'so', n: 'doc_no', nhom: 'so', sap: 'so', khoa: true, lop: 'td-g3 nowrap mono' },
    { k: 'quang', n: 'c_orebill', sap: 'quang', an: true, lop: 'mono td-quang' },
    { k: 'tuyen', n: 'c_route', sap: 'tuyen', lop: 'td-tuyen' },
    { k: 'loai', n: 'c_company', sap: 'loai', an_vai: [...THU, ...CHI] },
    { k: 'tai_xe', n: 'c_driver', sap: 'tai_xe', lop: 'td-hai' },
    { k: 'xe', n: 'tdp_c_xe', sap: 'xe', lop: 'td-hai nowrap' },
    { k: 'khach', n: 'c_customer', sap: 'khach', lop: 'td-khach' },
    { k: 'hang', n: 'c_goods', sap: 'hang', an: true },
    // `ngan` (20/10): chữ tiêu đề ngắn trên màn — nhóm phía trên đã ghi «Khối lượng (tấn)»; Excel (XUAT_DU) vẫn ghi tên đầy đủ
    { k: 'can_dau', n: 'c_w_origin', ngan: 'tdp_can_dau', nhom: 'can', sap: 'can_dau', lop: 'num' },
    { k: 'can_cuoi', n: 'c_w_dest', ngan: 'tdp_can_cuoi', nhom: 'can', sap: 'can_cuoi', lop: 'num nowrap' },
    { k: 'ccy', n: 'c_ccy', nhom: 'ban', tien: 'tien', lop: 'mono td-ccy' },
    { k: 'gia', n: 'c_price', nhom: 'ban', tien: 'tien', lop: 'num', an_vai: CHI },
    { k: 'dt', n: 'c_value', nhom: 'ban', tien: 'tien', lop: 'num', an_vai: CHI },
    { k: 'thu', n: 'collected', nhom: 'ban', tien: 'tien', lop: 'num', an: true },
    { k: 'con', n: 'remaining', nhom: 'ban', tien: 'tien', lop: 'num', an_vai: CHI },
    { k: 'thue', n: 'c_joint_fee', nhom: 'lk', tien: 'tien', lop: 'num', an: true },
    { k: 'phi', n: 'c_fee2', nhom: 'lk', tien: 'tien', lop: 'num', an: true },
    { k: 'vuot', n: 'c_over', nhom: 'lk', tien: 'tien', lop: 'num', an: true },
    { k: 'c_dau', n: 'c_fuel', nhom: 'chi', tien: 'tien-chi', lop: 'num', an: true },
    { k: 'c_di', n: 'c_travel', nhom: 'chi', tien: 'tien-chi', lop: 'num', an: true },
    { k: 'c_sua', n: 'c_repair', nhom: 'chi', tien: 'tien-chi', lop: 'num', an: true },
    { k: 'c_khac', n: 'c_other', nhom: 'chi', tien: 'tien-chi', lop: 'num', an: true },
    { k: 'c_tong', n: 'c_totexp', nhom: 'chi', tien: 'tien-chi', lop: 'num', an_vai: THU },
    { k: 'lai', n: 'net', tien: 'tien', lop: 'num', an_vai: THU },
    { k: 'vc', n: 'c_st_t', nhom: 'tt', sap: 'vc', lop: 'td-tt' },
    { k: 'tc', n: 'c_st_f', nhom: 'tt', sap: 'tc', an_bai: true, lop: 'td-tt' },
  ];
  /** Cột vai này được CHỌN ẩn / hiện: Bãi không có cột tiền (luôn giấu — CSS); cột khoá luôn hiện. */
  const chonDuoc = (c) => !c.khoa && !(c.tien && laBai());
  const K_COT = () => 'epl_lao_td_cot_' + (AUTH.role || 'x');
  const macDinh = () => new Set(COT.filter(c => chonDuoc(c) && !c.an && !(c.an_bai && laBai()) && !(c.an_vai || []).includes(AUTH.role)).map(c => c.k));
  function docChon() {
    try { const v = JSON.parse(localStorage.getItem(K_COT()) || 'null'); if (Array.isArray(v)) return new Set(v); } catch (e) { /* bỏ qua */ }
    return macDinh();
  }
  let CHON = new Set();
  /** Cột dựng ra bảng: cột khoá · cột tiền của Bãi (dựng như cũ, CSS giấu) · cột đang chọn · (Excel) mọi cột. */
  const cotHien = () => COT.filter(c => c.khoa || (c.tien && laBai()) || XUAT_DU || CHON.has(c.k));
  const lopO = (c) => [c.lop || '', c.tien || ''].join(' ').trim();

  /* ================================================================ tải */
  /* Dữ liệu cả năm (24/09): lọc · tìm · chia trang ở MÁY CHỦ; dòng tổng lấy từ /api/bao-cao/theo-doi/tong — cộng trên
   * TOÀN BỘ phiếu khớp bộ lọc, riêng từng loại tiền (hoặc quy về một tiền theo tỷ giá khoá trên từng phiếu). */
  const LOC = [['td-vc', 'transport_status'], ['td-tc', 'finance_status'], ['td-cty', 'company'], ['td-loai', 'kind'],
    ['td-kh', 'customer_id'], ['td-tuyen', 'route_id'], ['td-xe', 'vehicle_id']];
  function thamLoc() {
    const p = KTG.thamSo(KY.giaTri);          // trọn một tháng → thang (như cũ), khoảng khác → tu + den
    const tim = q('#td-q').value.trim(); if (tim) p.set('q', tim);
    LOC.forEach(([id, k]) => { const v = q('#' + id).value; if (v) p.set(k, v); });
    if (CHO_TOI) p.set('cho_toi', '1');
    return p;
  }
  let LUOT = 0;                // lượt tải mới nhất — gõ tìm trong lúc lượt trước (tự sang tháng) còn chờ thì lượt cũ không vẽ đè
  async function tai(trang = 1) {
    const luot = ++LUOT;
    TRANG = trang;
    const pt = thamLoc(); pt.set('trang', TRANG); pt.set('co', CO); if (SAP) pt.set('sap', SAP);
    const pq = thamLoc(); if (quy()) pq.set('quy', quy()); pq.set('tu_tim', '1');
    const [a, b] = await Promise.all([API.get('/api/bao-cao/theo-doi?' + pt), API.get('/api/bao-cao/theo-doi/tong?' + pq)]);
    if (luot !== LUOT || !root.isConnected) return;
    ds = a; TONG = b || {}; GAN = null;
    if (!ds.length && TONG.gan !== undefined) {
      GAN = TONG.gan || null;
      if (TU_DONG && GAN) { TU_DONG = false; BAO = { trong: KY.laThang() || KY.giaTri.tu.slice(0, 7), xem: GAN }; KY.dat(KTG.cuaThang(GAN)); return tai(1); }
    }
    TU_DONG = false;
    ghiDiaChi();
    locVaVe();
  }
  /** Bộ lọc ngoài tháng đang bật — khung trống nói "không khớp bộ lọc" thay vì "tháng chưa có phiếu". */
  const coLoc = () => !!q('#td-q').value.trim() || LOC.some(([id]) => q('#' + id).value);
  /** Người dùng TỰ chọn kỳ (bộ lọc thời gian, nút tháng gần nhất ở khung trống): giữ đúng kỳ đó, bỏ dòng báo, thôi tự sang tháng khác.
   *  `v` = 'YYYY-MM' (nút ở khung trống) — không có thì kỳ đang chọn trên bộ lọc. */
  function chonThang(v) { TU_DONG = false; BAO = null; KY_GIU = null; if (v) KY.dat(KTG.cuaThang(v)); return tai(1); }

  /* ================================================================ địa chỉ (D17)
   * Bộ lọc ghi vào hash bằng history.replaceState (không thêm bước Lùi, không bắn hashchange — màn không nạp lại). Khoá giữ đúng tên
   * Tổng quan vẫn gửi sang (transport_status · finance_status · cty · q · thang | tu + den), thêm: kind · kh · tuyen · xe · quy ·
   * cho_toi · sap · trang. */
  const KHOA_DC = [['td-vc', 'transport_status'], ['td-tc', 'finance_status'], ['td-cty', 'cty'], ['td-loai', 'kind'],
    ['td-kh', 'kh'], ['td-tuyen', 'tuyen'], ['td-xe', 'xe'], ['td-quy', 'quy']];
  function diaChi() {
    const p = KTG.thamSo(KY.giaTri);
    const tim = q('#td-q').value.trim(); if (tim) p.set('q', tim);
    KHOA_DC.forEach(([id, k]) => { const v = q('#' + id).value; if (v) p.set(k, v); });
    if (CHO_TOI) p.set('cho_toi', '1');
    if (SAP) p.set('sap', SAP);
    if (TRANG > 1) p.set('trang', TRANG);
    return '#/theo-doi?' + p;
  }
  function ghiDiaChi() {
    // người dùng đã rời sang màn khác trong lúc chờ: không đè địa chỉ của màn đó
    if (!root.isConnected || !/^#\/theo-doi(\?|$)/.test(location.hash)) return;
    const moi = diaChi();
    if (location.hash !== moi) { try { history.replaceState(history.state, '', moi); } catch (e) { /* trình duyệt chặn thì thôi */ } }
  }

  /* ================================================================ vẽ */
  /** Dòng báo cạnh ô tháng (tự sang tháng khác) và khung trống giữa vùng đang nhìn, có nút về tháng gần nhất có phiếu. */
  function veTrong(trong) {
    const bao = q('#td-bao');
    bao.hidden = !BAO;
    bao.innerHTML = BAO ? `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg><span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span>` : '';
    q('.td-cuon').hidden = trong;
    const o = q('#td-trong');
    o.hidden = !trong;
    if (!trong) { o.innerHTML = ''; return; }
    const th = KY.laThang();                  // kỳ trọn một tháng: câu cũ «Tháng 09/2026 chưa có phiếu»; khoảng khác: kèm hai ngày
    const chu = CHO_TOI && !q('#td-q').value.trim() && !LOC.some(([id]) => q('#' + id).value) ? NN.h('tdp_cho_toi_trong')
      : coLoc() || CHO_TOI ? NN.h('loc_trong') : th ? NN.h('thang_trong_n', { thang: nhanThang(th) }) : NN.h('ktg_trong_n', { khoang: KY.nhan() });
    o.innerHTML = `<b>${chu}</b>
      ${GAN ? `<button type="button" class="btn primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}`;
    const b = o.querySelector('[data-thang]');
    if (b) b.addEventListener('click', () => chonThang(b.dataset.thang).catch(EPL.baoLoi));
  }

  /** Nội dung từng ô của một phiếu — {khoá cột: html | [html, lớp thêm]}. */
  function oDong(p, i, dau) {
    const c = p.tinh || {}, ma = c.ccy, mh = c.hire_ccy || ma;
    const chi = c.chi || {};                 // Bãi không nhận tiền chi (anh Khampla A2) — cột đó ẩn với Bãi
    const d = '<span class="muted">—</span>';
    const hao = c.hao_hut_pct != null && c.hao_hut_pct > 1.5 ? `<span class="td-hao" title="${esc(NN.t('w_loss'))}">${so(c.hao_hut_pct, 1)}%</span>` : '';
    // 12/10 (anh Khampla: tổng tiền không đúng): chưa có cân cuối → doanh thu · còn lại · lãi là TẠM TÍNH — chữ nghiêng, nhãn
    // «tạm tính», không cộng vào dòng tổng (máy chủ tách riêng ở TONG.tam_tinh)
    const tam = !!c.tam_tinh;
    const goiTam = esc(NN.t(c.cach_tinh === 'chuyen' ? 'td_tam_goi_y_chuyen' : 'td_tam_goi_y'));
    const oTam = (html) => tam ? `<i class="td-tam" title="${goiTam}">${html}</i>` : html;
    const bien = [p.plate_head, p.plate_trailer].filter(Boolean).map(esc).join(' · ');
    return {
      stt: dau + i + 1,
      ngay: EPL.ngay(p.doc_date),
      // 21/10: số phiếu là <a href> — chuột phải «Mở trong thẻ mới»; Ctrl / nút giữa trên chỗ khác của dòng cũng mở thẻ mới (init)
      so: `<a class="td-so-lk" href="${EPL.href('phieu-xuat-xe', { id: p.id })}"><b>${esc(p.doc_no)}</b></a>`,
      quang: esc(p.ore_bill_no) || d,
      tuyen: p.origin || p.destination ? `<span lang="lo">${esc(p.origin) || '—'} → ${esc(p.destination) || '—'}</span>` : d,
      loai: p.company === 'joint' ? tag('plain', 'co_joint') : 'EPL',
      // tên Lào + tên đọc Latin (máy chủ gửi driver_latin, 20/10) — gõ "Bounmi" ở ô tìm thì thấy ngay dòng nào là Bounmi
      tai_xe: p.driver_name ? `<span lang="lo">${esc(p.driver_name)}</span>${p.driver_latin && !p.driver_name.includes(p.driver_latin) ? `<small>${esc(p.driver_latin)}</small>` : ''}` : d,
      xe: (p.truck_no || bien ? `<b lang="lo">${esc(p.truck_no) || '—'}</b>${bien ? `<small lang="lo">${bien}</small>` : ''}` : d)
        + (p.company === 'joint' && !CHON.has('loai') && !XUAT_DU ? ' ' + tag('plain', 'co_joint') : ''),   // cột Cty nhận đang ẩn (20/10)
      khach: p.customer_name ? `<span lang="lo">${esc(p.customer_name)}</span>` : d,
      hang: tag('ore', p.goods_type || 'iron_ore'),
      can_dau: so(p.weight_origin, 2),
      can_cuoi: (p.weight_dest != null ? so(p.weight_dest, 2) : d) + hao,
      ccy: esc(quy() || ma),
      gia: oTien(p, p.price, ma) + (c.cach_tinh === 'chuyen' ? `<span class="td-hao" style="color:var(--muted)" title="${esc(NN.t('pm_chuyen'))}">${NN.h('pm_chuyen_s')}</span>` : ''),
      dt: tam ? oTam(oTien(p, c.doanh_thu, ma)) + `<span class="td-tam-nhan" title="${goiTam}">${NN.h('td_tam')}</span>` : oTien(p, c.doanh_thu, ma, true),
      thu: c.da_thu ? oTien(p, c.da_thu, ma) : d,
      con: [c.con_lai ? oTam(oTien(p, c.con_lai, ma)) : d, c.con_lai && !tam ? 'neg' : ''],
      thue: c.lien_ket ? oTien(p, c.tien_thue, mh) : d,
      phi: c.lien_ket ? oTien(p, c.phi, mh) : d,
      vuot: c.lien_ket ? oTien(p, c.tru_vuot, mh) : d,
      c_dau: so(chi.fuel), c_di: so(chi.travel), c_sua: chi.repair ? so(chi.repair) : d, c_khac: chi.other ? so(chi.other) : d,
      c_tong: `<b>${so(c.tong_chi_lak)}</b>`,
      lai: [tam ? oTam(oTien(p, c.lai, ma)) : `<b>${oTien(p, c.lai, ma)}</b>`, tam ? '' : c.lai < 0 ? 'neg' : 'pos'],
      vc: tag(p.transport_status),
      tc: tag(p.finance_status),
    };
  }

  /** Hai tầng tiêu đề: cột ngoài nhóm cao hai tầng; nhóm (liền nhau) một ô tầng trên trải đúng số cột đang hiện của nhóm. Cột sắp
   *  được: chữ nằm trong <span data-i18n> (NN.apDung vẽ lại chữ mà không xoá mũi tên). Cột không sắp giữ data-i18n trên chính <th>. */
  function veDau(cot) {
    const h1 = [], h2 = [];
    const th = (c, cao) => {
      const sap = c.sap ? (SAP === c.sap ? 'tang' : SAP === '-' + c.sap ? 'giam' : '') : '';
      const n = c.ngan && !XUAT_DU ? c.ngan : c.n;
      const chu = c.n === '#' ? '#' : NN.h(n);
      const lop = [lopO(c), c.sap ? 'td-sap' : '', sap ? 'sap-' + sap : ''].join(' ').replace(/\s+/g, ' ').trim();
      const nd = c.sap ? `<span data-i18n="${n}">${chu}</span><i class="td-mui" aria-hidden="true"></i>`
        : chu;
      return `<th${cao ? ' rowspan="2"' : ''} class="${lop}"${c.sap ? ` data-sap="${c.sap}" tabindex="0" title="${esc(NN.t('tdp_sap_goi_y'))}"` + (sap ? ` aria-sort="${sap === 'tang' ? 'ascending' : 'descending'}"` : '') : (c.n !== '#' ? ` data-i18n="${n}"` : '')}>${nd}</th>`;
    };
    for (let i = 0; i < cot.length;) {
      const c = cot[i];
      if (!c.nhom) { h1.push(th(c, true)); i++; continue; }
      let j = i; while (j < cot.length && cot[j].nhom === c.nhom) j++;
      const nh = NHOM[c.nhom];
      h1.push(`<th colspan="${j - i}" class="grp ${nh.tien || ''} ${c.nhom === 'so' ? 'td-gso' : ''}" data-i18n="${nh.n}">${NN.h(nh.n)}</th>`);
      for (let k = i; k < j; k++) h2.push(th(cot[k], false));
      i = j;
    }
    return `<tr>${h1.join('')}</tr><tr>${h2.join('')}</tr>`;
  }

  function locVaVe() {
    const rows = ds, dau = (TRANG - 1) * CO, cot = cotHien();
    const sVal = TONG.doanh_thu || {}, sThu = TONG.da_thu || {}, sCon = TONG.con_lai || {}, sNet = TONG.lai || {};
    const sExp = TONG.tong_chi_lak || 0, soPhieu = TONG.so_phieu ?? rows.length;
    q('#td-dau').innerHTML = veDau(cot);
    q('#td-than').innerHTML = rows.length ? rows.map((p, i) => {
      const o = oDong(p, i, dau);
      return `<tr data-id="${esc(p.id)}">${cot.map(c => {
        const v = o[c.k], [html, them] = Array.isArray(v) ? v : [v, ''];
        return `<td class="${(lopO(c) + ' ' + (them || '')).trim()}">${html == null ? '' : html}</td>`;
      }).join('')}</tr>`;
    }).join('') : `<tr><td colspan="${cot.length}" class="empty">${NN.h('no_data')}</td></tr>`;
    const gop = (t) => `<span class="td-gop">${EPL.tienGop(t, '<br>')}</span>`;
    const chan = (nhan, gt, lop) => `<tr${lop ? ` class="${lop}"` : ''}><td colspan="3" class="td-chan-nhan">${nhan}</td>${
      cot.slice(3).map(c => `<td class="${lopO(c)}">${gt[c.k] || ''}</td>`).join('')}</tr>`;
    // nhãn "Tổng · n chuyến" chiếm đúng ba cột đứng yên (#, Ngày, Số phiếu) và đứng yên theo (01/10)
    q('#td-chan').innerHTML = chan(NN.ghep([{ k: 'total' }, ' · ' + so(soPhieu) + ' ', { k: 'trips' }]),
      { dt: gop(sVal), thu: gop(sThu), con: gop(sCon), c_tong: so(sExp) + ' LAK', lai: gop(sNet) }) +
      // 12/10: dòng riêng cho doanh thu TẠM TÍNH (DO chưa có cân cuối) — không nằm trong dòng tổng ở trên
      (TONG.so_phieu_tam && TONG.tam_tinh ? chan(NN.h('td_tam_dong', { n: so(TONG.so_phieu_tam) }),
        { dt: `<i>${gop(TONG.tam_tinh)}</i>`, con: `<i>${gop(TONG.tam_con_lai || {})}</i>` }, 'td-chan-tam') : '');
    const tong = ds.tong ?? rows.length, soTrang = Math.max(1, Math.ceil(tong / CO));
    q('#td-dem').textContent = rows.length ? `${so(dau + 1)}–${so(dau + rows.length)} / ${so(tong)} ${NN.t('rows')}` : '';
    const tr = q('#td-trang');
    tr.innerHTML = soTrang > 1 ? `<button class="btn sm" data-trang="${TRANG - 1}" ${TRANG <= 1 ? 'disabled' : ''}>${NN.h('trang_truoc')}</button>
      <span class="small muted">${NN.h('trang_n', { n: so(TRANG), tong: so(soTrang) })}</span>
      <button class="btn sm" data-trang="${TRANG + 1}" ${TRANG >= soTrang ? 'disabled' : ''}>${NN.h('trang_sau')}</button>` : '';
    tr.querySelectorAll('[data-trang]').forEach(b => b.addEventListener('click', () => tai(+b.dataset.trang).catch(EPL.baoLoi)));
    veTrong(!rows.length);
    datDinhTieuDe();
    datCao();
  }

  /** Bấm một dòng: ghi danh sách đang hiện cho màn Phiếu xuất xe (‹ trước · sau ›, Quay lại về đúng bộ lọc này) rồi mở phiếu. */
  function moPhieu(id) {
    EPL.ghiDsPhieu(ds.map(p => p.id), diaChi(), NN.t(CHO_TOI ? 'tdp_cho_toi' : 'nav_tracking_s'));
    EPL.di('phieu-xuat-xe', { id });
  }
  /** Bấm tiêu đề cột: tăng → giảm → về mặc định. */
  function bamSap(k) {
    SAP = SAP === k ? '-' + k : SAP === '-' + k ? '' : k;
    return tai(1);
  }

  /** Bảng cuộn trong khung cao VỪA cửa sổ: đo chỗ còn lại từ đầu bảng tới đáy cửa sổ, trừ phần nằm dưới bảng (thanh chia
   *  trang, dòng ghi chú, viền thẻ, lề đáy trang). Số cố định trong CSS chỉ đúng một kiểu: chế độ VI + ລາວ (nhãn hai dòng),
   *  hàng lọc xuống dòng, có thanh chia trang là trang lại cuộn dọc thêm 50–100px (rà 01/10). Toạ độ là điểm ảnh màn hình,
   *  max-height là px CSS bên trong .app (zoom = --ty-le) nên chia cho --ty-le. */
  function datCao() {
    const c = root && q('.td-cuon');
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
    const bang = q('.td-bang'), o = bang && bang.querySelector('thead tr:first-child th.grp');
    if (o && o.offsetHeight) bang.style.setProperty('--td-h1', o.offsetHeight + 'px');
  }

  function veChuThich() {
    const o = q('#td-ty-gia');
    if (!o) return;
    const ds_ = EPL.TIEN_TE.filter(m => m !== 'LAK' && tyGia[m]).map(m => `1 ${m} = ${so(tyGia[m], m === 'VND' ? 2 : 0)} LAK`);
    // 20/10: dòng tỷ giá mang lớp .tien (theo-doi.html) — Bãi không thấy tỷ giá (anh Khampla A2); title để đọc đủ khi dòng bị cắt «…»
    o.innerHTML = ds_.length ? `<span class="small muted" title="${esc(NN.t('rate_on_slip') + ': ' + ds_.join(' · '))}">${NN.h('rate_on_slip')}: ${esc(ds_.join(' · '))}</span>` : '';
  }

  /* ================================================================ Việc chờ tôi (D16) */
  /** Số trên nút + ngày cũ nhất (để mở rộng kỳ). Hỏi lại mỗi lần vẽ nút — số đổi khi người ta vừa làm xong một việc. */
  async function napDemCho() {
    try { DEM_CHO = await API.get('/api/viec-cho-toi?co=1'); } catch (e) { if (e && e.ma === 'HUY') return null; DEM_CHO = null; }
    if (root && root.isConnected) veNutChoToi();
    return DEM_CHO;
  }
  function veNutChoToi() {
    const b = q('#td-cho-toi'), n = q('#td-cho-toi-n');
    b.setAttribute('aria-pressed', CHO_TOI ? 'true' : 'false');
    b.classList.toggle('bat', CHO_TOI);
    b.dataset.xuatLoc = CHO_TOI ? NN.t('tdp_cho_toi') : '';      // đầu tệp Excel / PDF ghi rõ đang lọc «Việc chờ tôi» (js/xuat.js boLoc)
    const dem = DEM_CHO ? DEM_CHO.dem : null;
    n.hidden = dem == null; n.textContent = dem == null ? '' : so(dem);
  }
  /** Bật: nhớ kỳ đang xem, mở rộng kỳ từ ngày lập phiếu cũ nhất còn chờ tới hôm nay (tối đa một năm — bộ lọc thời gian không cho dài
   *  hơn) để danh sách có ĐỦ mọi việc như số trên nút. Tắt: trả kỳ cũ. */
  async function batChoToi(bat) {
    CHO_TOI = bat; TU_DONG = false; BAO = null;
    veNutChoToi();
    if (bat) {
      KY_GIU = KY.giaTri;
      const v = await napDemCho();
      if (v && v.tu_som) {
        const nay = EPL.homNay(), den = v.den_muon && v.den_muon > nay ? v.den_muon : nay;
        const d0 = new Date(den + 'T00:00:00'); d0.setDate(d0.getDate() - 365);
        const sat = d0.getFullYear() + '-' + String(d0.getMonth() + 1).padStart(2, '0') + '-' + String(d0.getDate()).padStart(2, '0');
        KY.dat({ tu: v.tu_som < sat ? sat : v.tu_som, den });
      }
    } else if (KY_GIU) { KY.dat(KY_GIU); KY_GIU = null; }
    return tai(1);
  }

  /* ================================================================ ẩn / hiện cột (D21) */
  async function hopCot() {
    const cac = COT.filter(chonDuoc);
    const nhom = (c) => c.nhom ? NHOM[c.nhom].n : '';
    const html = `<p class="small muted" style="margin:0 0 8px">${NN.h('tdp_cot_goi_y')}</p><div class="td-cot-luoi">${cac.map(c =>
      `<label class="td-cot-muc"><input type="checkbox" data-cot="${c.k}" ${CHON.has(c.k) ? 'checked' : ''}><span>${NN.h(c.n)}${nhom(c) && c.nhom !== 'so' ? ` <small>· ${NN.h(nhom(c))}</small>` : ''}</span></label>`).join('')}</div>
      <button type="button" class="btn sm" id="td-cot-md" style="margin-top:10px">${NN.h('tdp_cot_mac_dinh')}</button>`;
    const hoi = EPL.hoi(NN.t('tdp_cot_tieu_de'), html, NN.t('save'));
    const md = document.getElementById('td-cot-md');
    if (md) md.addEventListener('click', () => {
      const m = macDinh();
      document.querySelectorAll('#ht-noi-dung [data-cot]').forEach(x => { x.checked = m.has(x.dataset.cot); });
    });
    if (!(await hoi)) return;
    CHON = new Set([...document.querySelectorAll('#ht-noi-dung [data-cot]')].filter(x => x.checked).map(x => x.dataset.cot));
    try { localStorage.setItem(K_COT(), JSON.stringify([...CHON])); } catch (e) { /* riêng tư thì chỉ phiên này */ }
    locVaVe();
  }

  /* ================================================================ dòng chọn khách · tuyến · xe */
  async function napDongLoc(t) {
    const giu = { 'td-kh': t.kh, 'td-tuyen': t.tuyen, 'td-xe': t.xe };
    // giá trị từ địa chỉ: giữ ngay một dòng tạm cho ô chọn, tải xong danh sách thì thay bằng tên thật
    Object.entries(giu).forEach(([id, v]) => { if (v) { const s = q('#' + id); s.insertAdjacentHTML('beforeend', `<option value="${esc(v)}">…</option>`); s.value = v; } });
    let d;
    try { d = await API.get('/api/bao-cao/theo-doi/loc'); } catch (e) { if (e && e.ma !== 'HUY') EPL.baoLoi(e); return; }
    if (!root.isConnected) return;
    [['td-kh', d.khach], ['td-tuyen', d.tuyen], ['td-xe', d.xe]].forEach(([id, dong]) => {
      const s = q('#' + id), v = s.value;
      s.innerHTML = `<option value="">${esc(NN.t('all'))}</option>` + (dong || []).map(([ma, ten]) => `<option value="${esc(ma)}">${esc(ten)}</option>`).join('');
      if (v && !(dong || []).some(([ma]) => ma === v)) s.insertAdjacentHTML('beforeend', `<option value="${esc(v)}">${esc(v)}</option>`);
      s.value = v;
    });
  }

  // "Xuất báo cáo" (và nút cùng tên ở Tổng quan) giờ ra Excel thật .xlsx — trước đây là CSV (rà 23/09)
  const xuatBaoCao = () => EPL.xuatExcel();

  /** Excel ra ĐỦ mọi phiếu khớp bộ lọc, không chỉ trang đang xem: tải từng đợt 500 dòng, vẽ tạm cả bảng, đọc bảng
   *  bằng đúng cách xuất mặc định (cùng cột, cùng định dạng tiền), rồi vẽ lại trang đang xem. 20/10: đủ mọi cột vai được xem
   *  (XUAT_DU), không theo lựa chọn ẩn / hiện cột trên màn; giữ thứ tự sắp đang chọn. */
  async function xuatHet(r) {
    const tong = ds.tong ?? ds.length, tat = [];
    for (let t = 1; (t - 1) * 500 < tong; t++) {
      const p = thamLoc(); p.set('trang', t); p.set('co', 500); if (SAP) p.set('sap', SAP);
      tat.push(...await API.get('/api/bao-cao/theo-doi?' + p));
    }
    const giu = ds, giuTrang = TRANG;
    ds = tat; TRANG = 1; XUAT_DU = true; locVaVe();
    try { return EPL._xlsx.sheetMacDinh(r); } finally { ds = giu; TRANG = giuTrang; XUAT_DU = false; locVaVe(); }
  }

  EPL.modules['theo-doi'] = {
    async init(r, ctx) {
      root = r;
      const t = ctx.tham || {};
      CHON = docChon(); SAP = /^-?[a-z_]+$/.test(t.sap || '') ? t.sap : ''; CHO_TOI = t.cho_toi === '1'; KY_GIU = null; DEM_CHO = null;
      // Mở từ Tổng quan / mở lại địa chỉ đã ghi (D17): mang sẵn bộ lọc và kỳ đang xem sang đây.
      if (t.transport_status) r.querySelector('#td-vc').value = t.transport_status;
      if (t.finance_status) r.querySelector('#td-tc').value = t.finance_status;
      if (t.cty) r.querySelector('#td-cty').value = t.cty;
      if (t.kind) r.querySelector('#td-loai').value = t.kind;
      if (t.quy) r.querySelector('#td-quy').value = t.quy;
      if (t.q) r.querySelector('#td-q').value = t.q;
      // kỳ mang sang (?thang= hay ?tu=&den= — Tổng quan gửi đúng kỳ đang xem); không có thì tháng này
      const kyDc = KTG.tuDiaChi(t);
      KY = KTG(r.querySelector('#td-ky'), { cheDo: 'khoang', giaTri: kyDc || KTG.cuaThang(EPL.thangNay()), toiDaNgay: 366,
        khiDoi: () => chonThang() });          // tự chọn kỳ: bỏ dòng báo
      BAO = null; GAN = null;
      TU_DONG = !kyDc;                        // mở thẳng (menu, tìm một số phiếu từ Tổng quan): tháng này trống thì sang tháng gần nhất có
      let hen = null;
      r.querySelector('#td-q').addEventListener('input', () => { clearTimeout(hen); hen = setTimeout(() => tai(1).catch(EPL.baoLoi), 350); });
      LOC.forEach(([id]) => r.querySelector('#' + id).addEventListener('change', () => tai(1).catch(EPL.baoLoi)));
      r.querySelector('#td-quy').addEventListener('change', () => tai(TRANG).catch(EPL.baoLoi));   // dòng tổng quy đổi ở máy chủ
      r.querySelector('#td-cho-toi').addEventListener('click', () => batChoToi(!CHO_TOI).catch(EPL.baoLoi));
      r.querySelector('#td-cot').addEventListener('click', () => hopCot().catch(EPL.baoLoi));
      // bấm dòng mở phiếu · bấm / Enter trên tiêu đề cột để sắp — một bộ nghe cho cả bảng (bảng vẽ lại mỗi lần tải)
      const bang = r.querySelector('.td-bang');
      bang.addEventListener('click', (e) => {
        const th = e.target.closest('th[data-sap]');
        if (th) return bamSap(th.dataset.sap).catch(EPL.baoLoi);
      });
      // 21/10: bấm thường như cũ (ghi danh sách cho ‹ trước · sau › rồi mở phiếu); Ctrl / ⌘ / Shift / nút giữa → phiếu ở thẻ mới
      EPL.noiMo(bang, '#td-than tr[data-id]', (tr) => EPL.href('phieu-xuat-xe', { id: tr.dataset.id }), (tr) => moPhieu(tr.dataset.id));
      bang.addEventListener('keydown', (e) => {
        const th = e.target.closest && e.target.closest('th[data-sap]');
        if (th && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); bamSap(th.dataset.sap).catch(EPL.baoLoi); }
      });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      r.querySelector('#td-xuat').addEventListener('click', xuatBaoCao);
      EPL.noiLink(r.querySelector('#td-moi'), () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      veNutChoToi();
      // tỷ giá chỉ cho dòng chú thích — hỏi SONG SONG với bảng, bảng không phải chờ nó (rà 01/10: 40–465 ms đứng trước bảng)
      tyGia = {};
      const nhanTyGia = API.get('/api/rates').then(d => { tyGia = d || {}; }, () => { tyGia = {}; })
        .then(() => { if (root === r) veChuThich(); });
      // dòng chọn khách · tuyến · xe và số «Việc chờ tôi» cũng song song; bảng tải với giá trị đang có trong ô (địa chỉ đã đặt sẵn)
      const dongLoc = napDongLoc(t);
      napDemCho();
      await Promise.all([tai(Math.max(1, parseInt(t.trang, 10) || 1)), nhanTyGia, dongLoc]);
      if (t.xuat) xuatBaoCao();               // nút "Xuất báo cáo" bên Tổng quan bấm thẳng sang đây
    },
    xuatExcel: (r) => xuatHet(r),
    onLang() { veChuThich(); if (ds.length) locVaVe(); else { q('#td-dau').innerHTML = veDau(cotHien()); veTrong(true); datDinhTieuDe(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); },
  };
})();
