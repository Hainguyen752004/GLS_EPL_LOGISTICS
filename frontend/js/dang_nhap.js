/* Màn ĐĂNG NHẬP — sơ đồ tám bước của một chuyến hàng và khung chọn nhanh tài khoản (bản mẫu chủ dự án gửi 30/09).
 *
 * Bấm một bước trên sơ đồ → thẻ bên dưới nói việc của bước đó, vai nào làm; khung tài khoản bên phải chỉ còn tài khoản của
 * các vai đó ("Hiện tất cả" để bỏ lọc). Mở màn thì KHÔNG lọc: lối tắt demo phải hiện đủ mọi tài khoản.
 * Bước, nơi làm và vai theo ĐÚNG hệ thống (rà 01/10 — bản mẫu đặt sai: lập phiếu ở mỏ Kasi, quỹ chi tạm ứng ở gần cuối,
 * kế toán ở cửa khẩu / cảng, thiếu tài xế · tổ sửa chữa · thủ kho phụ tùng):
 *   · chuỗi từng mục theo bảng "Nhiệm Vụ" (services/phan_quyen.py): Bãi nhập → KT kiểm → KT ghi sổ → Quỹ chi;
 *   · tạm ứng chi TRƯỚC khi xe đi (máy chặn xuất phát khi chưa nhận tạm ứng);
 *   · mỗi vai có tài khoản phải nằm ở ít nhất một bước (bộ kiểm giao diện thử điều này).
 * Phạm vi 30/09: trang này chỉ lập phiếu ĐỀ NGHỊ; cấp dầu là bên kho, hoá đơn / thu tiền / công nợ là bên kế toán.
 * Không có số liệu "đang chờ" (chủ dự án chốt 30/09): trang này ai cũng mở được, chưa đăng nhập.
 * Danh sách tài khoản do js/chung.js tải (/api/tai-khoan-mau) rồi gọi EPL.lg.datDs(ds); bấm thẻ → EPL.lgVao().
 */
