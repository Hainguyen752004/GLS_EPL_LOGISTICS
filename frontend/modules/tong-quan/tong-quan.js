/* Tổng quan — bản thiết kế lại anh gửi, đã nối vào máy chủ thật.
   Nguồn số liệu:
     GET /api/bao-cao/tong-quan?thang=YYYY-MM  → doanh_thu_lak + doanh_thu_tien{}, so_phieu, chi_lak, tan_giao,
                                                 chua_thu_lak + chua_thu_tien{}, chua_thu_so, dem{}, chi_theo_muc{}, chu_y[]
     GET /api/bao-cao/xu-huong?thang=YYYY-MM   → thang_truoc, sau_thang, theo_ngay, hao_hut, xe, van_hanh, xem_nhanh, dong_thoi_gian
       (09/10: kỳ không trọn một tháng thì ?tu=YYYY-MM-DD&den=YYYY-MM-DD thay cho ?thang= — bộ lọc thời gian dùng chung)
     GET /api/rates                            → USD, THB, VND, CNY
 *
 * TIỀN TỆ: mỗi phiếu bán bằng tiền của hợp đồng phiếu đó, nên mọi ô số ở đây quy về KÍP (tiền gốc)
 * và ghi chú bên dưới chia ra từng loại tiền — cộng thẳng USD với Nhân dân tệ là cộng táo với cam.
   Biểu đồ: Chart.js 4.5.1 trong frontend/vendor/chartjs, module tự nạp — không gọi CDN.
   Mỗi lần vẽ lại destroy chart cũ để không rò bộ nhớ. */
