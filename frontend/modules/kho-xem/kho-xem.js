/* Xem kho — ເບິ່ງສາງ. CHỈ XEM (sếp 30/09: kho dời về trang logistics; thao tác kho do bên kho — anh Toàn).
 *
 * Giao diện theo bản mẫu chủ dự án gửi chiều 30/09 (Kho_new.zip): cột trái là danh sách kho nhóm theo khu vực (mỗi kho
 * một bồn nhỏ), phải là "Toàn bộ kho" (việc cần xử lý · bức tường bồn · ma trận phụ tùng · lô hàng gửi bãi) hoặc chi tiết
 * một kho (bồn lớn theo sức chứa, vạch mức an toàn, phiếu đề nghị chờ cấp, phụ tùng, hàng gửi bãi).
 * KHÔNG có sổ kho tháng / biểu đồ nhập xuất theo ngày (bỏ tối 30/09): Excel của khách, sheet ລາຍງານ, xếp báo cáo kho
 * nhiên liệu và kho phụ tùng vào ໂມດູນສາງ — hệ kho của anh Toàn; bên logistics chỉ xem TỒN theo mặt hàng.
 *
 * Số tồn, giá bình quân, sức chứa, mức an toàn, khu vực: hỏi bên kho (nay là trang kế toán tạm, sau là API anh Toàn).
 * Phần "chờ cấp" và "đã khai chưa đề nghị" là của trang điều xe. API: GET /api/kho-xem.
 * Vai không thấy giá vốn (thủ kho, thủ kho phụ tùng, tổ sửa chữa, Bãi) thì máy chủ không gửi giá — màn ẩn cột giá.
 * Kho chưa khai sức chứa: bồn vẽ theo mức cao nhất trong tháng, không có phần trăm; chưa khai mức an toàn: không báo
 * "dưới mức".
 */