(function () {
  const { NN, esc } = EPL;
  const TD = () => window.EPL_TU_DIEN || {};
  // x, y: vị trí (%) trên sơ đồ; lab: nhãn phía trên (up) hay dưới (down). Tám bước đi LƯỢN HAI HÀNG (01/10): bước lẻ ở hàng
  // trên nhãn hướng lên, bước chẵn ở hàng dưới nhãn hướng xuống — xếp một đường dốc thì nhãn bên phải đè lên nhau.
  const BUOC = [
    { id: 'dispatch', x: 5, y: 30, lab: 'up', vai: ['yard'] },                         // Bãi Thà Bốc lập phiếu, in hai tờ đề nghị
    { id: 'fuel', x: 17, y: 58, lab: 'down', vai: ['depot'] },                         // thủ kho quét QR, cấp dầu
    { id: 'advance', x: 30, y: 30, lab: 'up', vai: ['expacct', 'cash'] },              // KT Chi phí ghi sổ mục IV → quỹ chi
    { id: 'road', x: 43, y: 58, lab: 'down', vai: ['driver', 'repair', 'parts', 'yard'] },     // xe chạy: báo cân, dầu, sự cố
    { id: 'deliver', x: 56, y: 30, lab: 'up', vai: ['driver', 'yard'] },               // ký giao nhận, Bãi xác nhận xe tới
    { id: 'check', x: 69, y: 58, lab: 'down', vai: ['acct', 'fuel', 'expacct', 'treasury', 'cash'] },   // kiểm, ghi sổ, chi I–VI
    { id: 'lock', x: 81, y: 30, lab: 'up', vai: ['acct', 'rev'] },                     // khoá phiếu → đề nghị thu → SO
    { id: 'boss', x: 95, y: 58, lab: 'down', vai: ['admin'] },
  ];
  const XE = { sau: 3, t: 0.5 };            // hình minh hoạ: một xe đang chạy, giữa bước 4 và bước 5
  // nhóm vai của khung tài khoản — người dùng nghĩ theo năm nhóm việc, không theo mười hai vai
  const NHOM_VAI = [
    { id: 'admin', khoa: 'lg_g_admin', vai: ['admin'] },
    { id: 'acct', khoa: 'lg_g_acct', vai: ['acct', 'expacct', 'rev'] },
    { id: 'wh', khoa: 'lg_g_wh', vai: ['yard', 'fuel', 'depot', 'parts', 'repair'] },
    { id: 'cash', khoa: 'lg_g_cash', vai: ['treasury', 'cash'] },
    { id: 'drv', khoa: 'lg_g_drv', vai: ['driver'] },
  ];
  const st = { buoc: BUOC[XE.sau].id, loc: false, ds: null, loi: '' };
  const $ = (id) => document.getElementById(id);
  const buoc = (id) => BUOC.find(b => b.id === id);
  const viTri = (id) => BUOC.findIndex(b => b.id === id);
  // chế độ VI + ລາວ: trên sơ đồ tên nơi viết tiếng Lào, tên bước viết tiếng Việt — nhãn vẫn chỉ hai dòng
  const chuLo = (k) => (TD()[k] || {}).lo || NN.t(k);
  const chuVi = (k) => (TD()[k] || {}).vi || NN.t(k);

  /* ---------------- đường cong qua các bước (Catmull-Rom → Bezier, hệ 0..100) ---------------- */
  function doan() {
    const ra = [];
    for (let i = 0; i < BUOC.length - 1; i++) {
      const p0 = BUOC[Math.max(0, i - 1)], p1 = BUOC[i], p2 = BUOC[i + 1], p3 = BUOC[Math.min(BUOC.length - 1, i + 2)];
      ra.push({ a: [p1.x, p1.y], c1: [p1.x + (p2.x - p0.x) / 6, p1.y + (p2.y - p0.y) / 6], c2: [p2.x - (p3.x - p1.x) / 6, p2.y - (p3.y - p1.y) / 6], b: [p2.x, p2.y] });
    }
    return ra;
  }
  function bez(g, u) {
    const m = 1 - u;
    return [m * m * m * g.a[0] + 3 * m * m * u * g.c1[0] + 3 * m * u * u * g.c2[0] + u * u * u * g.b[0],
      m * m * m * g.a[1] + 3 * m * m * u * g.c1[1] + 3 * m * u * u * g.c2[1] + u * u * u * g.b[1]];
  }
  function chia(g, u) {
    const l = (p, q, k) => [p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k];
    const a1 = l(g.a, g.c1, u), b1 = l(g.c1, g.c2, u), c1 = l(g.c2, g.b, u), a2 = l(a1, b1, u), b2 = l(b1, c1, u), m = l(a2, b2, u);
    return [{ a: g.a, c1: a1, c2: a2, b: m }, { a: m, c1: b2, c2: c1, b: g.b }];
  }
  function duong(ds) {
    if (!ds.length) return '';
    const f = (p) => p[0].toFixed(2) + ' ' + p[1].toFixed(2);
    return 'M' + f(ds[0].a) + ds.map(g => ' C' + f(g.c1) + ', ' + f(g.c2) + ', ' + f(g.b)).join('');
  }
  function veDuong() {
    const ds = doan(), k = Math.min(XE.sau, ds.length - 1), hai = chia(ds[k], XE.t);
    $('lgDuongXong').setAttribute('d', duong(ds.slice(0, k).concat([hai[0]])));
    $('lgDuongChua').setAttribute('d', duong([hai[1]].concat(ds.slice(k + 1))));
    const p = bez(ds[k], XE.t), xe = $('lgXe');
    xe.style.left = p[0] + '%'; xe.style.top = p[1] + '%';
  }

  /* ---------------- các bước và thẻ bước ---------------- */
  const tenVai = (b) => b.vai.map(v => 'r_' + v);
  function veBuoc() {
    $('lgBuoc').innerHTML = BUOC.map((b, i) => {
      const chon = st.buoc === b.id, hai = NN.lang === 'both';
      return '<button type="button" class="node is-' + b.lab + (b.x > 88 ? ' is-left' : '') + (i > XE.sau ? ' is-todo' : '') + '" role="tab" data-buoc="' + b.id + '" aria-selected="' + chon + '"' +
        ' style="left:' + b.x + '%;top:' + b.y + '%" title="' + esc(NN.t('lg2_s_' + b.id) + ': ' + tenVai(b).map(k => NN.t(k)).join(', ')) + '">' +
        '<span class="dot">' + (i + 1) + '</span><span class="txt"><b lang="lo">' + esc(hai ? chuLo('lg2_p_' + b.id) : NN.t('lg2_p_' + b.id)) + '</b>' +
        '<small>' + esc(hai ? chuVi('lg2_s_' + b.id) : NN.t('lg2_s_' + b.id)) + '</small></span></button>';
    }).join('');
  }
  function veThe() {
    const b = buoc(st.buoc), i = viTri(st.buoc);
    $('lgThe').innerHTML =
      '<div class="sc-head"><span class="sc-num">' + NN.h('lg2_buoc', { i: i + 1, n: BUOC.length }) + '</span><h3>' + NN.h('lg2_s_' + b.id) + '</h3><span class="sc-place" lang="lo">' + esc(NN.t('lg2_p_' + b.id)) + '</span></div>' +
      '<div><span class="sc-label">' + NN.h('lg2_viec') + '</span><ul><li>' + NN.h('lg2_t_' + b.id + '_1') + '</li><li>' + NN.h('lg2_t_' + b.id + '_2') + '</li></ul></div>' +
      '<div><span class="sc-label">' + NN.h('lg2_ai_lam') + '</span><div class="roles">' + tenVai(b).map(k => '<span class="role-tag">' + NN.h(k) + '</span>').join('') + '</div></div>' +
      '<p class="hint"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>' + NN.h('lg2_chon_tk') + '</p>';
  }

  /* ---------------- khung tài khoản ---------------- */
  function veTaiKhoan() {
    const o = $('acctList'), tieuDe = $('lgNhanh');
    if (!o) return;
    const b = buoc(st.buoc), vai = st.loc && b ? b.vai : null;
    tieuDe.innerHTML = vai
      ? NN.h('lg2_tk_cho_buoc', { i: viTri(st.buoc) + 1 }) + ' <b>' + NN.h('lg2_s_' + b.id) + '</b><button type="button" id="lgHienHet">' + NN.h('lg2_hien_het') + '</button>'
      : NN.h('quick_pick');
    if (st.loi) { o.innerHTML = '<p class="none">' + esc(st.loi) + '</p>'; return; }
    if (!st.ds) { o.innerHTML = ''; return; }
    const dang = ($('lgU').value || '').trim();
    const html = NHOM_VAI.map(n => {
      // máy chủ trả theo chữ cái của vai — xếp lại theo thứ tự vai trong nhóm: vai chính của nhóm đứng trước
      const trong = st.ds.filter(a => n.vai.includes(a.role) && (!vai || vai.includes(a.role)))
        .sort((a, c) => n.vai.indexOf(a.role) - n.vai.indexOf(c.role) || a.username.localeCompare(c.username));
      if (!trong.length) return '';
      return '<div class="acc-group"><h4>' + NN.h(n.khoa) + '</h4><ul>' + trong.map(a =>
        '<li><button type="button" class="acc' + (a.username === dang ? ' is-picked' : '') + '" data-u="' + esc(a.username) + '" title="' + esc(a.username + ' · ' + NN.t('r_' + a.role)) + '">' +
          '<span class="av">' + esc(a.avatar || String(a.full_name || a.username).slice(0, 2).toUpperCase()) + '</span>' +
          '<span class="tt"><span class="nm" lang="lo">' + esc(a.full_name) + '</span><span class="ds"><span class="u">' + esc(a.username) + '</span> · ' + esc(NN.t('r_' + a.role)) + '</span></span>' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button></li>').join('') + '</ul></div>';
    }).join('');
    o.innerHTML = html || '<p class="none">' + NN.h('lg2_khong_tk') + '</p>';
  }
  function veVai() {
    const chip = $('lgVai'); if (!chip) return;
    const u = ($('lgU').value || '').trim(), a = (st.ds || []).find(x => x.username === u);
    chip.hidden = !a;
    if (a) chip.innerHTML = NN.h('lg2_dang_vao_vai') + ': <b>' + NN.h('r_' + a.role) + '</b>';
  }
  function ve() {
    if (!$('lgBuoc')) return;
    $('login').classList.toggle('is-hai', NN.lang === 'both');     // VI + ລາວ: chữ hai dòng, css thu gọn cột trái
    veBuoc(); veThe(); veTaiKhoan(); veVai();
  }
  function chonBuoc(id, focus) {
    st.buoc = id; st.loc = true; ve();
    if (focus) { const n = document.querySelector('#lgBuoc [data-buoc="' + id + '"]'); if (n) n.focus(); }
  }

  EPL.lg = {
    datDs(ds) { st.ds = ds || []; st.loi = ''; veTaiKhoan(); veVai(); },
    loi(chu) { st.loi = chu || ''; veTaiKhoan(); },
    ve,
  };
  EPL.khiDoiNN = (EPL.khiDoiNN || []).concat([ve]);

  document.addEventListener('DOMContentLoaded', () => {
    const goc = $('login'); if (!goc) return;
    goc.addEventListener('click', (e) => {
      const n = e.target.closest('[data-buoc]'); if (n) { chonBuoc(n.dataset.buoc); return; }
      if (e.target.closest('#lgHienHet')) { st.loc = false; veTaiKhoan(); return; }
      const a = e.target.closest('#acctList [data-u]');
      if (a) {
        // bấm thẻ là vào thẳng (lối tắt demo): điền tên + mật khẩu demo rồi đăng nhập
        $('lgU').value = a.dataset.u; $('lgP').value = '1234';
        document.querySelectorAll('#acctList .acc').forEach(x => x.classList.toggle('is-picked', x === a));
        veVai(); EPL.lgVao();
      }
    });
    goc.addEventListener('keydown', (e) => {
      if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && e.target.dataset && e.target.dataset.buoc) {
        e.preventDefault();
        const i = viTri(e.target.dataset.buoc), sau = BUOC[(i + (e.key === 'ArrowRight' ? 1 : BUOC.length - 1)) % BUOC.length];
        chonBuoc(sau.id, true);
      }
    });
    $('lgU').addEventListener('input', veVai);
    veDuong(); ve();
  });
})();
