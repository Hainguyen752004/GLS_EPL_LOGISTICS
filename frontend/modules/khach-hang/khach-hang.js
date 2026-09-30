/* Khách hàng — ລູກຄ້າ. Giao diện theo bản mẫu chủ dự án gửi chiều 30/09 (Khach_Hang_new.zip).
 *
 * Trái: danh sách khách (ảnh chữ đầu, số còn nợ, tình trạng hợp đồng, cách xuất hoá đơn), tìm theo tên / mã / điện
 * thoại / số hợp đồng, lọc Sắp hết hạn · Chưa có hợp đồng · Còn nợ. Phải: hồ sơ khách, bốn ô số của tháng, dải hợp đồng
 * đang áp dụng (đường đời hợp đồng, Sửa / Gia hạn), bốn tab Hợp đồng · Bảng giá · Chuyến & phiếu · Công nợ.
 *
 * Mã khách = mã khách BÊN KẾ TOÁN (chủ dự án chốt 30/09), gửi đi trong phiếu đề nghị thu / bàn giao DO.
 * Tiền theo đúng tiền của từng chứng từ (cước USD thì hiện USD), kèm số quy Kíp. Bãi không thấy tiền: không có số nợ,
 * doanh thu, bảng giá, công nợ; máy chủ cũng không gửi. Công nợ chỉ để XEM — thu tiền là việc bên kế toán.
 * Hợp đồng: /api/hop-dong (số chuyến máy tự đếm theo phiếu); bảng giá: /api/customers/{id}/bang-gia.
 */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root = null, ds = [], HD = [], NO_TONG = {}, tuyen = [];
  const cache = {};                       // theo khách: {trips, gia, no}
  const st = { id: null, tab: 'contracts', filter: 'all', query: '' };
  const WARN_DAYS = 30;

  // quyền — giữ như màn cũ (đúng bảng Nhiệm Vụ)
  const suaHd = () => AUTH.la('acct', 'rev');                 // hợp đồng vận chuyển: KT Thu/Chi, KT Doanh thu (Sếp luôn được)
  const suaDuoc = () => AUTH.la('yard', 'acct');              // thêm / sửa khách
  const xemTien = () => AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash', 'admin');   // Bãi không thấy tiền
  const suaGia = () => AUTH.la('acct', 'admin');
  const moPhieuDuoc = () => EPL.manCuaVai(AUTH.role).some(m => m.id === 'phieu-xuat-xe');

  /* ================= Tiện ích ================= */
  const $ = (s) => root.querySelector(s);
  const $$ = (s) => Array.from(root.querySelectorAll(s));
  const h = (k, p) => NN.h(k, p);
  const t = (k, p) => NN.t(k, p);
  const n0 = (v) => EPL.so(v || 0, 0);
  const n2 = (v) => EPL.so(v || 0, 2);
  const sum = (l, f) => l.reduce((s, x) => s + (typeof f === 'function' ? f(x) : (x[f] || 0)), 0);
  const thangNay = () => new Date().toISOString().slice(0, 7);
  const thangHien = () => thangNay().slice(5, 7) + '/' + thangNay().slice(0, 4);
  const ngay = (s) => s ? EPL.ngay(s) : '';
  const pad = (n) => (n < 10 ? '0' : '') + n;
  // ngày dd/mm/yyyy ⇄ Date UTC (ô nhập theo mẫu) · ISO ⇄ Date (máy chủ)
  function pd(s) {
    const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(s || '').trim());
    if (!m) return null;
    const d = new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
    return d.getUTCDate() === +m[1] && d.getUTCMonth() === +m[2] - 1 ? d : null;
  }
  const fd = (d) => d ? pad(d.getUTCDate()) + '/' + pad(d.getUTCMonth() + 1) + '/' + d.getUTCFullYear() : '';
  const iso = (d) => d ? d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) : '';
  const fromIso = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : null; };
  const days = (a, b) => Math.round((b - a) / 86400000);
  const addDays = (d, n) => new Date(d.getTime() + n * 86400000);
  function addMonths(d, n) {
    const r = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + n, 1));
    const last = new Date(Date.UTC(r.getUTCFullYear(), r.getUTCMonth() + 1, 0)).getUTCDate();
    r.setUTCDate(Math.min(d.getUTCDate(), last));
    return r;
  }
  const TODAY = () => fromIso(EPL.homNay());
  // nút biểu tượng trong bảng — chữ ở tooltip, để bảng vừa khung không phải cuộn ngang
  const IC = { edit: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4', renew: 'M4 12a8 8 0 0 1 13.7-5.7L20 8M20 4v4h-4M20 12a8 8 0 0 1-13.7 5.7L4 16M4 20v-4h4',
    del: 'M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3' };
  const nutIc = (act, ic, nhan, attrs) => '<button type="button" class="icon-btn icon-btn--sm row-ic" data-act="' + act + '" ' + attrs + ' title="' + esc(nhan) + '" aria-label="' + esc(nhan) + '">' +
    '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="' + IC[ic] + '"/></svg></button>';
  const tienGop = (d) => EPL.tienGop(d);
  const cong = (o, ccy, v) => { if (v) o[ccy] = Math.round(((o[ccy] || 0) + v) * 100) / 100; return o; };

  /* ================= Nghiệp vụ hợp đồng ================= */
  const hdCua = (cid) => HD.filter(x => x.customer_id === cid);
  // trạng thái do máy chủ tính (cùng ngưỡng 30 ngày): con_han · sap_het · chua_hieu_luc · het_han · ngung
  const KEY = { con_han: 'active', sap_het: 'expiring', chua_hieu_luc: 'future', het_han: 'expired', ngung: 'paused' };
  const CLS = { active: 'k3-tag--ok', expiring: 'k3-tag--warn', future: 'k3-tag--info', expired: 'k3-tag--muted', paused: 'k3-tag--muted' };
  function cStatus(c) {
    const key = KEY[c.trang_thai] || 'active';
    return { key, cls: CLS[key], label: t('hd_' + c.trang_thai), left: c.ngay_con };
  }
  function currentContract(cid) {
    const ds = hdCua(cid);
    const live = ds.filter(c => ['active', 'expiring'].includes(cStatus(c).key));
    if (live.length) return live.sort((a, b) => String(b.valid_to || '9999').localeCompare(String(a.valid_to || '9999')))[0];
    return ds.find(c => cStatus(c).key === 'future') || null;
  }
  function renewalOf(cid, c) {
    const e = fromIso(c.valid_to); if (!e) return null;
    return hdCua(cid).find(x => x.id !== c.id && x.active && fromIso(x.valid_from) > fromIso(c.valid_from) && days(e, fromIso(x.valid_from)) <= 1) || null;
  }
  function nextContractNo(year) {
    let max = 0;
    HD.forEach(c => { const m = /^HDVC-(\d{4})-(\d+)$/.exec(c.contract_no || ''); if (m && +m[1] === year) max = Math.max(max, +m[2]); });
    return 'HDVC-' + year + '-' + String(max + 1).padStart(3, '0');
  }
  function durText(c) {
    const s = fromIso(c.valid_from), e = fromIso(c.valid_to); if (!s || !e) return t('hd_vo_han');
    const end1 = addDays(e, 1); let m = 0;
    while (addMonths(s, m + 1) <= end1) m++;
    const rest = days(addMonths(s, m), end1);
    return [m ? t('k3_n_thang', { n: m }) : '', rest ? t('k3_n_ngay', { n: rest }) : ''].filter(Boolean).join(' ') || t('k3_n_ngay', { n: 1 });
  }

  /* ================= Số của khách ================= */
  const byId = (id) => ds.find(k => k.id === id);
  function initial(name) {
    const n = String(name || '').replace(/^(ບໍລິສັດ|ນາງ|ທ້າວ|ທ່ານ)\s+/, '');
    return Array.from(n)[0] || '?';
  }
  const modeLabel = (m) => h(m === 'thang' ? 'inv_thang_s' : 'inv_phieu_s');
  const modeHelp = (m) => t(m === 'thang' ? 'inv_thang' : 'inv_phieu');
  const noCua = (cid) => NO_TONG[cid] || null;
  function metrics(cid) {
    const c = cache[cid] || {}, tr = c.trips || [];
    const m = { trips: tr.length, gom: tr.filter(x => x.kind === 'gom').length, giao: tr.filter(x => x.kind !== 'gom').length,
      tons: sum(tr, x => (x.tinh || {}).tan_tinh || 0), rev: {}, revLak: 0, choGop: {} };
    tr.forEach(x => {
      const ti = x.tinh || {};
      cong(m.rev, ti.ccy || x.price_ccy, ti.doanh_thu || 0);
      m.revLak += ti.doanh_thu_lak || 0;
      if (x.inv_mode === 'thang' && !x.invoiced && x.locked) cong(m.choGop, ti.ccy || x.price_ccy, ti.doanh_thu || 0);
    });
    return m;
  }

  /* ================= Danh sách khách ================= */
  function matches(k) {
    const q = st.query.trim().toLowerCase();
    if (q) {
      const hay = [k.name, k.code, k.phone, k.address].concat(hdCua(k.id).map(c => c.contract_no)).join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    const cur = currentContract(k.id);
    if (st.filter === 'expiring') return cur && cStatus(cur).key === 'expiring' && !renewalOf(k.id, cur);
    if (st.filter === 'nocontract') return !cur;
    if (st.filter === 'debt') return (noCua(k.id) || {}).con_no_lak > 0;
    return true;
  }
  function listStatus(k) {
    const c = currentContract(k.id);
    if (!c) return { cls: 'muted', text: t('k3_chua_hd') };
    const s = cStatus(c), nx = s.key === 'expiring' ? renewalOf(k.id, c) : null;
    if (nx) return { cls: 'ok', text: t('k3_da_gia_han_so', { so: nx.contract_no }) };
    if (s.key === 'expiring') return { cls: 'warn', text: t('k3_het_sau', { n: s.left }) };
    if (s.key === 'future') return { cls: 'info', text: t('k3_hieu_luc_tu', { d: ngay(c.valid_from) }) };
    return { cls: 'ok', text: c.valid_to ? t('k3_con_han_den', { d: ngay(c.valid_to) }) : t('hd_vo_han') };
  }
  function renderList() {
    const list = ds.filter(matches), g = xemTien();
    $('#k3-dem').textContent = list.length === ds.length ? t('k3_n_khach', { n: ds.length }) : t('k3_n_tren', { n: list.length, m: ds.length });
    $('#k3-ds').innerHTML = list.length ? list.map(k => {
      const no = g ? noCua(k.id) : null, active = k.id === st.id, ls = listStatus(k);
      return '<li><button type="button" class="cust' + (active ? ' is-active' : '') + (k.active ? '' : ' is-off') + '" data-cust="' + esc(k.id) + '" aria-current="' + active + '">' +
        '<span class="avatar' + (k.cust_type === 'company' ? ' avatar--company' : '') + '" lang="lo">' + esc(initial(k.name)) + '</span>' +
        '<span class="cust-main"><span class="cust-row"><b class="cust-name" lang="lo">' + esc(k.name) + '</b>' +
          (no && no.con_no_lak > 0 ? '<span class="cust-debt" title="' + esc(tienGop(no.con_no_tien)) + '">' + n0(no.con_no_lak) + '</span>' : '') + '</span>' +
        '<span class="cust-row cust-row--sub"><span class="st st--' + ls.cls + '"><i></i>' + esc(ls.text) + '</span>' +
          '<span class="cust-mode">' + modeLabel(k.invoice_mode) + (k.active ? '' : ', ' + h('inactive')) + '</span></span></span>' +
        '</button></li>';
    }).join('') : '<li class="k3-empty">' + h('k3_khong_khop') + '</li>';
  }

  /* ================= Dải hợp đồng đang áp dụng ================= */
  function lifeHtml(k) {
    const c = currentContract(k.id), sua = suaHd();
    if (!c) {
      return '<section class="k3-panel strip strip--empty"><span class="strip-text">' + h('k3_strip_trong') + '</span>' +
        (sua ? '<button type="button" class="k3-btn k3-btn--primary k3-btn--sm" data-act="add-contract"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>' + h('hd_them') + '</button>' : '') + '</section>';
    }
    const s0 = cStatus(c), s = fromIso(c.valid_from), e = fromIso(c.valid_to), hom = TODAY();
    const nx = renewalOf(k.id, c);
    let life = '';
    if (s && e) {
      const total = Math.max(1, days(s, e));
      const usedP = Math.max(0, Math.min(100, days(s, hom) / total * 100));
      const zoneP = Math.min(100, WARN_DAYS / total * 100);
      life = '<div class="lifeline" role="img" aria-label="' + esc(t('k3_life_aria', { tu: ngay(c.valid_from), den: ngay(c.valid_to), nay: ngay(EPL.homNay()) })) + '">' +
        '<span class="d d--start">' + esc(ngay(c.valid_from)) + '</span>' +
        '<span class="k3-track"><span class="used" style="width:' + usedP + '%"></span><span class="zone" style="width:' + zoneP + '%" title="' + esc(t('k3_zone', { n: WARN_DAYS })) + '"></span>' +
          (s0.key !== 'future' ? '<span class="today" style="left:' + usedP + '%" title="' + esc(t('k3_hom_nay', { d: ngay(EPL.homNay()) })) + '"></span>' : '') + '</span>' +
        '<span class="d d--end">' + esc(ngay(c.valid_to)) + '</span></div>';
    }
    const head = nx ? h('k3_life_da_gia_han', { so: nx.contract_no, d: ngay(nx.valid_from) })
      : s0.key === 'future' ? h('k3_life_tu', { d: ngay(c.valid_from), n: s ? days(hom, s) : 0 })
      : !e ? h('k3_life_vo_han')
      : s0.key === 'expiring' ? h('k3_life_sap_het', { n: days(hom, e) })
      : h('k3_life_con', { n: days(hom, e) });
    return '<section class="k3-panel strip strip--' + (nx ? 'ok' : s0.key) + '">' +
      '<div class="strip-id"><span class="strip-label">' + h('k3_hd_dang_ap') + '</span><span class="code">' + esc(c.contract_no) + '</span></div>' +
      '<div class="strip-life"><div class="strip-text">' + head + ' ' + h('k3_life_chuyen', { n: c.so_phieu || 0 }) + '</div>' + life + '</div>' +
      (sua ? '<div class="strip-tools"><button type="button" class="k3-btn k3-btn--sm" data-act="edit-contract" data-hd="' + esc(c.id) + '">' + h('edit') + '</button>' +
        (nx ? '' : '<button type="button" class="k3-btn k3-btn--sm ' + (s0.key === 'expiring' ? 'k3-btn--warn' : '') + '" data-act="renew" data-hd="' + esc(c.id) + '">' + h('k3_gia_han') + '</button>') + '</div>' : '') +
      '</section>';
  }

  /* ================= Tab: Hợp đồng ================= */
  function contractsTab(k) {
    const cur = currentContract(k.id), sua = suaHd(), tk = API.token();
    const list = hdCua(k.id).slice().sort((a, b) => String(b.valid_to || '9999').localeCompare(String(a.valid_to || '9999')));
    if (!list.length) return '<div class="k3-empty">' + h(sua ? 'k3_hd_trong_sua' : 'hd_trong') + '</div>';
    const rows = list.map(c => {
      const s0 = cStatus(c), s = fromIso(c.valid_from), e = fromIso(c.valid_to);
      const usedP = s && e ? Math.max(0, Math.min(100, days(s, TODAY()) / Math.max(1, days(s, e)) * 100)) : 0;
      const renewed = s0.key === 'expiring' && renewalOf(k.id, c);
      const tag = renewed ? '<span class="k3-tag k3-tag--ok">' + h('k3_da_gia_han') + '</span>'
        : '<span class="k3-tag ' + s0.cls + '">' + esc(s0.label) + (s0.key === 'expiring' && s0.left != null ? ', ' + esc(t('k3_n_ngay', { n: s0.left })) : '') + '</span>';
      const files = (c.files || []).map(f => '<span class="file-chip"><a href="' + esc(f.url) + '?tk=' + encodeURIComponent(tk) + '" target="_blank" rel="noopener" title="' + esc(f.filename) + '">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8zM14 3v5h5"/></svg>' + esc(f.filename) + '</a>' +
        (sua ? '<button type="button" data-act="del-file" data-tep="' + esc(f.id) + '" aria-label="' + esc(t('delete')) + '">×</button>' : '') + '</span>').join('');
      return '<tr class="' + (s0.key === 'expired' || s0.key === 'paused' ? 'is-dim' : '') + '">' +
        '<td><span class="code strong">' + esc(c.contract_no) + '</span>' + (cur && cur.id === c.id ? '<span class="k3-sub ok-txt">' + h('k3_tu_dien') + '</span>' : '') + '</td>' +
        '<td>' + tag + '</td>' +
        '<td class="period"><span>' + esc(ngay(c.valid_from)) + ' <span class="arrow">→</span> ' + (c.valid_to ? esc(ngay(c.valid_to)) : h('hd_vo_han')) + '</span><span class="k3-sub">' + h('k3_ky', { d: ngay(c.sign_date) || '–' }) + '</span></td>' +
        '<td class="dur"><span>' + esc(durText(c)) + '</span>' + (e ? '<span class="mini-life"><i class="' + (s0.key === 'expiring' && !renewed ? 'is-warn' : s0.key === 'expired' ? 'is-done' : '') + '" style="width:' + usedP + '%"></i></span>' : '') + '</td>' +
        '<td class="num">' + n0(c.so_phieu) + '</td>' +
        '<td class="note-cell" title="' + esc(c.note || '') + '">' + (c.note ? esc(c.note) : '<span class="dash">–</span>') + '</td>' +
        '<td class="files-cell">' + files + (sua ? '<label class="icon-btn icon-btn--sm" title="' + esc(t('k3_dinh_kem')) + '"><input type="file" accept="image/*,application/pdf" multiple hidden data-attach="' + esc(c.id) + '">' +
          '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.5 12.6 21a5 5 0 0 1-7.1-7.1L14 5.4a3.3 3.3 0 0 1 4.7 4.7L10.2 18.6a1.7 1.7 0 0 1-2.4-2.4L15.5 8.5"/></svg></label>' : (files ? '' : '<span class="dash">–</span>')) + '</td>' +
        '<td class="row-tools">' + (sua ? nutIc('edit-contract', 'edit', t('edit'), 'data-hd="' + esc(c.id) + '"') +
          (s0.key !== 'expired' || list[0] === c ? nutIc('renew', 'renew', t('k3_gia_han'), 'data-hd="' + esc(c.id) + '"') : '') +
          (c.so_phieu ? '' : nutIc('del-contract', 'del', t('delete'), 'data-hd="' + esc(c.id) + '"')) : '') + '</td></tr>';
    }).join('');
    return '<div class="k3-tbl-wrap"><table class="k3-tbl k3-tbl--compact"><thead><tr><th>' + h('hd_so') + '</th><th>' + h('status') + '</th><th>' + h('k3_hieu_luc') + '</th><th>' + h('k3_thoi_han') + '</th>' +
      '<th class="num">' + h('k3_chuyen') + '</th><th class="note-cell">' + h('note') + '</th><th>' + h('hd_scan') + '</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  /* ================= Tab: Bảng giá ================= */
  function pricesTab(k) {
    const gia = (cache[k.id] || {}).gia;
    if (!gia) return '<div class="k3-empty">' + h('loading') + '</div>';
    if (!gia.length) return '<div class="k3-empty">' + h('kh_gia_trong') + '</div>';
    const hom = EPL.homNay();
    // giá đang dùng: mỗi tuyến × loại hàng, dòng còn dùng có ngày hiệu lực gần nhất mà đã tới
    const dangDung = {}, denKhi = {};
    const nhom = {};
    gia.filter(r => r.active).forEach(r => { (nhom[r.route_id + '|' + r.goods_type] = nhom[r.route_id + '|' + r.goods_type] || []).push(r); });
    Object.values(nhom).forEach(l => {
      l.sort((a, b) => String(a.valid_from || '').localeCompare(String(b.valid_from || '')));
      const toi = l.filter(r => !r.valid_from || r.valid_from <= hom);
      if (toi.length) dangDung[toi[toi.length - 1].id] = true;
      l.forEach((r, i) => { const sau = l[i + 1]; if (sau && sau.valid_from) denKhi[r.id] = iso(addDays(fromIso(sau.valid_from), -1)); });
    });
    const rows = gia.map(r => {
      const cur = !!dangDung[r.id];
      return '<tr class="' + (cur ? 'is-current' : '') + (r.active ? '' : ' is-dim') + '"><td><b>' + h(r.goods_type === 'iron_ore' ? 'iron_ore' : 'other_goods') + '</b>' +
        (cur ? '<span class="k3-sub" style="color:var(--primary);font-weight:600">' + h('k3_dang_ap_dung') + '</span>' : '') + '</td>' +
        '<td lang="lo">' + esc(r.route_name || '') + '</td><td>' + h(r.price_mode === 'chuyen' ? 'pm_chuyen_s' : 'pm_ton_s') + '</td>' +
        '<td class="num"><b>' + EPL.tien(r.price, r.price_ccy || 'USD') + '</b></td>' +
        '<td class="num">' + (r.hire_price == null ? '<span class="dash">–</span>' : EPL.tien(r.hire_price, r.hire_ccy || r.price_ccy)) + '</td>' +
        '<td>' + (r.valid_from ? esc(ngay(r.valid_from)) : '–') + ' ' + h('k3_den') + ' ' + (denKhi[r.id] ? esc(ngay(denKhi[r.id])) : h('k3_khi_gia_moi')) + '</td>' +
        '<td class="note-cell" title="' + esc(r.note || '') + '">' + (r.note ? esc(r.note) : '<span class="dash">–</span>') + (r.active ? '' : ' <span class="k3-tag k3-tag--muted">' + h('inactive') + '</span>') + '</td>' +
        '<td class="row-tools">' + (suaGia() ? nutIc('edit-price', 'edit', t('edit'), 'data-gia="' + esc(r.id) + '"') +
          nutIc('del-price', 'del', t('delete'), 'data-gia="' + esc(r.id) + '"') : '') + '</td></tr>';
    }).join('');
    return '<p class="tab-note">' + h('k3_gia_note') + '</p>' +
      '<div class="k3-tbl-wrap"><table class="k3-tbl k3-tbl--compact"><thead><tr><th>' + h('goods_type') + '</th><th>' + h('route') + '</th><th>' + h('unit') + '</th>' +
      '<th class="num">' + h('unit_price') + '</th><th class="num">' + h('hire_pt') + '</th><th>' + h('k3_hieu_luc') + '</th><th>' + h('note') + '</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  /* ================= Tab: Chuyến & phiếu ================= */
  function tripsTab(k) {
    const tr = (cache[k.id] || {}).trips;
    if (!tr) return '<div class="k3-empty">' + h('loading') + '</div>';
    if (!tr.length) return '<div class="k3-empty">' + h('k3_chuyen_trong', { thang: thangHien() }) + '</div>';
    const g = xemTien(), mo = moPhieuDuoc();
    const tong = {};
    const rows = tr.map(x => {
      const ti = x.tinh || {}, ccy = ti.ccy || x.price_ccy;
      if (g) cong(tong, ccy, ti.doanh_thu || 0);
      const inv = x.invoiced ? (x.inv_no ? '<span class="code">' + esc(x.inv_no) + '</span>' : '<span class="k3-tag k3-tag--ok">' + h('p_invoiced') + '</span>')
        : x.inv_mode === 'thang' ? '<span class="k3-tag k3-tag--info">' + h('k3_gop_cuoi_thang') + '</span>'
        : x.locked ? '<span class="k3-tag k3-tag--warn">' + h('k3_chua_xuat') + '</span>' : '<span class="k3-tag k3-tag--muted">' + h('k3_chua_khoa') + '</span>';
      const tuyenX = [x.origin, x.destination].filter(Boolean).join(' → ');
      return '<tr><td>' + esc(ngay(x.doc_date)) + '</td><td><span class="mv ' + (x.kind === 'gom' ? 'mv--in" title="' + esc(t('do_gom')) + '">' + h('k3_gom') : 'mv--out" title="' + esc(t('do_giao')) + '">' + h('k3_giao')) + '</span></td>' +
        '<td>' + (mo ? '<button type="button" class="link code" data-mo-phieu="' + esc(x.id) + '">' + esc(x.doc_no) + '</button>' : '<span class="code">' + esc(x.doc_no) + '</span>') + '</td>' +
        '<td>' + (x.truck_no ? esc(x.truck_no) : '<span class="dash">–</span>') + '</td><td class="route-cell" lang="lo" title="' + esc(tuyenX) + '">' + (tuyenX ? esc(tuyenX) : '<span class="dash">–</span>') + '</td>' +
        '<td class="num">' + n2(ti.tan_tinh) + '</td>' +
        (g ? '<td class="num">' + EPL.tien(ti.don_gia, ccy) + '</td><td class="num"><b>' + EPL.tien(ti.doanh_thu, ccy) + '</b></td>' : '') + '<td>' + inv + '</td></tr>';
    }).join('');
    return '<p class="tab-note">' + h('k3_chuyen_note', { thang: thangHien() }) + '</p>' +
      '<div class="k3-tbl-wrap"><table class="k3-tbl k3-tbl--compact"><thead><tr><th>' + h('c_date') + '</th><th>' + h('do_kind') + '</th><th>' + h('doc_no') + '</th><th>' + h('c_truck') + '</th><th>' + h('route') + '</th>' +
      '<th class="num">' + h('k3_khoi_luong') + '</th>' + (g ? '<th class="num">' + h('unit_price') + '</th><th class="num">' + h('c_value') + '</th>' : '') + '<th>' + h('k3_hoa_don') + '</th></tr></thead><tbody>' + rows +
      '</tbody><tfoot><tr><td colspan="5">' + h('k3_cong_thang') + '</td><td class="num">' + n2(sum(tr, x => (x.tinh || {}).tan_tinh || 0)) + '</td>' +
      (g ? '<td></td><td class="num">' + tienGop(tong) + '</td>' : '') + '<td></td></tr></tfoot></table></div>';
  }

  /* ================= Tab: Công nợ (chỉ xem) ================= */
  function debtTab(k) {
    const no = (cache[k.id] || {}).no;
    if (no === undefined) return '<div class="k3-empty">' + h('loading') + '</div>';
    if (no === null) return '<div class="k3-empty">' + h('k3_no_loi') + '</div>';
    const m = metrics(k.id);
    const rows = (no.dong || []).slice().sort((a, b) => String(b.ngay || '').localeCompare(String(a.ngay || ''))).map(x => {
      const so = x.loai === 'gop' ? '<a href="" class="code" data-kt-gop="' + esc(x.id) + '" data-thang="' + esc(String(x.ngay || '').slice(0, 7)) + '">' + esc(x.so) + ' ↗</a>'
        : (moPhieuDuoc() ? '<button type="button" class="link code" data-mo-phieu="' + esc(x.id) + '">' + esc(x.so) + '</button>' : '<span class="code">' + esc(x.so) + '</span>');
      return '<tr class="' + (x.con_lai_lak > 0 ? '' : 'is-dim') + '"><td>' + h(x.loai === 'gop' ? 'kh_no_gop' : 'kh_no_phieu') + (x.loai === 'gop' ? '<span class="k3-sub">' + esc(t('k3_n_phieu', { n: x.so_phieu })) + '</span>' : '') + '</td>' +
        '<td>' + so + '</td><td>' + esc(ngay(x.ngay)) + '</td><td class="num"><b>' + EPL.tien(x.tien, x.ccy) + '</b></td><td class="num">' + n0(x.tien_lak) + '</td>' +
        '<td class="num">' + n0(x.da_thu_lak) + '</td><td class="num"><b>' + (x.con_lai_lak > 0 ? n0(x.con_lai_lak) : '<span class="dash">–</span>') + '</b></td><td>' + EPL.tag(x.finance_status) + '</td></tr>';
    }).join('');
    const coNo = no.con_no_lak > 0;
    return '<div class="debt-top">' +
        '<div><span>' + h('kh_no_tong') + '</span><b>' + tienGop(no.tong_tien) + '</b><small>≈ ' + n0(no.tong_lak) + ' LAK</small></div>' +
        '<div><span>' + h('collected') + '</span><b>' + n0(no.da_thu_lak) + ' LAK</b></div>' +
        '<div class="' + (coNo ? 'is-danger' : '') + '"><span>' + h('kh_no_con_no') + '</span><b>' + (coNo ? tienGop(no.con_no_tien) : '0') + '</b><small>≈ ' + n0(no.con_no_lak) + ' LAK</small></div>' +
        '<div class="aging-box"><span class="aging-title">' + h('k3_so_to', { n: no.so_to, m: no.so_to_no }) + '</span><span class="aging-note">' + h('k3_no_chi_xem') + '</span></div></div>' +
      (Object.keys(m.choGop).length ? '<p class="tab-note tab-note--info">' + h('k3_cho_gop', { thang: thangHien(), tien: tienGop(m.choGop) }) + '</p>' : '') +
      (rows ? '<div class="k3-tbl-wrap"><table class="k3-tbl k3-tbl--compact"><thead><tr><th>' + h('type') + '</th><th>' + h('doc_no') + '</th><th>' + h('c_date') + '</th><th class="num">' + h('c_value') + '</th>' +
        '<th class="num">' + h('in_lak') + '</th><th class="num">' + h('collected') + '</th><th class="num">' + h('remaining') + '</th><th>' + h('c_st_f') + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>'
        : '<div class="k3-empty">' + h('kh_no_trong') + '</div>');
  }

  /* ================= Hồ sơ khách ================= */
  function renderDetail() {
    const k = byId(st.id);
    if (!k) { $('#k3-work').innerHTML = '<div class="k3-empty">' + h('k3_chon_khach') + '</div>'; return; }
    const g = xemTien(), m = metrics(k.id), no = g ? ((cache[k.id] || {}).no || noCua(k.id)) : null;
    const c = cache[k.id] || {};
    const tabs = [{ id: 'contracts', label: h('hd_nut'), count: hdCua(k.id).length }];
    if (g) tabs.push({ id: 'prices', label: h('kh_bang_gia'), count: c.gia ? c.gia.filter(r => r.active).length : '·' });
    tabs.push({ id: 'trips', label: h('k3_tab_chuyen'), count: c.trips ? c.trips.length : '·' });
    if (g) tabs.push({ id: 'debt', label: h('kh_cong_no'), count: no ? no.so_to_no : '·' });
    if (!tabs.some(x => x.id === st.tab)) st.tab = 'contracts';
    const body = st.tab === 'prices' ? pricesTab(k) : st.tab === 'trips' ? tripsTab(k) : st.tab === 'debt' ? debtTab(k) : contractsTab(k);
    const miss = (key) => '<span class="missing">' + h(key) + '</span>';
    const addBtn = st.tab === 'contracts' && suaHd()
      ? '<button type="button" class="k3-btn k3-btn--primary k3-btn--sm tabs-action" data-act="add-contract"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>' + h('hd_them') + '</button>'
      : st.tab === 'prices' && suaGia()
        ? '<button type="button" class="k3-btn k3-btn--primary k3-btn--sm tabs-action" data-act="add-price"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>' + h('k3_them_gia') + '</button>' : '';
    const stats = '<div class="stat"><span>' + h('k3_chuyen_thang', { thang: thangHien() }) + '</span><b>' + (c.trips ? m.trips : '·') + '</b><em>' + h('k3_gom_giao', { g: m.gom, d: m.giao }) + '</em></div>' +
      '<div class="stat"><span>' + h('k3_san_luong') + '</span><b>' + n2(m.tons) + '<small>' + h('ton') + '</small></b></div>' +
      (g ? '<div class="stat"><span>' + h('k3_doanh_thu_thang') + '</span><b class="stat-tien">' + (Object.keys(m.rev).length ? tienGop(m.rev) : '0') + '</b><em>≈ ' + n0(m.revLak) + ' LAK</em></div>' +
        '<div class="stat ' + (no && no.con_no_lak > 0 ? 'is-danger' : '') + '"><span>' + h('kh_cong_no') + '</span><b class="stat-tien">' + (no && no.con_no_lak > 0 ? tienGop(no.con_no_tien) : '0') + '</b>' +
          '<em>' + (no ? (no.con_no_lak > 0 ? '≈ ' + n0(no.con_no_lak) + ' LAK · ' + t('k3_to_con_no', { n: no.so_to_no }) : t('k3_khong_no')) : '') + '</em></div>'
        : '<div class="stat"><span>' + h('k3_hd_dang_ap') + '</span><b class="stat-tien">' + esc((currentContract(k.id) || {}).contract_no || '–') + '</b></div>');
    $('#k3-work').innerHTML =
      '<section class="k3-panel profile">' +
        '<div class="profile-top">' +
          '<span class="avatar avatar--lg' + (k.cust_type === 'company' ? ' avatar--company' : '') + '" lang="lo">' + esc(initial(k.name)) + '</span>' +
          '<div class="profile-id"><div class="profile-name"><h2 lang="lo">' + esc(k.name) + '</h2>' +
              '<span class="k3-tag ' + (k.active ? 'k3-tag--ok">' + h('active') : 'k3-tag--muted">' + h('k3_ngung_gd')) + '</span>' +
              (k.cust_type ? '<span class="k3-tag k3-tag--muted">' + h(k.cust_type === 'company' ? 'k3_cong_ty' : 'k3_ca_nhan') + '</span>' : '') +
              (k.code ? '<span class="k3-tag k3-tag--code" title="' + esc(t('k3_ma_goi_y')) + '">' + esc(k.code) + '</span>' : '<span class="k3-tag k3-tag--warn" title="' + esc(t('k3_ma_goi_y')) + '">' + h('k3_chua_ma') + '</span>') + '</div>' +
            '<div class="meta">' +
              '<span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>' + (k.phone ? esc(k.phone) : miss('k3_chua_dt')) + '</span>' +
              '<span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>' + (k.address ? '<span class="lo" lang="lo">' + esc(k.address) + '</span>' : miss('k3_chua_dc')) + '</span>' +
              '<span title="' + esc(modeHelp(k.invoice_mode)) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6"/></svg>' + h('inv_mode') + ': <b>' + modeLabel(k.invoice_mode) + '</b></span>' +
              (k.note ? '<span class="meta-note" title="' + esc(k.note) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v11H8l-4 4z"/></svg>' + esc(k.note) + '</span>' : '') +
            '</div></div>' +
          '<div class="profile-tools">' +
            (k.phone ? '<a class="k3-btn k3-btn--sm" href="tel:' + esc(String(k.phone).replace(/\s/g, '')) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>' + h('k3_goi') + '</a>' : '') +
            (suaDuoc() ? '<button type="button" class="k3-btn k3-btn--sm" data-act="edit-customer"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4"/></svg>' + h('edit') + '</button>' : '') + '</div>' +
        '</div>' +
        '<div class="stats">' + stats + '</div>' +
      '</section>' +
      lifeHtml(k) +
      '<section class="k3-panel tabs-panel"><div class="tabs-bar"><div class="tabs" role="tablist">' + tabs.map(x =>
        '<button type="button" class="tab" role="tab" data-tab="' + x.id + '" aria-selected="' + (st.tab === x.id) + '">' + x.label + ' <span class="count">' + x.count + '</span></button>').join('') +
      '</div>' + addBtn + '</div><div class="tab-panel" role="tabpanel">' + body + '</div></section>';
  }

  function render() {
    if (!root) return;
    renderList();
    renderDetail();
    const k = byId(st.id);
    $('#k3-phu').innerHTML = k ? h('k3_sub_khach', { ten: k.name }) : h('k3_sub');
  }

  /* ================= Tải dữ liệu ================= */
  async function taiKhach(cid) {
    if (!cid) return;
    const c = cache[cid] = cache[cid] || {};
    const viec = [API.get('/api/trips?customer_id=' + encodeURIComponent(cid) + '&thang=' + thangNay() + '&co=500').then(r => { c.trips = r; }).catch(() => { c.trips = []; })];
    if (xemTien()) {
      viec.push(API.get('/api/customers/' + cid + '/bang-gia').then(r => { c.gia = r; }).catch(() => { c.gia = []; }));
      viec.push(API.get('/api/customers/' + cid + '/cong-no').then(r => { c.no = r; }).catch(() => { c.no = null; }));
    }
    await Promise.all(viec);
    if (st.id === cid) render();
  }
  async function taiHd() { try { HD = await API.get('/api/hop-dong?kind=khach'); } catch (e) { HD = []; } }
  async function tai() {
    const [kh] = await Promise.all([API.get('/api/customers'), taiHd(),
      xemTien() ? API.get('/api/customers-cong-no').then(r => { NO_TONG = r || {}; }).catch(() => { NO_TONG = {}; }) : Promise.resolve()]);
    ds = kh || [];
    if (!ds.some(k => k.id === st.id)) {
      // mở màn là thấy một khách: khách có hợp đồng sắp hết hạn trước, không thì khách đầu
      const sap = ds.find(k => { const c = currentContract(k.id); return c && cStatus(c).key === 'expiring' && !renewalOf(k.id, c); });
      st.id = (sap || ds[0] || {}).id || null;
    }
    render();
    await taiKhach(st.id);
  }
  function chon(id) {
    st.id = id; render();
    if (!cache[id]) taiKhach(id);
    if (window.innerWidth <= 1180) $('#k3-work').scrollIntoView({ block: 'start' });
  }

  /* ================= Hộp thoại ================= */
  let onSave = null, onInput = null;
  const modal = () => $('#k3-modal'), form = () => $('#k3-form');
  function dateField(name, label, value, span, can) {
    return '<div class="k3-field ' + (span || 'f-2') + '"><label for="k3f-' + name + '">' + label + '</label>' +
      '<div class="input-wrap"><input class="input" id="k3f-' + name + '" name="' + name + '" inputmode="numeric" placeholder="dd/mm/yyyy" value="' + esc(value || '') + '" data-date autocomplete="off">' +
      '<input type="date" class="native" tabindex="-1" aria-hidden="true" data-native-for="k3f-' + name + '" value="' + iso(pd(value)) + '">' +
      '<button type="button" class="icon-btn cal" data-cal="k3f-' + name + '" aria-label="' + esc(label) + '"><svg class="ico" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></svg></button></div>' +
      (can ? '<span class="hint">' + can + '</span>' : '') + '<span class="err" data-err="' + name + '" hidden></span></div>';
  }
  function openModal(html, save) {
    const f = form(); f.innerHTML = html; onSave = save; onInput = null;
    NN.apDung(f);
    const m = modal(); if (typeof m.showModal === 'function') m.showModal(); else m.setAttribute('open', '');
    const first = f.querySelector('input:not([type=hidden]):not(.native):not([readonly]), textarea'); if (first) first.focus();
  }
  function closeModal() { const m = modal(); if (m && m.open) m.close(); onSave = null; onInput = null; }
  function setErr(name, msg) {
    const f = form(), e = f.querySelector('[data-err="' + name + '"]'), inp = f.elements[name];
    if (e) { e.textContent = msg || ''; e.hidden = !msg; }
    if (inp && inp.classList) inp.classList.toggle('is-invalid', !!msg);
  }
  const nutDong = () => '<button type="button" class="icon-btn" data-close aria-label="' + esc(t('close')) + '"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button>';
  const coTep = (fl) => fl.size > 1048576 ? (fl.size / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(fl.size / 1024)) + ' KB';

  /* ----- Hợp đồng ----- */
  function contractModal(k, c, mode) {                // mode: add · edit · renew
    const isEdit = mode === 'edit';
    const start = isEdit ? fd(fromIso(c.valid_from)) : mode === 'renew' && c.valid_to ? fd(addDays(fromIso(c.valid_to), 1)) : fd(TODAY());
    const endV = isEdit ? fd(fromIso(c.valid_to)) : fd(addDays(addMonths(pd(start), 12), -1));
    const no = isEdit ? c.contract_no : nextContractNo(pd(start).getUTCFullYear());
    const tieuDe = isEdit ? h('hd_sua') : mode === 'renew' ? h('k3_gia_han_hd') : h('hd_them');
    const moi = [], bo = [];
    const cu = isEdit ? (c.files || []).slice() : [];
    const html =
      '<div class="modal-head"><div><h2>' + tieuDe + '</h2><p>' + h('c_customer') + ' <span class="lo" lang="lo">' + esc(k.name) + '</span>' + (mode === 'renew' ? ', ' + h('k3_noi_tiep', { so: c.contract_no }) : '') + '</p></div>' + nutDong() + '</div>' +
      '<div class="modal-body">' +
        '<div class="k3-field f-3"><label for="k3f-no">' + h('hd_so') + ' <span class="hint-inline">' + h(isEdit ? 'k3_so_khong_doi' : 'k3_so_goi_y') + '</span></label><input class="input code" style="font-size:14px" id="k3f-no" name="no" value="' + esc(no) + '"' + (isEdit ? ' readonly' : '') + '>' +
          '<span class="err" data-err="no" hidden></span></div>' +
        '<div class="k3-field f-3"><span class="label">' + h('status') + '</span><div class="k3-seg" role="radiogroup">' +
          '<label><input type="radio" name="status" value="1"' + (!isEdit || c.active ? ' checked' : '') + '><span>' + h('active') + '</span></label>' +
          '<label><input type="radio" name="status" value="0"' + (isEdit && !c.active ? ' checked' : '') + '><span>' + h('hd_ngung') + '</span></label></div></div>' +
        dateField('signed', t('hd_ngay_ky'), isEdit ? fd(fromIso(c.sign_date)) : fd(TODAY())) +
        dateField('start', t('hd_tu'), start) +
        dateField('end', t('hd_den'), endV, 'f-2', h('k3_de_trong_vo_han')) +
        '<div class="k3-field f-6"><span class="label">' + h('k3_thoi_han_nhanh') + '</span><div class="durations" id="k3-durations">' +
          [3, 6, 12, 24].map(n => '<button type="button" data-months="' + n + '">' + esc(t('k3_n_thang', { n })) + '</button>').join('') + '</div></div>' +
        '<div class="k3-field f-6"><label for="k3f-note">' + h('note') + '</label><textarea class="input" id="k3f-note" name="note" rows="2" placeholder="' + esc(t('k3_note_ph')) + '">' + esc(isEdit ? (c.note || '') : mode === 'renew' ? t('k3_gia_han_tu', { so: c.contract_no }) : '') + '</textarea></div>' +
        '<div class="k3-field f-6"><span class="label">' + h('k3_anh_pdf') + '</span>' +
          '<div class="drop-row"><label class="dropzone dropzone--inline" id="k3-drop"><input type="file" accept="image/*,application/pdf" multiple id="k3f-files">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></svg><span>' + h('k3_keo_tha') + '</span></label>' +
          '<div class="file-list" id="k3-files"></div></div></div>' +
      '</div>' +
      '<div class="modal-foot"><span class="summary" id="k3-sum"></span><div class="actions">' +
        '<button type="button" class="k3-btn" data-close>' + h('cancel') + '</button><button type="submit" class="k3-btn k3-btn--primary">' + h('k3_luu_hd') + '</button></div></div>';

    openModal(html, async () => {
      const f = form().elements; let ok = true;
      const vNo = f.no.value.trim(), s = pd(f.start.value), e = f.end.value.trim() ? pd(f.end.value) : null, sg = pd(f.signed.value);
      ['no', 'signed', 'start', 'end'].forEach(n => setErr(n, ''));
      if (!vNo) { setErr('no', t('k3_e_so')); ok = false; }
      else if (!isEdit && HD.some(x => String(x.contract_no || '').toLowerCase() === vNo.toLowerCase())) { setErr('no', t('k3_e_so_trung')); ok = false; }
      if (!sg) { setErr('signed', t('k3_e_ngay')); ok = false; }
      if (!s) { setErr('start', t('k3_e_ngay')); ok = false; }
      if (f.end.value.trim() && !e) { setErr('end', t('k3_e_ngay')); ok = false; }
      else if (s && e && e < s) { setErr('end', t('k3_e_het_truoc')); ok = false; }
      if (!ok) { const bad = form().querySelector('.is-invalid'); if (bad) bad.focus(); return false; }
      const body = { contract_no: vNo, sign_date: iso(sg), valid_from: iso(s), valid_to: e ? iso(e) : '', active: form().querySelector('[name=status]:checked').value === '1',
        note: f.note.value.trim(), kind: 'khach', customer_id: k.id };
      let luu;
      try { luu = await (isEdit ? API.put('/api/hop-dong/' + c.id, body) : API.post('/api/hop-dong', body)); } catch (err) { EPL.baoLoi(err); return false; }
      const hid = isEdit ? c.id : (luu && luu.id);
      for (const tep of bo) { try { await API.goi('/api/hop-dong-tep/' + tep, { method: 'DELETE' }); } catch (err) { EPL.baoLoi(err); } }
      for (const fl of moi) {
        try { const nen = await EPL.nenTep(fl); const fdt = new FormData(); fdt.append('tep', nen, nen.name); await API.tep('/api/hop-dong/' + hid + '/tep', fdt); } catch (err) { EPL.baoLoi(err); }
      }
      st.tab = 'contracts';
      EPL.toast(t('k3_da_luu_hd', { so: vNo }), 'ok');
      await taiHd();
      return true;
    });
    function refresh() {
      const fe = form().elements, s = pd(fe.start.value), e = pd(fe.end.value);
      $$('#k3-durations button').forEach(b => b.classList.toggle('is-on', !!(s && e && fd(addDays(addMonths(s, +b.dataset.months), -1)) === fd(e))));
      $('#k3-sum').innerHTML = s && e && e >= s ? h('k3_sum', { tu: fd(s), den: fd(e), n: days(s, e) + 1 }) : s && !fe.end.value.trim() ? h('k3_sum_vo_han', { tu: fd(s) }) : h('k3_sum_nhap');
    }
    function drawFiles() {
      $('#k3-files').innerHTML = cu.map(x => '<span class="file">' + esc(x.filename) + '<button type="button" data-rm-cu="' + esc(x.id) + '" aria-label="' + esc(t('delete')) + '">×</button></span>').join('') +
        moi.map((x, i) => '<span class="file">' + esc(x.name) + ' <small>' + esc(coTep(x)) + '</small><button type="button" data-rm="' + i + '" aria-label="' + esc(t('delete')) + '">×</button></span>').join('');
    }
    onInput = refresh;
    $('#k3-durations').addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-months]'); if (!b) return;
      const s = pd(form().elements.start.value); if (!s) { setErr('start', t('k3_e_nhap_tu')); return; }
      form().elements.end.value = fd(addDays(addMonths(s, +b.dataset.months), -1));
      setErr('end', ''); refresh();
    });
    const them = (list) => { Array.from(list).forEach(fl => moi.push(fl)); drawFiles(); };
    $('#k3f-files').addEventListener('change', (ev) => { them(ev.target.files); ev.target.value = ''; });
    const drop = $('#k3-drop');
    drop.addEventListener('dragover', (ev) => { ev.preventDefault(); drop.classList.add('is-over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('is-over'));
    drop.addEventListener('drop', (ev) => { ev.preventDefault(); drop.classList.remove('is-over'); them(ev.dataTransfer.files); });
    $('#k3-files').addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-rm]'); if (b) { moi.splice(+b.dataset.rm, 1); drawFiles(); return; }
      const bc = ev.target.closest('[data-rm-cu]'); if (bc) { bo.push(bc.dataset.rmCu); cu.splice(cu.findIndex(x => x.id === bc.dataset.rmCu), 1); drawFiles(); }
    });
    drawFiles(); refresh();
  }

  /* ----- Khách hàng ----- */
  function customerModal(k) {
    const isEdit = !!k;
    k = k || { name: '', code: '', cust_type: 'person', active: true, phone: '', address: '', invoice_mode: 'phieu', note: '' };
    const html =
      '<div class="modal-head"><div><h2>' + h(isEdit ? 'k3_sua_khach' : 'k3_them_khach') + '</h2><p>' + h('k3_ma_goi_y') + '</p></div>' + nutDong() + '</div>' +
      '<div class="modal-body">' +
        '<div class="k3-field f-4"><label for="k3f-name">' + h('k3_ten_khach') + '</label><input class="input lo" lang="lo" id="k3f-name" name="name" value="' + esc(k.name) + '" placeholder="' + esc(t('k3_ten_ph')) + '"><span class="err" data-err="name" hidden></span></div>' +
        '<div class="k3-field f-2"><label for="k3f-code">' + h('k3_ma_khach') + '</label><input class="input code" id="k3f-code" name="code" value="' + esc(k.code || '') + '" placeholder="KH-0015" spellcheck="false" autocomplete="off"><span class="err" data-err="code" hidden></span></div>' +
        '<div class="k3-field f-3"><span class="label">' + h('k3_loai_khach') + '</span><div class="k3-seg" role="radiogroup">' +
          '<label><input type="radio" name="cust_type" value="person"' + (k.cust_type !== 'company' ? ' checked' : '') + '><span>' + h('k3_ca_nhan') + '</span></label>' +
          '<label><input type="radio" name="cust_type" value="company"' + (k.cust_type === 'company' ? ' checked' : '') + '><span>' + h('k3_cong_ty') + '</span></label></div></div>' +
        '<div class="k3-field f-3"><span class="label">' + h('status') + '</span><div class="k3-seg" role="radiogroup">' +
          '<label><input type="radio" name="active" value="1"' + (k.active ? ' checked' : '') + '><span>' + h('active') + '</span></label>' +
          '<label><input type="radio" name="active" value="0"' + (!k.active ? ' checked' : '') + '><span>' + h('inactive') + '</span></label></div></div>' +
        '<div class="k3-field f-3"><label for="k3f-phone">' + h('phone') + '</label><input class="input" id="k3f-phone" name="phone" inputmode="tel" value="' + esc(k.phone || '') + '" placeholder="020 5555 1234"></div>' +
        '<div class="k3-field f-3"><label for="k3f-address">' + h('address') + '</label><input class="input lo" lang="lo" id="k3f-address" name="address" value="' + esc(k.address || '') + '" placeholder="' + esc(t('k3_dc_ph')) + '"></div>' +
        '<div class="k3-field f-6"><span class="label">' + h('inv_mode') + '</span><div class="choice-cards">' +
          '<label class="choice"><input type="radio" name="invoice_mode" value="phieu"' + (k.invoice_mode !== 'thang' ? ' checked' : '') + '><b>' + h('inv_phieu_s') + '</b><small>' + h('inv_phieu') + '</small></label>' +
          '<label class="choice"><input type="radio" name="invoice_mode" value="thang"' + (k.invoice_mode === 'thang' ? ' checked' : '') + '><b>' + h('inv_thang_s') + '</b><small>' + h('inv_thang') + '</small></label></div></div>' +
        '<div class="k3-field f-6"><label for="k3f-knote">' + h('note') + '</label><textarea class="input" id="k3f-knote" name="note" rows="2">' + esc(k.note || '') + '</textarea></div>' +
      '</div>' +
      '<div class="modal-foot"><span class="summary">' + h('k3_bo_sung_sau') + '</span><div class="actions">' +
        '<button type="button" class="k3-btn" data-close>' + h('cancel') + '</button><button type="submit" class="k3-btn k3-btn--primary">' + h(isEdit ? 'k3_luu_thay_doi' : 'k3_them_khach') + '</button></div></div>';
    openModal(html, async () => {
      const f = form().elements; setErr('name', ''); setErr('code', '');
      if (!f.name.value.trim()) { setErr('name', t('k3_e_ten')); f.name.focus(); return false; }
      const body = { name: f.name.value.trim(), code: f.code.value.trim(), cust_type: form().querySelector('[name=cust_type]:checked').value,
        phone: f.phone.value.trim(), address: f.address.value.trim(), invoice_mode: form().querySelector('[name=invoice_mode]:checked').value, note: f.note.value.trim() };
      if (isEdit) body.active = form().querySelector('[name=active]:checked').value === '1';
      let luu;
      try { luu = await (isEdit ? API.put('/api/customers/' + k.id, body) : API.post('/api/customers', body)); }
      catch (err) {
        if (/MA_KHACH/.test(String(err.ma || err.code || '')) || /Mã khách/.test(err.message || '')) { setErr('code', err.message); return false; }
        EPL.baoLoi(err); return false;
      }
      EPL.toast(t(isEdit ? 'k3_da_luu_khach' : 'k3_da_them_khach'), 'ok');
      if (!isEdit && luu && luu.id) { st.id = luu.id; st.tab = 'contracts'; }
      ds = await API.get('/api/customers');
      return true;
    });
  }

  /* ----- Bảng giá (giữ ô nhập của màn cũ: tuyến, loại hàng, tiền tệ, cách tính, giá thuê xe liên kết) ----- */
  async function suaGiaDong(k, r) {
    if (!tuyen.length) { try { tuyen = await API.get('/api/routes'); } catch (e) { return EPL.baoLoi(e); } }
    const v = await EPL.hopNhap(NN.t('kh_bang_gia') + ' · ' + k.name, [
      { id: 'route_id', label: 'route', type: 'select', value: r ? r.route_id : (tuyen[0] || {}).id, options: tuyen.filter(x => x.active || (r && x.id === r.route_id)).map(x => [x.id, x.name]) },
      { id: 'goods_type', label: 'goods_type', type: 'select', value: r ? r.goods_type : 'iron_ore', options: [['iron_ore', NN.t('iron_ore')], ['other_goods', NN.t('other_goods')]] },
      { id: 'price_ccy', label: 'ccy_price', type: 'select', value: r ? (r.price_ccy || 'USD') : 'USD', options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'price_mode', label: 'price_mode', type: 'select', value: r ? (r.price_mode || 'ton') : 'ton', options: [['ton', NN.t('pm_ton')], ['chuyen', NN.t('pm_chuyen')]] },
      { id: 'price', label: 'price_usd', type: 'number', value: r ? r.price : '' },
      { id: 'hire_ccy', label: 'ccy_hire', type: 'select', value: r ? (r.hire_ccy || '') : '', options: [['', '—']].concat(EPL.TIEN_TE.map(m => [m, m])) },
      { id: 'hire_price', label: 'hire_pt', type: 'number', value: r ? (r.hire_price ?? '') : '' },
      { id: 'valid_from', label: 'valid_from', type: 'date', value: r ? (r.valid_from || '') : EPL.homNay() },
      { id: 'note', label: 'note', type: 'textarea', value: r ? r.note : '' },
      ...(r ? [{ id: 'active', label: 'status', type: 'select', value: r.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!(EPL.doc(v.price) > 0)) return EPL.toast(NN.t('price_usd') + '?', 'loi');
    try {
      const body = { route_id: v.route_id, goods_type: v.goods_type, price: v.price, price_ccy: v.price_ccy, price_mode: v.price_mode,
        hire_price: v.hire_price === '' ? null : v.hire_price, hire_ccy: v.hire_ccy || null, valid_from: v.valid_from || null, note: v.note };
      if (r) body.active = v.active === '1';
      await (r ? API.put('/api/bang-gia/' + r.id, body) : API.post('/api/customers/' + k.id + '/bang-gia', body));
      EPL.toast(NN.t('saved'), 'ok');
      cache[k.id].gia = await API.get('/api/customers/' + k.id + '/bang-gia'); render();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function xoaGia(k, r) {
    if (!await EPL.hoi(NN.t('delete'), '<p>' + esc(r.route_name || '') + ' · ' + EPL.tien(r.price, r.price_ccy) + '</p>', NN.t('delete'))) return;
    try { await API.del('/api/bang-gia/' + r.id); cache[k.id].gia = cache[k.id].gia.filter(x => x.id !== r.id); render(); EPL.toast(NN.t('saved'), 'ok'); } catch (e) { EPL.baoLoi(e); }
  }

  /* ================= Sự kiện ================= */
  async function onClick(e) {
    const kt = e.target.closest('[data-kt-gop]');
    if (kt) { e.preventDefault(); EPL.moKeToan('hoa-don-gop', { thang: kt.dataset.thang, id: kt.dataset.ktGop }); return; }
    const mp = e.target.closest('[data-mo-phieu]');
    if (mp) { EPL.di('phieu-xuat-xe', { id: mp.dataset.moPhieu }); return; }
    const c = e.target.closest('[data-cust]');
    if (c) { chon(c.dataset.cust); return; }
    const tb = e.target.closest('[role="tab"][data-tab]');
    if (tb) { st.tab = tb.dataset.tab; render(); const nb = root.querySelector('[role="tab"][data-tab="' + st.tab + '"]'); if (nb) nb.focus(); return; }
    const ch = e.target.closest('#k3-loc [data-filter]');
    if (ch) { st.filter = ch.dataset.filter; $$('#k3-loc .chip').forEach(x => x.classList.toggle('is-on', x === ch)); renderList(); return; }
    const a = e.target.closest('[data-act]');
    if (!a || a.closest('#k3-modal')) return;
    const k = byId(st.id), act = a.dataset.act;
    const hd = a.dataset.hd ? HD.find(x => x.id === a.dataset.hd) : null;
    const gia = a.dataset.gia && k ? ((cache[k.id] || {}).gia || []).find(x => x.id === a.dataset.gia) : null;
    if (act === 'add-customer') return customerModal(null);
    if (!k) return;
    if (act === 'add-contract') contractModal(k, null, 'add');
    else if (act === 'edit-contract' && hd) contractModal(k, hd, 'edit');
    else if (act === 'renew' && hd) contractModal(k, hd, 'renew');
    else if (act === 'edit-customer') customerModal(k);
    else if (act === 'add-price') suaGiaDong(k, null);
    else if (act === 'edit-price' && gia) suaGiaDong(k, gia);
    else if (act === 'del-price' && gia) xoaGia(k, gia);
    else if (act === 'del-contract' && hd) {
      if (!await EPL.hoi(NN.t('delete'), '<p class="mono">' + esc(hd.contract_no) + '</p>', NN.t('delete'))) return;
      try { await API.goi('/api/hop-dong/' + hd.id, { method: 'DELETE' }); EPL.toast(NN.t('saved'), 'ok'); await taiHd(); render(); } catch (err) { EPL.baoLoi(err); }
    } else if (act === 'del-file') {
      if (!await EPL.hoi(NN.t('delete'), '<p>' + NN.h('attach_del') + '</p>', NN.t('delete'))) return;
      try { await API.goi('/api/hop-dong-tep/' + a.dataset.tep, { method: 'DELETE' }); await taiHd(); render(); } catch (err) { EPL.baoLoi(err); }
    }
  }
  async function onChange(e) {
    const inp = e.target.closest && e.target.closest('[data-attach]');
    if (!inp || !inp.files || !inp.files.length) return;
    const hd = HD.find(x => x.id === inp.dataset.attach); let n = 0;
    for (const fl of Array.from(inp.files)) {
      try { const nen = await EPL.nenTep(fl); const fdt = new FormData(); fdt.append('tep', nen, nen.name); await API.tep('/api/hop-dong/' + inp.dataset.attach + '/tep', fdt); n++; } catch (err) { EPL.baoLoi(err); }
    }
    if (n) EPL.toast(t('k3_da_dinh_kem', { n, so: hd ? hd.contract_no : '' }), 'ok');
    await taiHd(); render();
  }
  function ganModal() {
    const f = form(), m = modal();
    f.addEventListener('input', (e) => {
      const x = e.target;
      if (x.hasAttribute && x.hasAttribute('data-date') && !(e.inputType && e.inputType.indexOf('delete') === 0)) {
        const so = x.value.replace(/\D/g, '').slice(0, 8);
        x.value = so.length > 4 ? so.slice(0, 2) + '/' + so.slice(2, 4) + '/' + so.slice(4) : so.length > 2 ? so.slice(0, 2) + '/' + so.slice(2) : so;
      }
      if (onInput) onInput(e);
    });
    f.addEventListener('click', (e) => {
      const cal = e.target.closest('[data-cal]');
      if (cal) {
        const nat = f.querySelector('[data-native-for="' + cal.dataset.cal + '"]'), txt = f.querySelector('#' + cal.dataset.cal);
        nat.value = iso(pd(txt.value));
        if (nat.showPicker) { try { nat.showPicker(); } catch (err) { txt.focus(); } } else txt.focus();
        return;
      }
      if (e.target.closest('[data-close]')) closeModal();
    });
    f.addEventListener('change', (e) => {
      const x = e.target; if (!x.hasAttribute || !x.hasAttribute('data-native-for')) return;
      const txt = f.querySelector('#' + x.dataset.nativeFor);
      txt.value = fd(fromIso(x.value)); txt.dispatchEvent(new Event('input', { bubbles: true }));
    });
    f.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nut = f.querySelector('[type=submit]'); if (nut) nut.disabled = true;
      let xong = false;
      try { xong = onSave ? (await onSave()) !== false : true; } finally { if (nut) nut.disabled = false; }
      if (xong) { closeModal(); render(); if (st.id && !cache[st.id]) taiKhach(st.id); }
    });
    m.addEventListener('click', (e) => { if (e.target === m) closeModal(); });
  }
  let daGanPhim = false;
  function ganPhim() {
    if (daGanPhim) return; daGanPhim = true;
    document.addEventListener('keydown', (e) => {
      if (!root || !root.isConnected) return;
      const a = document.activeElement;
      if (e.key === '/' && !(a && /INPUT|TEXTAREA|SELECT/.test(a.tagName)) && !(modal() && modal().open)) { const o = root.querySelector('#k3-tim'); if (o) { e.preventDefault(); o.focus(); } }
      if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && e.target.getAttribute && e.target.getAttribute('role') === 'tab' && root.contains(e.target)) {
        const ts = $$('[role="tab"]'), i = ts.indexOf(e.target), nt = ts[(i + (e.key === 'ArrowRight' ? 1 : ts.length - 1)) % ts.length];
        if (nt) nt.click();
      }
    });
  }

  EPL.modules['khach-hang'] = {
    async init(r, { tham } = {}) {
      root = r; ds = []; HD = []; NO_TONG = {}; Object.keys(cache).forEach(x => delete cache[x]);
      st.id = tham && tham.id ? tham.id : null; st.tab = tham && tham.tab ? tham.tab : 'contracts'; st.filter = 'all'; st.query = '';
      const them = $('#k3-them'); them.hidden = !suaDuoc();
      if (!xemTien()) { const cn = root.querySelector('#k3-loc [data-filter="debt"]'); if (cn) cn.remove(); }
      $('#k3-tim').addEventListener('input', (e) => { st.query = e.target.value; renderList(); });
      root.addEventListener('click', onClick);
      root.addEventListener('change', onChange);
      ganModal(); ganPhim();
      render();
      await tai();
    },
    onLang() { if (root) render(); },
    xuatExcel() {
      const g = xemTien();
      return [EPL.xuatSheet(t('nav_customers'),
        [t('k3_ma_khach'), t('k3_ten_khach'), t('k3_loai_khach'), t('status'), t('phone'), t('address'), t('inv_mode'), t('k3_hd_dang_ap'), t('status'), t('hd_den')]
          .concat(g ? [t('kh_no_con_no') + ' (LAK)'] : []),
        ds.map(k => {
          const c = currentContract(k.id), no = noCua(k.id);
          return [k.code || '', k.name, k.cust_type ? t(k.cust_type === 'company' ? 'k3_cong_ty' : 'k3_ca_nhan') : '', t(k.active ? 'active' : 'inactive'),
            k.phone || '', k.address || '', t(k.invoice_mode === 'thang' ? 'inv_thang_s' : 'inv_phieu_s'),
            c ? c.contract_no : '', c ? cStatus(c).label : '', c && c.valid_to ? EPL.oNgay(c.valid_to) : ''].concat(g ? [EPL.oSo(no ? no.con_no_lak : 0, 0, 'LAK')] : []);
        }))];
    },
  };
})();