(function () {
  const { API, NN, esc } = EPL;
  let root = null, R = null, D = null, loi = '';
  const st = { view: 'all', tab: 'fuel', ovTab: 'fuel', filter: 'all', query: '', flashDoc: null };
  let uid = 0;

  /* ================= Tiện ích ================= */
  const $ = (s) => root.querySelector(s);
  const $$ = (s) => Array.from(root.querySelectorAll(s));
  const n0 = (v) => EPL.so(v || 0, 0);
  const n2 = (v) => EPL.so(v || 0, 2);
  const dash = (v, f) => v ? (f || n0)(v) : '<span class="dash">–</span>';
  // giá vốn bên kho tính bằng Kíp — số tiền luôn kèm đơn vị (cột "Giá vốn bình quân" từng hiện "85,000" trần)
  const lak = (v) => dash(v, (x) => EPL.tien(x, 'LAK'));
  const ngay = (s) => s ? EPL.ngay(s) : '';
  const sum = (ds, f) => ds.reduce((s, x) => s + (typeof f === 'function' ? f(x) : (x[f] || 0)), 0);
  const pct = (a, b) => b ? Math.max(0, Math.min(1, a / b)) : 0;
  const h = (k, p) => NN.h(k, p);
  const t = (k, p) => NN.t(k, p);
  const donVi = (u) => u ? t(u) : '';
  /** Tên kho bên kho ghi "ສາງນໍ້າມັນ ທ່າບົກ (Kho dầu Thà Bốc)" — tách để hiện chữ theo ngôn ngữ đang chọn. */
  function tachTen(s) {
    const m = /^(.*?)\s*\(([^()]*)\)\s*$/.exec(s || '');
    return m ? { lo: m[1].trim(), vi: m[2].trim() } : { lo: s || '', vi: s || '' };
  }
  const tenChinh = (x) => NN.lang === 'lo' ? (x.lo || x.vi) : (x.vi || x.lo);
  const tenPhu = (x) => NN.lang === 'lo' ? (x.vi !== x.lo ? x.vi : '') : (x.lo !== x.vi ? x.lo : '');
  const tenNgan = (x) => tenChinh(x).replace(/^(Kho dầu|ສາງນໍ້າມັນ)\s+/i, '');
  // số phiếu mở phiếu xuất xe — chỉ vai vào được màn đó (thủ kho, thủ kho phụ tùng thì chỉ là chữ)
  const moDuoc = () => EPL.manCuaVai(EPL.AUTH.role).some(m => m.id === 'phieu-xuat-xe');
  const moPhieu = (id, chu) => id && moDuoc() ? `<button type="button" class="link" data-mo-phieu="${esc(id)}">${esc(chu)}</button>` : `<span class="code">${esc(chu)}</span>`;

  /* ================= Dữ liệu từ máy chủ → khuôn của màn ================= */
  function chuanHoa(r) {
    const g = !!r.thay_gia;
    const whs = (r.nhien_lieu || []).map(k => {
      const tn = tachTen(k.name);
      // tồn lấy THẲNG số bên kho; `gan_day` (mới trước) chỉ để biết lần nhập gần nhất — không dựng sổ tháng ở đây
      const nhapCuoi = (k.gan_day || []).find(m => m.kind === 'in');
      return {
        id: k.place_id, code: k.code || '', vi: tn.vi, lo: tn.lo, country: k.country || '',
        region: k.region || (k.country === 'VN' ? t('k2_kv_vn') : t('k2_kv_khac')),
        capacity: k.capacity_l || 0, safety: k.safety_l || 0, avgCost: g ? k.gia_bq : null,
        stock: Math.round((k.ton_lit || 0) * 100) / 100, lastIn: nhapCuoi ? nhapCuoi.ngay : null,
        pending: (k.de_nghi || []).map(v => ({ date: v.ngay, doc: v.voucher_no || '', trip: v.trip_id, tripNo: v.doc_no || '', vehicle: v.truck_no || '',
          driver: v.driver_name || '', route: v.route || '', qty: v.qty_l || 0, ban: v.company === 'joint' })),
        declared: (k.chua_de_nghi || []).map(v => ({ date: v.ngay, doc: v.doc_no || '', trip: v.trip_id, vehicle: v.truck_no || '',
          driver: v.driver_name || '', route: v.route || '', qty: v.qty_l || 0 })),
        active: k.active !== false, goc: !!k.kho_goc, parts: {}, cargoTypes: [],
      };
    });
    // Phụ tùng và hàng khách gửi ở bãi: bên này có MỘT kho phụ tùng và MỘT bãi — ở kho gốc (Thà Bốc)
    const goc = whs.find(w => w.goc) || whs[0] || null;
    const parts = (r.phu_tung || []).map(p => ({
      code: p.id, ten: p.name, unit: p.unit, min: p.min_qty || 0, cost: g ? p.gia_bq : null, stock: p.ton, active: p.active !== false,
      pending: (p.tren_phieu || []).map(x => ({ date: x.ngay, doc: x.doc_no || '', trip: x.trip_id, vehicle: x.truck_no || '', qty: x.qty || 0 })),
    }));
    if (goc) parts.forEach(p => { if ((p.stock || 0) > 0) goc.parts[p.code] = p.stock; });
    const cargo = (r.hang || []).map(c => ({
      // chỉ tồn theo lô — không bày nhập / xuất trong tháng hay sổ gần đây (sếp 30/09: màn kho theo mặt hàng, không sổ)
      code: c.name, ten: c.name, yard: goc ? goc.id : null, left: c.ton_t || 0,
      lots: (c.lo || []).map(l => ({ doc: l.doc_no || '', vehicle: l.truck_no || '', customer: l.customer_name || '', origin: l.origin || '',
        inQty: l.nhap_t || 0, left: l.con_t || 0, date: l.ngay })),
    }));
    if (goc) goc.cargoTypes = cargo;
    const byId = {}, byCode = {};
    whs.forEach(w => { tinhKho(w); byId[w.id] = w; if (w.code) byCode[w.code] = w; });
    const partById = {}; parts.forEach(p => { partById[p.code] = p; });
    // khu vực: theo thứ tự kho gốc trước, rồi tên; "khu vực khác" và Việt Nam xuống cuối
    const kv = [];
    whs.slice().sort((a, b) => (b.goc - a.goc) || a.region.localeCompare(b.region)).forEach(w => { if (!kv.includes(w.region)) kv.push(w.region); });
    const cuoi = [t('k2_kv_vn'), t('k2_kv_khac')];
    kv.sort((a, b) => (cuoi.indexOf(a) - cuoi.indexOf(b)) || 0);
    const d = { g, whs, byId, byCode, parts, partById, cargo, regions: kv, goc };
    d.T = {
      stock: sum(whs, 'stock'), declared: sum(whs, 'declaredQty'), pending: sum(whs, 'pendingQty'),
      pendingDocs: sum(whs, w => w.pending.length), whCount: whs.length,
      empty: whs.filter(w => w.status === 'empty'),
      partsLow: parts.filter(p => p.active && p.min > 0 && (p.stock || 0) <= p.min),
      cargoTons: sum(cargo, c => sum(c.lots, 'left')), cargoLots: sum(cargo, c => c.lots.length),
    };
    return d;
  }

  function tinhKho(w) {
    w.pendingQty = sum(w.pending, 'qty');
    w.declaredQty = sum(w.declared, 'qty');
    w.remain = w.stock - w.pendingQty - w.declaredQty;
    w.status = w.stock <= 0 ? 'empty' : (w.safety && w.remain < w.safety ? 'low' : 'ok');
    w.alerts = [];
    if (w.status === 'low') w.alerts.push('low');
    if (w.declaredQty > 0) w.alerts.push('declared');
    if (w.pendingQty > 0) w.alerts.push('pending');
    w.partKinds = 0;
    // thang vẽ bồn khi kho chưa khai sức chứa: số tồn hiện có (hoặc phần đã đề nghị, nếu lớn hơn)
    w.peak = Math.max(w.stock, w.pendingQty + w.declaredQty, 1);
    return w;
  }
  const thangVe = (w) => w.capacity || w.peak * 1.15;
  const partTotal = (code) => sum(D.whs, w => (w.parts && w.parts[code]) || 0);
  const isBelowMin = (p, qty) => p.min > 0 && qty <= p.min;

  /* ================= Bồn chứa (SVG) ================= */
  function tankSvg(w, o) {
    o = o || {};
    const id = 'k2t' + (++uid);
    const W = o.width || 84, H = o.height || 150, pad = o.scale && w.capacity ? 46 : 4;
    const bx = pad, bw = W - pad - 4, top = 10, bh = H - top - 6, r = Math.min(14, bw / 4);
    const cap = thangVe(w);
    const fillH = bh * pct(w.stock, cap);
    const declH = bh * pct(w.declaredQty + w.pendingQty, cap);
    const yFill = top + bh - fillH;
    const ySafe = w.safety ? top + bh - bh * pct(w.safety, cap) : null;
    let wave = '';
    if (fillH > 6) {
      const y = yFill, x0 = bx, x1 = bx + bw, amp = Math.min(3, fillH / 6), seg = bw / 4;
      wave = 'M' + x0 + ',' + (y + amp) + ' Q' + (x0 + seg * 0.5) + ',' + (y - amp) + ' ' + (x0 + seg) + ',' + (y + amp) +
        ' T' + (x0 + seg * 2) + ',' + (y + amp) + ' T' + (x0 + seg * 3) + ',' + (y + amp) + ' T' + x1 + ',' + (y + amp) +
        ' L' + x1 + ',' + (top + bh) + ' L' + x0 + ',' + (top + bh) + ' Z';
    }
    let ticks = '';
    if (o.scale && w.capacity) {
      [0, 0.25, 0.5, 0.75, 1].forEach(f => {
        const ty = top + bh - bh * f;
        ticks += '<line x1="' + (bx - 6) + '" x2="' + (bx - 2) + '" y1="' + ty + '" y2="' + ty + '" class="sv-line2"/>' +
          '<text x="' + (bx - 8) + '" y="' + (ty + 3.5) + '" text-anchor="end" font-size="10" class="sv-muted">' + n0(cap * f) + '</text>';
      });
    }
    const label = o.label !== false && w.stock > 0 && w.capacity
      ? '<text x="' + (bx + bw / 2) + '" y="' + Math.max(top + 16, yFill - 6) + '" text-anchor="middle" font-size="' + (o.scale ? 15 : 12) +
        '" font-weight="700" class="' + (fillH > bh - 22 ? 'sv-onfill' : 'sv-ink') + '">' + Math.round(pct(w.stock, cap) * 100) + '%</text>'
      : '';
    const aria = w.capacity ? t('k2_aria_bon', { kho: tenChinh(w), ton: n0(w.stock), cap: n0(w.capacity) }) : t('k2_aria_bon_ko', { kho: tenChinh(w), ton: n0(w.stock) });
    return '<svg class="' + (o.cls || '') + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(aria) + '">' +
      '<defs><clipPath id="' + id + 'c"><rect x="' + bx + '" y="' + top + '" width="' + bw + '" height="' + bh + '" rx="' + r + '"/></clipPath>' +
      '<pattern id="' + id + 'h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="6" height="6" class="sv-warn-tint"/><rect width="3" height="6" class="sv-warn"/></pattern>' +
      '<linearGradient id="' + id + 'g" x1="0" x2="1"><stop offset="0" class="sv-stop1"/><stop offset=".55" class="sv-stop2"/><stop offset="1" class="sv-stop1"/></linearGradient></defs>' +
      ticks +
      '<rect x="' + bx + '" y="' + top + '" width="' + bw + '" height="' + bh + '" rx="' + r + '" class="sv-body' + (w.capacity ? '' : ' sv-no-cap') + '" stroke-width="1.5"/>' +
      '<g clip-path="url(#' + id + 'c)">' +
        (wave ? '<path d="' + wave + '" fill="url(#' + id + 'g)"/>' : '') +
        (declH > 0 && fillH > 0 ? '<rect x="' + bx + '" y="' + yFill + '" width="' + bw + '" height="' + Math.min(declH, fillH) + '" fill="url(#' + id + 'h)" opacity=".92"/>' : '') +
      '</g>' +
      (ySafe !== null ? '<line x1="' + (bx + 2) + '" x2="' + (bx + bw - 2) + '" y1="' + ySafe + '" y2="' + ySafe + '" class="sv-safe" stroke-width="1.5" stroke-dasharray="4 3"/>' : '') +
      '<rect x="' + (bx + bw / 2 - 9) + '" y="' + (top - 7) + '" width="18" height="7" rx="2" class="sv-cap"/>' +
      label + '</svg>';
  }

  function miniTank(w) {
    const H = 30, top = 4, cap = thangVe(w), fill = H * pct(w.stock, cap), decl = H * pct(w.declaredQty + w.pendingQty, cap);
    const col = w.status === 'low' ? 'sv-danger' : 'sv-fill';
    return '<svg class="mini-tank" viewBox="0 0 30 38" aria-hidden="true">' +
      '<rect x="6" y="' + top + '" width="18" height="' + H + '" rx="5" class="sv-body' + (w.capacity ? '' : ' sv-no-cap') + '"/>' +
      (fill > 0 ? '<rect x="7" y="' + (top + H - fill) + '" width="16" height="' + fill + '" rx="4" class="' + col + '"/>' : '') +
      (decl > 0 && fill > 0 ? '<rect x="7" y="' + (top + H - fill) + '" width="16" height="' + Math.min(decl, fill) + '" class="sv-warn" opacity=".75"/>' : '') +
      '</svg>';
  }

  /* ================= Danh sách kho (cột trái) ================= */
  function matchesFilter(w) {
    if (st.filter === 'alert') return w.alerts.length > 0 || Object.keys(w.parts).some(k => D.partById[k] && isBelowMin(D.partById[k], partTotal(k)));
    if (st.filter === 'stock') return w.stock > 0;
    if (st.filter === 'empty') return w.status === 'empty';
    return true;
  }
  function matchesQuery(w) {
    const q = st.query.trim().toLowerCase();
    return !q || (w.vi + ' ' + w.lo + ' ' + w.code + ' ' + w.region).toLowerCase().includes(q);
  }
  function whTags(w) {
    let s = '';
    if (w.status === 'empty') s += '<span class="k2-tag k2-tag--empty">' + h('k2_trong') + '</span>';
    if (w.status === 'low') s += '<span class="k2-tag k2-tag--danger">' + h('k2_duoi_an_toan') + '</span>';
    if (w.declaredQty) s += '<span class="k2-tag k2-tag--warn">' + h('k2_da_khai_n', { n: n0(w.declaredQty) }) + '</span>';
    if (w.pendingQty) s += '<span class="k2-tag k2-tag--warn">' + h('k2_cho_cap_n', { n: n0(w.pendingQty) }) + '</span>';
    const pk = Object.keys(w.parts).length;
    if (pk) s += '<span class="k2-tag k2-tag--ok">' + h('k2_n_phu_tung', { n: pk }) + '</span>';
    if (w.cargoTypes.length) s += '<span class="k2-tag k2-tag--ok">' + h('k2_bai_hang') + '</span>';
    if (!w.active) s += '<span class="k2-tag k2-tag--empty">' + h('inactive') + '</span>';
    return s;
  }

  function renderList() {
    const T = D.T;
    let html = '<li><button type="button" class="wh-item wh-all' + (st.view === 'all' ? ' is-active' : '') + '" data-open="all" role="option" aria-selected="' + (st.view === 'all') + '">' +
      '<span class="all-ico"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10 12 4l9 6v10H3zM9 20v-6h6v6"/></svg></span>' +
      '<span><span class="wh-name">' + h('k2_toan_bo') + '</span><span class="wh-meta">' + h('k2_toan_bo_phu', { n: T.whCount }) + '</span></span>' +
      '<span class="wh-qty">' + n0(T.stock) + '<small>' + h('u_l') + '</small></span></button></li>';
    let shown = 0;
    D.regions.forEach(rg => {
      const ds = D.whs.filter(w => w.region === rg && matchesFilter(w) && matchesQuery(w));
      if (!ds.length) return;
      shown += ds.length;
      html += '<li class="wh-group"><div class="wh-group-head"><span>' + esc(rg) + '</span><span>' + n0(sum(ds, 'stock')) + ' ' + h('u_l') + '</span></div><ul class="wh-list">';
      ds.forEach(w => {
        const active = st.view === w.id;
        html += '<li><button type="button" class="wh-item' + (active ? ' is-active' : '') + '" data-open="' + esc(w.id) + '" role="option" aria-selected="' + active + '">' +
          miniTank(w) +
          '<span><span class="wh-name"' + (NN.lang === 'lo' ? ' lang="lo"' : '') + '>' + esc(tenChinh(w)) + '</span>' +
          '<span class="wh-meta">' + (w.code ? '<span class="code">' + esc(w.code) + '</span>' : '') + whTags(w) + '</span></span>' +
          '<span class="wh-qty">' + n0(w.stock) + '<small>' + (w.capacity ? '/ ' + n0(w.capacity) : h('u_l')) + '</small></span></button></li>';
      });
      html += '</ul></li>';
    });
    if (!shown) html += '<li class="k2-empty" style="margin-top:12px">' + h('k2_khong_khop') + '</li>';
    $('#k2-wh').innerHTML = html;
  }

  /* ================= Tìm theo số phiếu / số xe ================= */
  function allDocs() {
    const out = [];
    D.whs.forEach(w => {
      w.declared.forEach(m => out.push({ wh: w.id, tab: 'fuel', doc: m.doc, vehicle: m.vehicle, text: t('k2_da_khai_n', { n: n0(m.qty) }) + ' ' + t('u_l'), date: m.date }));
      w.pending.forEach(m => out.push({ wh: w.id, tab: 'fuel', doc: m.doc + ' ' + m.tripNo, vehicle: m.vehicle, text: t('k2_cho_cap_n', { n: n0(m.qty) }) + ' ' + t('u_l'), date: m.date }));
    });
    const kp = D.goc ? D.goc.id : 'all';
    D.parts.forEach(p => {
      p.pending.forEach(m => out.push({ wh: kp, tab: 'parts', doc: m.doc, vehicle: m.vehicle, text: p.ten + ' · ' + t('k2_pt_cho_ngan') + ' ' + n2(m.qty), date: m.date }));
    });
    D.cargo.forEach(c => {
      c.lots.forEach(l => out.push({ wh: c.yard, tab: 'cargo', doc: l.doc, vehicle: l.vehicle, text: c.ten + ' · ' + t('k2_lo_con', { t: n2(l.left) }), date: l.date }));
    });
    return out.filter(d => d.doc || d.vehicle);
  }
  let DOCS = [];

  function renderSearchResults() {
    const q = st.query.trim().toLowerCase(), box = $('#k2-sr');
    if (q.length < 2) { box.hidden = true; return; }
    const hits = DOCS.filter(d => ((d.doc || '') + ' ' + (d.vehicle ? t('k2_xe_x', { xe: d.vehicle }) : '')).toLowerCase().includes(q)).slice(0, 8);
    const partHits = D.parts.filter(p => (p.ten || '').toLowerCase().includes(q));
    const cargoHits = D.cargo.filter(c => (c.ten || '').toLowerCase().includes(q));
    if (!hits.length && !partHits.length && !cargoHits.length) { box.hidden = true; return; }
    let html = '';
    const ten = (id) => D.byId[id] ? tenChinh(D.byId[id]) : '';
    if (hits.length) {
      html += '<h3>' + h('k2_sr_phieu') + '</h3>' + hits.map(d => '<button type="button" class="sr-item" data-open="' + esc(d.wh) + '" data-tab="' + d.tab + '" data-doc="' + esc(d.doc) + '">' +
        '<span class="code">' + esc(d.doc || '—') + '</span><span>' + esc(d.text) + (d.vehicle ? ', ' + esc(t('k2_xe_x', { xe: d.vehicle })) : '') + '</span>' +
        '<small>' + esc(ten(d.wh)) + (d.date ? ', ' + esc(ngay(d.date)) : '') + '</small></button>').join('');
    }
    if (partHits.length) {
      html += '<h3>' + h('part') + '</h3>' + partHits.map(p => '<button type="button" class="sr-item" data-open="' + esc(D.goc ? D.goc.id : 'all') + '" data-tab="parts">' +
        '<span class="code">' + esc(donVi(p.unit)) + '</span><span' + ' lang="lo">' + esc(p.ten) + '</span><small>' + esc(t('k2_sr_pt', { sl: n2(p.stock), dv: donVi(p.unit) })) + '</small></button>').join('');
    }
    if (cargoHits.length) {
      html += '<h3>' + h('k2_hang_gui_bai') + '</h3>' + cargoHits.map(c => '<button type="button" class="sr-item" data-open="' + esc(c.yard) + '" data-tab="cargo">' +
        '<span class="code">' + esc(t('ton')) + '</span><span lang="lo">' + esc(c.ten) + '</span><small>' + esc(t('k2_sr_bai', { kho: ten(c.yard) })) + '</small></button>').join('');
    }
    box.innerHTML = html; box.hidden = false;
  }

  /* ================= Toàn bộ kho ================= */
  function renderAll() {
    const T = D.T;
    const sentence = h('k2_cau_ton', { l: n0(T.stock), co: T.whCount - T.empty.length, n: T.whCount }) + ' ' +
      (T.declared ? h('k2_cau_khai', { l: n0(T.declared) }) + ' ' : '') +
      (T.pending ? h('k2_cau_cho', { l: n0(T.pending), n: T.pendingDocs }) + ' ' : h('k2_cau_khong_cho') + ' ') +
      (T.empty.length ? h('k2_cau_trong', { n: T.empty.length }) : '');

    const tanks = D.regions.map(rg => D.whs.filter(w => w.region === rg).map(w =>
      '<button type="button" class="tank-card' + (w.status === 'empty' ? ' is-empty' : '') + '" data-open="' + esc(w.id) + '">' +
        tankSvg(w) +
        '<span class="t-name"' + (NN.lang === 'lo' ? ' lang="lo"' : '') + '>' + esc(tenNgan(w)) + '</span>' +
        '<span class="t-qty"><b>' + n0(w.stock) + '</b>' + (w.capacity ? ' / ' + n0(w.capacity) : '') + ' L</span>' +
        (w.status === 'low' ? '<span class="k2-tag k2-tag--danger">' + h('k2_duoi_muc') + '</span>'
          : w.declaredQty ? '<span class="k2-tag k2-tag--warn">' + h('k2_da_khai_n', { n: n0(w.declaredQty) }) + '</span>'
          : !w.capacity ? '<span class="k2-tag k2-tag--empty">' + h('k2_chua_suc_chua') + '</span>' : '') +
      '</button>').join('')).join('');

    // Ma trận phụ tùng × kho
    const partWh = D.whs.filter(w => Object.keys(w.parts).length > 0);
    const mHead = '<tr><th>' + h('part') + '</th><th>' + h('unit') + '</th>' + partWh.map(w => '<th class="num">' + esc(tenNgan(w)) + '</th>').join('') +
      '<th class="num">' + h('k2_tong') + '</th><th class="num">' + h('min_stock') + '</th>' + (D.g ? '<th class="num">' + h('fuel_avg') + '</th>' : '') + '</tr>';
    const mBody = D.parts.map(p => {
      const tot = partTotal(p.code), low = isBelowMin(p, tot);
      return '<tr class="is-clickable" data-open="' + esc(partWh[0] ? partWh[0].id : 'all') + '" data-tab="parts"><td><b lang="lo">' + esc(p.ten) + '</b>' + (p.active ? '' : '<span class="k2-sub">' + h('inactive') + '</span>') + '</td><td>' + esc(donVi(p.unit)) + '</td>' +
        partWh.map(w => { const q = w.parts[p.code] || 0; return '<td class="cell ' + (q ? (low ? 'cell-low' : 'cell-ok') : 'cell-none') + '"><span>' + (q ? n2(q) : '–') + '</span></td>'; }).join('') +
        '<td class="num"><b class="' + (low ? 'below' : '') + '">' + n2(tot) + '</b>' + (low ? '<span class="k2-sub below">' + h('k2_duoi_muc') + '</span>' : '') + '</td>' +
        '<td class="num">' + (p.min ? n2(p.min) : '<span class="dash">–</span>') + '</td>' + (D.g ? '<td class="num">' + lak(p.cost) + '</td>' : '') + '</tr>';
    }).join('') || '<tr><td colspan="9"><div class="k2-empty">' + h('no_data') + '</div></td></tr>';

    // Hàng khách gửi ở bãi
    const cargoRows = D.cargo.map(c => c.lots.map(l => {
      const leftP = pct(l.left, l.inQty) * 100;
      return '<tr class="is-clickable" data-open="' + esc(c.yard) + '" data-tab="cargo" data-doc="' + esc(l.doc) + '"><td><span class="code">' + esc(l.doc) + '</span><span class="k2-sub">' + esc(t('k2_xe_x', { xe: l.vehicle || '—' })) + '</span></td>' +
        '<td lang="lo">' + esc(c.ten) + '</td><td lang="lo">' + esc(l.customer) + '</td>' +
        '<td>' + esc(D.byId[c.yard] ? tenNgan(D.byId[c.yard]) : '') + '</td>' +
        '<td style="min-width:150px"><div class="lot-bar" title="' + esc(t('k2_lo_thanh', { con: n2(l.left), nhap: n2(l.inQty) })) + '"><span class="left" style="width:' + leftP + '%"></span><span class="gone" style="width:' + (100 - leftP) + '%"></span></div></td>' +
        '<td class="num"><b>' + n2(l.left) + '</b><span class="k2-sub">/ ' + n2(l.inQty) + '</span></td><td>' + esc(ngay(l.date)) + '</td></tr>';
    }).join('')).join('') || '<tr><td colspan="7"><div class="k2-empty">' + h('no_data') + '</div></td></tr>';

    // Cần xử lý
    const todos = [];
    D.whs.forEach(w => {
      if (w.status === 'low') todos.push({ lvl: 'danger', wh: w.id, tab: 'fuel', title: t('k2_td_con_lai', { kho: tenChinh(w), l: n0(w.remain) }), sub: t('k2_td_thap', { l: n0(w.safety) }) });
      if (w.declaredQty) todos.push({ lvl: 'warn', wh: w.id, tab: 'fuel', title: t('k2_td_khai', { l: n0(w.declaredQty) }), sub: t('k2_td_khai_s', { kho: tenChinh(w), n: w.declared.length }) });
      if (w.pendingQty) todos.push({ lvl: 'warn', wh: w.id, tab: 'fuel', title: t('k2_td_cho', { l: n0(w.pendingQty) }), sub: t('k2_td_khai_s2', { kho: tenChinh(w), n: w.pending.length }) });
    });
    T.partsLow.forEach(p => {
      todos.push({ lvl: 'danger', wh: D.goc ? D.goc.id : 'all', tab: 'parts', title: t('k2_td_pt', { ten: p.ten, sl: n2(partTotal(p.code)), dv: donVi(p.unit) }), sub: t('k2_td_pt_s', { min: n2(p.min) }) });
    });
    if (T.empty.length) todos.push({ lvl: 'muted', wh: T.empty[0].id, tab: 'fuel', title: t('k2_td_trong', { n: T.empty.length }), sub: T.empty.map(tenNgan).join(', ') });

    const ovTabs = [
      { id: 'fuel', label: h('e_fuel'), count: t('k2_n_kho', { n: T.whCount }) },
      { id: 'parts', label: h('part'), count: t('k2_n_mon', { n: D.parts.length }) },
      { id: 'cargo', label: h('k2_hang_gui_bai'), count: t('k2_n_lo', { n: T.cargoLots }) },
    ];
    let ovBody;
    if (st.ovTab === 'parts') {
      ovBody = '<div class="k2-panel-body"><p class="tab-intro">' + h('k2_intro_pt') + '</p>' +
        '<div class="k2-tbl-wrap"><table class="k2-tbl matrix"><thead>' + mHead + '</thead><tbody>' + mBody + '</tbody></table></div></div>';
    } else if (st.ovTab === 'cargo') {
      ovBody = '<div class="k2-panel-body"><p class="tab-intro">' + h('k2_intro_hang', { t: n2(T.cargoTons), n: T.cargoLots }) + '</p>' +
        '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('doc_no') + '</th><th>' + h('goods_type') + '</th><th>' + h('c_customer') + '</th><th>' + h('k2_bai') + '</th>' +
        '<th>' + h('k2_con_nhap') + '</th><th class="num">' + h('kx_con_t') + '</th><th>' + h('k2_ngay_nhap_c') + '</th></tr></thead><tbody>' + cargoRows + '</tbody></table></div></div>';
    } else {
      ovBody = '<div class="k2-panel-body"><div class="tab-intro-row"><p class="summary-line">' + sentence + '</p>' +
        '<div class="legend"><span><i class="lg-fill"></i>' + h('k2_lg_ton') + '</span><span><i class="lg-decl"></i>' + h('k2_lg_khai') + '</span><span><i class="lg-safe"></i>' + h('k2_lg_an_toan') + '</span></div></div>' +
        '<div class="tank-wall">' + (tanks || '<div class="k2-empty">' + h('no_data') + '</div>') + '</div></div>';
    }
    $('#k2-work').innerHTML =
      '<section class="k2-panel ov-todo"><div class="ov-todo-head"><h2>' + h('attention') + '</h2><p>' + h('k2_n_viec', { n: todos.length }) + '</p></div>' +
        (todos.length ? '<ul class="todo">' + todos.map(x => '<li><button type="button" data-open="' + esc(x.wh) + '" data-tab="' + x.tab + '"><span class="dot dot--' + x.lvl + '"></span>' +
          '<span><strong>' + esc(x.title) + '</strong><small>' + esc(x.sub) + '</small></span>' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" class="sv-chev" stroke-width="1.8" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg></button></li>').join('') + '</ul>'
          : '<div class="k2-empty" style="margin:10px 0 12px">' + h('k2_td_khong') + '</div>') + '</section>' +
      '<section class="k2-panel ov-main"><div class="tabs" role="tablist">' + ovTabs.map(x =>
        '<button type="button" class="tab" role="tab" data-ovtab="' + x.id + '" aria-selected="' + (st.ovTab === x.id) + '">' + x.label + ' <span class="count">' + esc(x.count) + '</span></button>').join('') +
      '</div><div role="tabpanel">' + ovBody + '</div></section>';
  }

  /* ================= Chi tiết một kho ================= */
  const flashCls = (doc) => st.flashDoc && doc && String(st.flashDoc).includes(doc) ? ' is-flash' : '';

  function fuelTab(w) {
    const pend = w.pending.length
      ? '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('c_date') + '</th><th>' + h('kx_v_no') + '</th><th>' + h('nav_dispatch') + '</th><th>' + h('c_truck') + '</th><th>' + h('c_driver') + '</th><th class="num">' + h('k2_so_lit') + '</th></tr></thead><tbody>' +
        w.pending.map(p => '<tr class="' + flashCls(p.doc + ' ' + p.tripNo) + '"><td>' + esc(ngay(p.date)) + '</td><td class="code">' + esc(p.doc) + '</td><td>' + moPhieu(p.trip, p.tripNo) +
          (p.ban ? '<span class="k2-sub">' + h('ht_xuat_xuat_ban') + '</span>' : '') + '</td><td>' + esc(p.vehicle || '—') + '</td><td lang="lo">' + esc(p.driver || '—') + '</td><td class="num">' + n0(p.qty) + '</td></tr>').join('') +
        '</tbody><tfoot><tr><td colspan="5">' + h('k2_cong') + '</td><td class="num">' + n0(w.pendingQty) + '</td></tr></tfoot></table></div>'
      : '<div class="k2-empty">' + h('k2_pend_trong') + '</div>';
    const decl = w.declared.length
      ? '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('c_date') + '</th><th>' + h('nav_dispatch') + '</th><th>' + h('c_truck') + '</th><th>' + h('c_route') + '</th><th class="num">' + h('k2_so_lit') + '</th></tr></thead><tbody>' +
        w.declared.map(p => '<tr class="' + flashCls(p.doc) + '"><td>' + esc(ngay(p.date)) + '</td><td>' + moPhieu(p.trip, p.doc) + '</td><td>' + esc(p.vehicle || '—') + '</td><td lang="lo">' + esc(p.route || '—') + '</td><td class="num warn-txt">' + n0(p.qty) + '</td></tr>').join('') +
        '</tbody><tfoot><tr><td colspan="4">' + h('k2_cong') + '</td><td class="num">' + n0(w.declaredQty) + '</td></tr></tfoot></table></div>'
      : '<div class="k2-empty">' + h('k2_decl_trong') + '</div>';
    return '<div class="block"><h3>' + h('td_await_iss') + ' <span class="count">' + w.pending.length + '</span></h3>' + pend + '</div>' +
      '<div class="block"><h3>' + h('k2_decl_h') + ' <span class="count">' + w.declared.length + '</span></h3>' + decl + '</div>' +
      '<p class="tab-intro">' + h('k2_so_o_ben_kho') + '</p>';
  }

  function partsTab(w) {
    const codes = Object.keys(w.parts);
    const pend = D.parts.flatMap(p => p.pending.map(x => Object.assign({ p }, x)));
    if (!codes.length && !(w.goc && pend.length)) {
      const co = D.whs.filter(x => Object.keys(x.parts).length);
      return '<div class="k2-empty">' + (co.length ? h('k2_pt_khong', { ds: '' }) + co.map(x => '<button type="button" class="link" data-open="' + esc(x.id) + '" data-tab="parts">' + esc(tenChinh(x)) + '</button>').join(', ') + '.'
        : h('k2_pt_khong_dau')) + '</div>';
    }
    const rows = codes.map(k => {
      const p = D.partById[k], q = w.parts[k], tot = partTotal(k), low = isBelowMin(p, tot);
      const scale = Math.max(tot, p.min * 2, 1);
      return '<tr><td><b lang="lo">' + esc(p.ten) + '</b></td><td>' + esc(donVi(p.unit)) + '</td>' +
        '<td class="num"><b>' + n2(q) + '</b></td>' +
        '<td style="min-width:170px"><div class="k2-bar" title="' + esc(t('k2_bar', { tot: n2(tot), min: n2(p.min) })) + '"><i class="' + (low ? 'is-low' : '') + '" style="width:' + (pct(tot, scale) * 100) + '%"></i>' +
        (p.min ? '<span class="min-mark" style="left:' + (pct(p.min, scale) * 100) + '%"></span>' : '') + '</div>' +
        '<span class="k2-sub ' + (low ? 'below' : '') + '">' + h(low ? 'k2_bar_duoi' : 'k2_bar', { tot: n2(tot), min: p.min ? n2(p.min) : '–' }) + '</span></td>' +
        (D.g ? '<td class="num">' + lak(p.cost) + '</td><td class="num">' + dash((p.cost || 0) * q) + '</td>' : '') + '</tr>';
    }).join('');
    const value = sum(codes, k => (w.parts[k] || 0) * (D.partById[k].cost || 0));
    const pendRows = pend.map(x => '<tr class="' + flashCls(x.doc) + '"><td>' + esc(ngay(x.date)) + '</td><td lang="lo">' + esc(x.p.ten) + '</td><td>' + moPhieu(x.trip, x.doc) + '</td><td>' + esc(x.vehicle || '—') + '</td><td class="num">' + n2(x.qty) + '</td></tr>').join('');
    return '<div class="block"><h3>' + h('k2_pt_h') + ' <span class="count">' + codes.length + '</span></h3>' +
      (codes.length ? '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('part') + '</th><th>' + h('unit') + '</th><th class="num">' + h('k2_ton_tai_kho') + '</th><th>' + h('k2_so_toi_thieu') + '</th>' +
        (D.g ? '<th class="num">' + h('fuel_avg') + '</th><th class="num">' + h('k2_gia_tri') + '</th>' : '') + '</tr></thead><tbody>' +
        rows + '</tbody>' + (D.g ? '<tfoot><tr><td colspan="5">' + h('k2_gia_tri_kho') + '</td><td class="num">' + n0(value) + '</td></tr></tfoot>' : '') + '</table></div>' : '<div class="k2-empty">' + h('no_data') + '</div>') + '</div>' +
      '<div class="block"><h3>' + h('k2_pt_cho_h') + ' <span class="count">' + pend.length + '</span></h3>' +
      (pendRows ? '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('c_date') + '</th><th>' + h('part') + '</th><th>' + h('nav_dispatch') + '</th><th>' + h('c_truck') + '</th><th class="num">' + h('kx_sl') + '</th></tr></thead><tbody>' + pendRows + '</tbody></table></div>'
        : '<div class="k2-empty">' + h('k2_pt_cho_trong') + '</div>') + '</div>' +
      '<p class="tab-intro">' + h('k2_so_o_ben_kho') + '</p>';
  }

  function cargoTab(w) {
    if (!w.cargoTypes.length) return '<div class="k2-empty">' + h('k2_hang_khong') + '</div>';
    return w.cargoTypes.map(c => {
      const lots = c.lots.map(l => {
        const p = pct(l.left, l.inQty) * 100;
        return '<tr class="' + flashCls(l.doc) + '"><td><span class="code">' + esc(l.doc) + '</span><span class="k2-sub">' + esc(t('k2_xe_x', { xe: l.vehicle || '—' })) + '</span></td><td lang="lo">' + esc(l.customer) + '</td><td lang="lo">' + esc(l.origin) + '</td>' +
          '<td style="min-width:150px"><div class="lot-bar"><span class="left" style="width:' + p + '%"></span><span class="gone" style="width:' + (100 - p) + '%"></span></div></td>' +
          '<td class="num">' + n2(l.inQty) + '</td><td class="num"><b>' + n2(l.left) + '</b></td><td>' + esc(ngay(l.date)) + '</td></tr>';
      }).join('');
      return '<div class="block"><h3 lang="lo">' + esc(c.ten) + '</h3>' +
        '<div class="fuel-stats k2-tom">' +
        '<div class="is-main"><span>' + h('k2_con_o_bai') + '</span><b>' + n2(c.left) + ' <small>' + h('ton') + '</small></b></div>' +
        '<div><span>' + h('kx_lo_con') + '</span><b>' + esc(t('k2_n_lo', { n: c.lots.length })) + '</b></div></div>' +
        '<h3>' + h('kx_lo_con') + ' <span class="count">' + c.lots.length + '</span></h3>' +
        (lots ? '<div class="k2-tbl-wrap"><table class="k2-tbl"><thead><tr><th>' + h('doc_no') + '</th><th>' + h('c_customer') + '</th><th>' + h('kx_origin') + '</th><th>' + h('k2_con_nhap') + '</th><th class="num">' + h('kx_nhap_t') + '</th><th class="num">' + h('kx_con_t') + '</th><th>' + h('c_date') + '</th></tr></thead><tbody>' + lots + '</tbody></table></div>'
          : '<div class="k2-empty">' + h('no_data') + '</div>') + '</div>' +
        '<p class="tab-intro">' + h('k2_so_o_ben_kho') + '</p>';
    }).join('');
  }

  function renderWarehouse(w) {
    const pk = Object.keys(w.parts).length, cl = sum(w.cargoTypes, c => c.lots.length);
    const tabs = [
      { id: 'fuel', label: h('e_fuel'), count: w.declared.length + w.pending.length },
      { id: 'parts', label: h('part'), count: pk },
      { id: 'cargo', label: h('k2_hang_gui_bai'), count: cl },
    ];
    if (!tabs.some(x => x.id === st.tab)) st.tab = 'fuel';
    const body = st.tab === 'parts' ? partsTab(w) : st.tab === 'cargo' ? cargoTab(w) : fuelTab(w);
    const remainCls = w.safety && w.remain < w.safety && w.stock > 0 ? 'is-danger' : '';
    const phu = tenPhu(w);
    const conCap = w.stock <= 0 ? h('k2_kho_trong') : !w.safety ? h('k2_chua_an_toan')
      : w.remain < w.safety ? h('k2_thap_hon', { l: n0(w.safety) }) : h('k2_tren_muc', { l: n0(w.remain - w.safety) });
    $('#k2-work').innerHTML =
      '<section class="k2-panel">' +
        '<div class="wh-head"><div>' +
          '<h2' + (NN.lang === 'lo' ? ' lang="lo"' : '') + '>' + esc(tenChinh(w)) + '</h2>' +
          (phu || w.country ? '<p class="lo-name"' + (NN.lang === 'lo' ? '' : ' lang="lo"') + '>' + esc(phu) + (w.country ? ' <span class="k2-tag k2-tag--la">' + esc(w.country) + '</span>' : '') + '</p>' : '') +
          '<div class="facts">' +
            '<span>' + h('k2_ma_kho') + '<b class="code" style="font-size:14px">' + esc(w.code || '—') + '</b></span>' +
            '<span>' + h('k2_khu_vuc') + '<b>' + esc(w.region) + '</b></span>' +
            '<span>' + h('k2_suc_chua') + '<b>' + (w.capacity ? n0(w.capacity) + ' ' + h('u_l') : h('k2_chua_khai')) + '</b></span>' +
            '<span>' + h('k2_muc_an_toan') + '<b>' + (w.safety ? n0(w.safety) + ' ' + h('u_l') : h('k2_chua_khai')) + '</b></span>' +
            (D.g ? '<span>' + h('fuel_avg') + '<b>' + (w.avgCost ? n0(w.avgCost) + ' LAK/' + h('u_l') : '–') + '</b></span>' : '') +
            '<span>' + h('k2_nhap_gan_nhat') + '<b>' + (w.lastIn ? esc(ngay(w.lastIn)) : '–') + '</b></span>' +
          '</div></div>' +
          '<div class="wh-head-tools"><button type="button" class="k2-btn k2-btn--ghost" data-open="all">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 6-6 6 6 6"/></svg>' + h('k2_toan_bo') + '</button></div>' +
        '</div>' +
        '<div class="fuel-hero"><div class="k2-bon-lon">' + tankSvg(w, { width: 190, height: 250, scale: true, cls: 'big-tank' }) +
          (w.capacity ? '' : '<span class="k2-sub">' + h('k2_chua_suc_chua_goi_y') + '</span>') + '</div>' +
          '<div class="fuel-stats">' +
            '<div><span>' + h('k2_ton_hien') + '</span><b>' + n0(w.stock) + ' <small>' + h('u_l') + '</small></b><p>' +
              (w.capacity ? h('k2_ton_hien_p', { p: Math.round(pct(w.stock, w.capacity) * 100) }) : h('k2_ton_ben_kho')) + '</p></div>' +
            '<div class="' + (w.pendingQty ? 'is-warn' : '') + '"><span>' + h('kx_c_cho') + '</span><b>' + n0(w.pendingQty) + ' <small>' + h('u_l') + '</small></b><p>' + h('k2_n_phieu_dn', { n: w.pending.length }) + '</p></div>' +
            '<div class="' + (w.declaredQty ? 'is-warn' : '') + '"><span>' + h('k2_khai_chua') + '</span><b>' + n0(w.declaredQty) + ' <small>' + h('u_l') + '</small></b><p>' + h('k2_n_pxx', { n: w.declared.length }) + '</p></div>' +
            '<div class="is-main ' + remainCls + '"><span>' + h('k2_con_cap') + '</span><b>' + n0(w.remain) + ' <small>' + h('u_l') + '</small></b><p>' + conCap + '</p></div>' +
          '</div></div>' +
      '</section>' +
      '<section class="k2-panel">' +
        '<div class="tabs" role="tablist">' + tabs.map(x =>
          '<button type="button" class="tab" role="tab" data-tab-go="' + x.id + '" aria-selected="' + (st.tab === x.id) + '">' + x.label + ' <span class="count">' + x.count + '</span></button>').join('') + '</div>' +
        '<div class="tab-panel" role="tabpanel">' + body + '</div>' +
      '</section>';
  }

  /* ================= Vẽ ================= */
  function render() {
    if (!root) return;
    if (!D) {
      $('#k2-wh').innerHTML = '';
      $('#k2-sr').hidden = true;
      $('#k2-work').innerHTML = '<section class="k2-panel"><div class="k2-panel-body"><div class="k2-empty">' + (loi ? h('kx_loi', { loi }) : h('loading')) + '</div></div></section>';
      $('#k2-phu').innerHTML = '';
      return;
    }
    renderList();
    renderSearchResults();
    const w = D.byId[st.view];
    if (w) {
      renderWarehouse(w);
      $('#k2-phu').innerHTML = h('k2_sub_kho', { kho: tenChinh(w) });
    } else {
      st.view = 'all';
      renderAll();
      $('#k2-phu').innerHTML = h('k2_sub_all');
    }
    const flash = root.querySelector('.is-flash');
    if (flash) flash.scrollIntoView({ block: 'center', behavior: 'smooth' });
    st.flashDoc = null;
    ghiDiaChi();
  }
  /** Kho và tab đang xem ghi vào địa chỉ (rà 01/10): bấm số phiếu sang Phiếu xuất xe rồi Quay lại, hay tải lại trang, là về đúng
   *  kho · tab đó — trước đây về "Toàn bộ kho". init đã đọc sẵn ?kho=&tab=. replaceState: không thêm bước lịch sử, không bắn
   *  hashchange. */
  function ghiDiaChi() {
    if (!root || !root.isConnected || !D) return;
    const tab = st.view === 'all' ? st.ovTab : st.tab, ts = new URLSearchParams();
    if (st.view !== 'all') ts.set('kho', st.view);
    if (tab && tab !== 'fuel') ts.set('tab', tab);
    const moi = '#/kho-xem' + (String(ts) ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }

  function open(view, tab, doc) {
    // "một màn": cột phải tự cuộn — sang kho khác thì về đầu cột (đổi tab trong cùng kho thì giữ chỗ đang xem)
    if ((view || 'all') !== st.view) { const wk = $('#k2-work'); if (wk) wk.scrollTop = 0; }
    st.view = view || 'all';
    if (tab) st.tab = tab;
    st.flashDoc = doc || null;
    render();
    if (window.innerWidth <= 1180) $('#k2-work').scrollIntoView({ block: 'start' });
  }

  /* Chiều cao "một màn" (CSS: rộng > 1180, cao ≥ 640): màn cao đúng phần còn lại của khung nhìn — trang không cuộn,
   * danh sách kho và cột phải tự cuộn. Trước đây trang cuộn với cột trái "dính" top: 84px: menu top (hai thanh, ~94px)
   * che mất ô tìm và nút lọc, cuộn tới đáy thì cột trái bị đẩy lên dưới thanh đầu. Phần đầu trang chung cao khác nhau theo
   * kiểu menu và theo chữ nên ĐO chỗ màn bắt đầu (lúc nạp có dải "Đang tải…" ở trên — init xong thì đo lại).
   * getBoundingClientRect là px thật, đổi ra px của khung đã zoom (chia --ty-le); lề dưới của trang thì đã là px khung. */
  let daGanDo = false;
  function doCao() {
    const k2 = root && root.isConnected ? root.querySelector('.k2') : null;
    if (!k2) return;
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const trang = document.getElementById('noi-dung');
    const duoi = trang ? parseFloat(getComputedStyle(trang).paddingBottom) || 0 : 0;
    k2.style.setProperty('--k2-tru', Math.ceil((k2.getBoundingClientRect().top + window.scrollY) / tl + duoi) + 'px');
  }
  function ganDoCao() {
    if (daGanDo) return; daGanDo = true;
    let cho = 0;
    const lai = () => { clearTimeout(cho); cho = setTimeout(doCao, 90); };
    window.addEventListener('resize', lai);
    // đổi kiểu menu top ⇄ side (EPL.datKieuXem) hay tiêu đề xuống dòng không báo cho module — thanh đầu đổi cỡ thì đo lại
    if (window.ResizeObserver) { const qs = new ResizeObserver(lai); ['tbar', 'topbar'].forEach(id => { const e = document.getElementById(id); if (e) qs.observe(e); }); }
  }

  async function tai() {
    loi = '';
    try {
      R = await API.get('/api/kho-xem');
      D = chuanHoa(R);
      DOCS = allDocs();
      // tham số kho theo mã (KHO-TB) thay vì id: đổi TRƯỚC khi vẽ — render() gặp mã lạ là về "Toàn bộ kho" ngay, nên đổi sau
      // (như trước 01/10, ở cuối init) thì không bao giờ tới được kho đó
      if (st.view !== 'all' && !D.byId[st.view] && D.byCode[st.view]) st.view = D.byCode[st.view].id;
    } catch (e) { R = null; D = null; loi = e.message || String(e); }
    render();
  }

  /* ================= Sự kiện ================= */
  function onClick(e) {
    const mp = e.target.closest('[data-mo-phieu]');
    if (mp) { EPL.di('phieu-xuat-xe', { id: mp.dataset.moPhieu }); return; }
    const o = e.target.closest('[data-open]');
    if (o) { open(o.getAttribute('data-open'), o.getAttribute('data-tab'), o.getAttribute('data-doc')); return; }
    const ov = e.target.closest('[data-ovtab]');
    if (ov) { st.ovTab = ov.getAttribute('data-ovtab'); renderAll(); ghiDiaChi(); const b = root.querySelector('[data-ovtab="' + st.ovTab + '"]'); if (b) b.focus(); return; }
    const tb = e.target.closest('[data-tab-go]');
    if (tb) { st.tab = tb.getAttribute('data-tab-go'); open(st.view, st.tab); const b = root.querySelector('[data-tab-go="' + st.tab + '"]'); if (b) b.focus(); return; }
    const c = e.target.closest('#k2-loc [data-filter]');
    if (c) {
      st.filter = c.getAttribute('data-filter');
      $$('#k2-loc .chip').forEach(x => x.classList.toggle('is-on', x === c));
      renderList();
    }
  }
  function onKey(e) {
    if (e.key === 'Escape' && e.target === $('#k2-tim')) { e.target.value = ''; st.query = ''; renderList(); renderSearchResults(); }
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && e.target.closest && e.target.closest('#k2-wh')) {
      const it = $$('#k2-wh .wh-item'), i = it.indexOf(e.target.closest('.wh-item'));
      const nx = it[i + (e.key === 'ArrowDown' ? 1 : -1)];
      if (nx) { e.preventDefault(); nx.focus(); }
    }
    if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && e.target.getAttribute && e.target.getAttribute('role') === 'tab') {
      const ts = $$('[role="tab"]'), j = ts.indexOf(e.target), nt = ts[(j + (e.key === 'ArrowRight' ? 1 : ts.length - 1)) % ts.length];
      if (nt) nt.click();
    }
  }
  // phím "/" nhảy vào ô tìm — gắn một lần cho cả trang, chỉ chạy khi màn này đang mở
  let daGanPhim = false;
  function ganPhim() {
    if (daGanPhim) return;
    daGanPhim = true;
    document.addEventListener('keydown', (e) => {
      if (!root || !root.isConnected || e.key !== '/') return;
      const a = document.activeElement;
      if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.tagName === 'SELECT' || a.isContentEditable)) return;
      const o = root.querySelector('#k2-tim'); if (o) { e.preventDefault(); o.focus(); }
    });
  }

  EPL.modules['kho-xem'] = {
    async init(r, { tham } = {}) {
      root = r; R = null; D = null; loi = ''; st.query = ''; st.filter = 'all'; st.view = 'all'; st.tab = 'fuel'; st.ovTab = 'fuel';
      if (tham) {
        const tabCu = { dau: 'fuel', pt: 'parts', hang: 'cargo' };
        if (tham.tab) { st.tab = tabCu[tham.tab] || tham.tab; st.ovTab = st.tab; }
        if (tham.kho) st.view = tham.kho;
      }
      $('#k2-tim').addEventListener('input', (e) => { st.query = e.target.value; if (D) { renderList(); renderSearchResults(); } });
      root.addEventListener('click', onClick);
      root.addEventListener('keydown', onKey);
      ganPhim(); ganDoCao();
      render(); doCao();
      await tai();
      setTimeout(doCao, 0);                    // sau khi khung bỏ dải "Đang tải…" (chạy ngay khi init trả về)
    },
    onLang() {
      if (!root) return;
      if (R) { D = chuanHoa(R); DOCS = allDocs(); }
      render(); doCao();
    },
    xuatExcel() {
      if (!D) return [];
      const w = D.byId[st.view], S = [], g = D.g;
      const cotKho = [t('k2_ma_kho'), t('fuel_kho'), t('k2_khu_vuc'), t('k2_suc_chua') + ' (L)', t('k2_ton_hien') + ' (L)', t('kx_c_cho') + ' (L)',
        t('k2_khai_chua') + ' (L)', t('k2_con_cap') + ' (L)', t('k2_muc_an_toan') + ' (L)'].concat(g ? [t('fuel_avg')] : []);
      const dongKho = (x) => [x.code, tenChinh(x), x.region, x.capacity ? EPL.oSo(x.capacity, 0, 'L') : '', EPL.oSo(x.stock, 0, 'L'), EPL.oSo(x.pendingQty, 0, 'L'),
        EPL.oSo(x.declaredQty, 0, 'L'), EPL.oSo(x.remain, 0, 'L'), x.safety ? EPL.oSo(x.safety, 0, 'L') : ''].concat(g ? [x.avgCost ? EPL.oSo(x.avgCost, 0, 'LAK') : ''] : []);
      if (!w) {
        S.push(EPL.xuatSheet(t('e_fuel'), cotKho, D.whs.map(dongKho)));
        S.push(EPL.xuatSheet(t('part'), [t('part'), t('unit'), t('stock'), t('min_stock')].concat(g ? [t('fuel_avg')] : []),
          D.parts.map(p => [p.ten, donVi(p.unit), EPL.oSo(p.stock, 2), EPL.oSo(p.min, 2)].concat(g ? [p.cost ? EPL.oSo(p.cost, 0, 'LAK') : ''] : []))));
        S.push(EPL.xuatSheet(t('k2_hang_gui_bai'), [t('goods_type'), t('doc_no'), t('c_customer'), t('kx_origin'), t('kx_nhap_t'), t('kx_con_t'), t('c_date')],
          D.cargo.flatMap(c => c.lots.map(l => [c.ten, l.doc, l.customer, l.origin, EPL.oSo(l.inQty, 3), EPL.oSo(l.left, 3), EPL.oNgay(l.date)]))));
        return S;
      }
      S.push(EPL.xuatSheet(t('e_fuel') + ' ' + (w.code || ''), cotKho, [dongKho(w)]));
      S.push(EPL.xuatSheet(t('td_await_iss'), [t('c_date'), t('kx_v_no'), t('nav_dispatch'), t('c_truck'), t('c_driver'), t('k2_so_lit')],
        w.pending.map(p => [EPL.oNgay(p.date), p.doc, p.tripNo, p.vehicle, p.driver, EPL.oSo(p.qty, 0, 'L')])));
      S.push(EPL.xuatSheet(t('k2_decl_h'), [t('c_date'), t('nav_dispatch'), t('c_truck'), t('c_route'), t('k2_so_lit')],
        w.declared.map(p => [EPL.oNgay(p.date), p.doc, p.vehicle, p.route, EPL.oSo(p.qty, 0, 'L')])));
      return S;
    },
  };
})();
