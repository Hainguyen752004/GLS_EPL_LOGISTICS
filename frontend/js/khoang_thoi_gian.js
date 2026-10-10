/* EPL Lào — BỘ LỌC THỜI GIAN dùng chung (09/10/2026).
 *
 * Anh Khampla (kế toán bên Lào) gửi ảnh phần mềm kế toán của anh ấy và muốn lọc kiểu đó: hàng «Năm» (các năm + «Theo năm»),
 * hàng «Tháng» (1 … 12 + «Theo tháng»), «Khoảng thời gian: [từ ngày] Đến [đến ngày] [Tìm kiếm]» và nút nhanh Hôm qua · Hôm nay ·
 * Tuần này · Tháng này · Năm này. Nút đang chọn tô màu chủ đạo. Thay ô chọn tháng ở các màn danh sách / báo cáo.
 *
 *   const k = EPL.khoangThoiGian(holder, { cheDo, giaTri, khiDoi, choTrong, toiDaNgay })
 *     cheDo 'khoang' — đủ ba hàng; giá trị {tu, den} (YYYY-MM-DD). Bấm năm = cả năm đó · bấm tháng = tháng đó của năm đang chọn ·
 *                      «Theo năm» = cả năm đang chọn · «Theo tháng» = tháng chọn gần nhất của năm đó · nút nhanh tự điền ·
 *                      «Tìm kiếm» (hay Enter trong ô ngày) áp hai ô ngày. choTrong: hai ô trống + Tìm kiếm = mọi ngày ({tu:'', den:''}).
 *                      toiDaNgay: khoảng dài hơn thì báo, không áp (báo cáo đệm theo từng ngày — máy chủ cũng chặn).
 *     cheDo 'thang'  — màn nghiệp vụ theo KỲ THÁNG (tất toán, tiền chuyến & nước, thẻ cao tốc): chỉ hàng Năm + hàng Tháng;
 *                      giá trị {thang: 'YYYY-MM'}; bấm năm giữ số tháng đang chọn.
 *     khiDoi(giaTri) — người dùng đổi (bấm). Module tự đặt bằng k.dat(giaTri) thì KHÔNG gọi.
 *   k.giaTri · k.dat(giaTri) · k.nhan(gon) · k.laThang() ('YYYY-MM' khi đang xem trọn một tháng) · k.ve() (vẽ lại)
 * Hàm phụ (không cần bộ lọc): EPL.khoangThoiGian.cuaThang('YYYY-MM') → {tu, den} · .laThang(gt) · .nhan(gt, gon) ·
 *   .thamSo(gt, p) — gắn vào URLSearchParams: trọn một tháng → `thang` (đường cũ, Web C# cùng hiểu), còn lại `tu` + `den` ·
 *   .diaChi(gt) (tham số cho EPL.di) · .tuDiaChi(t) (đọc lại tu/den hoặc thang) · .gan(gt, loc) (tháng gần nhất có phiếu).
 * Hai ô ngày là <input type="date"> — js/lich.js tự gắn lịch chọn ngày. Chữ qua NN (khoá ktg_* trong js/ngon_ngu.js). Kiểu ở
 * css/khoang_thoi_gian.css. Xuất Excel / PDF (js/xuat.js boLoc) đọc khoảng đang xem từ data-xuat-loc của khung.
 */