(function () {

  const { API, NN, esc, so, AUTH } = EPL;
  const KTG = EPL.khoangThoiGian;
  const HAO_HUT_MUC = 1.5;              // % hao hụt cân cho phép — cùng ngưỡng với màn Theo dõi phiếu
  // Bãi không thấy TIỀN BÁN (doanh thu, khách chưa trả, doanh thu theo xe) — đó là biên lợi nhuận.
  // Tiền CHI thì thấy hết, vì chính họ chi. Sếp thấy tất cả nên so vai thẳng, không dùng AUTH.la.
  const laBai = () => AUTH.role === 'yard';
  // 09/10 (anh Khampla): kỳ xem là KHOẢNG NGÀY {tu, den} chọn ở bộ lọc thời gian dùng chung (KY) — trước đây chỉ một tháng.
  // Trọn một tháng thì gọi API bằng `thang` như cũ (KTG.thamSo), còn lại tu/den; tối đa một năm (máy chủ đệm báo cáo theo ngày).
  let root, ky, KY, d, xh, ty_gia, charts = {};
  const laKyThang = () => !!KTG.laThang(ky);
  /* Tháng trống (01/10). BAO: vào màn mà tháng này chưa có phiếu → đã tự sang tháng gần nhất có phiếu. GAN: tháng gần nhất
   * có phiếu khi người dùng TỰ chọn một tháng trống — nút trên thanh công cụ đưa về đó. */
  let BAO = null, GAN = null;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');
  /** G8 (06/10): ô «phiếu lĩnh chờ» mở Web kho anh Tune: Quản lý kho → Danh sách chứng từ (gốc `kho_web` = QLSX_WEB_URL — như
   *  services/kho_ke_toan.web_ke_toan). Trước đây mở <gốc>/#/cap-phat của kho tạm đã bỏ (05/10). */
  async function moKhoChungTu() {
    try {
      const web = ((await API.get('/api/lien-thong/dia-chi', { giu: true })) || {}).kho_web || '';
      if (!web) return EPL.toast(NN.t('kho_web_chua_dat'), 'loi');
      window.open(web.replace(/\/+$/, '') + '/Warehouse/DocumentList', '_blank', 'noopener');
    } catch (e) { EPL.baoLoi(e); }
  }

  /* «Tháng gần nhất có phiếu» dùng chung: EPL.khoangThoiGian.gan (09/10 — trước đây hàm thangGan riêng ở đây, cùng cách). */
  function veBao() {
    const o = root.querySelector('#tq-bao'), trong = d && !d.so_phieu;
    const icon = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>';
    o.hidden = !(trong || BAO);
    o.classList.toggle('trong', !!trong);
    // kỳ trống: trọn một tháng thì câu «Tháng 09/2026 chưa có phiếu» như cũ, khoảng khác thì «01/09/2026 – 15/09/2026 chưa có phiếu»
    const chuTrong = laKyThang() ? NN.h('thang_trong_n', { thang: nhanThang(KTG.laThang(ky)) }) : NN.h('ktg_trong_n', { khoang: KTG.nhan(ky) });
    o.innerHTML = trong ? `${icon}<span>${chuTrong}</span>${GAN ? `<button type="button" class="btn sm primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}`
      : BAO ? `${icon}<span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span>` : '';
    const b = o.querySelector('[data-thang]');
    if (b) b.addEventListener('click', () => { BAO = null; KY.dat(KTG.cuaThang(b.dataset.thang)); tai().catch(EPL.baoLoi); });
  }
  /** Không có dữ liệu thì phải nói ĐÚNG lý do: máy chủ chưa trả được (hỏng/mất mạng) khác hẳn với
   *  tháng này chưa có chuyến nào. Câu sau mà viết như câu trước thì người dùng tưởng phần mềm hỏng. */
  const chuaCo = () => NN.h(!xh ? 'tq_need_endpoint' : laKyThang() ? 'tq_thang_trong' : 'ktg_tq_trong');

  /** Chart.js để sẵn trong dự án, nạp một lần khi mở màn. Không có thư viện thì các khối biểu đồ
   *  báo "chưa vẽ được", phần số vẫn chạy — mất mạng hay thiếu tệp cũng không làm sập màn. */
  function napChart() {
    if (window.Chart) return Promise.resolve(window.Chart);
    return new Promise((res) => {
      const sc = document.createElement('script');
      sc.src = 'vendor/chartjs/chart.umd.min.js';
      sc.onload = () => res(window.Chart);
      sc.onerror = () => res(null);
      document.head.appendChild(sc);
    });
  }

  /* ---------- Màu lấy từ CSS để đổi token là đổi biểu đồ ---------- */
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const C = () => ({
    ink: css('--tq-ink'), muted: css('--tq-muted'), line: css('--tq-line2') || '#eceeec', card: css('--tq-card') || '#fff',
    brand: css('--tq-brand'), navy: css('--tq-navy'), info: css('--tq-info'), good: css('--tq-good'), bad: css('--tq-bad'), warn: css('--tq-warn'),
    fuel: css('--tq-c-fuel'), travel: css('--tq-c-travel'), repair: css('--tq-c-repair'), other: css('--tq-c-other'),
    steps: ['--tq-s1', '--tq-s2', '--tq-s3', '--tq-s4', '--tq-s5'].map(css),
  });
  const FONT = () => ({ family: getComputedStyle(document.body).fontFamily, size: 11 });

  /** Vẽ một biểu đồ. Không có Chart.js hoặc trình duyệt không cho vẽ canvas thì BỎ QUA im lặng:
   *  phần số của màn vẫn đọc được, và màn không phun lỗi ra bảng điều khiển. */
  /** Khung biểu đồ rỗng: ĐẶT một dòng chữ trống cạnh canvas rồi giấu canvas, KHÔNG xoá canvas.
   *  Trước đây xoá cả khung bằng innerHTML, nên đổi sang tháng có số liệu (hay đổi ngôn ngữ) thì
   *  lượt vẽ sau không tìm lại được canvas và màn đổ lỗi giữa chừng — bản rà đã bắt được. */
  /** `khoa`: câu trống riêng của khối khi tháng CÓ chuyến mà khối vẫn chưa có gì (hao hụt: chưa chuyến nào có cân cuối) —
   *  trước đây khối hao hụt ghi "Tháng này chưa có chuyến nào" ngay cạnh dòng thời gian 22 chuyến (rà 01/10). */
  function khungTrong(id, trong, khoa) {
    const el = root.querySelector('#' + id); if (!el) return;
    const khung = el.parentElement;
    let chu = khung.querySelector('.tq-empty');
    if (trong) {
      if (!chu) { chu = document.createElement('div'); chu.className = 'tq-empty'; khung.appendChild(chu); }
      chu.innerHTML = khoa && xh ? NN.h(khoa) : chuaCo(); el.hidden = true;
    } else { if (chu) chu.remove(); el.hidden = false; }
  }

  function chart(id, cfg) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
    const el = root.querySelector('#' + id);
    if (!el || !window.Chart) return null;
    // Không hỏi getContext khi trình duyệt không có canvas 2D (jsdom của bộ kiểm): hỏi là nó kêu ầm lên.
    if (typeof window.CanvasRenderingContext2D === 'undefined') return null;
    try { charts[id] = new Chart(el, cfg); } catch (e) { return null; }
    return charts[id];
  }
  const tooltipBase = (c) => ({ backgroundColor: c.navy, titleFont: { weight: '600' }, bodyFont: FONT(), padding: 8, cornerRadius: 8, displayColors: true, boxPadding: 4 });
  const gridBase = (c) => ({ color: c.line, drawTicks: false });
  const tickBase = (c) => ({ color: c.muted, font: FONT(), padding: 6 });

  /* ---------- Tải ---------- */
  // Lần tải đang chạy — nút Excel bấm ngay lúc vừa mở màn (UAT 25/09: bấm trước khi số liệu về thì "không có gì để
  // xuất") thì CHỜ lần tải này xong rồi mới dựng sheet.
  let dangTai = null;
  function tai() { dangTai = taiThat(); return dangTai; }
  async function taiThat() {
    ky = KY.giaTri;
    const ts = KTG.thamSo(ky).toString();
    const [a, b, c] = await Promise.all([
      API.get('/api/bao-cao/tong-quan?' + ts),
      API.get('/api/bao-cao/xu-huong?' + ts).catch(() => null),   // endpoint mới; thiếu thì vẫn vẽ phần cũ
      API.get('/api/rates'),
    ]);
    // kỳ trống mà người dùng tự chọn: tìm tháng gần nhất có phiếu cho nút trên thanh công cụ (chỉ hỏi khi trống)
    const g = a && !a.so_phieu ? await KTG.gan(ky, {}) : null;
    GAN = g && !g.co ? g.gan : null;
    d = a; xh = b; ty_gia = c; ve();
  }

  /* ---------- Tiện ích ---------- */
  const pct = (a, b) => (b ? (a - b) / b * 100 : null);
  function delta(cur, prev, inv) {                 // inv = true khi tăng là xấu (chi phí, nợ)
    const soSanh = root.querySelector('#tq-so-sanh').checked;
    if (!soSanh || prev == null) return '';
    const p = pct(cur, prev); if (p == null) return `<span class="tq-delta flat">—</span>`;
    const k = Math.abs(p) < 0.5 ? 'flat' : p > 0 ? 'up' : 'down';
    return `<span class="tq-delta ${k} ${inv ? 'inv' : ''}" title="${esc(NN.t(laKyThang() ? 'tq_vs_prev' : 'ktg_vs_prev'))}">${k === 'up' ? '▲' : k === 'down' ? '▼' : '•'} ${so(Math.abs(p), 1)}%</span>`;
  }
  function spark(id, data, color) {
    const c = C();
    chart(id, { type: 'line', data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: color, pointHoverBorderColor: c.card, pointHoverBorderWidth: 2, fill: true, backgroundColor: color + '1a', tension: .35 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false, beginAtZero: true } }, layout: { padding: 2 } } });
  }

  /* ---------- Vẽ ---------- */
  function ve() {
    const c = C(), r_usd = ty_gia.USD || 22000, tt = xh && xh.thang_truoc, st = xh && xh.sau_thang;
    const trieu = (v) => so((v || 0) / 1e6, 1);        // Kíp đọc theo triệu cho dễ nhìn
    const chia = (o) => EPL.tienGop(o || {});           // "8,101.36 USD · 12,000 CNY"
    root.querySelector('#tq-stamp').textContent = `${NN.t('tq_updated')} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
    // ô «So với tháng trước»: kỳ không trọn một tháng thì so với kỳ trước cùng độ dài (máy chủ: KN.ky_truoc) — đổi chữ theo
    const ss = root.querySelector('#tq-so-sanh + span');
    if (ss) { ss.dataset.i18n = laKyThang() ? 'tq_compare' : 'ktg_compare'; ss.innerHTML = NN.h(ss.dataset.i18n); }
    veBao();

    /* 1. KPI — Bãi thay hai ô tiền bán bằng hai ô việc của họ */
    const K = laBai() ? [
      { k: laKyThang() ? 'k_month_trips' : 'ktg_k_trips', v: so(d.so_phieu, 0), u: NN.t('trips'), s: `${d.dem.arrived} ${NN.t('s_arrived')}`, dl: '', sp: null, col: c.brand },
      // Bãi không thấy tiền chi (anh Khampla A2, 23/09) — ô Tổng chi phí bỏ khỏi vai Bãi
      { k: 'k_tons', v: so(d.tan_giao, 2), u: NN.t('ton'), s: `${d.dem.arrived} ${NN.t('trips')} · ${NN.t('s_arrived')}`, dl: delta(d.tan_giao, tt && tt.tan_giao, false), sp: st && st.tan_giao, col: c.info },
      { k: 'k_running', v: so((d.dem.dispatched || 0) + (d.dem.transit || 0), 0), u: NN.t('trips'), s: `${d.dem.dispatched} ${NN.t('s_dispatched')} · ${d.dem.transit} ${NN.t('s_transit')}`, dl: '', sp: null, col: c.warn },
    ] : [
      { k: 'k_rev', v: trieu(d.doanh_thu_lak), u: 'M LAK', s: `${d.so_phieu} ${NN.t('trips')} · ${chia(d.doanh_thu_tien)}`, dl: delta(d.doanh_thu_lak, tt && tt.doanh_thu_lak, false), sp: st && st.doanh_thu_lak, col: c.brand },
      { k: 'k_exp', v: trieu(d.chi_lak), u: 'M LAK', s: `${d.doanh_thu_lak ? so(d.chi_lak / d.doanh_thu_lak * 100) : 0}% ${NN.t('tq_of_revenue')} · ≈ ${so(d.chi_lak / r_usd)} USD`, dl: delta(d.chi_lak, tt && tt.chi_lak, true), sp: st && st.chi_lak, col: c.fuel },
      { k: 'k_tons', v: so(d.tan_giao, 2), u: NN.t('ton'), s: `${d.dem.arrived} ${NN.t('trips')} · ${NN.t('s_arrived')}`, dl: delta(d.tan_giao, tt && tt.tan_giao, false), sp: st && st.tan_giao, col: c.info },
      { k: 'k_unpaid', v: trieu(d.chua_thu_lak), u: 'M LAK', s: `${d.chua_thu_so} ${NN.t('trips')} · ${chia(d.chua_thu_tien)}`, dl: delta(d.chua_thu_lak, tt && tt.chua_thu_lak, true), sp: st && st.chua_thu_lak, col: c.warn },
    ];
    root.querySelector('#tq-kpi').innerHTML = K.map((k, i) => `<div class="tq-kpi">
        <div class="l"><i style="background:${k.col}"></i>${NN.h(k.k)}</div>
        <div class="v">${k.v}<small>${esc(k.u)}</small></div>
        <div class="spark">${k.sp ? `<canvas id="tq-sp-${i}"></canvas>` : ''}</div>
        <div class="s">${k.dl}<span>${esc(k.s)}</span></div>
      </div>`).join('');
    K.forEach((k, i) => k.sp && spark('tq-sp-' + i, k.sp, k.col));

    veXemNhanh(c);
    veGantt(c);

    /* 2. Tiến trình 5 bước */
    const P = [['s_dispatched', d.dem.dispatched, 'dispatched'], ['s_transit', d.dem.transit, 'transit'], ['s_arrived', d.dem.arrived, 'arrived'], ['dt_st_da_tao_so', d.dem.invoiced, 'invoiced'], ['s_paid', d.dem.paid, 'paid']];
    const tongP = P.reduce((a, p) => a + (p[1] || 0), 0) || 1;
    root.querySelector('#tq-tien-do').innerHTML = P.map((p, i) => `<div class="tq-step" role="button" tabindex="0" data-i="${i}" data-st="${p[2]}">
        <div class="n">${p[1]}<small>${so(p[1] / tongP * 100)}%</small></div>
        <div class="l"><i></i>${NN.h(p[0])}</div>
        <div class="m"><b style="width:${p[1] / tongP * 100}%"></b></div>
      </div>`).join('');
    root.querySelector('#tq-phan-bo').innerHTML = P.map((p, i) => `<span style="width:${p[1] / tongP * 100}%;background:${c.steps[i]}" title="${esc(NN.t(p[0]))}: ${p[1]}"></span>`).join('');
    root.querySelectorAll('.tq-step').forEach(el => {
      const go = () => EPL.di('theo-doi', { transport_status: el.dataset.st, ...KTG.diaChi(ky) });
      el.addEventListener('click', go); el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
    const vh = (xh && xh.van_hanh) || {};
    const ring = (p, col) => `<span class="ring" style="--p:${Math.max(0, Math.min(100, p || 0))};--c:${col}" data-v="${p != null ? Math.round(p) + '%' : '—'}"></span>`;
    root.querySelector('#tq-ops').innerHTML = `
      <div class="tq-op">${ring(vh.dung_han_pct, c.good)}<div><b>${vh.dung_han_pct != null ? so(vh.dung_han_pct) + '%' : '—'}</b><br>${NN.h('tq_ontime', { n: vh.nguong_ngay != null ? vh.nguong_ngay : '—' })}</div></div>
      <div class="tq-op">${ring(vh.ngay_tb != null && vh.nguong_ngay ? 100 - Math.min(100, vh.ngay_tb / vh.nguong_ngay * 100) : null, c.info)}<div><b>${vh.ngay_tb != null ? so(vh.ngay_tb, 1) : '—'} ${NN.t('tq_days')}</b><br>${NN.h('tq_avg_days')}</div></div>
      <div class="tq-op">${ring(vh.hao_hut_tb_pct != null ? 100 - Math.min(100, vh.hao_hut_tb_pct / HAO_HUT_MUC * 100) : null, vh.hao_hut_tb_pct > HAO_HUT_MUC ? c.bad : c.good)}<div><b>${vh.hao_hut_tb_pct != null ? so(vh.hao_hut_tb_pct, 2) + '%' : '—'}</b><br>${NN.h('tq_avg_loss')} <span class="muted">(≤ ${HAO_HUT_MUC}%)</span></div></div>`;

    /* 3a. Doanh thu & chi phí theo ngày — MỘT trục KÍP, cột doanh thu + cột chi phí.
       Kíp vì mỗi phiếu bán bằng tiền riêng; quy hết về một tiền mới xếp cạnh nhau được. */
    const ngay = (xh && xh.theo_ngay) || [];
    const cotNgay = [
      { label: NN.t('tq_revenue'), data: ngay.map(x => x.doanh_thu_lak), backgroundColor: c.brand, borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: 'bottom', maxBarThickness: 22, categoryPercentage: .6, barPercentage: .9 },
      { label: NN.t('tq_cost'), data: ngay.map(x => x.chi_lak), backgroundColor: c.fuel, borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: 'bottom', maxBarThickness: 22, categoryPercentage: .6, barPercentage: .9 },
    ].slice(laBai() ? 1 : 0);          // Bãi: chỉ cột chi phí
    root.querySelector('#tq-legend-ngay').innerHTML = cotNgay.map(x => `<span><i style="background:${x.backgroundColor}"></i>${esc(x.label)} (LAK)</span>`).join('');
    chart('tq-c-ngay', {
      type: 'bar',
      data: { labels: ngay.map(x => x.ngay.slice(8, 10) + '/' + x.ngay.slice(5, 7)), datasets: cotNgay },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false }, tooltip: Object.assign(tooltipBase(c), { callbacks: { label: (t) => ` ${t.dataset.label}: ${so(t.parsed.y)} LAK` } }) },
        scales: { x: { grid: { display: false }, ticks: tickBase(c), border: { color: c.line } }, y: { beginAtZero: true, grid: gridBase(c), border: { display: false }, ticks: Object.assign(tickBase(c), { callback: (v) => so(v / 1e6, 1) + 'M' }) } } },
    });
    khungTrong('tq-c-ngay', !ngay.length);

    /* 3b. Cơ cấu chi phí — donut ≤ 4 phần, số ở giữa, danh sách có giá trị + % */
    const cm = d.chi_theo_muc || {}, tong = Object.values(cm).reduce((a, b) => a + b, 0) || 1;
    const M = [['e_fuel', 'fuel', c.fuel], ['e_travel', 'travel', c.travel], ['e_repair', 'repair', c.repair], ['e_other', 'other', c.other]];
    chart('tq-c-cocau', { type: 'doughnut', data: { labels: M.map(m => NN.t(m[0])), datasets: [{ data: M.map(m => cm[m[1]] || 0), backgroundColor: M.map(m => m[2]), borderColor: c.card, borderWidth: 2, hoverOffset: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '72%', plugins: { legend: { display: false }, tooltip: Object.assign(tooltipBase(c), { callbacks: { label: (t) => ` ${so(t.parsed)} LAK · ${so(t.parsed / tong * 100)}%` } }) } } });
    root.querySelector('#tq-donut-center').innerHTML = `<b>${so(tong / 1e6, 1)}</b><small>M LAK</small>`;
    // Tổng của vòng tròn cộng theo DÒNG CHI trên phiếu (kể cả khoản ứng cho xe thuê, trừ vào tiền trả chủ xe); ô "Tổng chi phí"
    // là chi của EPL (xe thuê tính tiền thuê). Hai số khác nhau thì nói rõ vì sao, đừng để hai con số "chi phí" lệch không lời.
    const tongMuc = Object.values(cm).reduce((a, b) => a + b, 0);
    root.querySelector('#tq-co-cau').innerHTML = M.map(m => `<div class="row" data-muc="${m[1]}"><i style="background:${m[2]}"></i><span>${NN.h(m[0])}</span><span class="v">${so(cm[m[1]] || 0)}</span><span class="p">${so((cm[m[1]] || 0) / tong * 100)}%</span></div>`).join('')
      + (d.chi_lak != null && Math.abs(tongMuc - d.chi_lak) >= 1 ? `<p class="tq-co-cau-ghi small muted">${NN.h('tq_co_cau_ghi_chu')}</p>` : '');
    root.querySelectorAll('#tq-co-cau .row').forEach(el => el.addEventListener('click', () => EPL.di('theo-doi', KTG.diaChi(ky))));

    /* 4a. Hao hụt cân theo chuyến — cột %, vạch ngưỡng 1,5 %, cột vượt ngưỡng đổi màu xấu */
    const hh = ((xh && xh.hao_hut) || []).map(x => Object.assign({ pct: x.can_dau ? (x.can_dau - (x.can_cuoi ?? x.can_dau)) / x.can_dau * 100 : 0 }, x)).filter(x => x.can_cuoi != null);
    // máy chủ chỉ gửi 50 chuyến hao hụt nặng nhất (một tháng ~30.000 chuyến) — số đếm lấy từ hao_hut_dem của cả tháng
    const hd = (xh && xh.hao_hut_dem) || { vuot: hh.filter(x => x.pct > HAO_HUT_MUC).length, tong: hh.length };
    root.querySelector('#tq-loss-sub').textContent = hd.tong ? `${so(hd.vuot)}/${so(hd.tong)} ${NN.t('tq_over_limit')}` : '';
    const nguong = { id: 'nguong', afterDatasetsDraw(ch) { const { ctx, chartArea: a, scales: { y } } = ch; const yy = y.getPixelForValue(HAO_HUT_MUC); ctx.save(); ctx.strokeStyle = c.bad; ctx.lineWidth = 1; ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(a.left, yy); ctx.lineTo(a.right, yy); ctx.stroke(); ctx.fillStyle = c.bad; ctx.font = `600 10.5px ${FONT().family}`; ctx.textAlign = 'right'; ctx.fillText(`${NN.t('tq_loss_limit')} ${HAO_HUT_MUC}%`, a.right, yy - 4); ctx.restore(); } };
    chart('tq-c-haohut', { type: 'bar', plugins: [nguong],
      data: { labels: hh.map(x => x.doc_no.replace(/\/EPL$/, '')), datasets: [{ data: hh.map(x => +x.pct.toFixed(2)), backgroundColor: hh.map(x => x.pct > HAO_HUT_MUC ? c.bad : c.info), borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: 'bottom', maxBarThickness: 24, categoryPercentage: .55 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: Object.assign(tooltipBase(c), { callbacks: { title: (t) => hh[t[0].dataIndex].doc_no, label: (t) => { const x = hh[t.dataIndex]; return [` ${so(x.can_dau, 2)} → ${so(x.can_cuoi, 2)} t`, ` ${NN.t('tq_loss')}: ${so(x.pct, 2)}%`]; } } }) },
        scales: { x: { grid: { display: false }, ticks: Object.assign(tickBase(c), { font: { family: 'ui-monospace, JetBrains Mono, monospace', size: 10.5 } }), border: { color: c.line } }, y: { beginAtZero: true, suggestedMax: Math.max(2, ...hh.map(x => x.pct)) * 1.15, grid: gridBase(c), border: { display: false }, ticks: Object.assign(tickBase(c), { callback: (v) => v + '%' }) } },
        onClick: (_, els) => { if (els.length) EPL.di('theo-doi', { q: hh[els[0].index].doc_no }); } } });
    khungTrong('tq-c-haohut', !hh.length, d.so_phieu ? 'tq_hao_chua_can' : null);

    /* 4b. Hiệu suất xe — thanh đo doanh thu cùng một màu, sắp theo doanh thu */
    const xe = ((xh && xh.xe) || []).slice().sort((a, b) => b.doanh_thu_lak - a.doanh_thu_lak), maxDT = Math.max(1, ...xe.map(x => x.doanh_thu_lak));
    // Bãi: xếp theo TẤN và bỏ cột doanh thu — doanh thu là tiền bán.
    const maxTan = Math.max(1, ...xe.map(x => x.tan));
    if (laBai()) xe.sort((a, b) => b.tan - a.tan);
    // 500 xe thì vẽ 20 xe đứng đầu (Excel vẫn xuất đủ) — thanh đo cho cả đội xe dài vài màn hình là không đọc được
    const XE_HIEN = 20;
    root.querySelector('#tq-xe').innerHTML = xe.length ? `<div class="tq-fleet-head"><span>${NN.h('tq_vehicle')}</span><span>${NN.h('tq_trips_tons_km')}</span><span>${laBai() ? NN.h('ton') : 'M LAK'}</span></div>` +
      xe.slice(0, XE_HIEN).map(x => `<div class="tq-veh" data-xe="${esc(x.so_xe)}"><span class="code">${esc(x.so_xe)}</span><div><div class="meta">${x.so_chuyen} ${NN.t('trips')} · ${so(x.tan, 1)} t · ${so(x.km)} km</div><div class="track"><b style="width:${(laBai() ? x.tan / maxTan : x.doanh_thu_lak / maxDT) * 100}%"></b></div></div>${laBai()
        ? `<div class="v">${so(x.tan, 1)}<small>${so(x.km / Math.max(1, x.so_chuyen))} km/${NN.t('trips').toLowerCase()}</small></div>`
        : `<div class="v">${so(x.doanh_thu_lak / 1e6, 1)}<small>${so(x.doanh_thu_lak / Math.max(1, x.tan) / 1e3)} k LAK/t</small></div>`}</div>`).join('')
      : `<div class="tq-empty">${chuaCo()}</div>`;
    root.querySelectorAll('.tq-veh').forEach(el => el.addEventListener('click', () => EPL.di('theo-doi', { q: el.dataset.xe })));

    /* Tỷ giá */
    root.querySelector('#tq-ty-gia').innerHTML = `<div class="tq-ty-gia">${['USD', 'CNY', 'THB', 'VND'].map(m => `<div><span class="small muted">1 ${m} =</span><b>${so(ty_gia[m], m === 'VND' ? 2 : 0)} LAK</b></div>`).join('')}</div>`;
    root.querySelector('#tq-rate-date').textContent = ty_gia.ngay ? EPL.ngay ? EPL.ngay(ty_gia.ngay) : ty_gia.ngay : '';

    /* Cần xử lý — mức độ theo loại: hao hụt / quá hạn = xấu, chưa tạo SO = cảnh báo, chờ kiểm = thông tin.
       Từ 01/10 khoá "chua_hoa_don" / dem.invoiced của máy chủ nghĩa là DO chưa / đã tạo SO bên hệ kế toán (bỏ trang kế toán tạm). */
    // Mã loại do máy chủ đặt (routes/bao_cao.py): hao_hut · chua_hoa_don · chua_can · cho_kiem.
    const MUC = { hao_hut: 'bad', chua_hoa_don: 'warn', chua_can: 'warn', cho_kiem: 'info' };
    // câu trong từ điển đã có {doc_no} ở đầu — trước đây còn in thêm mã phiếu đậm ngay trước, đọc thành hai lần (rà 01/10)
    const cy = d.chu_y || [];
    root.querySelector('#tq-chu-y-n').textContent = cy.length || '';
    root.querySelector('#tq-chu-y').innerHTML = cy.length
      ? `<div class="tq-chu-y">${cy.map(x => `<div class="it ${MUC[x.loai] || 'warn'}" data-doc="${esc(x.doc_no || '')}"><i></i><div class="t">${NN.h('attention_' + (x.loai === 'chua_hoa_don' ? 'chua_tao_so' : x.loai), x)}${x.ngay ? `<small>${esc(x.ngay)}</small>` : ''}</div><button class="btn sm" type="button">${NN.h('tq_open')}</button></div>`).join('')}</div>`
      : `<div class="tq-empty ok">✓ ${NN.h('none_attention')}</div>`;
    root.querySelectorAll('.tq-chu-y .it').forEach(el => el.addEventListener('click', () => { if (el.dataset.doc) EPL.di('theo-doi', { q: el.dataset.doc }); else EPL.di('phieu-xuat-xe'); }));
  }

  /* ---------- B1. Thanh xem nhanh: 7 chip = 7 bộ lọc của màn Theo dõi phiếu ---------- */
  function veXemNhanh(c) {
    const q = (xh && xh.xem_nhanh) || {};
    // Mỗi chip dẫn sang MÀN CÓ THẬT với đúng bộ lọc của màn đó: [khoá, số, màu, màn, tham số]
    const chips = [
      ['tq_q_running', q.dang_chay, 'info', 'theo-doi-tuyen', { o: 'dang_chay' }],
      ['tq_q_late', q.di_lau, 'bad', 'theo-doi-tuyen', { o: 'di_lau' }],
      ['tq_q_incident', q.su_co, 'bad', 'theo-doi-tuyen', { o: 'su_co_mo' }],
      ['tq_q_cho_so', q.cho_hoa_don, 'warn', 'theo-doi-tuyen', { o: 'cho_hoa_don' }],
      ['tq_q_my_work', q.viec_toi, 'info', 'phieu-xuat-xe', q.viec_phieu ? { id: q.viec_phieu } : {}],
      ['tq_q_fuel', q.phieu_linh_cho, 'tan', 'kho:chung-tu', {}],       // G8 06/10: Web kho anh Tune → Danh sách chứng từ
      ['tq_q_unpaid', q.chua_thu_lak != null ? so(q.chua_thu_lak / 1e6, 1) + 'M LAK' : null, 'warn', 'theo-doi', { finance_status: 'unpaid', ...KTG.diaChi(ky) }],
    ].filter(ch => !(laBai() && ['tq_q_unpaid', 'tq_q_cho_so'].includes(ch[0])));   // hoá đơn và thu tiền không phải việc của Bãi
    root.querySelector('#tq-xem-nhanh').innerHTML = `<span class="lbl">${NN.h('tq_quick')}</span>` +
      chips.map((ch, i) => { const v = ch[1]; const zero = v == null || v === 0; return `<button type="button" class="tq-chip ${ch[2]} ${zero ? 'zero' : ''}" data-i="${i}"><b>${v == null ? '—' : esc(v)}</b>${NN.h(ch[0])}</button>`; }).join('') +
      `<span class="sep"></span><span class="right"><span id="tq-quick-stamp"></span><label><input type="checkbox" id="tq-auto">${NN.h('tq_auto')}</label></span>`;
    root.querySelector('#tq-quick-stamp').textContent = `${NN.t('tq_updated')} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
    root.querySelectorAll('.tq-chip').forEach(el => { const ch = chips[+el.dataset.i];
      el.addEventListener('click', () => (ch[3] === 'kho:chung-tu' ? moKhoChungTu() : ch[3].startsWith('kt:') ? EPL.moKeToan(ch[3].slice(3), ch[4]) : EPL.di(ch[3], ch[4]))); });
    const auto = root.querySelector('#tq-auto'); auto.checked = !!autoTimer;
    auto.addEventListener('change', () => { clearInterval(autoTimer); autoTimer = auto.checked ? setInterval(() => tai().catch(EPL.baoLoi), 60000) : null; });
  }
  let autoTimer = null;

  /* ---------- B2. Dòng thời gian chuyến: Gantt theo ngày, 5 giai đoạn nối tiếp ---------- */
  const GD = [['s_dispatched', 'xuat_xe'], ['s_transit', 'toi_bai'], ['tq_g_border', 'cua_khau'], ['s_arrived', 'cang'], ['dt_st_da_tao_so', 'hoa_don']];   // mốc kết thúc mỗi đoạn; 'thanh_toan' là chấm cuối
  /* 09/10: trục là các NGÀY CỦA KỲ (tu … den), không còn cố định một tháng. Kỳ dài (trên 62 ngày — vd cả năm) thì ô ngày rất hẹp:
   * bỏ lưới từng ngày, đầu cột chỉ ghi tháng ở ngày mùng 1 (lớp tq-gantt--dai). */
  const NGAY_MS = 864e5;
  const soNgayCua = (s) => Math.round(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / NGAY_MS);
  function veGantt(c) {
    const rows = (xh && xh.dong_thoi_gian) || [];
    const box = root.querySelector('#tq-gantt');
    const tu = ky.tu, den = ky.den, n0 = soNgayCua(tu), n = soNgayCua(den) - n0 + 1, homNay = EPL.homNay();
    const td = homNay < tu ? 0 : homNay > den ? n : soNgayCua(homNay) - n0 + 1;
    const dayOf = (iso) => { if (!iso) return null; const s = String(iso).slice(0, 10); if (s < tu) return 1; if (s > den) return n + 1; return soNgayCua(s) - n0 + 1; };
    const pos = (day) => ((day - 1) / n * 100), wid = (a, b) => Math.max(0.6, (b - a) / n * 100);
    const dai = n > 62;
    // 60 dòng cần nhìn nhất (đi lâu → đang chạy → mới nhất) trong tổng số chuyến của tháng
    const tongGantt = (xh && xh.dong_thoi_gian_tong) || rows.length;
    root.querySelector('#tq-gantt-sub').textContent = rows.length ? `${rows.length < tongGantt ? so(rows.length) + ' / ' : ''}${so(tongGantt)} ${NN.t('trips')} · ${NN.t('tq_gantt_sub')}` : '';
    root.querySelector('#tq-gantt-legend').innerHTML = GD.map((g, i) => `<span><i style="background:${c.steps[i]}"></i>${NN.h(g[0])}</span>`).join('') + `<span><i style="background:${c.navy};width:10px;border-radius:50%"></i>${NN.h('s_paid')}</span>`;
    box.classList.toggle('tq-gantt--dai', dai);
    if (!rows.length) { box.innerHTML = `<div class="tq-empty">${chuaCo()}</div>`; return; }
    box.style.setProperty('--n', n);
    box.style.setProperty('--cot', dai ? 31 : Math.max(31, n));       // tối thiểu 31 cột rộng --day (như một tháng); dài thì vừa khung
    const [y0, m0, d0] = tu.split('-').map(Number);
    const hdr = `<div class="hdr"><div></div><div class="days">${Array.from({ length: n }, (_, i) => {
      const nd = new Date(y0, m0 - 1, d0 + i), dd = nd.getDate(), w = nd.getDay();
      // kỳ dài: chỉ ghi «MM/YY» ở mùng 1; kỳ ngắn: số ngày như cũ (kỳ qua nhiều tháng thì mùng 1 ghi «1/MM» cho khỏi lẫn)
      const chu = dai ? (dd === 1 || i === 0 ? String(nd.getMonth() + 1).padStart(2, '0') + '/' + String(nd.getFullYear() % 100).padStart(2, '0') : '')
        : (dd === 1 && i > 0 ? dd + '/' + String(nd.getMonth() + 1).padStart(2, '0') : dd);
      return `<span class="${i + 1 === td ? 'today' : (!dai && (w === 0 || w === 6)) ? 'we' : ''}">${chu}</span>`; }).join('')}</div></div>`;
    const body = rows.map(r => {
      const mo = r.moc || {}, start = dayOf(mo.xuat_xe) || dayOf(mo.lap_phieu) || 1;
      let cur = start, segs = '', lastDone = start;
      GD.forEach((g, i) => { const e = dayOf(mo[g[1]]); if (e != null) { segs += `<span class="seg s${i}" style="left:${pos(cur)}%;width:${wid(cur, e + 1)}%" title="${esc(NN.t(g[0]))}: ${esc(mo[g[1]])}"></span>`; cur = e + 1; lastDone = e + 1; } });
      const done = mo.thanh_toan != null, open = !done && r.trang_thai !== 'planned';
      if (open && td >= cur) segs += `<span class="seg open ${r.late ? 'late' : ''}" style="left:${pos(cur)}%;width:${wid(cur, Math.min(n + 1, td + 1))}%" title="${esc(NN.t(r.late ? 'tq_q_late' : 'tq_g_inprogress'))}"></span>`;
      if (done) segs += `<span class="dot paid" style="left:${pos(dayOf(mo.thanh_toan)) + 100 / n / 2}%" title="${esc(NN.t('s_paid'))}: ${esc(mo.thanh_toan)}"></span>`;
      const pill = r.late ? ['st-late', NN.t('tq_q_late')] : done ? ['st-paid', NN.t('s_paid')] : r.trang_thai === 'arrived' ? ['st-arrived', NN.t('s_arrived')] : r.trang_thai === 'planned' ? ['st-planned', NN.t('tq_g_planned')] : ['st-running', NN.t('s_transit')];
      return `<div class="row"><div class="lab" data-doc="${esc(r.doc_no)}"><div><span class="code">${esc(r.doc_no.replace(/\/EPL$/, ''))}</span><small>${esc(r.so_xe)} · <span class="lo">${esc(r.khach || '')}</span></small></div><span class="pill ${pill[0]}">${esc(pill[1])}</span></div><div class="track">${segs}${td ? `<span class="now" style="left:${pos(td) + 100 / n / 2}%"></span>` : ''}</div></div>`;
    }).join('');
    box.innerHTML = hdr + body + `<div class="cap"><span><i style="background:repeating-linear-gradient(135deg,${c.steps[2]} 0 3px,transparent 3px 6px)"></i>${NN.h('tq_g_inprogress')}</span><span><i style="background:${c.bad};width:2px"></i>${NN.h('tq_g_today')}</span><span>${NN.h('tq_g_hint')}</span></div>`;
    box.querySelectorAll('.lab').forEach(el => el.addEventListener('click', () => EPL.di('theo-doi', { q: el.dataset.doc })));
  }

  EPL.modules['tong-quan'] = {
    async init(r) {
      root = r;
      // Mặc định: tháng này (giờ máy) nếu có phiếu; không có thì THÁNG GẦN NHẤT CÓ PHIẾU, kèm dòng báo.
      // Trước đây lấy tháng của phiếu mới nhất: một phiếu ghi nhầm ngày tương lai là màn mở ra tháng đó.
      // 09/10: kỳ chọn ở bộ lọc thời gian dùng chung (Năm · Tháng · Khoảng thời gian · nút nhanh); đổi kỳ là tải lại, bỏ dòng báo.
      BAO = null; GAN = null;
      const nay = EPL.thangNay();
      KY = KTG(r.querySelector('#tq-ky'), { cheDo: 'khoang', giaTri: KTG.cuaThang(nay), toiDaNgay: 366,
        khiDoi: () => { BAO = null; return tai(); } });
      ky = KY.giaTri;
      const g = await KTG.gan(ky, {});
      if (!g.co && g.gan) { BAO = { trong: nay, xem: g.gan }; KY.dat(KTG.cuaThang(g.gan)); ky = KY.giaTri; }
      r.querySelector('#tq-so-sanh').addEventListener('change', () => d && ve());
      r.querySelector('#tq-moi').addEventListener('click', () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      r.querySelector('#tq-xuat').addEventListener('click', () => EPL.di('theo-doi', { ...KTG.diaChi(ky), xuat: 1 }));
      r.querySelector('#tq-chu-y-all').addEventListener('click', () => EPL.di('theo-doi', KTG.diaChi(ky)));
      dangTai = (async () => { await napChart(); await taiThat(); })();
      await dangTai;
    },
    onLang() { if (d) ve(); },
    destroy() { Object.values(charts).forEach(c => c.destroy()); charts = {}; clearInterval(autoTimer); autoTimer = null; },
    /* Nút Excel trên thanh đầu trang: màn này vẽ bằng thẻ và biểu đồ, không có bảng — dựng sheet từ chính số liệu.
       Tiền để NGUYÊN Kíp (thẻ trên màn đọc theo triệu cho dễ nhìn). Bãi: không có ô tiền bán, không có tiền chi (A2). */
    async xuatExcel() {
      if (dangTai) { try { await dangTai; } catch (e) { /* tải hỏng thì xuất phần đang có */ } }
      if (!d) return [];
      const T = NN.t, L = (v) => EPL.oTien(v, 'LAK'), bai = laBai();
      const chiTieu = [
        [T(laKyThang() ? 'k_month_trips' : 'ktg_k_trips'), EPL.oSo(d.so_phieu, 0, T('trips'))],
        ...(bai ? [] : [[T('k_rev'), L(d.doanh_thu_lak)], [T('k_exp'), L(d.chi_lak)], [T('k_unpaid'), L(d.chua_thu_lak)]]),
        [T('k_tons'), EPL.oSo(d.tan_giao, 2, 't')],
        [T('s_dispatched'), d.dem.dispatched], [T('s_transit'), d.dem.transit], [T('s_arrived'), d.dem.arrived],
        ...(bai ? [] : [[T('dt_st_da_tao_so'), d.dem.invoiced], [T('s_paid'), d.dem.paid]]),
        ...(bai ? [] : Object.entries(d.chi_theo_muc || {}).map(([m, v]) => [`${T('k_exp')} · ${T('e_' + m)}`, L(v)])),
      ];
      const ds = [EPL.xuatSheet(T('xuat_chi_tieu'), [T('xuat_chi_tieu'), T('xuat_gia_tri')], chiTieu)];
      const ngay = (xh && xh.theo_ngay) || [];
      if (ngay.length && !bai) ds.push(EPL.xuatSheet(T('c_date'), [T('c_date'), T('tq_revenue') + ' (LAK)', T('tq_cost') + ' (LAK)'],
        ngay.map(x => [EPL.oNgay(x.ngay), L(x.doanh_thu_lak), L(x.chi_lak)]),
        { tong: [T('total'), L(ngay.reduce((a, x) => a + (x.doanh_thu_lak || 0), 0)), L(ngay.reduce((a, x) => a + (x.chi_lak || 0), 0))] }));
      const xe = (xh && xh.xe) || [];
      if (xe.length) ds.push(EPL.xuatSheet(T('tq_vehicle'), [T('tq_vehicle'), T('trips'), T('ton'), 'km', ...(bai ? [] : [T('tq_revenue') + ' (LAK)'])],
        xe.map(x => [x.so_xe, x.so_chuyen, EPL.oSo(x.tan, 2, 't'), EPL.oSo(x.km, 0, 'km'), ...(bai ? [] : [L(x.doanh_thu_lak)])])));
      const hh = ((xh && xh.hao_hut) || []).filter(x => x.can_cuoi != null);
      if (hh.length) ds.push(EPL.xuatSheet(T('tq_loss'), [T('doc_no'), T('w_origin'), T('w_dest'), T('tq_loss') + ' %'],
        hh.map(x => [x.doc_no, EPL.oSo(x.can_dau, 2, 't'), EPL.oSo(x.can_cuoi, 2, 't'),
          x.can_dau ? { v: (x.can_dau - x.can_cuoi) / x.can_dau, f: '0.00%' } : null])));
      return ds;
    },
  };
})();
