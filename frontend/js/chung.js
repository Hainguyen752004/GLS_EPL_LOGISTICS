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
    token() { try { return localStorage.getItem(KHOA_PHIEN) || ''; } catch (e) { return ''; } },
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
        throw new LoiAPI(r.status, ct.ma || 'LOI', ct.loi || (typeof ct === 'string' ? ct : NN.t('err_generic')));
      }
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
    /** Áp mọi data-i18n trong một gốc DOM. */
    apDung(root) {
      (root || document).querySelectorAll('[data-i18n]').forEach(el => { el.innerHTML = NN.h(el.dataset.i18n); });
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
  function veNutNgonNgu() {
    document.querySelectorAll('.lang').forEach(o => {
      o.innerHTML = NGON_NGU.map(m => `<button data-lang="${m}" class="${m === lang ? 'active' : ''}" ${m === 'lo' ? 'lang="lo"' : ''}>${NHAN_NN[m]}</button>`).join('');
      o.querySelectorAll('button').forEach(b => b.addEventListener('click', () => NN.dat(b.dataset.lang)));
    });
  }

  /* ================================================================ Định dạng */
  const esc = EPL.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // Số kiểu 1,724.46 — đúng như Excel và bản mẫu họ đã duyệt (họ dùng dấu phẩy ngăn nghìn).
  EPL.so = (n, d = 0) => (n === null || n === undefined || n === '' || isNaN(Number(n))) ? '—'
    : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  EPL.tien = (n, ma, d) => n === null || n === undefined ? '—' : EPL.so(n, d === undefined ? (ma === 'USD' ? 2 : 0) : d) + (ma ? ' ' + ma : '');
  EPL.ngay = (s) => { if (!s) return '—'; const d = new Date(String(s).slice(0, 10) + 'T00:00:00'); return isNaN(d) ? s : d.toLocaleDateString('en-GB'); };
  EPL.ngayGio = (s) => { if (!s) return '—'; const d = new Date(s); return isNaN(d) ? s : d.toLocaleDateString('en-GB') + ' ' + d.toTimeString().slice(0, 5); };
  EPL.homNay = () => new Date().toISOString().slice(0, 10);
  EPL.thangNay = () => new Date().toISOString().slice(0, 7);
  EPL.doc = (v) => parseFloat(String(v == null ? '' : v).replace(/,/g, '')) || 0;
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
      f.type === 'select' ? `<select id="hn-${f.id}">${(f.options || []).map(o => `<option value="${esc(o[0])}" ${o[0] === f.value ? 'selected' : ''}>${esc(o[1])}</option>`).join('')}</select>`
      : f.type === 'textarea' ? `<textarea id="hn-${f.id}" rows="3">${esc(f.value || '')}</textarea>`
      : `<input id="hn-${f.id}" type="${f.type || 'text'}" value="${esc(f.value == null ? '' : f.value)}" ${f.lo ? 'lang="lo"' : ''}>`}</div>`).join('');
    const ok = await EPL.hoi(tieuDe, html, nhanOk);
    if (!ok) return null;
    const ra = {}; fields.forEach(f => { const el = document.getElementById('hn-' + f.id); ra[f.id] = el ? el.value : undefined; });
    return ra;
  };

  /* ================================================================ Đăng nhập */
  let USER = null;
  const AUTH = EPL.AUTH = {
    get user() { return USER; },
    get role() { return USER ? USER.role : ''; },
    la: (...vai) => USER && (USER.role === 'admin' || vai.includes(USER.role)),
    async dangNhap(u, p) {
      const g = await API.post('/api/dang-nhap', { username: u, password: p });
      try { localStorage.setItem(KHOA_PHIEN, g.token); } catch (e) { /* bỏ qua */ }
      USER = g.user; hienApp();
    },
    dangXuat(xoaHash = true) {
      try { localStorage.removeItem(KHOA_PHIEN); } catch (e) { /* bỏ qua */ }
      USER = null; document.getElementById('app').hidden = true; document.getElementById('login').hidden = false;
      document.getElementById('lgU').value = ''; document.getElementById('lgP').value = '';
      if (xoaHash) location.hash = '';
      veTaiKhoanMau();
    },
  };
  async function veTaiKhoanMau() {
    try {
      const ds = await API.get('/api/tai-khoan-mau');
      document.getElementById('acctList').innerHTML = ds.map(a => `<button class="acct-btn" data-u="${esc(a.username)}">
        <span class="av">${esc(a.avatar)}</span><span><b>${esc(a.full_name)}</b><small>${NN.h('r_' + a.role)} · ${esc(a.username)}</small></span></button>`).join('');
      document.querySelectorAll('.acct-btn').forEach(b => b.addEventListener('click', () => {
        document.getElementById('lgU').value = b.dataset.u; document.getElementById('lgP').value = '1234'; dangNhapTuForm();
      }));
    } catch (e) { document.getElementById('acctList').innerHTML = `<div class="small neg">${esc(e.message)}</div>`; }
  }
  async function dangNhapTuForm() {
    const u = document.getElementById('lgU').value.trim(), p = document.getElementById('lgP').value;
    const err = document.getElementById('lgErr'); err.textContent = '';
    try { await AUTH.dangNhap(u, p); } catch (e) { err.textContent = e.ma === 'SAI_TAI_KHOAN' ? NN.t('login_err') : e.message; }
  }
  function hienApp() {
    document.getElementById('login').hidden = true; document.getElementById('app').hidden = false;
    document.getElementById('roleAv').textContent = USER.avatar || USER.full_name.slice(0, 2).toUpperCase();
    document.getElementById('uName').textContent = USER.full_name;
    document.getElementById('uRole').innerHTML = NN.h('r_' + USER.role);
    veNav(); dieuHuong();
  }

  /* ================================================================ Module & điều hướng */
  // Thứ tự nhóm và module đúng theo sheet "ລາຍງານ" của Excel + hai nhóm danh mục/hệ thống.
  const MODULES = EPL.MODULES = [
    { id: 'tong-quan',      nhom: 'mod_transport', nav: 'nav_dash',     ic: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' },
    { id: 'theo-doi',       nhom: 'mod_transport', nav: 'nav_tracking', ic: 'M3 6h18M3 12h18M3 18h12' },
    { id: 'phieu-xuat-xe',  nhom: 'mod_transport', nav: 'nav_dispatch', ic: 'M1 3h15v13H1zM16 8h4l3 3v5h-7z' },
    { id: 'hoa-don',        nhom: 'mod_transport', nav: 'nav_bill',     ic: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h8' },
    { id: 'xe-lien-ket',    nhom: 'mod_transport', nav: 'nav_joint',    ic: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8' },
    { id: 'tien-tai-xe',    nhom: 'mod_transport', nav: 'nav_driver',   ic: 'M2 6h20v12H2zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5' },
    { id: 'nha-cung-cap',   nhom: 'mod_transport', nav: 'nav_supplier', ic: 'M3 9l9-6 9 6v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM9 21V12h6v9' },
    { id: 'kho-nhien-lieu', nhom: 'mod_warehouse', nav: 'nav_fuel',     ic: 'M3 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18M3 22h12M6 6h6v5H6z' },
    { id: 'kho-phu-tung',   nhom: 'mod_warehouse', nav: 'nav_parts',    ic: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6M19 12l2 1-1 3-2-.5a7 7 0 0 1-2 2l.5 2-3 1-1-2a7 7 0 0 1-3 0l-1 2-3-1 .5-2a7 7 0 0 1-2-2L2 16l-1-3 2-1a7 7 0 0 1 0-3L1 8l1-3 2 .5a7 7 0 0 1 2-2L5.5 1.5l3-1 1 2a7 7 0 0 1 3 0l1-2 3 1-.5 2a7 7 0 0 1 2 2l2-.5 1 3-2 1a7 7 0 0 1 0 3z' },
    { id: 'khach-hang',     nhom: 'mod_master',    nav: 'nav_customers', ic: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8' },
    { id: 'xe',             nhom: 'mod_master',    nav: 'nav_vehicles', ic: 'M1 3h15v13H1zM16 8h4l3 3v5h-7zM5.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M18.5 16a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5' },
    { id: 'tai-xe',         nhom: 'mod_master',    nav: 'nav_drivers',  ic: 'M12 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10M4 22a8 8 0 0 1 16 0' },
    { id: 'quy-trinh',      nhom: 'mod_system',    nav: 'nav_workflow', ic: 'M12 3v4M6 21v-4M18 21v-4M4 11h16M9 7h6v4H9zM3 17h6v4H3zM15 17h6v4h-6z' },
    { id: 'tai-khoan',      nhom: 'mod_system',    nav: 'nav_users',    ic: 'M12 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10M4 22a8 8 0 0 1 16 0M19 8l2 2-4 4-2-2', vai: ['admin'] },
  ];
  let moduleHienTai = '';
  const daNapJS = new Set(), daNapCSS = new Set();

  function thayDuoc(m) { return !m.vai || AUTH.la(...m.vai); }
  function veNav() {
    const nav = document.getElementById('nav'); if (!nav || !USER) return;
    let html = '', nhom = '';
    MODULES.filter(thayDuoc).forEach(m => {
      if (m.nhom !== nhom) { nhom = m.nhom; html += `<div class="nav-group">${NN.h(nhom)}</div>`; }
      html += `<button data-mod="${m.id}" class="${m.id === moduleHienTai ? 'active' : ''}"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="${m.ic}"/></svg><span>${NN.h(m.nav)}</span></button>`;
    });
    nav.innerHTML = html;
    nav.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { location.hash = '#/' + b.dataset.mod; }));
  }
  function datTieuDe() {
    const m = MODULES.find(x => x.id === moduleHienTai); const h = document.getElementById('pageTitle');
    if (m && h) h.innerHTML = NN.h('title_' + m.id.replace(/-/g, '_'));
  }
  EPL.di = (id, tham) => { location.hash = '#/' + id + (tham ? '?' + new URLSearchParams(tham).toString() : ''); };
  EPL.thamSo = () => { const q = location.hash.split('?')[1] || ''; return Object.fromEntries(new URLSearchParams(q)); };

  async function napModule(id) {
    const m = MODULES.find(x => x.id === id) || MODULES[0];
    if (!thayDuoc(m)) { EPL.toast(NN.t('no_permission'), 'loi'); return EPL.di('tong-quan'); }
    const noiDung = document.getElementById('noi-dung');
    const truoc = EPL.modules[moduleHienTai]; if (truoc && truoc.destroy) { try { truoc.destroy(); } catch (e) { /* bỏ qua */ } }
    moduleHienTai = m.id; veNav(); datTieuDe();
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
      if (!daNapCSS.has(m.id)) { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = goc + '.css'; document.head.appendChild(l); daNapCSS.add(m.id); }
      const html = await (await fetch(goc + '.html', { cache: 'no-cache' })).text();
      if (!daNapJS.has(m.id)) {
        await new Promise((res, rej) => { const s = document.createElement('script'); s.src = goc + '.js'; s.onload = res; s.onerror = () => rej(new Error('Không nạp được ' + goc + '.js')); document.head.appendChild(s); });
        daNapJS.add(m.id);
      }
      if (!conHienTai()) return;          // người dùng đã bấm sang module khác trong lúc chờ
      root.innerHTML = html;
      NN.apDung(root);
      const mod = EPL.modules[m.id];
      if (!mod || !mod.init) throw new Error('Module ' + m.id + ' chưa đăng ký EPL.modules["' + m.id + '"]');
      await mod.init(root, { tham: EPL.thamSo(), user: USER });
      if (conHienTai()) NN.apDung(root);
    } catch (e) {
      if (!conHienTai()) return;          // lỗi của module đã bị rời — không được đè lên màn hiện tại
      root.innerHTML = `<div class="card"><div class="bd"><b class="neg">${esc(NN.t('err_generic'))}</b><div class="small muted">${esc(e.message)}</div></div></div>`;
    }
  }
  function dieuHuong() {
    if (!USER) return;
    const id = (location.hash.replace(/^#\/?/, '').split('?')[0]) || 'tong-quan';
    // Lời hứa của lượt nạp hiện tại — bộ kiểm chờ nó thay vì đoán bằng setTimeout.
    EPL.sanSang = napModule(id);
  }
  window.addEventListener('hashchange', dieuHuong);

  /* ================================================================ Khởi động */
  async function khoiDong() {
    veNutNgonNgu(); NN.apDung(document);
    document.getElementById('lgBtn').addEventListener('click', dangNhapTuForm);
    document.getElementById('lgP').addEventListener('keydown', e => { if (e.key === 'Enter') dangNhapTuForm(); });
    document.getElementById('lgU').addEventListener('keydown', e => { if (e.key === 'Enter') dangNhapTuForm(); });
    document.getElementById('btnLogout').addEventListener('click', () => AUTH.dangXuat());
    if (API.token()) {
      try { USER = await API.get('/api/toi'); hienApp(); return; } catch (e) { /* phiên hết hạn → về đăng nhập */ }
    }
    AUTH.dangXuat(false);
  }
  document.addEventListener('DOMContentLoaded', khoiDong);
})();
