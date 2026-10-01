/* EPL Lào — BỘ CHỌN NGÀY / THÁNG dùng chung (01/10/2026).
 *
 * Chủ dự án: ô "Tháng" là <select> liệt kê "09/2026"… trông lạ; ô ngày của trình duyệt hiện mm/dd/yyyy kiểu Mỹ, lịch bật
 * lên theo ngôn ngữ của máy chứ không theo Việt / Lào. Muốn một lịch bấm chọn kiểu "Date Picker" của Windows: đầu lịch ghi
 * ngày đang chọn bằng chữ, hai tháng cạnh nhau, nút lên / xuống đổi tháng, bấm tiêu đề để chọn nhanh tháng / năm,
 * nút Hôm nay · Xoá · OK. Hôm nay tô nền, ngày đang chọn có khung (như Windows).
 *
 * TỰ GẮN — module KHÔNG phải sửa gì:
 *   · <input type="date">: ô gốc ở lại làm NGUỒN GIÁ TRỊ (yyyy-mm-dd, id, bộ nghe sự kiện… y nguyên) nhưng ẩn đi. Cạnh nó
 *     là ô hiện dd/mm/yyyy (gõ tay được) + nút lịch. Chọn xong: gán .value cho ô gốc rồi bắn input + change (bubbles).
 *     Ô gốc disabled / readonly thì ô hiện chỉ xem.
 *   · <select> mà mọi option.value đều dạng YYYY-MM (ô "Tháng" do EPL.doiOThang dựng, hay module tự dựng như màn tài xế):
 *     select ẩn đi nhưng VẪN CÒN trong trang (xuất Excel đọc bộ lọc từ nó), thay bằng nút "Tháng 09/2026" mở lưới 12 tháng.
 *     Tháng không có trong danh sách thì mờ, không chọn được. Option value "" ("Tất cả các tháng") thành một nút riêng.
 *   · MutationObserver: module vẽ lại thì tự gắn ô mới; đổi disabled / hidden / class… của ô gốc thì ô hiện đổi theo.
 *     Module gán .value bằng mã (không có sự kiện nào): vá setter value / selectedIndex ở prototype → ô hiện cập nhật ngay.
 *   · Đổi ngôn ngữ (EPL.khiDoiNN): vẽ lại chữ.
 *   · Ô gốc do module TỰ ẨN làm lịch phụ (data-native-for / aria-hidden="true" — hộp thoại màn Khách hàng): không dựng ô
 *     hiện, chỉ thay showPicker() của nó bằng lịch này.
 *   · Ô nào muốn giữ kiểu gốc của trình duyệt: thêm data-lich="khong".
 * Kiểu ở css/lich.css. Chữ giao diện lấy từ từ điển chung (khoá lich_*), thiếu khoá thì dùng bảng CHU bên dưới.
 */
