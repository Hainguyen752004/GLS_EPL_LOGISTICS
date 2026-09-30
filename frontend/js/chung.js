/* EPL Lào — phần dùng chung của giao diện.
 *
 * Gồm: gọi API kèm phiên, ngôn ngữ (vi · lo · en · vi+lo), đăng nhập, thanh điều hướng,
 * nạp module theo #/ten-module, định dạng số/ngày, hộp thoại trong ứng dụng.
 *
 * MỘT MODULE = MỘT THƯ MỤC modules/<id>/ với ba tệp <id>.html · <id>.css · <id>.js.
 * Tệp .js đăng ký: EPL.modules['<id>'] = { init(root, ctx), onLang() }.
 * Khung này KHÔNG biết nội dung module; sai đâu mở đúng thư mục đó mà sửa.
 */
(function () {
  'use strict';
  const EPL = window.EPL = { modules: {} };

  /* ================================================================ API */
  const KHOA_PHIEN = 'epl_lao_phien';
  const API = EPL.API = {
    // Không tick "ghi nhớ" thì phiên nằm ở sessionStorage: đóng trình duyệt là mất, đúng thói quen
    // của máy dùng chung ngoài bãi. Đọc thì phải dò cả hai chỗ.
    token() {
      try { return localStorage.getItem(KHOA_PHIEN) || sessionStorage.getItem(KHOA_PHIEN) || ''; }
      catch (e) { return ''; }
    },
    async goi(duong, tuy_chon = {}) {
      const dau = { 'Accept': 'application/json' };
      if (tuy_chon.body !== undefined) dau['Content-Type'] = 'application/json';
      const tk = API.token(); if (tk) dau['Authorization'] = 'Bearer ' + tk;
      const r = await fetch(duong, { method: tuy_chon.method || (tuy_chon.body !== undefined ? 'POST' : 'GET'),
        headers: dau, body: tuy_chon.body !== undefined ? JSON.stringify(tuy_chon.body) : undefined });
      let d = null; try { d = await r.json(); } catch (e) { d = null; }
      if (r.status === 401 && !duong.startsWith('/api/dang-nhap')) { AUTH.dangXuat(false); throw new LoiAPI(401, 'CHUA_DANG_NHAP', NN.t('login_err')); }
      if (!r.ok) {
        const ct = (d && d.detail) || {};
        // Lỗi NGHIỆP VỤ của mình luôn có dạng {ma, loi} bằng tiếng người. Còn 404 kèm chuỗi thô
        // "Not Found" là của FastAPI: đường API không tồn tại, gần như luôn vì máy chủ đang chạy
        // bản cũ hơn giao diện. Nói thẳng câu đó ra, đừng bày chữ tiếng Anh kỹ thuật lên màn.
        if (r.status === 404 && typeof ct === 'string' && duong.startsWith('/api/')) {
          throw new LoiAPI(404, 'THIEU_DUONG_API', NN.t('err_old_server'));
        }
        throw new LoiAPI(r.status, ct.ma || 'LOI', ct.loi || (typeof ct === 'string' ? ct : NN.t('err_generic')));
      }
      // Danh sách phân trang (24/09, dữ liệu cả năm): máy chủ gửi tổng số dòng khớp ở header X-Tong — gắn vào mảng
      // thành `ds.tong` (không liệt kê được, nên không lẫn vào dữ liệu hay vào tệp Excel xuất ra).
      const tong = r.headers && r.headers.get('X-Tong');
      if (Array.isArray(d) && tong != null && tong !== '') Object.defineProperty(d, 'tong', { value: +tong, enumerable: false });
      // máy chủ chỉ đếm tới 10.000 (đếm cả năm là tăng theo dữ liệu) — còn nhiều hơn thì hiện "10.000+"
      if (Array.isArray(d) && r.headers.get('X-Tong-Tran') === '1') Object.defineProperty(d, 'tongTran', { value: true, enumerable: false });
      return d;
    },
    /** Gửi tệp (multipart) — không đặt Content-Type để trình duyệt tự ghi boundary. */
    async tep(duong, formData) {
      const dau = { 'Accept': 'application/json' }; const tk = API.token(); if (tk) dau['Authorization'] = 'Bearer ' + tk;
      const r = await fetch(duong, { method: 'POST', headers: dau, body: formData });
      let d = null; try { d = await r.json(); } catch (e) { d = null; }
      if (!r.ok) { const ct = (d && d.detail) || {}; throw new LoiAPI(r.status, ct.ma || 'LOI', ct.loi || NN.t('err_generic')); }
      return d;
    },
    get: (d) => API.goi(d),
    post: (d, b) => API.goi(d, { method: 'POST', body: b === undefined ? {} : b }),
    put: (d, b) => API.goi(d, { method: 'PUT', body: b }),
    del: (d) => API.goi(d, { method: 'DELETE' }),
  };
  class LoiAPI extends Error { constructor(status, ma, loi) { super(loi); this.status = status; this.ma = ma; } }
  EPL.LoiAPI = LoiAPI;

  /* ================================================================ Ngôn ngữ */
  const NGON_NGU = ['vi', 'lo', 'en', 'both'];
  const NHAN_NN = { vi: 'Tiếng Việt', lo: 'ພາສາລາວ', en: 'English', both: 'VI + ລາວ' };
  const TU_DIEN = window.EPL_TU_DIEN || {};
  let lang = 'vi';
  try { const l = localStorage.getItem('epl_lao_lang'); if (NGON_NGU.includes(l)) lang = l; } catch (e) { /* bỏ qua */ }

  const NN = EPL.NN = {
    get lang() { return lang; },
    /** Chữ THUẦN (cho placeholder, title, toast): bỏ thẻ HTML trong từ điển. Chế độ vi+lo → "vi / lo".
     *  Không có khoá → trả chính khoá để lộ ra mà sửa. */
    t(khoa, thay) {
      const m = TU_DIEN[khoa];
      let s;
      if (!m) s = khoa;
      else if (lang === 'both') s = (m.vi || '') + (m.lo ? ' / ' + m.lo : '');
      else s = m[lang] || m.vi || khoa;
      s = s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      return thay ? s.replace(/\{(\w+)\}/g, (_, k) => (thay[k] === undefined ? '' : thay[k])) : s;
    },
    /** HTML. Chuỗi trong từ điển là của mình, có thẻ <span class="sub">, <small> — TRẢ NGUYÊN, không thoát
     *  (đã có lần thoát nhầm và tiêu đề hiện chữ "<span class="sub">" ra màn). Giá trị thay {x} thì thoát,
     *  vì đó là dữ liệu (mã phiếu, con số). Chế độ vi+lo → dòng Việt, dưới là dòng Lào nhỏ. */
    h(khoa, thay) {
      const m = TU_DIEN[khoa];
      if (!m) return esc(khoa);
      const th = (s) => thay ? s.replace(/\{(\w+)\}/g, (_, k) => esc(thay[k] === undefined ? '' : thay[k])) : s;
      if (lang === 'both') return th(m.vi || '') + (m.lo ? '<span class="lo-sub" lang="lo">' + th(m.lo) + '</span>' : '');
      return th(m[lang] || m.vi || khoa);
    },
    /** Ghép nhiều mảnh thành MỘT khối hai dòng ở chế độ vi+lo: mảnh {k:'khoá'} được dịch, chuỗi thường giữ nguyên.
     *  Dùng cho dòng "Tổng · 3 chuyến": trước đây mỗi khoá tự xuống dòng Lào riêng nên đọc rất rối. */
    ghep(manh) {
      const lay = (ng) => manh.map(m => typeof m === 'string' ? esc(m) : (TU_DIEN[m.k] ? (TU_DIEN[m.k][ng] || TU_DIEN[m.k].vi || m.k) : m.k)).join('');
      if (lang === 'both') return lay('vi') + '<span class="lo-sub" lang="lo">' + lay('lo') + '</span>';
      return lay(lang);
    },
    /** Áp mọi data-i18n trong một gốc DOM. */
    apDung(root) {
      (root || document).querySelectorAll('[data-i18n]').forEach(el => {
        // Trong SVG không dựng được HTML: <span> nhét vào <text> là mất chữ. Dùng bản chữ thuần.
        if (el.ownerSVGElement) el.textContent = NN.t(el.dataset.i18n);
        else el.innerHTML = NN.h(el.dataset.i18n);
      });
      (root || document).querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = NN.t(el.dataset.i18nPh); });
      (root || document).querySelectorAll('[data-i18n-title]').forEach(el => { el.title = NN.t(el.dataset.i18nTitle); });
      document.documentElement.lang = lang === 'both' ? 'vi' : lang;
    },
    dat(ma) {
      if (!NGON_NGU.includes(ma)) return;
      lang = ma; try { localStorage.setItem('epl_lao_lang', ma); } catch (e) { /* bỏ qua */ }
      veNutNgonNgu(); NN.apDung(document); veNav(); datTieuDe();
      const m = EPL.modules[moduleHienTai]; if (m && m.onLang) m.onLang();
    },
    danhSach: NGON_NGU, nhan: NHAN_NN,
  };
  /* ---------------------------------------------------------------- chọn ngôn ngữ
   * Hai chỗ, hai cách, cố ý khác nhau:
   *   · MÀN ĐĂNG NHẬP giữ dãy phẳng bốn nút — người mới mở máy phải thấy ngay là có tiếng Lào,
   *     không bắt họ đoán trong một cái nút thả xuống.
   *   · TRONG ỨNG DỤNG là nút thả xuống gọn (cờ + mã), vì chỗ trên thanh chật và người dùng đã
   *     chọn ngôn ngữ của mình từ lúc đăng nhập rồi.
   */
  const CO_NN = {            // cờ vẽ bằng SVG, KHÔNG dùng emoji: Windows hiện emoji cờ thành hai chữ cái
    vi: '<rect width="24" height="16" fill="#DA251D"/><path d="M12 3.4l1.42 4.37h4.6l-3.72 2.7 1.42 4.37L12 12.13l-3.72 2.71 1.42-4.37-3.72-2.7h4.6z" fill="#FFFF00"/>',
    lo: '<rect width="24" height="16" fill="#CE1126"/><rect y="4" width="24" height="8" fill="#002868"/><circle cx="12" cy="8" r="2.7" fill="#fff"/>',
    en: '<rect width="24" height="16" fill="#012169"/><path d="M0 0l24 16M24 0L0 16" stroke="#fff" stroke-width="3.4"/>'
        + '<path d="M0 0l24 16M24 0L0 16" stroke="#C8102E" stroke-width="2"/>'
        + '<path d="M12 0v16M0 8h24" stroke="#fff" stroke-width="5.4"/><path d="M12 0v16M0 8h24" stroke="#C8102E" stroke-width="3.2"/>',
  };
  const MA_NN = { vi: 'VN', lo: 'LA', en: 'EN', both: 'VI·LA' };
  // Tên từng ngôn ngữ, viết trong từng ngôn ngữ giao diện — dòng phụ dưới tên gốc
  const TEN_NN = {
    vi:   { vi: 'Tiếng Việt', lo: 'Tiếng Lào', en: 'Tiếng Anh', both: 'Việt + Lào' },
    lo:   { vi: 'ພາສາຫວຽດນາມ', lo: 'ພາສາລາວ', en: 'ພາສາອັງກິດ', both: 'ຫວຽດ + ລາວ' },
    en:   { vi: 'Vietnamese', lo: 'Lao', en: 'English', both: 'Vietnamese + Lao' },
  };
  const co = (m) => m === 'both'
    ? `<span class="ln-co hai"><svg viewBox="0 0 24 16">${CO_NN.vi}</svg><svg viewBox="0 0 24 16">${CO_NN.lo}</svg></span>`
    : `<span class="ln-co"><svg viewBox="0 0 24 16">${CO_NN[m]}</svg></span>`;

  function veNutNgonNgu() {
    // màn đăng nhập: dãy phẳng như cũ
    document.querySelectorAll('.lang:not(.lang-tha)').forEach(o => {
      o.innerHTML = NGON_NGU.map(m => `<button data-lang="${m}" class="${m === lang ? 'active' : ''}" ${m === 'lo' ? 'lang="lo"' : ''}>${NHAN_NN[m]}</button>`).join('');
      o.querySelectorAll('button').forEach(b => b.addEventListener('click', () => NN.dat(b.dataset.lang)));
    });
    // trong ứng dụng: nút thả xuống
    document.querySelectorAll('.lang-tha').forEach(o => {
      const phu = (m) => {
        const t = (TEN_NN[lang === 'both' ? 'vi' : lang] || TEN_NN.vi)[m];
        return t === NHAN_NN[m] ? TEN_NN.en[m] : t;         // trùng tên gốc thì lấy tên tiếng Anh
      };
      o.innerHTML = `<button type="button" class="ln-nut" aria-haspopup="true" title="${esc(NHAN_NN[lang])}">
          ${co(lang)}<span class="ma">${MA_NN[lang]}</span>
          <svg class="mui" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button>
        <div class="ln-menu" hidden>${NGON_NGU.map(m => `
          <button type="button" class="ln-muc ${m === lang ? 'active' : ''}" data-lang="${m}">
            ${co(m)}
            <span class="tt"><b ${m === 'lo' || m === 'both' ? 'lang="lo"' : ''}>${NHAN_NN[m]}</b><small>${esc(phu(m))}</small></span>
            <span class="ma">${MA_NN[m]}</span>
            <svg class="tick" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></button>`).join('')}</div>`;
      const nut = o.querySelector('.ln-nut'), menu = o.querySelector('.ln-menu');
      nut.addEventListener('click', (e) => { e.stopPropagation(); const mo = menu.hidden; dongMenuPhu(); menu.hidden = !mo; o.classList.toggle('mo', mo); });
      o.querySelectorAll('[data-lang]').forEach(b => b.addEventListener('click', () => { menu.hidden = true; o.classList.remove('mo'); NN.dat(b.dataset.lang); }));
    });
  }
  /** Đóng mọi menu nhỏ đang mở (ngôn ngữ, người dùng). */
  function dongMenuPhu() {
    document.querySelectorAll('.lang-tha').forEach(o => { o.classList.remove('mo'); const m = o.querySelector('.ln-menu'); if (m) m.hidden = true; });
    const n = document.getElementById('nguoiMenu'); if (n) n.hidden = true;
  }

  /* ================================================================ Định dạng */
  const esc = EPL.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // Số kiểu 1,724.46 — đúng như Excel và bản mẫu họ đã duyệt (họ dùng dấu phẩy ngăn nghìn).
  EPL.so = (n, d = 0) => (n === null || n === undefined || n === '' || isNaN(Number(n))) ? '—'
    : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  /* Tiền: Kíp và Đồng ghi tròn đơn vị, các tiền khác hai số lẻ. Đơn vị LUÔN đi kèm con số —
     phiếu này cước USD, phiếu kia Nhân dân tệ, con số trần không nói được nó là tiền gì. */
  EPL.TIEN_TE = ['LAK', 'USD', 'THB', 'VND', 'CNY'];
  EPL.leTien = (ma) => (String(ma || 'LAK').toUpperCase() === 'LAK' || String(ma).toUpperCase() === 'VND') ? 0 : 2;
  EPL.tien = (n, ma, d) => n === null || n === undefined ? '—' : EPL.so(n, d === undefined ? EPL.leTien(ma) : d) + (ma ? ' ' + ma : '');
  /** Gộp nhiều loại tiền thành một chuỗi: {USD: 8101.36, CNY: 12000} → "8,101.36 USD · 12,000 CNY" */
  EPL.tienGop = (d, phanCach = ' · ') => {
    const ds = Object.entries(d || {}).filter(([, v]) => v);
    return ds.length ? ds.map(([m, v]) => EPL.tien(v, m)).join(phanCach) : '—';
  };
  EPL.ngay = (s) => { if (!s) return '—'; const d = new Date(String(s).slice(0, 10) + 'T00:00:00'); return isNaN(d) ? s : d.toLocaleDateString('en-GB'); };
  EPL.ngayGio = (s) => { if (!s) return '—'; const d = new Date(s); return isNaN(d) ? s : d.toLocaleDateString('en-GB') + ' ' + d.toTimeString().slice(0, 5); };
  EPL.homNay = () => new Date().toISOString().slice(0, 10);
  EPL.thangNay = () => new Date().toISOString().slice(0, 7);
  EPL.doc = (v) => parseFloat(String(v == null ? '' : v).replace(/,/g, '')) || 0;
  // BẢN CHẤT đề nghị theo LOẠI XE (chủ dự án 29/09): xe nhà → tạm ứng nội bộ · xuất nội bộ; xe thuê, EPL ứng → tạm ứng ghi
  // công nợ chủ xe · dầu kho là xuất bán cho chủ xe. `loai`: 'tam_ung' | 'xuat'; `ht`: mã máy chủ (noi_bo · cong_no_chu_xe · xuat_ban).
  EPL.banChat = (loai, ht, chuXe) => {
    if (!ht) return '';
    const ten = NN.h('ht_' + loai + '_' + ht);
    return ht === 'noi_bo' || !chuXe ? ten : `${ten} · <b lang="lo">${EPL.esc(chuXe)}</b>`;
  };
  EPL.maBanChat = (loai, company) => company === 'joint' ? (loai === 'tam_ung' ? 'cong_no_chu_xe' : 'xuat_ban') : 'noi_bo';
  EPL.tag = (ma, khoa) => `<span class="tag ${esc(ma)}">${NN.h(khoa || ('s_' + ma))}</span>`;
  EPL.khoanMuc = (d) => d.item_key ? NN.t(d.item_key) : (d.item_name || '—');

  /* ================================================================ Hộp thoại & toast */
  EPL.toast = (chu, loai) => {
    const t = document.getElementById('toast'); t.textContent = chu; t.className = 'toast ' + (loai || ''); t.hidden = false;
    clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3200);
  };
  EPL.baoLoi = (e) => EPL.toast(e && e.message ? e.message : String(e), 'loi');
  /** Hộp xác nhận trong ứng dụng. Trả true/false. `noiDungHtml` tuỳ chọn. */
  EPL.hoi = (tieuDe, noiDungHtml, nhanOk) => new Promise(res => {
    const dlg = document.getElementById('hop-thoai');
    document.getElementById('ht-tieu-de').textContent = tieuDe;
    document.getElementById('ht-noi-dung').innerHTML = noiDungHtml || '';
    document.getElementById('ht-ok').textContent = nhanOk || NN.t('ok');
    document.getElementById('ht-huy').textContent = NN.t('cancel');
    const xong = () => { dlg.removeEventListener('close', xong); res(dlg.returnValue === 'ok'); };
    dlg.addEventListener('close', xong); dlg.returnValue = ''; dlg.showModal();
    NN.apDung(dlg);
  });
  /** Hộp nhập một/nhiều ô: fields = [{id,label(khoa),type,value,options}] → object hoặc null. */
  EPL.hopNhap = async (tieuDe, fields, nhanOk) => {
    const html = fields.map(f => `<div class="field"><label>${NN.h(f.label)}</label>${
      f.type === 'select' ? `<select id="hn-${f.id}">${(f.options || []).map(o => `<option value="${esc(o[0])}" ${o[0] === f.value ? 'selected' : ''} ${o[2] ? 'disabled' : ''}>${esc(o[1])}</option>`).join('')}</select>`
      : f.type === 'textarea' ? `<textarea id="hn-${f.id}" rows="3">${esc(f.value || '')}</textarea>`
      // Ô số PHẢI nhận số lẻ: cân 40,6 tấn, tiền 1.812,80 USD, tỷ giá, lít dầu. Thiếu step="any" thì trình duyệt
      // chỉ nhận số nguyên và chặn nút Đồng ý bằng câu tiếng Anh — Bãi không báo xe tới được, KT không ghi thu được.
      : `<input id="hn-${f.id}" type="${f.type || 'text'}" ${f.type === 'number' ? 'step="any" inputmode="decimal"' : ''} ${f.placeholder ? `placeholder="${esc(f.placeholder)}"` : ''} value="${esc(f.value == null ? '' : f.value)}" ${f.lo ? 'lang="lo"' : ''}>`}</div>`).join('');
    const ok = await EPL.hoi(tieuDe, html, nhanOk);
    if (!ok) return null;
    const ra = {}; fields.forEach(f => { const el = document.getElementById('hn-' + f.id); ra[f.id] = el ? el.value : undefined; });
    return ra;
  };

  /* ================================================================ Định khoản (Acc code từ API bên công nợ) */
  let ACC_CACHE = null;
  /** Danh mục Acc code — tải một lần, dùng chung mọi module. Trả {data, source}. */
  /** Ô CHỌN PHIẾU cho dữ liệu cả năm (24/09): một năm ~365.000 phiếu thì ô chọn không liệt kê hết được nữa.
   *  Nạp 50 phiếu mới nhất (lọc thêm bằng `loc`, ví dụ 'locked=true'); gõ vào ô tìm thì máy chủ tìm trên TOÀN BỘ phiếu.
   *  Phiếu đang mở luôn có mặt trong ô chọn, kể cả khi nó không nằm trong trang vừa nạp.
   *    const oc = EPL.oChonPhieu({ tim, chon, nhan: p => '…', loc, khiTim })   →  await oc.nap(); oc.ve(phieuDangMo)  */
  EPL.oChonPhieu = (o) => {
    let ds = [];
    const nap = async () => {
      const t = o.tim ? o.tim.value.trim() : '';
      ds = await API.get('/api/trips?co=50' + (o.loc ? '&' + o.loc : '') + (t ? '&q=' + encodeURIComponent(t) : ''));
      return ds;
    };
    const ve = (hien) => {
      const cac = hien && hien.id && !ds.some(p => p.id === hien.id) ? [hien, ...ds] : ds;
      o.chon.innerHTML = cac.map(p => `<option value="${esc(p.id)}">${o.nhan(p)}</option>`).join('')
        + (ds.tong > ds.length ? `<option value="" disabled>… ${EPL.so(ds.length)} / ${EPL.so(ds.tong)}${ds.tongTran ? '+' : ''}</option>` : '')
        || `<option value="">${NN.h('no_data')}</option>`;
      o.chon.value = hien && hien.id ? hien.id : (cac[0] ? cac[0].id : '');
    };
    if (o.tim) {
      let hen = null;
      o.tim.addEventListener('input', () => { clearTimeout(hen); hen = setTimeout(() => nap().then(() => o.khiTim && o.khiTim(ds)).catch(EPL.baoLoi), 350); });
    }
    return { nap, ve, get ds() { return ds; } };
  };

  EPL.accCodes = async (refresh) => {
    if (ACC_CACHE && !refresh) return ACC_CACHE;
    try { ACC_CACHE = await API.get('/api/acc-codes' + (refresh ? '?refresh=true' : '')); }
    catch (e) { ACC_CACHE = { data: [], source: 'error', message: e.message }; }
    return ACC_CACHE;
  };
  /** Hộp chọn định khoản "Nợ / Có". Mỗi nửa chọn từ danh mục anh Khang; nửa hiện tại không có trong
   *  danh mục vẫn được giữ làm một tuỳ chọn có ghi rõ "không có trong danh mục" — không tự đổi mã của họ. */
  EPL.chonDinhKhoan = async (hienTai) => {
    const acc = await EPL.accCodes();
    const [no, co] = String(hienTai || '/').split('/');
    const ds = (acc.data || []).slice().sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }));
    const opts = (chon) => {
      // Mã TỔNG (danh mục anh Khang ghi "không ghi sổ", ví dụ 10, 70) không định khoản được — hiện mờ để thấy
      // cây tài khoản nhưng không chọn nhầm. Phiếu đang mang sẵn mã tổng thì vẫn giữ để thấy, kèm chữ cảnh báo.
      const o = ds.map(x => [x.code, x.code + ' — ' + (x.description || x.name || '') + (x.postable === false ? ' · ' + NN.t('acct_header') : ''),
        x.postable === false && x.code !== chon]);
      if (chon && !ds.some(x => x.code === chon)) o.unshift([chon, chon + ' — ' + NN.t('acct_not_in_catalogue')]);
      return o;
    };
    const v = await EPL.hopNhap(NN.t('acct_pair') + (acc.source === 'remote' || acc.source === 'cached' ? '' : ' · ' + NN.t('acct_source_fallback')), [
      { id: 'no', label: 'acct_debit', type: 'select', value: no, options: opts(no) },
      { id: 'co', label: 'acct_credit', type: 'select', value: co, options: opts(co) },
    ], NN.t('ok'));
    return v ? v.no + '/' + v.co : null;
  };

  /* ================================================================ Đăng nhập */
  let USER = null;
  /** Thân trang mang lớp vai-<vai> để CSS ẩn/hiện theo vai — ví dụ `.vai-yard .tien{display:none}`:
   *  Bãi nhập cân, lít, khoản đi đường nhưng KHÔNG thấy tiền (đơn giá, thành tiền, quy đổi, giá dầu, lãi). */
  function apLopVai() {
    [...document.body.classList].filter(c => c.startsWith('vai-')).forEach(c => document.body.classList.remove(c));
    if (USER) document.body.classList.add('vai-' + USER.role);
  }
  const AUTH = EPL.AUTH = {
    get user() { return USER; },
    get role() { return USER ? USER.role : ''; },
    la: (...vai) => USER && (USER.role === 'admin' || vai.includes(USER.role)),
    async dangNhap(u, p) {
      const g = await API.post('/api/dang-nhap', { username: u, password: p });
      const nho = document.getElementById('lgNho');
      try {
        const kho = (nho && !nho.checked) ? sessionStorage : localStorage;
        localStorage.removeItem(KHOA_PHIEN); sessionStorage.removeItem(KHOA_PHIEN);
        kho.setItem(KHOA_PHIEN, g.token);
      } catch (e) { /* bỏ qua */ }
      USER = g.user;
      // C9.2 (anh Khampla): máy ở bãi mặc định tiếng Lào. Chỉ áp khi máy này CHƯA từng chọn ngôn ngữ và
      // người vào là người ở hiện trường (Bãi · thủ kho · tài xế); ai đã chọn rồi thì giữ nguyên chọn của họ.
      try {
        if (!localStorage.getItem('epl_lao_lang') && ['yard', 'depot', 'driver'].includes(USER.role)) NN.dat('lo');
      } catch (e) { /* bỏ qua */ }
      // Mờ màn đăng nhập rồi mới đổi sang ứng dụng — chuyển cảnh mềm thay vì cụp một cái.
      const lg = document.getElementById('login');
      if (lg && !lg.hidden && typeof lg.getAnimations === 'function') {
        lg.classList.add('di');
        await new Promise(r => setTimeout(r, 240));
        lg.classList.remove('di');
      }
      hienApp();
    },
    dangXuat(xoaHash = true) {
      try { localStorage.removeItem(KHOA_PHIEN); sessionStorage.removeItem(KHOA_PHIEN); } catch (e) { /* bỏ qua */ }
      USER = null; apLopVai();
      // Xoá nội dung màn đang mở: máy ở bãi dùng chung, người sau đăng nhập không được thấy
      // loáng qua số liệu của người trước trong lúc màn mới còn đang tải.
      const nd = document.getElementById('noi-dung'); if (nd) nd.replaceChildren();
      moduleHienTai = '';
      document.getElementById('app').hidden = true; document.getElementById('login').hidden = false;
      document.getElementById('lgU').value = ''; document.getElementById('lgP').value = '';
      document.getElementById('lgP').type = 'password';
      const nm = document.getElementById('lgMat'); if (nm) nm.classList.remove('mo');
      const ne = document.getElementById('lgErr'); if (ne) { ne.textContent = ''; ne.hidden = true; }
      if (xoaHash) location.hash = '';
      veTaiKhoanMau(); chayNhanXe();
    },
  };
  /* Chọn nhanh tài khoản, gom theo NHÓM VAI như bản mẫu. Hệ có chín vai nhưng người dùng chỉ nghĩ
     theo năm nhóm việc, nên gộp lại cho dễ tìm: quản trị · kế toán · bãi và kho · quỹ · tài xế. */
  const NHOM_VAI = [
    { id: 'admin', khoa: 'lg_g_admin', vai: ['admin'] },
    { id: 'acct', khoa: 'lg_g_acct', vai: ['acct', 'expacct', 'rev'] },
    { id: 'wh', khoa: 'lg_g_wh', vai: ['yard', 'fuel', 'depot', 'parts', 'repair'] },
    { id: 'cash', khoa: 'lg_g_cash', vai: ['treasury', 'cash'] },
    { id: 'drv', khoa: 'lg_g_drv', vai: ['driver'] },
  ];
  async function veTaiKhoanMau() {
    const o = document.getElementById('acctList');
    try {
      const ds = await API.get('/api/tai-khoan-mau');
      const dang = document.getElementById('lgU').value.trim();
      o.innerHTML = NHOM_VAI.map(n => {
        // Máy chủ trả theo thứ tự chữ cái của vai, nên Bãi Thà Bốc (yard) rơi xuống cuối nhóm kho và
        // bị khuất. Xếp lại theo đúng thứ tự vai ghi trong nhóm: vai chính của nhóm đứng trước.
        const trong = ds.filter(a => n.vai.includes(a.role))
          .sort((a, b) => n.vai.indexOf(a.role) - n.vai.indexOf(b.role) || a.username.localeCompare(b.username));
        if (!trong.length) return '';
        return `<div class="role__head"><b>${NN.h(n.khoa)}</b></div>` + trong.map(a => {
          const vai = NN.t('r_' + a.role);
          // Nhóm chỉ có một tài khoản thì trải hết hàng, khỏi cụt chữ vì nửa cột quá hẹp
          return `<button type="button" class="person ${trong.length === 1 ? 'mot' : ''} ${a.username === dang ? 'active' : ''}" data-u="${esc(a.username)}"
            title="${esc(a.username + ' · ' + vai)}">
            <span class="person__ini">${esc(a.avatar)}</span>
            <span class="tt"><span lang="lo">${esc(a.full_name)}</span><small>${esc(a.username)} · ${esc(vai)}</small></span>
            <svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg></button>`;
        }).join('');
      }).join('');
      o.querySelectorAll('.person').forEach(b => b.addEventListener('click', () => {
        document.getElementById('lgU').value = b.dataset.u;
        document.getElementById('lgP').value = '1234';
        o.querySelectorAll('.person').forEach(x => x.classList.toggle('active', x === b));
        dangNhapTuForm();
      }));
    } catch (e) { o.innerHTML = `<div class="small neg" style="padding:12px 14px">${esc(e.message)}</div>`; }
  }
  // Cờ chống bấm hai lần: đang gọi máy chủ mà bấm nữa thì bỏ qua, không gửi thêm lần đăng nhập.
  let dangBan = false;
  async function dangNhapTuForm() {
    if (dangBan) return;
    const u = document.getElementById('lgU').value.trim(), p = document.getElementById('lgP').value;
    const err = document.getElementById('lgErr'), nut = document.getElementById('lgBtn');
    err.textContent = ''; err.hidden = true; dangBan = true; nut.classList.add('dang-vao');
    try {
      await AUTH.dangNhap(u, p);
    } catch (e) {
      // Xoá rồi gán lại để hoạt ảnh "rung" chạy lại mỗi lần sai, không chỉ lần đầu.
      err.textContent = ''; void err.offsetWidth;
      err.textContent = e.ma === 'SAI_TAI_KHOAN' ? NN.t('login_err') : e.message;
      err.hidden = false;
    } finally { dangBan = false; nut.classList.remove('dang-vao'); }
  }
  function hienApp() {
    apLopVai();
    dungNhanXe();
    document.getElementById('login').hidden = true; document.getElementById('app').hidden = false;
    document.getElementById('roleAv').textContent = USER.avatar || USER.full_name.slice(0, 2).toUpperCase();
    document.getElementById('uName').textContent = USER.full_name;
    document.getElementById('uRole').innerHTML = NN.h('r_' + USER.role);
    noiVoBoc(); apKieuXem(); veNav(); dieuHuong(); taiDem();
  }

  /* ---------------------------------------------------------------- nhãn xe trên sơ đồ đăng nhập
   * Bản đồ ở nửa trái có bốn chấm xe; nhãn "Xe đang ở đây" nhảy lần lượt sang từng chấm cho màn
   * đỡ chết cứng. Dừng hẳn khi người dùng đặt "giảm chuyển động", và dừng khi rời màn đăng nhập
   * để không chạy vô ích suốt phiên làm việc.
   */
  let nhipXe = null;
  function chayNhanXe() {
    dungNhanXe();
    const nhan = document.getElementById('lg-nhan-xe');
    const xe = [...document.querySelectorAll('.lg-xe')];
    if (!nhan || !xe.length) return;
    let i = 0;
    const dat = () => {
      xe.forEach((x, n) => x.classList.toggle('dam', n === i));
      const v = xe[i].dataset.nhan;
      if (v) nhan.setAttribute('transform', 'translate(' + v + ')');
    };
    dat();
    try { if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return; } catch (e) { /* bỏ qua */ }
    nhipXe = setInterval(() => { i = (i + 1) % xe.length; dat(); }, 3600);
  }
  function dungNhanXe() { if (nhipXe) clearInterval(nhipXe); nhipXe = null; }

  /* ================================================================ Module & điều hướng */
  // Thứ tự nhóm và module đúng theo sheet "ລາຍງານ" của Excel + hai nhóm danh mục/hệ thống.
  const MODULES = EPL.MODULES = [
    { id: 'tong-quan',      nhom: 'mod_transport', nav: 'nav_dash',     ic: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' },
    { id: 'theo-doi',       nhom: 'mod_transport', nav: 'nav_tracking', nav_s: 'nav_tracking_s', ic: 'M3 6h18M3 12h18M3 18h12' },
    { id: 'theo-doi-tuyen', nhom: 'mod_transport', nav: 'nav_track_route', ic: 'M4 18a3 3 0 1 0 0-6 3 3 0 0 0 0 6M20 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6M7 15l10-6' },
    { id: 'phieu-xuat-xe',  nhom: 'mod_transport', nav: 'nav_dispatch', ic: 'M1 3h15v13H1zM16 8h4l3 3v5h-7z' },
    // Hai module dưới là TIỀN BÁN: hoá đơn cho khách và bảng lãi xe liên kết. Bãi không thấy — đó là
    // biên lợi nhuận. Còn tiền tài xế và công nợ nhà cung cấp là chi phí, Bãi xem được.
    // 'hoa-don' (Hoá đơn vận chuyển) và 'hoa-don-gop' (Hoá đơn gộp tháng) dời sang trang kế toán 28/09 (đợt 7a) — xuất hoá
    // đơn, sổ thu tiền, in phiếu thu, gộp tháng ở đó; phiếu bên này giữ bản chép trạng thái (đã xuất hoá đơn, đã thu)
    // Phiếu của bên mình là phiếu ĐỀ NGHỊ (sếp 30/09): đề nghị chi (tạm ứng, nhiên liệu) · đề nghị thu (DO xong) · theo dõi theo DO
    { id: 'de-nghi-chi',    nhom: 'mod_transport', nav: 'nav_de_nghi_chi', vai: ['yard', 'acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel'],
      ic: 'M4 3h16v18l-3-2-3 2-2-2-2 2-3-2-3 2zM8 8h8M8 12h8M8 16h5' },
    { id: 'de-nghi-thu',    nhom: 'mod_transport', nav: 'nav_de_nghi_thu', vai: ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel'],
      ic: 'M4 3h16v18l-3-2-3 2-2-2-2 2-3-2-3 2zM12 7v9M9 13l3 3 3-3' },
    { id: 'chung-tu',       nhom: 'mod_transport', nav: 'nav_vouchers', ic: 'M4 4h16v16H4zM4 9h16M9 9v11M14 13h3M14 17h3' },
    { id: 'phieu-cua-toi',  nhom: 'mod_transport', nav: 'nav_my_slips', ic: 'M12 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10M4 22a8 8 0 0 1 16 0M1 3h15v13H1z', vai: ['driver'], chi_vai: true, khong_xuat: true },
    { id: 'xe-lien-ket',    nhom: 'mod_transport', nav: 'nav_joint', vai: ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel'],    ic: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8' },
    // 'tien-tai-xe' (Tiền chuyến & tiền nước tài xế) và 'tat-toan' (Tất toán tài xế) dời sang trang kế toán 28/09 (đợt 7c) —
    // bản chốt, tờ TT_CHI / TT_THU ở đó; số vẫn tính từ phiếu bên này (đường máy /api/lien-thong/tat-toan…)
    { id: 'nha-cung-cap',   nhom: 'mod_transport', nav: 'nav_supplier', nav_s: 'nav_supplier_s', ic: 'M3 9l9-6 9 6v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM9 21V12h6v9' },
    // 'kho-hang' (Kho hàng) dời sang trang kế toán 28/09 (đợt 5) — sổ, tồn từng lô, điều chỉnh ở đó; dòng hàng vẫn trên phiếu
    // 'cap-phat' (Cấp phát) và 'kho-nhien-lieu' (Kho nhiên liệu) dời sang trang kế toán 28/09 (đợt 4)
    // 'diem-do' (Điểm đổ nhiên liệu) dời sang trang kế toán 28/09 — bản gốc ở đó, bên này chỉ còn bản chép để đọc
    // 'kho-phu-tung' (Kho phụ tùng) dời sang trang kế toán 28/09 — tồn, giá, sổ ở đó; bên này còn danh mục để chọn trên phiếu
    // 'sua-chua' (Lệnh sửa chữa) dời sang trang kế toán 28/09 (đợt 6) — lệnh, chuỗi duyệt, xuất kho, PC_SC ở đó; mục V vẫn trên phiếu
    // 'ban-hang' (Bán hàng) dời sang trang kế toán 28/09 (đợt 6) — phiếu bán, xuất kho, hoá đơn, thu ở đó
    // 'kho-xem' (Xem kho) — sếp 30/09: kho dời về trang logistics, CHỈ XEM theo mặt hàng; thao tác kho do bên kho (anh Toàn)
    { id: 'kho-xem',        nhom: 'mod_warehouse', nav: 'nav_kho_xem', vai: ['yard', 'acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'depot'],
      ic: 'M3 21V9l9-6 9 6v12M3 21h18M8 21v-6h8v6M8 12h8' },
    { id: 'khach-hang',     nhom: 'mod_master',    nav: 'nav_customers', ic: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8' },
    { id: 'xe',             nhom: 'mod_master',    nav: 'nav_vehicles', ic: 'M1 3h15v13H1zM16 8h4l3 3v5h-7zM5.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M18.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5' },
    { id: 'tai-xe',         nhom: 'mod_master',    nav: 'nav_drivers',  ic: 'M12 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10M4 22a8 8 0 0 1 16 0' },
    { id: 'the-cao-toc',    nhom: 'mod_master',    nav: 'nav_toll', nav_s: 'nav_toll_s',
      vai: ['yard', 'acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel'],
      ic: 'M2 7h20v10H2zM2 11h20M6 15h4' },
    { id: 'ty-gia',         nhom: 'mod_master',    nav: 'nav_rates', vai: ['acct', 'expacct', 'rev', 'treasury', 'cash'],
      ic: 'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6' },
    { id: 'tuyen-duong',    nhom: 'mod_master',    nav: 'nav_routes',   ic: 'M6 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6M18 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6M6 9v3a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3' },
    { id: 'quy-trinh',      nhom: 'mod_system',    nav: 'nav_workflow', nav_s: 'nav_workflow_s', ic: 'M12 3v4M6 21v-4M18 21v-4M4 11h16M9 7h6v4H9zM3 17h6v4H3zM15 17h6v4h-6z' },
    { id: 'tai-khoan',      nhom: 'mod_system',    nav: 'nav_users',    ic: 'M12 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10M4 22a8 8 0 0 1 16 0M19 8l2 2-4 4-2-2', vai: ['admin'] },
  ];
  let moduleHienTai = '';
  const daNapJS = new Set(), daNapCSS = new Set();

  // Bốn nhóm module — dùng cho tiêu đề nhóm ở thanh bên và bốn tab ở thanh trên.
  const NHOM_MOD = [
    { id: 'mod_transport', tab: 'tab_transport', ic: 'M1 3h15v13H1zM16 8h4l3 3v5h-7zM5.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M18.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5' },
    { id: 'mod_warehouse', tab: 'tab_warehouse', ic: 'M3 21V9l9-6 9 6v12M3 21h18M9 21v-7h6v7' },
    { id: 'mod_master',    tab: 'tab_master',    ic: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01' },
    { id: 'mod_system',    tab: 'tab_system',    ic: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 13.6H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.7 7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9.4A1.6 1.6 0 0 0 10.4 3V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.4 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z' },
  ];

  // Tài xế chỉ thấy module ghi rõ vai driver; các vai khác thấy mọi module trừ module "chỉ vai".
  // Thủ kho phụ tùng giữ kho phụ tùng; tổ sửa chữa duyệt báo hỏng, ghi mục V trên phiếu, xem tồn kho.
  const MAN_CUA_VAI = {
    parts:  ['xe', 'kho-xem'],            // thao tác kho phụ tùng: ở bên kho; bên này chỉ xem (30/09)
    repair: ['theo-doi-tuyen', 'phieu-xuat-xe', 'xe', 'kho-xem'],   // lệnh sửa chữa: ở trang kế toán (đợt 6)
  };

  function thayDuoc(m) {
    // Hai vai làm MỘT việc duy nhất nên màn của họ phải sạch: tài xế chỉ có phiếu của mình,
    // thủ kho chỉ có hàng chờ cấp dầu và tồn kho nhiên liệu. Module nào muốn cho họ thấy thì
    // phải ghi tên vai đó trong `vai` — không có là không hiện.
    if (AUTH.role === 'driver') return !!(m.vai && m.vai.includes('driver'));
    if (AUTH.role === 'depot') return !!(m.vai && m.vai.includes('depot'));
    // Hai vai ở Thà Bốc (anh Khampla C1.2) cũng làm một việc: liệt kê thẳng màn của họ cho dễ đọc,
    // khỏi phải ghi tên hai vai này vào `vai` của từng module.
    if (MAN_CUA_VAI[AUTH.role]) return MAN_CUA_VAI[AUTH.role].includes(m.id);
    if (m.vai) return AUTH.la(...m.vai);
    return true;
  }
  // null = tài khoản không còn màn nào ở trang điều xe (thủ kho dầu từ 28/09: việc của họ ở trang kế toán)
  const moduleDau = () => { const m = MODULES.find(thayDuoc); return m ? m.id : null; };
  /** Mở một màn ở TRANG KẾ TOÁN (kho, cấp phát… dời sang đó 28/09) trong thẻ mới. Địa chỉ hỏi máy chủ một lần. */
  let _diaChiKT = null;
  EPL.moKeToan = async (man, thamSo) => {
    try {
      if (_diaChiKT === null) _diaChiKT = ((await API.get('/api/lien-thong/dia-chi')) || {}).ke_toan_web || '';
      if (!_diaChiKT) return EPL.toast(NN.t('mo_ke_toan_loi'), 'loi');
      const q = thamSo ? '?' + new URLSearchParams(thamSo) : '';
      window.open(_diaChiKT + '/#/' + (man || '') + q, '_blank', 'noopener');
    } catch (e) { EPL.baoLoi(e); }
  };
  function veKhongCoMan() {
    const nd = document.getElementById('noi-dung');
    nd.innerHTML = `<div class="card" style="max-width:640px"><div class="bd"><h3>${NN.h('khong_co_man')}</h3>
      <p class="muted">${NN.h('khong_co_man_goi_y')}</p><button class="btn primary" id="mo-ke-toan">${NN.h('mo_ke_toan')}</button></div></div>`;
    nd.querySelector('#mo-ke-toan').addEventListener('click', () => EPL.moKeToan(''));
  }
  /** Ô chọn THÁNG thống nhất: mọi <input type="month"> trong màn đổi thành <select> "09/2026". Rà giao diện 23/09:
   *  ô tháng của trình duyệt hiện "---------- ----" khi trống và "September 2026" kiểu Mỹ khi có giá trị. Giữ nguyên
   *  id, `.value` = 'YYYY-MM' và sự kiện change nên mã từng màn không phải đổi. Ô có data-tat-ca thì có dòng
   *  "Tất cả các tháng" (value '') — màn danh sách xem cả kỳ. Gán .value tháng ngoài danh sách thì tự thêm dòng đó. */
  EPL.doiOThang = (goc) => {
    goc.querySelectorAll('input[type="month"]').forEach(o => {
      const s = document.createElement('select');
      s.id = o.id; s.className = (o.className + ' o-thang').trim();
      const nay = new Date(); const ds = [];
      for (let i = 3; i >= -24; i--) { const d = new Date(nay.getFullYear(), nay.getMonth() + i, 1); ds.push(d); }
      const ma = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
      const nhan = (v) => v.slice(5, 7) + '/' + v.slice(0, 4);
      s.innerHTML = (o.hasAttribute('data-tat-ca') ? '<option value="" data-i18n="all_months"></option>' : '')
        + ds.map(d => `<option value="${ma(d)}">${nhan(ma(d))}</option>`).join('');
      const dat = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
      Object.defineProperty(s, 'value', {
        get() { return dat.get.call(this); },
        set(v) {
          v = v ? String(v).slice(0, 7) : '';
          if (v && ![...this.options].some(x => x.value === v)) { const x = document.createElement('option'); x.value = v; x.textContent = nhan(v); this.prepend(x); }
          dat.set.call(this, v);
        },
      });
      s.value = o.value || (o.hasAttribute('data-tat-ca') ? '' : ma(nay));
      o.replaceWith(s);
    });
  };
  /** Các màn một vai BẤT KỲ vào được — cùng luật với thayDuoc (dùng cho màn Tài khoản · vai trò). */
  EPL.manCuaVai = (vai) => MODULES.filter(m => {
    if (vai === 'driver' || vai === 'depot') return !!(m.vai && m.vai.includes(vai));
    if (MAN_CUA_VAI[vai]) return MAN_CUA_VAI[vai].includes(m.id);
    if (m.vai) return vai === 'admin' || m.vai.includes(vai);
    return true;
  });

  /* ---------------------------------------------------------------- kiểu xem
   * Hai kiểu đều có cái lợi riêng nên giữ cả hai, người dùng tự chọn ở nút bánh răng:
   *   'side' thanh bên  — thấy hết màn cùng lúc, gắn được số việc đang chờ cạnh từng mục;
   *   'top'  thanh trên — nhường trọn chiều ngang cho bảng, hợp bảng nhiều cột.
   * Nhớ theo máy (localStorage) chứ không theo tài khoản: một máy ngoài bãi nhiều người dùng chung,
   * nhưng màn hình thì vẫn là màn hình ấy. */
  const K_VIEW = 'epl_lao_kieu_xem', K_HEP = 'epl_lao_thanh_hep', K_GAP = 'epl_lao_nhom_gap';
  const docLS = (k, md) => { try { const v = localStorage.getItem(k); return v === null ? md : v; } catch (e) { return md; } };
  const ghiLS = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* riêng tư thì thôi */ } };
  let kieuXem = docLS(K_VIEW, 'side') === 'top' ? 'top' : 'side';
  let thanhHep = docLS(K_HEP, '0') === '1';
  let nhomGap = new Set((docLS(K_GAP, '') || '').split(',').filter(Boolean));
  let timMenu = '';
  let DEM = {};                                    // số việc đang chờ theo từng module

  const HEP_MAN = 900;                       // khớp với @media (max-width:900px) trong chung.css
  /** Kiểu ĐANG DÙNG THẬT: màn hẹp thì luôn là thanh bên, dù người dùng chọn thanh trên. */
  const kieuThuc = () => ((window.innerWidth || 1600) <= HEP_MAN ? 'side' : kieuXem);
  function apKieuXem() {
    const app = document.getElementById('app'); if (!app) return;
    const kt = kieuThuc();
    app.dataset.view = kt;
    app.dataset.hep = kt === 'side' && thanhHep ? '1' : '0';
    const tbar = document.getElementById('tbar'); if (tbar) tbar.hidden = kt !== 'top';
    // .lang và .userbox là một bản duy nhất — chuyển chỗ chứ không nhân đôi
    const oi = document.getElementById(kt === 'top' ? 'tbarPhai' : 'topbarPhai');
    // Màn đăng nhập cũng có một khối .lang, nên phải gọi đúng khối của ứng dụng bằng id
    const lang = document.getElementById('langApp'), hop = document.getElementById('userbox');
    if (oi && lang) oi.appendChild(lang);
    const chan = document.getElementById(kt === 'top' ? 'tbarPhai' : 'chanOi');
    if (chan && hop) chan.appendChild(hop);
  }
  EPL.datKieuXem = (k) => { kieuXem = k === 'top' ? 'top' : 'side'; ghiLS(K_VIEW, kieuXem); apKieuXem(); veNav(); };

  async function taiDem() {
    try { DEM = await API.get('/api/dem-viec'); } catch (e) { DEM = {}; }
    // Người dùng có thể đăng xuất hoặc đóng trang trong lúc chờ; vẽ vào trang đã mất thì bỏ qua.
    try { veNav(); } catch (e) { /* trang không còn */ }
  }
  EPL.lamMoiDem = taiDem;

  const tenMod = (m, ngan) => NN.h(ngan && m.nav_s ? m.nav_s : m.nav);
  const tenModTho = (m) => NN.t(m.nav);
  const svgIc = (d, cls) => `<svg class="${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"><path d="${d}"/></svg>`;
  const pillDem = (id) => DEM[id] ? `<span class="dem">${DEM[id]}</span>` : '';

  /** Một mục ở thanh bên. `data-ten` để chế độ hẹp còn hiện được mách nhỏ. */
  function nutBen(m) {
    return `<button type="button" class="muc ${m.id === moduleHienTai ? 'active' : ''}" data-mod="${m.id}" data-ten="${esc(tenModTho(m))}" title="${esc(tenModTho(m))}">
      ${svgIc(m.ic, 'ic')}<span class="ten">${tenMod(m, true)}</span>${pillDem(m.id)}</button>`;
  }

  function veThanhBen() {
    const nav = document.getElementById('nav'); if (!nav) return;
    const loc = timMenu.trim().toLowerCase();
    const hop = MODULES.filter(thayDuoc).filter(m => !loc || tenModTho(m).toLowerCase().includes(loc) || m.id.includes(loc));
    let html = '';
    if (!hop.length) html = `<div class="trong">${NN.h('nav_none')}</div>`;
    NHOM_MOD.forEach(n => {
      const trong = hop.filter(m => m.nhom === n.id);
      if (!trong.length) return;
      const gap = !loc && nhomGap.has(n.id);      // đang tìm thì mở hết ra cho thấy kết quả
      html += `<button type="button" class="nav-group ${gap ? 'gap' : ''}" data-nhom="${n.id}">
        <svg viewBox="0 0 24 24" fill="none"><path d="M6 9l6 6 6-6"/></svg><span>${NN.h(n.id)}</span><i class="vach"></i></button>`;
      if (!gap) html += trong.map(nutBen).join('');
    });
    nav.innerHTML = html;
    nav.querySelectorAll('[data-mod]').forEach(b => b.addEventListener('click', () => { location.hash = '#/' + b.dataset.mod; }));
    nav.querySelectorAll('[data-nhom]').forEach(b => b.addEventListener('click', () => {
      const id = b.dataset.nhom;
      if (nhomGap.has(id)) nhomGap.delete(id); else nhomGap.add(id);
      ghiLS(K_GAP, [...nhomGap].join(',')); veThanhBen();
    }));
  }

  /** Thanh trên kiểu MENU THẢ XUỐNG: một hàng, mỗi nhóm một menu mở ra bảng hai cột.
   *  Mỗi dòng có biểu tượng, tên màn và một câu nói màn đó làm gì — đọc là biết vào đâu, thay cho
   *  một hàng dài mười chữ chen nhau. Màn đang mở được tô sáng ngay trong bảng. */
  function veThanhTren() {
    const o2 = document.getElementById('tbar2'); if (!o2) return;
    const hien = MODULES.filter(thayDuoc);
    const cua = hien.find(m => m.id === moduleHienTai);
    const dau = hien[0];
    const rieng = dau && dau.nhom === NHOM_MOD[0].id ? dau : null;   // màn đứng riêng ngoài menu
    const demNhom = (n) => hien.filter(m => m.nhom === n).reduce((a, m) => a + (DEM[m.id] || 0), 0);
    const mucPanel = (m) => `<button type="button" class="mn-muc ${m.id === moduleHienTai ? 'active' : ''}" data-mod="${m.id}">
      <span class="ic">${svgIc(m.ic)}</span>
      <span class="tt"><b>${NN.h(m.nav)}</b><small>${NN.h('d_' + m.id.replace(/-/g, '_'))}</small></span>
      ${DEM[m.id] ? `<span class="dem">${DEM[m.id]}</span>` : ''}</button>`;

    let html = '';
    if (rieng) {
      html += `<div class="mn"><button type="button" class="mn-nut ${rieng.id === moduleHienTai ? 'dang' : ''}" data-mod="${rieng.id}">
        ${svgIc(rieng.ic)}<span>${NN.h(rieng.nav)}</span></button></div>`;
    }
    NHOM_MOD.forEach(n => {
      const trong = hien.filter(m => m.nhom === n.id && m !== rieng);
      if (!trong.length) return;
      const d = demNhom(n.id), dangO = cua && cua.nhom === n.id && cua !== rieng;
      html += `<div class="mn" data-nhom="${n.id}">
        <button type="button" class="mn-nut ${dangO ? 'dang' : ''}"><span>${NN.h(n.tab)}</span>
          ${d ? `<span class="dem">${d}</span>` : ''}
          <svg class="mui" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button>
        <div class="mn-panel ${trong.length < 4 ? 'mot-cot' : ''}" hidden>${trong.map(mucPanel).join('')}</div></div>`;
    });
    o2.innerHTML = html;
    o2.querySelectorAll('[data-mod]').forEach(b => b.addEventListener('click', () => {
      dongMenuTren(); location.hash = '#/' + b.dataset.mod;
    }));
    o2.querySelectorAll('.mn[data-nhom] > .mn-nut').forEach(b => b.addEventListener('click', (e) => {
      e.stopPropagation();
      const mn = b.parentElement, dangMo = mn.classList.contains('mo');
      dongMenuTren();
      if (!dangMo) moMenuTren(mn);
    }));
    // đang mở một menu mà rê sang menu khác thì chuyển luôn, khỏi bấm hai lần
    o2.querySelectorAll('.mn[data-nhom]').forEach(mn => mn.addEventListener('mouseenter', () => {
      if (o2.querySelector('.mn.mo') && !mn.classList.contains('mo')) { dongMenuTren(); moMenuTren(mn); }
    }));
  }
  function moMenuTren(mn) {
    mn.classList.add('mo');
    const p = mn.querySelector('.mn-panel'); if (!p) return;
    p.hidden = false; p.classList.remove('phai');
    // tràn khỏi mép phải thì neo bảng vào bên phải nút
    const r = p.getBoundingClientRect();
    if (r.right > (window.innerWidth || 0) - 8) p.classList.add('phai');
  }
  function dongMenuTren() {
    document.querySelectorAll('#tbar2 .mn.mo').forEach(mn => {
      mn.classList.remove('mo');
      const p = mn.querySelector('.mn-panel'); if (p) p.hidden = true;
    });
  }

  function veNav() {
    if (!USER) return;
    apKieuXem();
    if (kieuThuc() === 'top') veThanhTren(); else veThanhBen();
  }
  EPL.veNav = veNav;

  /* ---------------------------------------------------------------- hộp chọn kiểu xem */
  async function hopGiaoDien() {
    const html = `<div class="chon-view">
      <label><input type="radio" name="kx" value="side" ${kieuXem === 'side' ? 'checked' : ''}>
        <span class="the"><span class="ve side"><i></i></span><b>${NN.h('view_side')}</b><small>${NN.h('view_side_d')}</small></span></label>
      <label><input type="radio" name="kx" value="top" ${kieuXem === 'top' ? 'checked' : ''}>
        <span class="the"><span class="ve top"><i></i><i></i></span><b>${NN.h('view_top')}</b><small>${NN.h('view_top_d')}</small></span></label>
    </div>
    <label class="remember" style="margin-top:6px"><input type="checkbox" id="kxHep" ${thanhHep ? 'checked' : ''}> <span>${NN.h('view_narrow')}</span></label>`;
    const ok = await EPL.hoi(NN.t('view_settings'), html, NN.t('save'));
    if (!ok) return;
    const chon = document.querySelector('input[name="kx"]:checked');
    thanhHep = !!(document.getElementById('kxHep') || {}).checked;
    ghiLS(K_HEP, thanhHep ? '1' : '0');
    EPL.datKieuXem(chon ? chon.value : kieuXem);
    EPL.toast(NN.t('saved'), 'ok');
  }
  EPL.hopGiaoDien = hopGiaoDien;

  function noiVoBoc() {
    const nut = document.getElementById('btnNguoi'), menu = document.getElementById('nguoiMenu');
    if (nut && menu && !nut.dataset.noi) {
      nut.dataset.noi = '1';
      nut.addEventListener('click', (e) => { e.stopPropagation(); menu.hidden = !menu.hidden; });
      menu.querySelectorAll('[data-mn]').forEach(b => b.addEventListener('click', () => {
        menu.hidden = true;
        if (b.dataset.mn === 'doi') AUTH.dangXuat(); else hopGiaoDien();
      }));
    }
    const thu = document.getElementById('btnThuGon');
    if (thu && !thu.dataset.noi) {
      thu.dataset.noi = '1';
      thu.addEventListener('click', () => { thanhHep = !thanhHep; ghiLS(K_HEP, thanhHep ? '1' : '0'); apKieuXem(); });
    }
    const tim = document.getElementById('navTim');
    if (tim && !tim.dataset.noi) {
      tim.dataset.noi = '1';
      tim.addEventListener('input', () => { timMenu = tim.value; veThanhBen(); });
      tim.addEventListener('keydown', (e) => { if (e.key === 'Escape') { tim.value = ''; timMenu = ''; veThanhBen(); } });
    }
    if (!document.body.dataset.noiMenu) {
      document.body.dataset.noiMenu = '1';
      document.addEventListener('click', () => {
        dongMenuPhu();
        dongMenuTren();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
          const t = document.getElementById('navTim');
          if (t && kieuThuc() === 'side' && !thanhHep) { e.preventDefault(); t.focus(); t.select(); }
        }
      });
    }
  }
  EPL.noiVoBoc = noiVoBoc;

  function datTieuDe() {
    const m = MODULES.find(x => x.id === moduleHienTai); const h = document.getElementById('pageTitle');
    if (m && h) h.innerHTML = NN.h('title_' + m.id.replace(/-/g, '_'));
  }
  /** Tỷ lệ co giãn của cả ứng dụng. Khung thiết kế là 1600 × 900.
   *  Lấy số NHỎ HƠN của hai tỷ lệ ngang và dọc: zoom trình duyệt làm cả hai chiều cùng tăng nên
   *  phóng theo đúng mức zoom, còn màn rộng mà thấp (2560 × 900) thì không bị phóng quá rồi tràn đáy.
   *  Kẹp 0,85–2 để màn quá nhỏ vẫn đọc được và màn quá lớn không thành chữ khổng lồ. */
  const KHUNG_W = 1600, KHUNG_H = 900;
  function coGian() {
    const w = window.innerWidth || KHUNG_W, h = window.innerHeight || KHUNG_H;
    const t = Math.min(2, Math.max(0.85, Math.min(w / KHUNG_W, h / KHUNG_H)));
    document.documentElement.style.setProperty('--ty-le', t.toFixed(3));
  }
  EPL.coGian = coGian; coGian();
  let choCoGian = 0;
  let kieuTruoc = '';
  window.addEventListener('resize', () => {
    clearTimeout(choCoGian);
    choCoGian = setTimeout(() => {
      coGian();
      const kt = kieuThuc();
      if (USER && kt !== kieuTruoc) { kieuTruoc = kt; try { veNav(); } catch (e) { /* trang không còn */ } }
    }, 60);
  });

  EPL.di = (id, tham) => {
    const q = tham ? new URLSearchParams(tham).toString() : '';   // không tham số thì đừng để dấu '?' trơ ra trên thanh địa chỉ
    const moi = '#/' + id + (q ? '?' + q : '');
    // Đang đứng đúng địa chỉ đó rồi (ví dụ vừa lưu phiếu mới ở #/phieu-xuat-xe?moi=1 rồi bấm "Tạo phiếu"
    // lần nữa): trình duyệt không bắn hashchange, khung phải tự nạp lại — không thì nút bấm như chết.
    if (location.hash === moi) { dieuHuong(); return; }
    location.hash = moi;
  };
  EPL.thamSo = () => { const q = location.hash.split('?')[1] || ''; return Object.fromEntries(new URLSearchParams(q)); };

  /** Lấy HTML của module, có NHỚ ĐỆM để còn dùng được khi mất mạng.
   *  Kho dầu ngoài hiện trường hay rớt mạng giữa chừng; nếu khung cứ phải tải lại tệp .html mỗi
   *  lần chuyển màn thì mất mạng là cả ứng dụng đứng, dù dữ liệu đã lưu sẵn trong máy. */
  const HTML_DEM = new Map();
  // Dấu phiên bản do máy chủ đóng vào index.html — đổi tệp là đổi đường dẫn nên trình duyệt
  // tự tải lại, và bản nhớ đệm ngoại tuyến của bản cũ cũng không bị dùng nhầm.
  const VER = (window.EPL_VER && window.EPL_VER !== '__VER__') ? window.EPL_VER : '';
  const themVer = (u) => VER ? u + (u.includes('?') ? '&' : '?') + 'v=' + VER : u;
  const khoaHTML = (id) => 'epl_lao_html_' + id + (VER ? '_' + VER : '');
  async function napHTML(id, goc) {
    try {
      const html = await (await fetch(themVer(goc + '.html'), { cache: 'no-cache' })).text();
      HTML_DEM.set(id, html);
      try { localStorage.setItem(khoaHTML(id), html); } catch (e) { /* hết chỗ thì thôi */ }
      return html;
    } catch (e) {
      if (HTML_DEM.has(id)) return HTML_DEM.get(id);
      let cu = null;
      try { cu = localStorage.getItem(khoaHTML(id)); } catch (e2) { cu = null; }
      if (cu) { HTML_DEM.set(id, cu); return cu; }
      throw e;
    }
  }

  async function napModule(id) {
    const m = MODULES.find(x => x.id === id) || MODULES[0];
    if (!thayDuoc(m)) {
      const dau = moduleDau();
      if (!dau) return veKhongCoMan();          // không còn màn nào ở đây — chỉ sang trang kế toán, không chuyển vòng
      EPL.toast(NN.t('no_permission'), 'loi'); return EPL.di(dau);
    }
    const noiDung = document.getElementById('noi-dung');
    const truoc = EPL.modules[moduleHienTai]; if (truoc && truoc.destroy) { try { truoc.destroy(); } catch (e) { /* bỏ qua */ } }
    moduleHienTai = m.id; veNav(); datTieuDe(); if (EPL.veNutXuat) EPL.veNutXuat(m.id);
    // MỖI LƯỢT NẠP MỘT GỐC RIÊNG. Trước đây mọi module vẽ thẳng vào #noi-dung, nên khi người
    // dùng bấm sang module khác trong lúc module cũ còn đang chờ API, module cũ vẽ xong sẽ đè
    // lên (hoặc vẽ vào ô đã mất rồi bật lỗi, và khối lỗi đó xoá luôn màn mới). Gốc riêng thì
    // module cũ vẽ vào một phần tử đã tháo khỏi trang — vô hại.
    const root = document.createElement('div'); root.className = 'mod-root'; root.dataset.mod = m.id;
    root.innerHTML = `<div class="muted small">${NN.h('loading')}</div>`;
    noiDung.replaceChildren(root);
    const conHienTai = () => moduleHienTai === m.id && root.isConnected;
    const goc = `modules/${m.id}/${m.id}`;
    try {
      if (!daNapCSS.has(m.id)) { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = themVer(goc + '.css'); document.head.appendChild(l); daNapCSS.add(m.id); }
      const html = await napHTML(m.id, goc);
      if (!daNapJS.has(m.id)) {
        await new Promise((res, rej) => { const s = document.createElement('script'); s.src = themVer(goc + '.js'); s.onload = res; s.onerror = () => rej(new Error('Không nạp được ' + goc + '.js')); document.head.appendChild(s); });
        daNapJS.add(m.id);
      }
      if (!conHienTai()) return;          // người dùng đã bấm sang module khác trong lúc chờ
      root.innerHTML = html;
      EPL.doiOThang(root);
      NN.apDung(root);
      const mod = EPL.modules[m.id];
      if (!mod || !mod.init) throw new Error('Module ' + m.id + ' chưa đăng ký EPL.modules["' + m.id + '"]');
      // Đang chờ dữ liệu: dải "Đang tải…" trên đầu màn. Rà giao diện 23/09: khung trống 1–3 giây (tải tệp + 2–3 API
      // tới DB ở xa) trông như màn hỏng — Theo dõi phiếu, Phiếu chi của Bãi. Tắt khi init xong, kể cả khi lỗi.
      root.classList.add('mod-dang-tai'); root.dataset.tai = NN.t('loading');
      try { await mod.init(root, { tham: EPL.thamSo(), user: USER }); } finally { root.classList.remove('mod-dang-tai'); }
      if (conHienTai()) NN.apDung(root);
    } catch (e) {
      if (!conHienTai()) return;          // lỗi của module đã bị rời — không được đè lên màn hiện tại
      root.innerHTML = `<div class="card"><div class="bd"><b class="neg">${esc(NN.t('err_generic'))}</b><div class="small muted">${esc(e.message)}</div></div></div>`;
    }
  }
  // Các lượt nạp chạy NỐI TIẾP nhau, không chồng lên nhau. Hai lượt nạp CÙNG một module mà chạy song
  // song thì cùng gán biến `root` bên trong module, lượt xong sau vẽ vào gốc của lượt kia (đã tháo
  // khỏi trang) và màn đang hiện trắng trơn. Gặp thật: đăng nhập khi địa chỉ còn hash của module vai
  // này không có quyền → khung tự chuyển sang màn đầu, lượt chuyển đó chồng lên lượt người dùng bấm.
  let hangCho = Promise.resolve();
  function dieuHuong() {
    if (!USER) return;
    const id = (location.hash.replace(/^#\/?/, '').split('?')[0]) || moduleDau();
    // Lời hứa của lượt nạp hiện tại — bộ kiểm chờ nó thay vì đoán bằng setTimeout.
    EPL.sanSang = hangCho = hangCho.then(() => napModule(id), () => napModule(id));
  }
  window.addEventListener('hashchange', dieuHuong);

  /* ================================================================ Khởi động */
  async function khoiDong() {
    veNutNgonNgu(); NN.apDung(document);
    document.getElementById('lgBtn').addEventListener('click', dangNhapTuForm);
    document.getElementById('lgP').addEventListener('keydown', e => { if (e.key === 'Enter') dangNhapTuForm(); });
    document.getElementById('lgU').addEventListener('keydown', e => { if (e.key === 'Enter') dangNhapTuForm(); });
    const mat = document.getElementById('lgMat');
    mat.addEventListener('click', () => {
      const o = document.getElementById('lgP'), hien = o.type === 'password';
      o.type = hien ? 'text' : 'password';
      mat.classList.toggle('mo', hien);
      mat.title = NN.t(hien ? 'hide_pw' : 'show_pw');
      o.focus();
    });
    if (API.token()) {
      try { USER = await API.get('/api/toi'); hienApp(); return; } catch (e) { /* phiên hết hạn → về đăng nhập */ }
    }
    AUTH.dangXuat(false);
  }
  document.addEventListener('DOMContentLoaded', khoiDong);
})();