(function () {
  'use strict';
  const EPL = window.EPL;
  const { NN, esc } = EPL;

  /* ================================================================ Ngày — chuỗi YYYY-MM-DD theo GIỜ MÁY (như EPL.homNay) */
  const hai = (n) => String(n).padStart(2, '0');
  const iso = (d) => d.getFullYear() + '-' + hai(d.getMonth() + 1) + '-' + hai(d.getDate());
  const ngay = (y, m, d) => iso(new Date(y, m - 1, d));          // tự tràn: (y, m + 1, 0) = ngày cuối tháng m
  const RE_NGAY = /^\d{4}-\d{2}-\d{2}$/, RE_THANG = /^\d{4}-(0[1-9]|1[0-2])$/;
  const hopLe = (s) => RE_NGAY.test(s || '') && ngay(+s.slice(0, 4), +s.slice(5, 7), +s.slice(8, 10)) === s;
  const cuaThang = (th) => { const y = +th.slice(0, 4), m = +th.slice(5, 7); return { tu: ngay(y, m, 1), den: ngay(y, m + 1, 0) }; };
  const cuaNam = (y) => ({ tu: y + '-01-01', den: y + '-12-31' });
  const soNgay = (s) => Math.round(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 864e5);
  const dmy = (s) => s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4);
  const mY = (th) => th.slice(5, 7) + '/' + th.slice(0, 4);
  const soThang = (th) => +th.slice(0, 4) * 12 + +th.slice(5, 7);

  /** 'YYYY-MM' khi `gt` là trọn MỘT tháng ({thang} hoặc {tu: ngày 1, den: ngày cuối}); không thì null. */
  function laThang(gt) {
    if (!gt) return null;
    if (gt.thang) return RE_THANG.test(gt.thang) ? gt.thang : null;
    if (!hopLe(gt.tu) || !hopLe(gt.den)) return null;
    const th = gt.tu.slice(0, 7), k = cuaThang(th);
    return k.tu === gt.tu && k.den === gt.den ? th : null;
  }
  /** Năm (số) khi `gt` là trọn một năm dương lịch; không thì null. */
  function laNam(gt) {
    if (!gt || !hopLe(gt.tu)) return null;
    const y = gt.tu.slice(0, 4);
    return gt.tu === y + '-01-01' && gt.den === y + '-12-31' ? +y : null;
  }
  /** Chữ của kỳ: «Tháng 09/2026» · «Năm 2026» · «05/10/2026» · «01/09/2026 – 15/09/2026». gon: bỏ chữ Tháng / Năm.
   *  Chế độ VI + ລາວ: bản Việt (một dòng — chỗ dùng là câu đã có bản Lào riêng hoặc ô hẹp). */
  function nhan(gt, gon) {
    const th = laThang(gt);
    if (th) return gon ? mY(th) : NN.t('ktg_nhan_thang', { thang: mY(th) }).split(' / ')[0];
    const y = laNam(gt);
    if (y) return gon ? String(y) : NN.t('ktg_nhan_nam', { nam: y }).split(' / ')[0];
    if (!gt || !hopLe(gt.tu) || !hopLe(gt.den)) return '';
    return gt.tu === gt.den ? dmy(gt.tu) : dmy(gt.tu) + ' – ' + dmy(gt.den);
  }
  /** Gắn kỳ vào tham số gọi API: trọn một tháng → `thang` (đường cũ, máy chủ cũ và Web C# cùng hiểu), còn lại `tu` + `den`. */
  function thamSo(gt, p) {
    p = p || new URLSearchParams();
    const th = laThang(gt);
    if (th) p.set('thang', th);
    else if (gt && hopLe(gt.tu) && hopLe(gt.den)) { p.set('tu', gt.tu); p.set('den', gt.den); }
    return p;
  }
  const diaChi = (gt) => Object.fromEntries(thamSo(gt));
  /** Kỳ ghi trên địa chỉ (?tu=&den= hoặc ?thang=) → giá trị khoảng; không có / sai → null. */
  function tuDiaChi(t) {
    t = t || {};
    if (hopLe(t.tu) && hopLe(t.den) && t.tu <= t.den) return { tu: t.tu, den: t.den };
    if (RE_THANG.test(t.thang || '')) return cuaThang(t.thang);
    return null;
  }
  /** Khoảng của nút nhanh, theo GIỜ MÁY. Tuần bắt đầu thứ Hai (như lịch js/lich.js). */
  function nhanh(ma) {
    const d = new Date(), y = d.getFullYear(), m = d.getMonth() + 1, n = d.getDate();
    if (ma === 'hom_qua') { const s = ngay(y, m, n - 1); return { tu: s, den: s }; }
    if (ma === 'hom_nay') { const s = ngay(y, m, n); return { tu: s, den: s }; }
    if (ma === 'tuan_nay') { const t = (d.getDay() + 6) % 7; return { tu: ngay(y, m, n - t), den: ngay(y, m, n - t + 6) }; }
    if (ma === 'thang_nay') return cuaThang(y + '-' + hai(m));
    return cuaNam(y);
  }
  const NHANH = ['hom_qua', 'hom_nay', 'tuan_nay', 'thang_nay', 'nam_nay'];

  /** Kỳ trống thì THÁNG GẦN NHẤT có phiếu (cùng bộ lọc `loc` của /api/trips) — bản chung của các hàm thangGan từng màn (01/10).
   *  Hỏi hai dòng: phiếu mới nhất tới ngày cuối kỳ, phiếu cũ nhất từ ngày đầu kỳ — không tải cả năm. Cách đều thì lấy phía trước.
   *  → {co: kỳ có phiếu?, gan: 'YYYY-MM' | null}. Kỳ trọn một tháng: y như thangGan cũ. */
  async function gan(gt, loc) {
    if (!gt || !hopLe(gt.tu) || !hopLe(gt.den)) return { co: true, gan: null };
    const hoi = (them) => {
      const p = new URLSearchParams(loc || {});
      ['thang', 'tu', 'den', 'trang'].forEach(k => p.delete(k));      // bộ lọc khác giữ, kỳ thì thay bằng hai mép
      p.set('co', '1');
      Object.entries(them).forEach(([k, v]) => p.set(k, v));
      return EPL.API.get('/api/trips?' + p).then(d => (d && d[0] && d[0].doc_date ? d[0].doc_date.slice(0, 10) : null), () => null);
    };
    const [truoc, sau] = await Promise.all([hoi({ den: gt.den }), hoi({ tu: gt.tu, sap: 'cu' })]);
    if ((truoc && truoc >= gt.tu) || (sau && sau <= gt.den)) return { co: true, gan: null };
    const t = truoc && truoc.slice(0, 7), s = sau && sau.slice(0, 7);
    if (!t || !s) return { co: false, gan: t || s || null };
    return { co: false, gan: soThang(s) - soThang(gt.den.slice(0, 7)) < soThang(gt.tu.slice(0, 7)) - soThang(t) ? s : t };
  }

  /* ================================================================ Bộ lọc */
  const SONG = new Set();            // bộ đang trên màn — đổi ngôn ngữ thì vẽ lại chữ; bộ đã bị tháo khỏi trang thì bỏ
  EPL.khiDoiNN = (EPL.khiDoiNN || []).concat([() => SONG.forEach(k => (k.holder.isConnected ? k.ve() : SONG.delete(k)))]);

  function khoangThoiGian(holder, o) {
    o = o || {};
    const cheDo = o.cheDo === 'thang' ? 'thang' : 'khoang';
    const nam0 = new Date().getFullYear();
    let gt, nam, thangNho;

    /** Chuẩn hoá giá trị đưa vào (module / địa chỉ). Sai thì về tháng này (chế độ khoang có choTrong: trống). */
    function chuan(v) {
      if (cheDo === 'thang') {
        const th = laThang(v) || (v && hopLe(v.tu) ? v.tu.slice(0, 7) : null) || EPL.thangNay();
        return { thang: th };
      }
      if (v && v.thang && RE_THANG.test(v.thang)) return cuaThang(v.thang);
      if (v && hopLe(v.tu) && hopLe(v.den) && v.tu <= v.den) return { tu: v.tu, den: v.den };
      if (o.choTrong && v && !v.tu && !v.den) return { tu: '', den: '' };
      return cuaThang(EPL.thangNay());
    }
    /** Năm / tháng đang chọn theo giá trị: năm của ngày đầu kỳ; tháng nhớ lại khi giá trị là trọn một tháng. */
    function theoGiaTri() {
      const th = laThang(gt) || (gt.thang || null);
      const dau = cheDo === 'thang' ? gt.thang : gt.tu;
      if (dau) nam = +dau.slice(0, 4);
      else if (!nam) nam = nam0;
      if (th) thangNho = +th.slice(5, 7);
      else if (!thangNho) thangNho = nam === nam0 ? new Date().getMonth() + 1 : 1;
    }

    const nut = (loai, v, chu, title) => `<button type="button" class="ktg-b" data-ktg="${loai}" data-v="${esc(v)}" aria-pressed="false"${
      title ? ` title="${esc(title)}"` : ''}>${chu}</button>`;
    function cacNam() {
      const ds = [];
      for (let y = nam0 - 4; y <= nam0 + 1; y++) ds.push(y);       // 4 năm trước → năm sau (như ảnh phần mềm kế toán)
      if (!ds.includes(nam)) ds.push(nam);                           // kỳ ở năm xa hơn (địa chỉ cũ): vẫn có nút của nó
      return ds.sort((a, b) => a - b);
    }
    function veNam() {
      const o2 = holder.querySelector('.ktg-day-nam');
      o2.innerHTML = cacNam().map(y => nut('nam', y, y)).join('');
      o2.dataset.ds = cacNam().join(',');
    }

    /** Dựng khung một lần (và lúc đổi ngôn ngữ). Bấm chỉ cập nhật lớp / giá trị — không vẽ lại, tiêu điểm phím giữ nguyên chỗ. */
    function ve() {
      holder.classList.add('ktg', 'ktg--' + cheDo);
      const khoang = cheDo === 'khoang';
      holder.innerHTML = `
        <div class="ktg-nhom ktg-nam" role="group" aria-label="${esc(NN.t('ktg_nam'))}">
          <span class="ktg-nhan">${NN.h('ktg_nam')}</span><span class="ktg-day ktg-day-nam"></span>
          ${khoang ? `<button type="button" class="ktg-b ktg-theo" data-ktg="theo_nam" aria-pressed="false">${NN.h('ktg_theo_nam')}</button>` : ''}</div>
        <div class="ktg-nhom ktg-thang" role="group" aria-label="${esc(NN.t('month'))}">
          <span class="ktg-nhan">${NN.h('month')}</span><span class="ktg-day">${
            Array.from({ length: 12 }, (_, i) => nut('thang', i + 1, i + 1)).join('')}</span>
          ${khoang ? `<button type="button" class="ktg-b ktg-theo" data-ktg="theo_thang" aria-pressed="false">${NN.h('ktg_theo_thang')}</button>` : ''}</div>
        ${khoang ? `<div class="ktg-nhom ktg-khoang" role="group" aria-label="${esc(NN.t('ktg_khoang'))}">
          <span class="ktg-nhan">${NN.h('ktg_khoang')}</span>
          <span class="ktg-o"><input type="date" data-ktg-o="tu" aria-label="${esc(NN.t('ktg_tu_ngay'))}"></span>
          <span class="ktg-den">${NN.h('ktg_den')}</span>
          <span class="ktg-o"><input type="date" data-ktg-o="den" aria-label="${esc(NN.t('ktg_den_ngay'))}"></span>
          <button type="button" class="ktg-b ktg-tim" data-ktg="tim">${NN.h('ktg_tim')}</button></div>
        <div class="ktg-nhom ktg-nhanh" role="group">${NHANH.map(m => nut(m, m, NN.h('ktg_' + m))).join('')}</div>` : ''}`;
      veNam();
      capNhat();
    }

    /** Tô nút theo giá trị, điền hai ô ngày, ghi dòng bộ lọc cho tệp xuất. */
    function capNhat() {
      if (holder.querySelector('.ktg-day-nam').dataset.ds !== cacNam().join(',')) veNam();
      const th = laThang(gt), ny = laNam(gt);
      const trongNam = (y) => (cheDo === 'thang' ? +gt.thang.slice(0, 4) === y
        : !!gt.tu && +gt.tu.slice(0, 4) === y && +gt.den.slice(0, 4) === y);
      const bat = (b, on) => { b.classList.toggle('on', !!on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); };
      holder.querySelectorAll('[data-ktg="nam"]').forEach(b => bat(b, trongNam(+b.dataset.v)));
      holder.querySelectorAll('[data-ktg="thang"]').forEach(b => {
        const v = nam + '-' + hai(+b.dataset.v);
        bat(b, th === v);
        b.title = NN.t('ktg_nhan_thang', { thang: mY(v) });
      });
      const tn = holder.querySelector('[data-ktg="theo_nam"]'); if (tn) bat(tn, ny);
      const tt = holder.querySelector('[data-ktg="theo_thang"]'); if (tt) bat(tt, th);
      NHANH.forEach(m => {
        const b = holder.querySelector(`[data-ktg="${m}"]`); if (!b) return;
        const k = nhanh(m); bat(b, gt.tu === k.tu && gt.den === k.den);
      });
      const oTu = holder.querySelector('[data-ktg-o="tu"]'), oDen = holder.querySelector('[data-ktg-o="den"]');
      if (oTu) { oTu.value = gt.tu || ''; oDen.value = gt.den || ''; }
      const chu = nhan(gt, true);
      holder.dataset.xuatLoc = chu ? (cheDo === 'thang' ? NN.t('month') : NN.t('ktg_khoang')) + ': ' + chu : '';
    }

    /** Người dùng đổi kỳ: cập nhật rồi báo module (kể cả bấm lại đúng kỳ đang xem — coi như tải lại). */
    function doi(moi) {
      gt = chuan(moi); theoGiaTri(); capNhat();
      if (o.khiDoi) {
        try { const r = o.khiDoi(api.giaTri); if (r && typeof r.catch === 'function') r.catch(EPL.baoLoi); } catch (e) { EPL.baoLoi(e); }
      }
    }
    /** «Tìm kiếm»: áp hai ô ngày (đã kiểm: đủ hai ngày, từ ≤ đến, không quá toiDaNgay). */
    function apNgay() {
      const tu = (holder.querySelector('[data-ktg-o="tu"]') || {}).value || '', den = (holder.querySelector('[data-ktg-o="den"]') || {}).value || '';
      if (!tu && !den && o.choTrong) return doi({ tu: '', den: '' });
      if (!hopLe(tu) || !hopLe(den)) return EPL.toast(NN.t('ktg_loi_thieu'), 'loi');
      if (tu > den) return EPL.toast(NN.t('ktg_loi_khoang'), 'loi');
      if (o.toiDaNgay && soNgay(den) - soNgay(tu) + 1 > o.toiDaNgay) return EPL.toast(NN.t('ktg_loi_dai', { n: o.toiDaNgay }), 'loi');
      doi({ tu, den });
    }
    /** Bấm năm / tháng / nút nhanh trong chế độ khoang: khoảng quá toiDaNgay thì báo (nút sẵn có không bao giờ quá một năm). */
    function chon(moi) {
      if (o.toiDaNgay && moi.tu && soNgay(moi.den) - soNgay(moi.tu) + 1 > o.toiDaNgay) return EPL.toast(NN.t('ktg_loi_dai', { n: o.toiDaNgay }), 'loi');
      doi(moi);
    }

    holder.addEventListener('click', (e) => {
      const b = e.target.closest('[data-ktg]');
      if (!b || !holder.contains(b)) return;
      const loai = b.dataset.ktg;
      if (loai === 'nam') {
        nam = +b.dataset.v;
        if (cheDo === 'thang') doi({ thang: nam + '-' + hai(thangNho) }); else chon(cuaNam(nam));
      } else if (loai === 'thang') {
        thangNho = +b.dataset.v;
        const th = nam + '-' + hai(thangNho);
        if (cheDo === 'thang') doi({ thang: th }); else chon(cuaThang(th));
      } else if (loai === 'theo_nam') chon(cuaNam(nam));
      else if (loai === 'theo_thang') chon(cuaThang(nam + '-' + hai(thangNho)));
      else if (loai === 'tim') apNgay();
      else if (NHANH.includes(loai)) chon(nhanh(loai));
    });
    // Enter trong ô ngày = Tìm kiếm. js/lich.js ghi chữ vừa gõ vào ô gốc trước (bộ nghe của nó gắn ở chính ô hiện); lịch đang
    // mở (aria-expanded) thì Enter là chọn ngày trong lịch — không áp.
    holder.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || !e.target.closest || !e.target.closest('.ktg-o')) return;
      if (e.target.getAttribute('aria-expanded') === 'true') return;
      setTimeout(apNgay, 0);
    });

    const api = {
      holder,
      get giaTri() { return cheDo === 'thang' ? { thang: gt.thang } : { tu: gt.tu, den: gt.den }; },
      /** Module tự đặt kỳ (tự sang tháng gần nhất có phiếu, mở từ địa chỉ…) — không gọi khiDoi. */
      dat(v) { gt = chuan(v); theoGiaTri(); capNhat(); return api; },
      nhan: (gon) => nhan(gt, gon),
      laThang: () => laThang(gt),
      ve,
    };
    gt = chuan(o.giaTri); theoGiaTri();
    ve();
    // màn vẽ lại cả khung mỗi lần đổi (tab Chuyến màn Khách hàng) thì mỗi lần một bộ mới — bỏ ngay bộ cũ đã rời trang, đừng giữ cây DOM chết
    SONG.forEach(k => { if (!k.holder.isConnected) SONG.delete(k); });
    SONG.add(api);
    holder._ktg = api;                 // bộ kiểm giao diện (kiem/thu_giao_dien.js, ra_tong_quan.js) đọc kỳ đang xem từ khung
    return api;
  }

  Object.assign(khoangThoiGian, { cuaThang, cuaNam, laThang, laNam, nhan, thamSo, diaChi, tuDiaChi, gan, hopLe });
  EPL.khoangThoiGian = khoangThoiGian;
})();