(function () {
  'use strict';
  if (window.EPL_LICH) return;
  const EPL = window.EPL || (window.EPL = { modules: {} });

  /* ================================================================ Tên tháng / thứ theo ngôn ngữ (tuần bắt đầu thứ Hai) */
  const THANG_LO = ['ມັງກອນ', 'ກຸມພາ', 'ມີນາ', 'ເມສາ', 'ພຶດສະພາ', 'ມິຖຸນາ', 'ກໍລະກົດ', 'ສິງຫາ', 'ກັນຍາ', 'ຕຸລາ', 'ພະຈິກ', 'ທັນວາ'];
  const THANG_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const LOCALE = {
    vi: {
      thu: ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'],
      thuNgan: ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'],
      thang: (m) => 'Tháng ' + m,                                      // ô trong lưới 12 tháng
      thangNam: (m, y) => 'Tháng ' + m + ' năm ' + y,                  // tiêu đề một tháng
      dayDu: (y, m, d, thu) => thu + ', ' + d + ' tháng ' + m + ' năm ' + y,
      nut: 'Tháng',                                                     // chữ đứng trước "09/2026" trên nút chọn tháng
    },
    lo: {
      thu: ['ວັນຈັນ', 'ວັນອັງຄານ', 'ວັນພຸດ', 'ວັນພະຫັດ', 'ວັນສຸກ', 'ວັນເສົາ', 'ວັນອາທິດ'],
      thuNgan: ['ຈ', 'ອ', 'ພ', 'ພຫ', 'ສຸ', 'ສ', 'ອາ'],
      thang: (m) => THANG_LO[m - 1],
      thangNam: (m, y) => THANG_LO[m - 1] + ' ' + y,
      dayDu: (y, m, d, thu) => thu + ', ' + d + ' ' + THANG_LO[m - 1] + ' ' + y,
      nut: 'ເດືອນ',
    },
    en: {
      thu: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      thuNgan: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
      thang: (m) => THANG_EN[m - 1].slice(0, 3),
      thangNam: (m, y) => THANG_EN[m - 1] + ' ' + y,
      dayDu: (y, m, d, thu) => thu + ', ' + d + ' ' + THANG_EN[m - 1] + ' ' + y,   // ngày trước tháng, khớp dd/mm/yyyy
      nut: '',
    },
  };

  /* Chữ giao diện — từ điển chung (js/ngon_ngu.js) trước; chưa có khoá thì dùng bảng dự phòng này (bản Lào thật). */
  const CHU = {
    lich_hom_nay: { vi: 'Hôm nay', lo: 'ມື້ນີ້', en: 'Today' },
    lich_hom_qua: { vi: 'Hôm qua', lo: 'ມື້ວານນີ້', en: 'Yesterday' },
    lich_ngay_mai: { vi: 'Ngày mai', lo: 'ມື້ອື່ນ', en: 'Tomorrow' },
    lich_truoc: { vi: '{n} ngày trước hôm nay', lo: '{n} ວັນກ່ອນມື້ນີ້', en: '{n} days before today' },
    lich_sau: { vi: '{n} ngày sau hôm nay', lo: '{n} ວັນຫຼັງມື້ນີ້', en: '{n} days after today' },
    lich_xoa: { vi: 'Xoá', lo: 'ລຶບ', en: 'Clear' },
    lich_ok: { vi: 'OK', lo: 'ຕົກລົງ', en: 'OK' },
    lich_chua_chon: { vi: 'Chưa chọn ngày', lo: 'ຍັງບໍ່ໄດ້ເລືອກວັນທີ', en: 'No date selected' },
    lich_mo: { vi: 'Mở lịch', lo: 'ເປີດປະຕິທິນ', en: 'Open calendar' },
    lich_thang_truoc: { vi: 'Tháng trước', lo: 'ເດືອນກ່ອນ', en: 'Previous month' },
    lich_thang_sau: { vi: 'Tháng sau', lo: 'ເດືອນຖັດໄປ', en: 'Next month' },
    lich_nam_truoc: { vi: 'Năm trước', lo: 'ປີກ່ອນ', en: 'Previous year' },
    lich_nam_sau: { vi: 'Năm sau', lo: 'ປີຖັດໄປ', en: 'Next year' },
    lich_muoi_nam_truoc: { vi: '10 năm trước', lo: '10 ປີກ່ອນ', en: 'Previous 10 years' },
    lich_muoi_nam_sau: { vi: '10 năm sau', lo: '10 ປີຖັດໄປ', en: 'Next 10 years' },
    lich_chon_thang: { vi: 'Chọn tháng', lo: 'ເລືອກເດືອນ', en: 'Choose month' },
    lich_chon_nam: { vi: 'Chọn năm', lo: 'ເລືອກປີ', en: 'Choose year' },
    lich_thang_nay: { vi: 'Tháng này', lo: 'ເດືອນນີ້', en: 'This month' },
    lich_n_thang_truoc: { vi: '{n} tháng trước tháng này', lo: '{n} ເດືອນກ່ອນເດືອນນີ້', en: '{n} months before this month' },
    lich_n_thang_sau: { vi: '{n} tháng sau tháng này', lo: '{n} ເດືອນຫຼັງເດືອນນີ້', en: '{n} months after this month' },
    lich_ngoai_khoang: { vi: 'Ngoài khoảng chọn được', lo: 'ຢູ່ນອກຂອບເຂດທີ່ເລືອກໄດ້', en: 'Outside the selectable range' },
    lich_sai: { vi: 'Ngày không hợp lệ — gõ theo dạng dd/mm/yyyy', lo: 'ວັນທີບໍ່ຖືກຕ້ອງ — ພິມແບບ ວວ/ດດ/ປປປປ', en: 'Invalid date — type it as dd/mm/yyyy' },
    lich_ph: { vi: 'dd/mm/yyyy', lo: 'ວວ/ດດ/ປປປປ', en: 'dd/mm/yyyy' },
    lich_nam_ngoai: { vi: 'Chỉ chọn được năm {tu}–{den}', lo: 'ເລືອກໄດ້ສະເພາະປີ {tu}–{den}', en: 'Only years {tu}–{den} can be chosen' },
  };
  const ngonNgu = () => { const l = EPL.NN && EPL.NN.lang; return l === 'lo' || l === 'en' || l === 'both' ? l : 'vi'; };
  const LC = (ng) => LOCALE[ng] || LOCALE.vi;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const thuan = (s) => String(s || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  /** Một khoá, MỘT ngôn ngữ (vi | lo | en), chữ thuần. */
  function chu1(khoa, ng, th) {
    const m = (window.EPL_TU_DIEN || {})[khoa] || CHU[khoa];
    const s = m ? thuan(m[ng] || m.vi || khoa) : khoa;
    return th ? s.replace(/\{(\w+)\}/g, (_, k) => (th[k] == null ? '' : th[k])) : s;
  }
  /** fn(ng) → chữ thuần của ngôn ngữ ng. Trả HTML: một ngôn ngữ; VI + ລາວ thì dòng Việt, dưới là dòng Lào nhỏ (như NN.h). */
  function hai(fn) {
    const ng = ngonNgu();
    if (ng !== 'both') return esc(fn(ng));
    const vi = fn('vi'), lo = fn('lo');
    return esc(vi) + (lo && lo !== vi ? '<span class="lo-sub" lang="lo">' + esc(lo) + '</span>' : '');
  }
  const h = (khoa, th) => hai((ng) => chu1(khoa, ng, th));
  /** Chữ thuần (title, aria-label): VI + ລາວ → "vi / lo", như NN.t. */
  function t(khoa, th) {
    const ng = ngonNgu();
    if (ng !== 'both') return chu1(khoa, ng, th);
    const vi = chu1(khoa, 'vi', th), lo = chu1(khoa, 'lo', th);
    return lo && lo !== vi ? vi + ' / ' + lo : vi;
  }
  const mot = () => (ngonNgu() === 'both' ? 'vi' : ngonNgu());       // chỗ chỉ đủ một dòng (ô hiện, nút tháng)
  const so = (n) => (EPL.so ? EPL.so(n) : String(n));

  /* ================================================================ Ngày — chuỗi yyyy-mm-dd, tính theo UTC cho khỏi dính múi giờ */
  const hai2 = (n) => String(n).padStart(2, '0');
  const ghep = (y, m, d) => String(y).padStart(4, '0') + '-' + hai2(m) + '-' + hai2(d);
  const ngayUTC = (y, m, d) => { const x = new Date(0); x.setUTCFullYear(y, m - 1, d); return x; };
  const soNgayThang = (y, m) => ngayUTC(y, m + 1, 0).getUTCDate();
  function tach(s) {
    const k = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
    if (!k) return null;
    const y = +k[1], m = +k[2], d = +k[3];
    return m >= 1 && m <= 12 && d >= 1 && d <= soNgayThang(y, m) ? { y, m, d } : null;
  }
  const soNgay = (p) => Math.round(ngayUTC(p.y, p.m, p.d).getTime() / 864e5);
  const tuSoNgay = (n) => { const x = new Date(n * 864e5); return ghep(x.getUTCFullYear(), x.getUTCMonth() + 1, x.getUTCDate()); };
  const congNgay = (iso, n) => tuSoNgay(soNgay(tach(iso)) + n);
  const thuCua = (y, m, d) => (ngayUTC(y, m, d).getUTCDay() + 6) % 7;     // 0 = thứ Hai … 6 = Chủ nhật
  // theo GIỜ MÁY như EPL.homNay (toISOString là UTC: Lào UTC+7, 0–7 giờ sáng ra hôm qua)
  const homNay = () => { const d = new Date(); return ghep(d.getFullYear(), d.getMonth() + 1, d.getDate()); };
  const thangNay = () => homNay().slice(0, 7);
  const hienNgay = (iso) => { const p = tach(iso); return p ? hai2(p.d) + '/' + hai2(p.m) + '/' + p.y : ''; };
  const congThang = (y, m, n) => { const k = y * 12 + (m - 1) + n; return { y: Math.floor(k / 12), m: (((k % 12) + 12) % 12) + 1 }; };
  const trongKhoang = (iso, min, max) => !!iso && (!min || iso >= min) && (!max || iso <= max);
  const RE_THANG = /^\d{4}-(0[1-9]|1[0-2])$/;
  const NAM_THANG = [2000, 2100];   // khoảng năm bộ chọn tháng (chủ dự án 01/10: mọi năm bấm được, trong giới hạn hợp lý)
  const NAM_NGAY = [1900, 2100];    // ô ngày rộng hơn: có ngày sinh, ngày vào làm của tài xế
  /** Chữ người dùng gõ → 'yyyy-mm-dd' · '' (để trống) · null (không đọc được). Nhận 29/9/2026, 29-09-26, 29.09.2026, 29092026. */
  function docGo(s) {
    s = String(s || '').trim();
    if (!s) return '';
    let k = /^(\d{1,2})\s*[/.\-\s]\s*(\d{1,2})\s*[/.\-\s]\s*(\d{4}|\d{2})$/.exec(s) || /^(\d{2})(\d{2})(\d{4}|\d{2})$/.exec(s);
    if (!k) { const q = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(s); if (q) k = [s, q[3], q[2], q[1]]; }
    if (!k) return null;
    const y = k[3].length === 2 ? 2000 + +k[3] : +k[3];
    const iso = ghep(y, +k[2], +k[1]);
    return tach(iso) ? iso : null;
  }

  /* ================================================================ Biểu tượng */
  const SVG = {
    lich: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
    mui: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
    len: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>',
    xuong: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
  };

  /* ================================================================ Gắn vào ô */
  const GAN = new WeakMap();        // ô gốc → bộ điều khiển
  const DANG_GAN = new Set();       // các bộ đang gắn — để vẽ lại chữ khi đổi ngôn ngữ
  let POP = null;                   // lịch đang mở (mỗi lúc chỉ một)
  // Lần chọn một tháng CHƯA CÓ trong select (đã thêm option). Có module dựng lại select từ danh sách riêng ngay sau change
  // (màn tài xế: 12 tháng gần nhất) — select mới thiếu tháng vừa chọn nên nút lại hiện "Mọi tháng" trong khi màn đang lọc
  // đúng tháng đó. Select mới cùng id, trong 5 giây, người dùng chưa bấm / gõ gì khác → thêm lại option đó và chọn nó
  // (không bắn sự kiện: module đã ở tháng này rồi).
  let NHO = null, tuongTac = 0;

  /** Chữ của nhãn ô (cho aria-label của ô hiện / nút tháng). */
  function tenNhan(goc) {
    const al = goc.getAttribute('aria-label'); if (al) return al;
    let lab = goc.labels && goc.labels[0];
    if (!lab) { const f = goc.closest('.field, .x2-field, label'); lab = f && (f.tagName === 'LABEL' ? f : f.querySelector('label')); }
    return lab ? thuan(lab.textContent) : '';
  }
  const lopCua = (goc) => [...goc.classList].filter((x) => !x.startsWith('lich-')).join(' ');
  const anDi = (goc) => goc.hidden || goc.style.display === 'none';

  /** Ô do module tự ẩn để làm lịch phụ (màn Khách hàng): không dựng ô hiện, chỉ thay showPicker(). */
  const laOPhu = (o) => o.hasAttribute('data-native-for') || o.getAttribute('aria-hidden') === 'true';

  function ganNgay(goc) {
    const c = { kieu: 'ngay', goc };
    if (laOPhu(goc)) {
      c.phu = true;
      c.neo = () => goc.parentElement || goc;
      c.lamMoi = () => {};
      c.datCho = () => {};
    } else {
      const vo = document.createElement('span'); vo.className = 'lich-o';
      const hien = document.createElement('input');
      hien.type = 'text'; hien.className = 'lich-hien'; hien.size = 10; hien.autocomplete = 'off'; hien.spellcheck = false;
      // điện thoại: bấm vào là mở lịch, đừng bật bàn phím che mất lịch
      const camUng = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
      hien.setAttribute('inputmode', camUng ? 'none' : 'numeric');
      hien.setAttribute('aria-haspopup', 'dialog'); hien.setAttribute('aria-expanded', 'false');
      const nut = document.createElement('button'); nut.type = 'button'; nut.className = 'lich-nut'; nut.tabIndex = -1; nut.innerHTML = SVG.lich;
      vo.append(hien, nut);
      Object.assign(c, { vo, hien, nut });
      c.neo = () => vo;
      c.datCho = () => { if (goc.isConnected && goc.nextSibling !== vo) goc.after(vo); };
      c.lamMoi = (chu) => {
        hien.className = (lopCua(goc) + ' lich-hien').trim();
        hien.style.cssText = goc.style.cssText;
        vo.hidden = anDi(goc);
        hien.disabled = goc.disabled; hien.readOnly = goc.readOnly; nut.disabled = goc.disabled || goc.readOnly;
        vo.classList.toggle('chi-xem', goc.disabled || goc.readOnly);
        if (goc.title) hien.title = goc.title;
        if (chu) {
          hien.placeholder = chu1('lich_ph', mot());
          nut.title = t('lich_mo'); nut.setAttribute('aria-label', t('lich_mo'));
          const ten = tenNhan(goc); if (ten) hien.setAttribute('aria-label', ten);
        }
        if (POP && POP.c === c) {                               // module đổi giá trị trong lúc lịch đang mở
          if (goc.value !== POP.gocCu) { POP.gocCu = goc.value; POP.chon = tach(goc.value) ? goc.value : ''; POP.daChon = false; veLai(); }
          return;
        }
        hien.value = hienNgay(goc.value);
      };
      // Nút lịch không nhận chuột (pointer-events:none, xem lich.css): bấm vào nó là bấm vào ô hiện bên dưới. Nhờ vậy ô
      // module cố ý khoá chuột (tab "Toàn phiếu" của Phiếu xuất xe: input{pointer-events:none}) thì nút cũng chết theo.
      hien.addEventListener('click', (e) => {
        if (!(POP && POP.c === c)) { mo(c); return; }
        const r = nut.getBoundingClientRect();                  // lịch đang mở, bấm đúng chỗ nút lịch → đóng
        if (r.width && e.clientX >= r.left && e.clientX <= r.right) dong(true, true);
      });
      hien.addEventListener('keydown', (e) => {
        if (POP && POP.c === c) return;                       // lịch đang mở: bộ nghe phím chung lo
        if (e.key === 'F4' || (e.key === 'ArrowDown' && !e.ctrlKey && !e.metaKey)) { e.preventDefault(); mo(c); }
        else if (e.key === 'Enter') chotGo(c);                // ghi chữ đã gõ; Enter vẫn đi tiếp như ô ngày gốc
      });
      // Sự kiện của ô hiện KHÔNG cho nổi lên: module chỉ nghe thấy input / change của ô gốc, đúng như trước khi có lịch này
      hien.addEventListener('input', (e) => { e.stopPropagation(); tuChenGach(e, hien); if (POP && POP.c === c) xemGo(); });
      hien.addEventListener('change', (e) => { e.stopPropagation(); if (!(POP && POP.c === c)) chotGo(c); });
      hien.addEventListener('focusout', (e) => {
        if (POP && POP.c === c && !(e.relatedTarget && POP.el.contains(e.relatedTarget))) dong(true);
      });
      goc.classList.add('lich-goc');
      c.datCho();
      // Tiêu điểm: module gọi .focus() ô gốc (báo thiếu ngày) hay hộp thoại vừa tự đặt con trỏ vào ô gốc → chuyển sang ô hiện
      goc.focus = (o) => hien.focus(o);
      if (document.activeElement === goc) hien.focus({ preventScroll: true });
    }
    goc.showPicker = () => { if (POP && POP.c === c) dong(true); else if (!goc.disabled && !goc.readOnly) mo(c); };
    c.go = () => {
      if (POP && POP.c === c) dong(false);
      if (c.vo) c.vo.remove();
      goc.classList.remove('lich-goc');
      delete goc.focus; delete goc.showPicker;
      GAN.delete(goc); DANG_GAN.delete(c);
    };
    GAN.set(goc, c); DANG_GAN.add(c);
    THEO_DOI.observe(goc, TT_THEO_DOI);
    c.lamMoi(true);
  }

  /** <select> tháng: các option.value đều dạng YYYY-MM (hoặc "" = tất cả các tháng). */
  function laThang(s) {
    if (s.multiple) return false;
    let co = 0;
    for (let i = 0; i < s.options.length; i++) {
      const v = s.options[i].value;
      if (v === '') continue;
      if (!RE_THANG.test(v)) return false;
      co++;
    }
    return co > 0;
  }
  function nhanThang(v) {
    const tien = LC(mot()).nut, s = v.slice(5, 7) + '/' + v.slice(0, 4);
    return tien ? tien + ' ' + s : s;
  }
  function ganThang(goc) {
    const nut = document.createElement('button'); nut.type = 'button';
    nut.innerHTML = '<span class="lich-ic">' + SVG.lich + '</span><span class="lich-thang-chu"></span><span class="lich-mui">' + SVG.mui + '</span>';
    nut.setAttribute('aria-haspopup', 'dialog'); nut.setAttribute('aria-expanded', 'false');
    const c = { kieu: 'thang', goc, nut, tabCu: goc.getAttribute('tabindex') };
    c.neo = () => nut;
    c.datCho = () => { if (goc.isConnected && goc.nextSibling !== nut) goc.after(nut); };
    c.lamMoi = (chu) => {
      nut.className = (lopCua(goc) + ' lich-thang').trim();
      nut.style.cssText = goc.style.cssText;
      nut.hidden = anDi(goc); nut.disabled = goc.disabled;
      const v = goc.value, o = goc.options[goc.selectedIndex];
      nut.querySelector('.lich-thang-chu').textContent = RE_THANG.test(v) ? nhanThang(v) : (o ? thuan(o.textContent) : '');
      if (chu) { const ten = tenNhan(goc); if (ten) nut.setAttribute('aria-label', ten + ': ' + nut.textContent.trim()); }
      if (POP && POP.c === c && goc.value !== POP.chon) { POP.chon = goc.value; veLai(); }
    };
    nut.addEventListener('click', () => { if (POP && POP.c === c) dong(false, true); else mo(c); });
    nut.addEventListener('focusout', (e) => {
      if (POP && POP.c === c && !(e.relatedTarget && POP.el.contains(e.relatedTarget))) dong(false);
    });
    goc.addEventListener('change', () => { const x = GAN.get(goc); if (x === c) c.lamMoi(); });
    goc.classList.add('lich-an'); goc.tabIndex = -1;          // còn trong trang nhưng không nhận Tab, không thấy
    c.datCho();
    if (NHO && goc.id && NHO.id === goc.id && Date.now() - NHO.luc < 5000 && tuongTac <= NHO.luc && goc.value !== NHO.v) {
      themThang(goc, NHO.v); goc.value = NHO.v;
    }
    goc.focus = (o) => nut.focus(o);
    c.go = () => {
      if (POP && POP.c === c) dong(false);
      nut.remove(); goc.classList.remove('lich-an');
      if (c.tabCu == null) goc.removeAttribute('tabindex'); else goc.setAttribute('tabindex', c.tabCu);
      delete goc.focus;
      GAN.delete(goc); DANG_GAN.delete(c);
    };
    GAN.set(goc, c); DANG_GAN.add(c);
    THEO_DOI.observe(goc, TT_THEO_DOI);
    c.lamMoi(true);
  }

  /** Xét một ô: gắn nếu đúng loại, gỡ nếu không còn đúng (đổi type, option không còn là tháng). */
  function xet(el) {
    if (!el || el.nodeType !== 1 || !el.isConnected) return;
    if (el.closest('.lich-pop') || (el.dataset && el.dataset.lich === 'khong')) return;
    const c = GAN.get(el);
    if (el.tagName === 'INPUT') {
      const la = el.type === 'date';
      if (c) { if (!la) c.go(); else { DANG_GAN.add(c); c.datCho(); c.lamMoi(); } } else if (la) ganNgay(el);
    } else if (el.tagName === 'SELECT') {
      const la = laThang(el);
      if (c) { if (!la) c.go(); else { DANG_GAN.add(c); c.datCho(); c.lamMoi(true); } } else if (la) ganThang(el);
    }
  }
  const quet = (goc) => goc.querySelectorAll('input[type="date"], select').forEach(xet);

  // Thuộc tính của RIÊNG các ô đã gắn (theo dõi cả trang thì bản đồ, hoạt ảnh đổi style liên tục)
  const TT_THEO_DOI = { attributes: true, attributeFilter: ['type', 'disabled', 'readonly', 'hidden', 'style', 'class', 'min', 'max', 'value', 'title', 'aria-label'] };
  const THEO_DOI = new MutationObserver((ds) => {
    const xong = new Set();
    ds.forEach((m) => {
      const el = m.target; if (xong.has(el)) return; xong.add(el);
      const c = GAN.get(el); if (!c) return;
      if (m.attributeName === 'type') xet(el); else c.lamMoi();
    });
  });
  function khiDoiCay(ds) {
    const can = new Set();
    let coXoa = false;
    for (const m of ds) {
      const tg = m.target;
      if (tg.nodeType !== 1 || (tg.closest && tg.closest('.lich-pop'))) continue;
      // option thêm / bớt / đổi chữ (đổi ngôn ngữ) trong một select
      const sel = tg.tagName === 'SELECT' ? tg : (tg.tagName === 'OPTION' || tg.tagName === 'OPTGROUP') ? tg.closest('select') : null;
      if (sel) can.add(sel);
      m.addedNodes.forEach((n) => {
        if (n.nodeType !== 1) return;
        if (n.tagName === 'INPUT' || n.tagName === 'SELECT') can.add(n);
        else if (n.firstElementChild && n.tagName !== 'OPTION') n.querySelectorAll('input[type="date"], select').forEach((x) => can.add(x));
      });
      if (m.removedNodes.length) coXoa = true;
    }
    can.forEach(xet);
    if (coXoa) {
      DANG_GAN.forEach((c) => { if (!c.goc.isConnected) DANG_GAN.delete(c); });     // ô đã bị module vẽ đè
      if (POP && !POP.neo.isConnected) dong(false);
    }
  }

  /** Module gán .value bằng mã thì không có sự kiện nào → vá setter ở prototype để ô hiện / nút tháng cập nhật ngay.
   *  Vá một lần lúc nạp tệp, TRƯỚC khi chung.js dựng ô tháng (EPL.doiOThang chụp setter lúc chạy nên dùng bản đã vá). */
  function vaSetter() {
    const va = (proto, ten, sau) => {
      const g = proto && Object.getOwnPropertyDescriptor(proto, ten);
      if (!g || !g.set || !g.configurable) return;
      Object.defineProperty(proto, ten, {
        configurable: true, enumerable: g.enumerable, get: g.get,
        set(v) { g.set.call(this, v); try { sau(this); } catch (e) { /* bỏ qua */ } },
      });
    };
    const lamMoi = (el) => { const c = GAN.get(el); if (c) c.lamMoi(); };
    va(HTMLInputElement.prototype, 'value', lamMoi);
    va(HTMLInputElement.prototype, 'valueAsDate', lamMoi);
    va(HTMLInputElement.prototype, 'valueAsNumber', lamMoi);
    va(HTMLSelectElement.prototype, 'value', lamMoi);
    va(HTMLSelectElement.prototype, 'selectedIndex', lamMoi);
    va(window.HTMLOptionElement && HTMLOptionElement.prototype, 'selected', (o) => { const s = o.closest && o.closest('select'); if (s) lamMoi(s); });
  }

  /** Gán giá trị cho ô gốc rồi bắn input + change (bubbles) — như người dùng vừa chọn trên ô gốc. */
  function ganGiaTri(goc, v) {
    if (goc.value === v) return false;
    goc.value = v;
    goc.dispatchEvent(new Event('input', { bubbles: true }));
    goc.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }
  function baoSai(c) {
    if (!c.vo) return;
    c.vo.classList.add('sai'); clearTimeout(c.hSai); c.hSai = setTimeout(() => c.vo.classList.remove('sai'), 2200);
    if (EPL.toast) EPL.toast(t('lich_sai'), 'loi');
  }
  /** Ghi chữ đã gõ ở ô hiện (lịch đóng). Sai thì trả lại ngày cũ và báo. */
  function chotGo(c) {
    const v = docGo(c.hien.value), goc = c.goc;
    if (v === null || (v && !trongKhoang(v, gioiHan(goc.min), gioiHan(goc.max))) || (v === '' && goc.required)) {
      if (thuan(c.hien.value)) baoSai(c);
      c.hien.value = hienNgay(goc.value);
      return false;
    }
    ganGiaTri(goc, v);
    c.hien.value = hienNgay(goc.value);
    return true;
  }
  /** Gõ liền số 29092026 → 29/09/2026 (chèn "/" ngay khi gõ). Người gõ tự có dấu phân cách (1/9/2026) thì để yên;
   *  xoá, hay gõ giữa chừng (con trỏ không ở cuối) thì không đụng. */
  function tuChenGach(e, o) {
    if (e.inputType && e.inputType.indexOf('insert') !== 0) return;
    const v = o.value;
    if (o.selectionStart != null && o.selectionStart !== v.length) return;
    let k;
    if (/^\d{3,8}$/.test(v)) o.value = v.slice(0, 2) + '/' + v.slice(2, 4) + (v.length > 4 ? '/' + v.slice(4) : '');
    else if ((k = /^(\d{1,2})\/(\d{2})(\d{1,4})$/.exec(v))) o.value = k[1] + '/' + k[2] + '/' + k[3];
  }
  const gioiHan = (s) => (tach(s) ? s : '');

  /* ================================================================ Lịch bật lên */
  function tyLeApp() {
    const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le'));
    return v > 0 ? v : 1;
  }
  /** Zoom thật của một phần tử = tích `zoom` của nó và mọi tổ tiên (.app, .hop-thoai dùng zoom: var(--ty-le)). */
  function zoomCua(el) {
    let z = 1;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) { const v = parseFloat(getComputedStyle(a).zoom); if (v > 0) z *= v; }
    return z;
  }

  function mo(c) {
    if (POP) dong(true);
    const goc = c.goc;
    if (goc.disabled || goc.readOnly) return;
    const el = document.createElement('div');
    el.className = 'lich-pop';
    const P = POP = { c, el, kieu: c.kieu, neo: c.neo(), xem: c.kieu === 'ngay' ? 'ngay' : 'thang' };
    if (c.kieu === 'ngay') {
      P.min = gioiHan(goc.min); P.max = gioiHan(goc.max);
      P.gocCu = goc.value;
      P.chon = tach(goc.value) ? goc.value : '';
      P.daChon = false;
      const p = tach(P.chon || ngayGanNhat(P, homNay()));
      P.dau = { y: p.y, m: p.m };
      // năm chọn được: theo min / max của ô, không có thì 1900–2100 (ngày sinh tài xế cũng phải chọn được)
      P.namMin = P.min ? +P.min.slice(0, 4) : NAM_NGAY[0]; P.namMax = P.max ? +P.max.slice(0, 4) : NAM_NGAY[1];
    } else {
      // Chủ dự án 01/10: MỌI tháng, MỌI năm đều bấm được — danh sách option của select không giới hạn gì. Tháng chưa có
      // option thì lúc chọn mới thêm option vào (themThang); module tự báo "tháng trống" như cũ.
      P.tatCa = null;
      const ds = [];
      [...goc.options].forEach((o) => { if (o.value === '') P.tatCa = thuan(o.textContent); else if (RE_THANG.test(o.value)) ds.push(+o.value.slice(0, 4)); });
      P.namMin = Math.min(NAM_THANG[0], ...ds); P.namMax = Math.max(NAM_THANG[1], ...ds);
      P.chon = goc.value;
      P.td = RE_THANG.test(P.chon) ? P.chon : thangNay();
      P.namXem = +P.td.slice(0, 4);
    }
    // Trong hộp thoại modal: lịch phải nằm TRONG hộp thoại — ngoài nó cả trang bị khoá (inert), bấm không ăn
    const noi = goc.closest('dialog[open]') || document.body;
    noi.appendChild(el);
    P.zoomNoi = zoomCua(noi);
    if ('popover' in el && typeof el.showPopover === 'function') {
      // lớp trên cùng: không bị khung cuộn / hộp thoại (overflow:hidden) cắt, không phải đua z-index
      try { el.popover = 'manual'; el.showPopover(); } catch (e) { /* vẫn hiện bằng position:fixed */ }
    }
    el.addEventListener('mousedown', (e) => e.preventDefault());    // bấm trong lịch: con trỏ vẫn ở ô hiện / nút tháng
    // Bấm trong lịch không nổi lên: lịch có thể nằm trong hộp thoại của module, mà module nghe click chung cả hộp thoại
    el.addEventListener('click', (e) => { e.stopPropagation(); khiBam(e); });
    el.addEventListener('dblclick', (e) => e.stopPropagation());
    document.addEventListener('pointerdown', ngoai, true);
    document.addEventListener('keydown', phim, true);
    window.addEventListener('scroll', cuon, true);
    window.addEventListener('resize', coLai);
    window.addEventListener('hashchange', dongNgay);
    const dlg = noi.tagName === 'DIALOG' ? noi : null;
    if (dlg) { P.dlg = dlg; dlg.addEventListener('close', dongNgay); }
    if (c.vo) c.vo.classList.add('mo');
    if (c.hien || c.nut) (c.hien || c.nut).setAttribute('aria-expanded', 'true');
    boCuc(); veLai();
  }
  const dongNgay = () => dong(false);

  /** Đóng lịch. `chot`: ghi ngày người dùng đã bấm (bấm ra ngoài, Tab đi) · `traFocus`: đưa con trỏ về ô. */
  function dong(chot, traFocus) {
    const P = POP; if (!P) return;
    POP = null;
    document.removeEventListener('pointerdown', ngoai, true);
    document.removeEventListener('keydown', phim, true);
    window.removeEventListener('scroll', cuon, true);
    window.removeEventListener('resize', coLai);
    window.removeEventListener('hashchange', dongNgay);
    if (P.dlg) P.dlg.removeEventListener('close', dongNgay);
    try { if (typeof P.el.hidePopover === 'function' && P.el.matches(':popover-open')) P.el.hidePopover(); } catch (e) { /* bỏ qua */ }
    P.el.remove();
    const c = P.c;
    if (c.vo) c.vo.classList.remove('mo');
    if (c.hien || c.nut) (c.hien || c.nut).setAttribute('aria-expanded', 'false');
    if (P.kieu === 'ngay') {
      if (chot && P.daChon && P.chon !== c.goc.value && (!P.chon ? !c.goc.required : trongKhoang(P.chon, P.min, P.max))) ganGiaTri(c.goc, P.chon);
      if (c.hien) c.hien.value = hienNgay(c.goc.value);
    }
    if (traFocus) {
      const f = c.hien || c.nut || (c.goc.dataset.nativeFor && document.getElementById(c.goc.dataset.nativeFor));
      if (f && f.isConnected) { try { f.focus({ preventScroll: true }); } catch (e) { /* bỏ qua */ } }
    }
  }
  function chotNgay(v) {
    const P = POP; if (!P) return;
    if (v && !trongKhoang(v, P.min, P.max)) return;
    if (!v && P.c.goc.required) return;
    const c = P.c;
    dong(false, true);                       // đóng trước rồi mới gán: ô hiện vẽ theo giá trị mới
    ganGiaTri(c.goc, v || '');
    if (c.hien) c.hien.value = hienNgay(c.goc.value);
  }
  function chotThang(v) {
    const P = POP; if (!P) return;
    if (v ? !RE_THANG.test(v) : P.tatCa == null) return;
    const c = P.c;
    dong(false, true);
    if (v && themThang(c.goc, v)) NHO = { id: c.goc.id, v, luc: Date.now() };
    ganGiaTri(c.goc, v);
  }
  /** Thêm option 'YYYY-MM' vào select tháng nếu chưa có, ĐÚNG THỨ TỰ của danh sách (mới → cũ như EPL.doiOThang, hay
   *  cũ → mới). Nhãn theo mẫu option sẵn có ("09/2026", "Tháng 09/2026"…), không có mẫu thì MM/YYYY. Trả true nếu đã thêm. */
  function themThang(s, v) {
    if ([...s.options].some((o) => o.value === v)) return false;
    const ds = [...s.options].filter((o) => RE_THANG.test(o.value));
    const giam = ds.length < 2 || ds[0].value > ds[ds.length - 1].value;
    const nhan = (x) => x.slice(5, 7) + '/' + x.slice(0, 4);
    const o = document.createElement('option'); o.value = v;
    const mau = ds.find((x) => x.textContent.includes(nhan(x.value)));
    o.textContent = mau ? mau.textContent.replace(nhan(mau.value), nhan(v)) : nhan(v);
    const sau = ds.find((x) => (giam ? x.value < v : x.value > v));
    if (sau) sau.before(o); else if (ds.length) ds[ds.length - 1].after(o); else s.appendChild(o);
    return true;
  }

  /** Ngày gần nhất trong khoảng min–max (mở lịch khi ô trống mà hôm nay nằm ngoài khoảng). */
  function ngayGanNhat(P, iso) {
    if (P.min && iso < P.min) return P.min;
    if (P.max && iso > P.max) return P.max;
    return iso;
  }
  /** Cỡ lịch. Màn thường: to nhỏ theo ứng dụng (zoom = --ty-le), hai tháng cạnh nhau nếu đủ chỗ.
   *  Điện thoại (< 600 px): một tháng, KHÔNG thu theo --ty-le (0,85 là ô ngày còn 34 px — khó bấm bằng ngón tay):
   *  ô ngày 40–46 px, lịch rộng gần bằng màn. */
  function boCuc() {
    const P = POP; if (!P) return;
    const vw = window.innerWidth || document.documentElement.clientWidth || 1600;
    P.hep = vw < 600;
    const z = P.hep ? 1 : tyLeApp();
    P.el.style.zoom = String(z / (P.zoomNoi || 1));
    const o = P.hep ? Math.max(36, Math.min(46, Math.floor((vw - 16 - 32) / 7))) : 36;
    P.el.style.setProperty('--o', o + 'px');
    P.soThang = P.kieu === 'ngay' && !P.hep && (o * 14 + 52) * z <= vw - 16 ? 2 : 1;
  }
  /** Vẽ lại (giữ con trỏ trên nút đang đứng nếu người dùng đã Tab vào lịch). */
  function veLai() {
    const P = POP; if (!P) return;
    const ae = document.activeElement, dangO = ae && P.el.contains(ae) ? ae.getAttribute('data-lhd') : null;
    const ng = ngonNgu();
    P.el.lang = ng === 'lo' ? 'lo' : ng === 'en' ? 'en' : 'vi';
    P.el.className = 'lich-pop ' + (P.kieu === 'thang' ? 'kt' : P.soThang === 2 ? 'k2' : 'k1') + (P.hep ? ' hep' : '') + (ng === 'both' ? ' hai' : '');
    P.el.setAttribute('role', 'dialog');
    P.el.setAttribute('aria-label', P.kieu === 'thang' ? t('lich_chon_thang') : (tenNhan(P.c.goc) || t('lich_mo')));
    P.el.innerHTML = P.kieu === 'ngay' ? veNgay(P) : veThang(P);
    if (dangO) { const b = P.el.querySelector('[data-lhd="' + dangO + '"]'); if (b && !b.disabled) b.focus({ preventScroll: true }); }
    datViTri();
  }

  const nutDk = (hd, svg, khoa, tat) => `<button type="button" class="lich-dk" data-lhd="${hd}" title="${esc(t(khoa))}" aria-label="${esc(t(khoa))}"${tat ? ' disabled' : ''}>${svg}</button>`;

  function veNgay(P) {
    let dau;
    if (!P.chon) dau = `<b>${h('lich_chua_chon')}</b><small>${h('lich_ph')}</small>`;
    else {
      const p = tach(P.chon), thu = thuCua(p.y, p.m, p.d);
      const n = soNgay(p) - soNgay(tach(homNay()));
      const phu = n === 0 ? h('lich_hom_nay') : n === -1 ? h('lich_hom_qua') : n === 1 ? h('lich_ngay_mai')
        : n < 0 ? h('lich_truoc', { n: so(-n) }) : h('lich_sau', { n: so(n) });
      dau = `<b>${hai((ng) => LC(ng).dayDu(p.y, p.m, p.d, LC(ng).thu[thu]))}</b><small>${phu}</small>`;
    }
    let than = '';
    if (P.xem === 'ngay') {
      const dauTien = P.dau, cuoi = congThang(dauTien.y, dauTien.m, P.soThang - 1);
      const truocTat = (P.min && ghep(dauTien.y, dauTien.m, 1) <= P.min) || (dauTien.y <= P.namMin && dauTien.m === 1);
      const sauTat = (P.max && ghep(cuoi.y, cuoi.m, soNgayThang(cuoi.y, cuoi.m)) >= P.max) || (cuoi.y >= P.namMax && cuoi.m === 12);
      for (let i = 0; i < P.soThang; i++) {
        const { y, m } = congThang(dauTien.y, dauTien.m, i);
        const dk = i === P.soThang - 1 ? '<span class="lich-gian"></span>' + nutDk('len', SVG.len, 'lich_thang_truoc', truocTat) + nutDk('xuong', SVG.xuong, 'lich_thang_sau', sauTat) : '';
        than += `<div class="lich-khoi"><div class="lich-hang-tieu"><button type="button" class="lich-tieu" data-lhd="xem-thang" data-ly="${y}" title="${esc(t('lich_chon_thang'))}"><span>${hai((ng) => LC(ng).thangNam(m, y))}</span>${SVG.mui}</button>${dk}</div>${luoiNgay(P, y, m)}</div>`;
      }
    } else if (P.xem === 'thang') {
      const y = P.namXem;
      const tat = (yy) => yy < P.namMin || yy > P.namMax;
      than = `<div class="lich-khoi rong"><div class="lich-hang-tieu"><button type="button" class="lich-tieu" data-lhd="xem-nam" title="${esc(t('lich_chon_nam'))}">${y}${SVG.mui}</button><span class="lich-gian"></span>`
        + nutDk('len', SVG.len, 'lich_nam_truoc', tat(y - 1)) + nutDk('xuong', SVG.xuong, 'lich_nam_sau', tat(y + 1)) + '</div>'
        + (P.goNam ? `<div class="lich-go-nam">${esc(P.goNam)}<i></i></div>` : '')
        + luoiMuoiHaiThang(P, y, (v) => {
          const d1 = v + '-01', d2 = v + '-' + soNgayThang(+v.slice(0, 4), +v.slice(5, 7));
          return !(P.max && d1 > P.max) && !(P.min && d2 < P.min);
        }, P.chon ? P.chon.slice(0, 7) : '', 'thang-xem') + '</div>';
    } else {
      than = veNam(P, (yy) => yy >= P.namMin && yy <= P.namMax, P.chon ? +P.chon.slice(0, 4) : 0);
    }
    const homNayDuoc = trongKhoang(homNay(), P.min, P.max);
    const chan = `<div class="lich-chan"><button type="button" class="lich-btn" data-lhd="hom-nay"${homNayDuoc ? '' : ' disabled'}>${h('lich_hom_nay')}</button>`
      + `<button type="button" class="lich-btn" data-lhd="xoa"${P.c.goc.required ? ' disabled' : ''}>${h('lich_xoa')}</button><span class="lich-gian"></span>`
      + `<button type="button" class="lich-btn chinh" data-lhd="ok">${h('lich_ok')}</button></div>`;
    return `<div class="lich-dau">${dau}</div><div class="lich-than">${than}</div>${chan}`;
  }

  function luoiNgay(P, y, m) {
    let s = '<div class="lich-luoi" role="grid">';
    for (let i = 0; i < 7; i++) s += `<span class="lich-thu${i === 6 ? ' cn' : ''}">${hai((ng) => LC(ng).thuNgan[i])}</span>`;
    const lech = thuCua(y, m, 1), n = soNgayThang(y, m), nay = homNay(), L1 = LC(mot());
    for (let i = 0; i < 42; i++) {
      const d = i - lech + 1;
      if (d < 1 || d > n) { s += '<span class="lich-trong"></span>'; continue; }
      const iso = ghep(y, m, d), duoc = trongKhoang(iso, P.min, P.max);
      const lop = 'lich-ngay' + (i % 7 === 6 ? ' cn' : '') + (iso === nay ? ' hn' : '') + (iso === P.chon ? ' chon' : '');
      const ten = L1.dayDu(y, m, d, L1.thu[i % 7]);
      s += `<button type="button" tabindex="-1" class="${lop}" data-lhd="ngay" data-lv="${iso}" aria-label="${esc(ten)}"`
        + `${iso === P.chon ? ' aria-selected="true"' : ''}${iso === nay ? ' aria-current="date"' : ''}${duoc ? '' : ' disabled title="' + esc(t('lich_ngoai_khoang')) + '"'}>${d}</button>`;
    }
    return s + '</div>';
  }
  /** Lưới 12 tháng của năm y (4 × 3). `duoc(v)`: tháng 'YYYY-MM' chọn được không · `chon`: tháng đang chọn (có khung). */
  function luoiMuoiHaiThang(P, y, duoc, chon, hd) {
    const nay = thangNay();
    let s = '<div class="lich-luoi12">';
    for (let m = 1; m <= 12; m++) {
      const v = y + '-' + hai2(m), ok = duoc(v);
      const lop = 'lich-o12' + (v === nay ? ' hn' : '') + (v === chon ? ' chon' : '') + (P.td === v ? ' td' : '');
      s += `<button type="button" tabindex="-1" class="${lop}" data-lhd="${hd}" data-lv="${v}" aria-label="${esc(LC(mot()).thangNam(m, y))}"`
        + `${v === chon ? ' aria-selected="true"' : ''}${ok ? '' : ' disabled title="' + esc(t('lich_ngoai_khoang')) + '"'}>${hai((ng) => LC(ng).thang(m))}</button>`;
    }
    return s + '</div>';
  }
  /** Lưới năm: một thập kỷ, thêm năm cuối thập kỷ trước và năm đầu thập kỷ sau (mờ) như Windows. */
  function veNam(P, duoc, chon) {
    const y0 = Math.floor(P.namXem / 10) * 10;
    let s = `<div class="lich-khoi rong"><div class="lich-hang-tieu"><span class="lich-tieu tinh">${y0} – ${y0 + 9}</span><span class="lich-gian"></span>`
      + nutDk('len', SVG.len, 'lich_muoi_nam_truoc', !duoc(y0 - 1)) + nutDk('xuong', SVG.xuong, 'lich_muoi_nam_sau', !duoc(y0 + 10)) + '</div>'
      + (P.goNam ? `<div class="lich-go-nam">${esc(P.goNam)}<i></i></div>` : '') + '<div class="lich-luoi12">';
    const nay = +homNay().slice(0, 4);
    for (let y = y0 - 1; y <= y0 + 10; y++) {
      const lop = 'lich-o12' + (y < y0 || y > y0 + 9 ? ' ngoai' : '') + (y === nay ? ' hn' : '') + (y === chon ? ' chon' : '') + (P.tdNam === y ? ' td' : '');
      s += `<button type="button" tabindex="-1" class="${lop}" data-lhd="nam-xem" data-lv="${y}"${duoc(y) ? '' : ' disabled'}>${y}</button>`;
    }
    return s + '</div></div>';
  }

  function veThang(P) {
    let dau;
    if (RE_THANG.test(P.chon)) {
      const y = +P.chon.slice(0, 4), m = +P.chon.slice(5, 7), nay = thangNay();
      const n = (y * 12 + m) - (+nay.slice(0, 4) * 12 + +nay.slice(5, 7));
      const phu = n === 0 ? h('lich_thang_nay') : n === -1 ? h('lich_thang_truoc') : n === 1 ? h('lich_thang_sau')
        : n < 0 ? h('lich_n_thang_truoc', { n: -n }) : h('lich_n_thang_sau', { n });
      dau = `<b>${hai((ng) => LC(ng).thangNam(m, y))}</b><small>${phu}</small>`;
    } else dau = `<b>${esc(P.tatCa || '')}</b><small>${h('lich_chon_thang')}</small>`;
    let than;
    if (P.xem === 'thang') {
      const y = P.namXem;
      than = `<div class="lich-khoi rong"><div class="lich-hang-tieu"><button type="button" class="lich-tieu" data-lhd="xem-nam" title="${esc(t('lich_chon_nam'))}">${y}${SVG.mui}</button><span class="lich-gian"></span>`
        + nutDk('len', SVG.len, 'lich_nam_truoc', y <= P.namMin) + nutDk('xuong', SVG.xuong, 'lich_nam_sau', y >= P.namMax) + '</div>'
        + (P.goNam ? `<div class="lich-go-nam">${esc(P.goNam)}<i></i></div>` : '')
        + luoiMuoiHaiThang(P, y, () => true, P.chon, 'chon-thang') + '</div>';
    } else {
      than = veNam(P, (yy) => yy >= P.namMin && yy <= P.namMax, RE_THANG.test(P.chon) ? +P.chon.slice(0, 4) : 0);
    }
    const chan = `<div class="lich-chan"><button type="button" class="lich-btn" data-lhd="thang-nay">${h('lich_thang_nay')}</button>`
      + `${P.tatCa != null ? `<button type="button" class="lich-btn" data-lhd="tat-ca">${esc(P.tatCa)}</button>` : ''}<span class="lich-gian"></span></div>`;
    return `<div class="lich-dau">${dau}</div><div class="lich-than">${than}</div>${chan}`;
  }

  /** Cho ngày đang chọn vào khung đang xem (bấm phím đi quá tháng cuối / trước tháng đầu). */
  function choVaoKhung(P) {
    if (!P.chon) return;
    const p = tach(P.chon), k = p.y * 12 + p.m, k0 = P.dau.y * 12 + P.dau.m;
    if (k < k0) P.dau = { y: p.y, m: p.m };
    else if (k > k0 + P.soThang - 1) P.dau = congThang(p.y, p.m, -(P.soThang - 1));
  }
  /** Ô hiện xem trước ngày đang bấm trong lịch (Esc thì trả lại ngày cũ). */
  function xemTruoc(P) { if (P.c.hien) P.c.hien.value = hienNgay(P.chon); }
  /** Gõ trong ô hiện lúc lịch đang mở: đọc được ngày nào thì lịch nhảy tới ngày đó. */
  function xemGo() {
    const P = POP; if (!P || P.kieu !== 'ngay') return;
    const v = docGo(P.c.hien.value);
    if (v === null || (v && !trongKhoang(v, P.min, P.max))) return;
    P.chon = v; P.daChon = true; P.xem = 'ngay';
    choVaoKhung(P); veLai();
  }

  function khiBam(e) {
    const b = e.target.closest('[data-lhd]'), P = POP;
    if (!b || b.disabled || !P) return;
    const hd = b.dataset.lhd;
    if (hd === 'ngay') {
      // bấm đúp một ngày = chọn luôn. Tự đếm chứ không dùng dblclick: lần bấm đầu vẽ lại lịch, nút dưới chuột đã là nút mới
      const v = b.dataset.lv, luc = Date.now(), dup = P.bamTruoc && P.bamTruoc.v === v && luc - P.bamTruoc.t < 450;
      P.bamTruoc = { v, t: luc };
      if (dup) { chotNgay(v); return; }
      P.chon = v; P.daChon = true; xemTruoc(P); veLai();
    }
    else if (hd === 'len' || hd === 'xuong') { luot(P, hd === 'len' ? -1 : 1); veLai(); }
    else if (hd === 'xem-thang') { P.namXem = +b.dataset.ly; P.td = P.chon && +P.chon.slice(0, 4) === P.namXem ? P.chon.slice(0, 7) : P.namXem + '-' + hai2(P.dau.m); P.xem = 'thang'; veLai(); }
    else if (hd === 'xem-nam') { P.xem = 'nam'; P.tdNam = P.namXem; P.goNam = ''; veLai(); }
    else if (hd === 'thang-xem') { P.dau = { y: +b.dataset.lv.slice(0, 4), m: +b.dataset.lv.slice(5, 7) }; P.xem = 'ngay'; veLai(); }
    else if (hd === 'nam-xem') { P.namXem = +b.dataset.lv; P.xem = 'thang'; P.td = tdTrongNam(P, P.namXem); veLai(); }
    else if (hd === 'hom-nay') chotNgay(homNay());
    else if (hd === 'xoa') chotNgay('');
    else if (hd === 'ok') chotNgay(P.chon);
    else if (hd === 'chon-thang') chotThang(b.dataset.lv);
    else if (hd === 'thang-nay') chotThang(thangNay());
    else if (hd === 'tat-ca') chotThang('');
  }
  const kepNam = (P, y) => Math.max(P.namMin, Math.min(P.namMax, y));
  function luot(P, n) {
    if (P.xem === 'ngay') P.dau = congThang(P.dau.y, P.dau.m, n);
    else if (P.xem === 'thang') { P.namXem = kepNam(P, P.namXem + n); P.td = tdTrongNam(P, P.namXem); }
    else { P.namXem = kepNam(P, P.namXem + 10 * n); P.tdNam = P.namXem; }
  }
  /** Ô đứng của phím mũi tên khi sang năm y: cùng tháng đang đứng. */
  const tdTrongNam = (P, y) => y + '-' + (P.td ? P.td.slice(5, 7) : '01');
  function baoSaiNam(P) { if (EPL.toast) EPL.toast(t('lich_nam_ngoai', { tu: P.namMin, den: P.namMax }), 'loi'); }

  /* ---------------------------------------------------------------- phím: Esc đóng · Enter chọn · mũi tên di chuyển */
  function phim(e) {
    const P = POP; if (!P) return;
    const k = e.key, tg = e.target;
    if (k === 'Escape') { e.preventDefault(); e.stopPropagation(); dong(false, true); return; }   // không để Esc đóng luôn hộp thoại
    if (k === 'Tab' || e.altKey || e.ctrlKey || e.metaKey) return;
    const trong = P.el.contains(tg);
    if (!trong && tg !== P.c.hien && tg !== P.c.nut && !(P.neo && P.neo.contains(tg))) return;
    if (trong && (k === 'Enter' || k === ' ') && tg.closest('.lich-chan, .lich-dk, .lich-tieu')) return;   // nút trong lịch tự bấm
    const dk = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -1, ArrowDown: 1 }[k];
    const doc = k === 'ArrowUp' || k === 'ArrowDown';
    if (P.xem === 'ngay') {
      if (dk) {
        const goc = P.chon || ngayGanNhat(P, homNay());
        const moi = P.chon ? congNgay(goc, dk * (doc ? 7 : 1)) : goc;
        if (trongKhoang(moi, P.min, P.max)) { P.chon = moi; P.daChon = true; choVaoKhung(P); xemTruoc(P); veLai(); }
      } else if (k === 'PageUp' || k === 'PageDown') {
        const p = tach(P.chon || ngayGanNhat(P, homNay())), q = congThang(p.y, p.m, (k === 'PageUp' ? -1 : 1) * (e.shiftKey ? 12 : 1));
        const moi = ghep(q.y, q.m, Math.min(p.d, soNgayThang(q.y, q.m)));
        if (trongKhoang(moi, P.min, P.max)) { P.chon = moi; P.daChon = true; choVaoKhung(P); xemTruoc(P); veLai(); }
      } else if (k === 'Enter') {
        const v = P.c.hien ? docGo(P.c.hien.value) : P.chon;      // ô hiện luôn khớp ngày đang bấm, trừ khi người dùng gõ dở
        if (v === null || (v && !trongKhoang(v, P.min, P.max))) baoSai(P.c); else chotNgay(v);
      } else return;
      e.preventDefault(); e.stopPropagation();
      return;
    }
    // gõ bốn số năm khi đang ở lưới tháng / lưới năm → nhảy tới năm đó (ô hiện ngày không nhận các số này)
    if (/^\d$/.test(k)) {
      P.goNam = (P.goNam || '') + k;
      clearTimeout(P.hGo); P.hGo = setTimeout(() => { if (POP === P && P.goNam) { P.goNam = ''; veLai(); } }, 1500);
      if (P.goNam.length === 4) {
        const y = +P.goNam; P.goNam = '';
        if (y >= P.namMin && y <= P.namMax) { P.namXem = y; P.tdNam = y; P.td = tdTrongNam(P, y); P.xem = 'thang'; } else baoSaiNam(P);
      }
      veLai(); e.preventDefault(); e.stopPropagation();
      return;
    }
    if (P.xem === 'thang') {
      if (dk) {
        const p = P.td || P.namXem + '-01';
        const q = congThang(+p.slice(0, 4), +p.slice(5, 7), dk * (doc ? 4 : 1));
        if (q.y >= P.namMin && q.y <= P.namMax) { P.td = q.y + '-' + hai2(q.m); P.namXem = q.y; veLai(); }
      } else if (k === 'Enter' || k === ' ') {
        const v = P.td || tdTrongNam(P, P.namXem);
        if (P.kieu === 'thang') chotThang(v);
        else { P.dau = { y: +v.slice(0, 4), m: +v.slice(5, 7) }; P.xem = 'ngay'; veLai(); }
      } else return;
      e.preventDefault(); e.stopPropagation();
      return;
    }
    // xem năm
    if (dk) { P.tdNam = kepNam(P, (P.tdNam || P.namXem) + dk * (doc ? 4 : 1)); P.namXem = P.tdNam; veLai(); }
    else if (k === 'Enter' || k === ' ') {
      const y = P.tdNam || P.namXem;
      P.namXem = y; P.xem = 'thang'; P.td = tdTrongNam(P, y); veLai();
    } else return;
    e.preventDefault(); e.stopPropagation();
  }
  function ngoai(e) {
    const P = POP; if (!P) return;
    if (P.el.contains(e.target) || (P.neo && P.neo.contains(e.target))) return;
    dong(true);
  }
  function cuon(e) {
    const P = POP; if (!P || (e.target && e.target.nodeType === 1 && P.el.contains(e.target))) return;
    datViTri();
  }
  // đổi cỡ cửa sổ: chờ chung.js tính lại --ty-le (nó chờ 60 ms) rồi mới đo, đổi zoom và số tháng
  let hCoLai = 0;
  function coLai() {
    clearTimeout(hCoLai);
    hCoLai = setTimeout(() => {
      const P = POP; if (!P) return;
      const cu = P.soThang; boCuc();
      if (P.soThang !== cu) { choVaoKhung(P); veLai(); } else datViTri();
    }, 90);
  }

  /** Đặt lịch dưới ô (hết chỗ thì lên trên), không tràn mép màn hình.
   *  Đo chứ không đoán: đặt thử ở 0 rồi 100 để biết gốc toạ độ và tỷ lệ zoom thật của chính lịch (zoom của ứng dụng,
   *  lớp trên cùng hay không) — jsdom không có bố cục thì đo ra 0, để yên ở góc. */
  function datViTri() {
    const P = POP; if (!P) return;
    const el = P.el, neo = P.neo;
    if (!neo || !neo.isConnected) return dong(false);
    const r = neo.getBoundingClientRect();
    const vw = window.innerWidth || document.documentElement.clientWidth || 0;
    const vh = window.innerHeight || document.documentElement.clientHeight || 0;
    el.style.maxHeight = ''; el.style.left = '0px'; el.style.top = '0px';
    const a = el.getBoundingClientRect();
    el.style.left = '100px'; el.style.top = '100px';
    const b = el.getBoundingClientRect();
    let k = (b.left - a.left) / 100; if (!(k > 0.05 && k < 20)) k = 1;
    if (!a.width || !vw || !vh) { el.style.left = '0px'; el.style.top = '0px'; return; }
    if (r.bottom < 0 || r.top > vh || (!r.width && !r.height)) return dong(true);     // ô đã cuộn khuất / bị ẩn
    const LE = 8, w = a.width;
    let hh = a.height;
    if (hh > vh - 2 * LE) { el.style.maxHeight = ((vh - 2 * LE) / k) + 'px'; hh = vh - 2 * LE; }
    let x = r.left;
    if (x + w > vw - LE) x = vw - LE - w;
    if (x < LE) x = LE;
    let y = r.bottom + 4;
    if (y + hh > vh - LE) { const tren = r.top - 4 - hh; y = tren >= LE ? tren : Math.max(LE, vh - LE - hh); }
    el.style.left = ((x - a.left) / k) + 'px';
    el.style.top = ((y - a.top) / k) + 'px';
  }

  /* ================================================================ Khởi động */
  function doiNgonNgu() {
    DANG_GAN.forEach((c) => { if (!c.goc.isConnected) { DANG_GAN.delete(c); return; } try { c.lamMoi(true); } catch (e) { /* bỏ qua */ } });
    if (POP) veLai();
  }
  /** Bấm nhãn của ô gốc (label for=…): ô gốc đã ẩn nên đưa con trỏ sang ô hiện / nút tháng. */
  function bamNhan(e) {
    const lab = e.target && e.target.closest && e.target.closest('label');
    if (!lab) return;
    const ctl = lab.control || (lab.htmlFor && document.getElementById(lab.htmlFor));
    const c = ctl && GAN.get(ctl);
    if (!c || c.phu || (c.hien && e.target === c.hien)) return;
    const f = c.hien || c.nut;
    if (f && !f.disabled) f.focus();
  }
  function batDau() {
    quet(document);
    new MutationObserver(khiDoiCay).observe(document.documentElement, { childList: true, subtree: true });
    document.addEventListener('click', bamNhan);
    const ghiTT = () => { tuongTac = Date.now(); };
    document.addEventListener('pointerdown', ghiTT, true);
    document.addEventListener('keydown', ghiTT, true);
  }

  vaSetter();
  EPL.khiDoiNN = (EPL.khiDoiNN || []).concat([doiNgonNgu]);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', batDau); else batDau();

  /** Cho module / bộ kiểm: EPL.lich.quet(goc) gắn ngay (khỏi chờ MutationObserver), .dong() đóng lịch đang mở. */
  EPL.lich = { quet: (goc) => quet(goc || document), dong: () => dong(false), docGo, hienNgay };
  window.EPL_LICH = true;
})();
