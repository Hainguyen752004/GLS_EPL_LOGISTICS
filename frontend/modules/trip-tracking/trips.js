/* Theo dõi chuyến – EPL · HTML/CSS/JS thuần
   Cấu hình qua window.TRIPS_CONFIG (trips, onEvent, onCost, openTicketUrl, today, storageKey) */
(function () {
  "use strict";

  /* ============ Cấu hình ============ */
  const CONFIG = Object.assign({
    trips: null,
    onEvent: null,
    onCost: null,
    openTicketUrl: null,
    today: "2026-09-17",
    storageKey: "epl_trips_v1",
    lateDays: 25,
  }, window.TRIPS_CONFIG || {});

  const TODAY = CONFIG.today ? new Date(CONFIG.today + "T00:00:00") : new Date();

  /* ============ Dữ liệu mẫu ============ */
  const SAMPLE = [
    {
      id: "t432", code: "T4-0432-08/EPL", vehicle: "342", plate: "ບອ 3311", driver: "ທ້າວ ບຸນມີ", customer: "ຖໍ່ເຫຼືອ",
      cargo: "Quặng sắt", weightIn: 41.9, weightOut: null, depart: "2026-08-23", status: "running", fuelTicket: "issued",
      fare: 18500000, paid: 0, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: true, at: "23/08 06:10", x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: true, at: "24/08 15:40", x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: false, x: 450, y: 105 },
        { name: "ທ່າເຮືອກະລ້", sub: "Cảng dỡ", km: 150, done: false, x: 610, y: 60 },
      ],
      approvals: ["done", "done", "pending", "pending", "check", "pending"],
      events: [
        { date: "2026-09-17", time: "07:30", type: "warn", text: "Chuyến đã đi 25 ngày, chưa xác nhận tới cửa khẩu ນ້ຳພາວ", by: "Hệ thống" },
        { date: "2026-08-25", time: "09:15", type: "fuel", text: "Cấp phiếu lĩnh nhiên liệu 400 L – PL-0812", by: "Kế toán (Souk)" },
        { date: "2026-08-24", time: "15:40", type: "stop", text: "Xác nhận tới ທ່ານໍາ (ສະໜາມ EPL) – 145 km", by: "Tài xế" },
        { date: "2026-08-23", time: "06:10", type: "depart", text: "Xuất xe tại ກາສີ, cân đầu 41,90 t", by: "Điều độ (Vilay)" },
      ],
      costs: [
        { id: "c1", item: "Lốp 11R22.5", qty: 2, price: 1700000, amount: 3400000, voucher: "V-01", status: "entered", date: "2026-09-02" },
        { id: "c2", item: "Công thay lốp", qty: 1, price: 450000, amount: 450000, voucher: "V-02", status: "check", date: "2026-09-02" },
      ],
      docs: [
        { name: "Phiếu cân đầu ກາສີ", date: "2026-08-23", status: "ok" },
        { name: "Lệnh vận chuyển LVC-0432", date: "2026-08-22", status: "ok" },
        { name: "Tờ khai hải quan", date: "", status: "missing" },
        { name: "Phiếu cân cuối", date: "", status: "missing" },
      ],
    },
    {
      id: "t428", code: "T4-0428-08/EPL", vehicle: "318", plate: "ບອ 2087", driver: "ທ້າວ ຄໍາພອນ", customer: "Vinacomin Lào",
      cargo: "Quặng sắt", weightIn: 40.2, weightOut: null, depart: "2026-08-19", status: "running", fuelTicket: "issued",
      fare: 17800000, paid: 0, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: true, at: "19/08 05:50", x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: true, at: "20/08 14:05", x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: false, x: 450, y: 105 },
        { name: "Cảng Vũng Áng", sub: "Cảng dỡ", km: 165, done: false, x: 640, y: 40 },
      ],
      approvals: ["done", "done", "pending", "pending", "pending", "pending"],
      events: [
        { date: "2026-09-16", time: "08:00", type: "warn", text: "Chuyến đã đi 28 ngày, chưa tới cửa khẩu", by: "Hệ thống" },
        { date: "2026-09-05", time: "11:20", type: "incident", text: "Hỏng bơm cao áp tại km 180, chờ thợ từ ທ່ານໍາ", by: "Tài xế", approved: true },
        { date: "2026-08-20", time: "14:05", type: "stop", text: "Xác nhận tới ທ່ານໍາ (ສະໜາມ EPL)", by: "Tài xế" },
        { date: "2026-08-19", time: "05:50", type: "depart", text: "Xuất xe, cân đầu 40,20 t", by: "Điều độ (Vilay)" },
      ],
      costs: [
        { id: "c3", item: "Bơm cao áp (sửa)", qty: 1, price: 2800000, amount: 2800000, voucher: "V-05", status: "approved", date: "2026-09-06" },
      ],
      docs: [
        { name: "Phiếu cân đầu ກາສີ", date: "2026-08-19", status: "ok" },
        { name: "Lệnh vận chuyển LVC-0428", date: "2026-08-18", status: "ok" },
      ],
    },
    {
      id: "t430", code: "T4-0430-08/EPL", vehicle: "355", plate: "ບອ 4410", driver: "ທ້າວ ສົມສັກ", customer: "ຖໍ່ເຫຼືອ",
      cargo: "Quặng sắt", weightIn: 42.5, weightOut: 42.3, depart: "2026-08-21", arrived: "2026-09-03", status: "arrived", fuelTicket: "issued",
      fare: 18500000, paid: 0, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: true, at: "21/08 06:00", x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: true, at: "22/08 13:30", x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: true, at: "30/08 10:10", x: 450, y: 105 },
        { name: "ທ່າເຮືອກະລ້", sub: "Cảng dỡ", km: 150, done: true, at: "03/09 16:45", x: 610, y: 60 },
      ],
      approvals: ["done", "done", "done", "done", "done", "pending"],
      events: [
        { date: "2026-09-03", time: "16:45", type: "arrive", text: "Đã giao hàng tại ທ່າເຮືອກະລ້, cân cuối 42,30 t", by: "Tài xế" },
        { date: "2026-08-30", time: "10:10", type: "stop", text: "Qua cửa khẩu ນ້ຳພາວ", by: "Tài xế" },
        { date: "2026-08-21", time: "06:00", type: "depart", text: "Xuất xe, cân đầu 42,50 t", by: "Điều độ (Vilay)" },
      ],
      costs: [],
      docs: [
        { name: "Phiếu cân đầu", date: "2026-08-21", status: "ok" },
        { name: "Phiếu cân cuối", date: "2026-09-03", status: "ok" },
        { name: "Tờ khai hải quan", date: "2026-08-30", status: "ok" },
        { name: "Hóa đơn cước", date: "", status: "missing" },
      ],
    },
    {
      id: "t429", code: "T4-0429-08/EPL", vehicle: "327", plate: "ບອ 1932", driver: "ທ້າວ ວິໄລ", customer: "Vinacomin Lào",
      cargo: "Quặng sắt", weightIn: 39.8, weightOut: 39.6, depart: "2026-08-20", arrived: "2026-09-01", status: "arrived", fuelTicket: "issued",
      fare: 17800000, paid: 0, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: true, at: "20/08 05:40", x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: true, at: "21/08 12:50", x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: true, at: "28/08 09:30", x: 450, y: 105 },
        { name: "Cảng Vũng Áng", sub: "Cảng dỡ", km: 165, done: true, at: "01/09 15:20", x: 640, y: 40 },
      ],
      approvals: ["done", "done", "done", "done", "done", "pending"],
      events: [
        { date: "2026-09-01", time: "15:20", type: "arrive", text: "Đã giao hàng tại Vũng Áng, cân cuối 39,60 t", by: "Tài xế" },
        { date: "2026-08-20", time: "05:40", type: "depart", text: "Xuất xe, cân đầu 39,80 t", by: "Điều độ (Vilay)" },
      ],
      costs: [],
      docs: [
        { name: "Phiếu cân đầu", date: "2026-08-20", status: "ok" },
        { name: "Phiếu cân cuối", date: "2026-09-01", status: "ok" },
        { name: "Hóa đơn cước", date: "", status: "missing" },
      ],
    },
    {
      id: "t433", code: "T4-0433-09/EPL", vehicle: "361", plate: "ບອ 5128", driver: "ທ້າວ ພູວົງ", customer: "ຖໍ່ເຫຼືອ",
      cargo: "Quặng sắt", weightIn: null, weightOut: null, depart: "2026-09-18", status: "planned", fuelTicket: "pending",
      fare: 18500000, paid: 0, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: false, x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: false, x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: false, x: 450, y: 105 },
        { name: "ທ່າເຮືອກະລ້", sub: "Cảng dỡ", km: 150, done: false, x: 610, y: 60 },
      ],
      approvals: ["pending", "pending", "pending", "pending", "pending", "pending"],
      events: [
        { date: "2026-09-16", time: "16:00", type: "note", text: "Lập lệnh vận chuyển LVC-0433, dự kiến xuất xe 18/09", by: "Điều độ (Vilay)" },
      ],
      costs: [],
      docs: [{ name: "Lệnh vận chuyển LVC-0433", date: "2026-09-16", status: "ok" }],
    },
    {
      id: "t425", code: "T4-0425-08/EPL", vehicle: "342", plate: "ບອ 3311", driver: "ທ້າວ ບຸນມີ", customer: "Vinacomin Lào",
      cargo: "Quặng sắt", weightIn: 41.2, weightOut: 41.0, depart: "2026-08-02", arrived: "2026-08-14", status: "closed", fuelTicket: "issued",
      fare: 17800000, paid: 17800000, currency: "LAK",
      stops: [
        { name: "ກາສີ (ບ່ອນຂຸດແຮ່)", sub: "Điểm xếp", km: 0, done: true, at: "02/08 06:00", x: 110, y: 200 },
        { name: "ທ່ານໍາ (ສະໜາມ EPL)", sub: "Sân bãi", km: 145, done: true, at: "03/08 13:00", x: 270, y: 150 },
        { name: "ດ່ານ ນ້ຳພາວ", sub: "Cửa khẩu", km: 210, done: true, at: "10/08 09:00", x: 450, y: 105 },
        { name: "Cảng Vũng Áng", sub: "Cảng dỡ", km: 165, done: true, at: "14/08 15:00", x: 640, y: 40 },
      ],
      approvals: ["done", "done", "done", "done", "done", "done"],
      events: [
        { date: "2026-08-20", time: "10:00", type: "note", text: "Đã thu cước 17.800.000 LAK – PT-0302", by: "Kế toán (Souk)" },
        { date: "2026-08-14", time: "15:00", type: "arrive", text: "Đã giao hàng tại Vũng Áng", by: "Tài xế" },
        { date: "2026-08-02", time: "06:00", type: "depart", text: "Xuất xe, cân đầu 41,20 t", by: "Điều độ (Vilay)" },
      ],
      costs: [],
      docs: [
        { name: "Phiếu cân đầu", date: "2026-08-02", status: "ok" },
        { name: "Phiếu cân cuối", date: "2026-08-14", status: "ok" },
        { name: "Hóa đơn cước HD-0125", date: "2026-08-16", status: "ok" },
      ],
    },
  ];

  const APPROVAL_LABELS = [["I", "Xuất xe"], ["II", "Cân đầu"], ["III", "Tới điểm"], ["IV", "Cân cuối"], ["V", "Chi phí"], ["VI", "Thu tiền"]];
  const STATUS = {
    planned: { label: "Chưa xuất bến", pill: "muted" },
    running: { label: "Đang vận chuyển", pill: "blue" },
    arrived: { label: "Đã giao hàng", pill: "green" },
    closed: { label: "Đã thu tiền", pill: "green" },
  };
  const EVENT_TYPES = {
    depart: { label: "Xuất xe", pill: "blue" }, stop: { label: "Tới điểm", pill: "blue" }, arrive: { label: "Giao hàng", pill: "green" },
    fuel: { label: "Phiếu lĩnh", pill: "tan" }, warn: { label: "Cảnh báo", pill: "amber" }, incident: { label: "Sự cố", pill: "red" },
    note: { label: "Ghi chú", pill: "muted" }, cost: { label: "Sửa xe", pill: "tan" }, money: { label: "Thu tiền", pill: "green" },
  };
  const COST_STATUS = { entered: ["Đã nhập", "muted"], check: ["Chờ kiểm", "amber"], approved: ["Đã duyệt", "green"] };

  /* ============ Tiện ích ============ */
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nf = new Intl.NumberFormat("vi-VN");
  const money = (n, cur) => nf.format(Math.round(n || 0)) + " " + (cur || "LAK");
  const fmtDate = (iso) => { if (!iso) return "—"; const [y, m, d] = iso.split("-"); return `${d}/${m}/${y}`; };
  const fmtShort = (iso) => { if (!iso) return ""; const [, m, d] = iso.split("-"); return `${d}/${m}`; };
  const todayISO = () => TODAY.toISOString().slice(0, 10);
  const nowHM = () => { const d = new Date(); return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0"); };
  const daysSince = (iso) => Math.max(0, Math.round((TODAY - new Date(iso + "T00:00:00")) / 86400000));
  const pill = (txt, kind) => `<span class="pill pill--${kind}">${esc(txt)}</span>`;
  const uid = () => Math.random().toString(36).slice(2, 8);

  /* ============ Kho dữ liệu (localStorage) ============ */
  const store = {
    trips: [],
    load() {
      let saved = null;
      try { saved = JSON.parse(localStorage.getItem(CONFIG.storageKey) || "null"); } catch (_) { saved = null; }
      this.trips = saved && Array.isArray(saved) && saved.length ? saved : JSON.parse(JSON.stringify(CONFIG.trips || SAMPLE));
    },
    save() { try { localStorage.setItem(CONFIG.storageKey, JSON.stringify(this.trips)); } catch (_) {} },
    reset() { try { localStorage.removeItem(CONFIG.storageKey); } catch (_) {} this.load(); },
    get(id) { return this.trips.find((t) => t.id === id); },
  };

  /* Chỉ số phái sinh của một chuyến */
  function derive(t) {
    const days = t.status === "planned" ? 0 : daysSince(t.depart);
    const doneStops = t.stops.filter((s) => s.done).length;
    const totalKm = t.stops.reduce((a, s) => a + (s.km || 0), 0);
    const doneKm = t.stops.filter((s) => s.done).reduce((a, s) => a + (s.km || 0), 0);
    const late = t.status === "running" && days >= CONFIG.lateDays;
    const incidentOpen = t.events.some((e) => e.type === "incident" && !e.approved);
    const costTotal = t.costs.reduce((a, c) => a + (c.amount || 0), 0);
    const due = Math.max(0, (t.fare || 0) - (t.paid || 0));
    const nextStop = t.stops.findIndex((s) => !s.done);
    return { days, doneStops, totalKm, doneKm, late, incidentOpen, costTotal, due, nextStop };
  }

  /* ============ Trạng thái giao diện ============ */
  const ui = {
    selectedId: null, sort: "priority", tileFilter: null, mapView: "fleet", tab: "events", q: "", onlyOpen: true, focusStop: -1, timer: null,
  };

  /* ============ Ô thống kê ============ */
  const TILES = [
    { id: "running", label: "Phiếu đang chạy", test: (t) => t.status === "running" },
    { id: "planned", label: "Chưa xuất bến", test: (t) => t.status === "planned" },
    { id: "late", label: "Đi lâu chưa về", cls: "red", test: (t, d) => d.late },
    { id: "arrived", label: "Đã tới chờ hóa đơn", test: (t) => t.status === "arrived" },
    { id: "incident", label: "Sự cố chưa duyệt", cls: "red", test: (t, d) => d.incidentOpen },
    { id: "fuel", label: "Phiếu lĩnh chờ cấp", cls: "amber", test: (t) => t.fuelTicket === "pending" },
    { id: "due", label: "Chưa thu tiền", test: (t, d) => t.status !== "planned" && d.due > 0 },
  ];

  function renderTiles() {
    $("#tiles").innerHTML = TILES.map((tile) => {
      const n = store.trips.filter((t) => tile.test(t, derive(t))).length;
      return `<div class="tile ${tile.cls || ""} ${ui.tileFilter === tile.id ? "active" : ""}" data-tile="${tile.id}" title="Bấm để lọc danh sách"><span>${esc(tile.label)}</span><b class="${n ? "nz" : ""}">${n}</b></div>`;
    }).join("");
  }

  /* ============ Danh sách chuyến ============ */
  function visibleTrips() {
    const q = ui.q.trim().toLowerCase();
    const tile = TILES.find((x) => x.id === ui.tileFilter);
    let list = store.trips.filter((t) => {
      const d = derive(t);
      if (ui.onlyOpen && t.status === "closed") return false;
      if (tile && !tile.test(t, d)) return false;
      if (q) { const hay = [t.code, t.vehicle, t.plate, t.driver, t.customer, t.cargo].join(" ").toLowerCase(); if (!hay.includes(q)) return false; }
      return true;
    });
    const rank = (t) => { const d = derive(t); return (d.incidentOpen ? 0 : 1) * 100 + (d.late ? 0 : 1) * 10 + ({ running: 0, arrived: 1, planned: 2, closed: 3 }[t.status]); };
    if (ui.sort === "priority") list.sort((a, b) => rank(a) - rank(b) || derive(b).days - derive(a).days);
    else if (ui.sort === "date") list.sort((a, b) => b.depart.localeCompare(a.depart));
    else list.sort((a, b) => a.customer.localeCompare(b.customer) || a.code.localeCompare(b.code));
    return list;
  }

  function renderList() {
    const list = visibleTrips();
    $("#trip-count").textContent = `${list.length} / ${store.trips.length} phiếu`;
    if (!list.length) { $("#trip-list").innerHTML = `<div class="empty">Không có chuyến nào khớp bộ lọc.</div>`; return; }
    if (!list.some((t) => t.id === ui.selectedId)) ui.selectedId = list[0].id;
    $("#trip-list").innerHTML = list.map((t) => {
      const d = derive(t); const st = STATUS[t.status];
      const dayTxt = t.status === "planned" ? `Dự kiến đi ${fmtShort(t.depart)}` : t.status === "running" ? `<span class="${d.late ? "late" : ""}">${d.days} ngày</span>` : `Tới ${fmtShort(t.arrived)}`;
      const flag = d.incidentOpen ? `<span class="late">● Sự cố</span>` : d.late ? `<span class="warn">● Đi lâu</span>` : "";
      return `<div class="trip ${t.id === ui.selectedId ? "active" : ""}" data-id="${t.id}">
        <div class="top"><span class="code mono">${esc(t.code)}</span>${pill(st.label, st.pill)}</div>
        <div class="mid"><span class="lo">${esc(t.customer)}</span><span class="veh">${esc(t.cargo)}</span></div>
        <div class="bot"><span class="veh lo">Xe ${esc(t.vehicle)} · ${esc(t.plate)} · ${esc(t.driver)}</span></div>
        <div class="bot"><span>${dayTxt} · ${d.doneStops}/${t.stops.length} chặng</span>${flag}</div>
      </div>`;
    }).join("");
  }

  /* ============ Bản đồ ============ */
  const MAP_BG = `<defs><pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0v28" fill="none" stroke="#c9d3cc" stroke-width=".6"/></pattern></defs>
    <rect width="700" height="250" fill="url(#grid)"/>
    <path d="M40 235 C 120 190, 200 175, 270 150 S 400 120, 450 105 S 560 70, 660 30" fill="none" stroke="#b8c4bc" stroke-width="6" stroke-linecap="round"/>
    <path d="M450 105 C 500 130, 560 150, 640 40" fill="none" stroke="#c4cec8" stroke-width="4" stroke-dasharray="6 6"/>
    <path d="M0 60 C 120 80, 220 40, 330 55 S 520 20, 700 45" fill="none" stroke="#a9c5d9" stroke-width="10" opacity=".55"/>
    <text x="30" y="52" font-size="11" fill="#7b8a80">ແມ່ນ້ຳ / Sông</text>
    <text x="505" y="238" font-size="11" fill="#7b8a80">Biên giới Lào – Việt</text>
    <line x1="470" y1="0" x2="520" y2="250" stroke="#8d9a91" stroke-width="1" stroke-dasharray="4 5"/>`;

  function colorOf(t, d) { return d.incidentOpen ? "var(--red)" : d.late ? "var(--amber)" : t.status === "running" ? "var(--blue)" : t.status === "planned" ? "var(--faint)" : "var(--green)"; }
  function vehiclePos(t) {
    const done = t.stops.filter((s) => s.done);
    if (!done.length) return { x: t.stops[0].x, y: t.stops[0].y, none: true };
    const last = done[done.length - 1]; const next = t.stops[done.length];
    if (!next || t.status !== "running") return { x: last.x, y: last.y };
    return { x: last.x + (next.x - last.x) * 0.45, y: last.y + (next.y - last.y) * 0.45 };
  }
  const truckIcon = (x, y, color, id, big) => `<g class="marker" data-id="${id}" transform="translate(${x} ${y})"><circle r="${big ? 13 : 10}" fill="${color}" opacity=".18"/><circle r="${big ? 8 : 6}" fill="${color}" stroke="#fff" stroke-width="2"/></g>`;

  function renderMap() {
    const t = store.get(ui.selectedId);
    let svg = "", floats = "";
    if (ui.mapView === "fleet" || !t) {
      svg = store.trips.filter((x) => x.status !== "closed").map((x) => { const d = derive(x); const p = vehiclePos(x); return truckIcon(p.x, p.y, colorOf(x, d), x.id, x.id === ui.selectedId) + `<text x="${p.x + 12}" y="${p.y + 4}" font-size="10.5" font-weight="600" fill="#1b2530">${esc(x.vehicle)}</text>`; }).join("");
      const n = store.trips.filter((x) => x.status !== "closed").length;
      floats = `<div class="float" style="left:12px;top:12px"><div class="tag"><b>${n} xe</b> đang theo dõi · bấm điểm để chọn chuyến</div></div>`;
    } else {
      const d = derive(t);
      const pts = t.stops.map((s) => `${s.x},${s.y}`).join(" ");
      const donePts = t.stops.filter((s) => s.done).map((s) => `${s.x},${s.y}`).join(" ");
      svg += `<polyline points="${pts}" fill="none" stroke="#1b2530" stroke-width="2" stroke-dasharray="5 5" opacity=".5"/>`;
      if (t.stops.filter((s) => s.done).length > 1) svg += `<polyline points="${donePts}" fill="none" stroke="#1b2530" stroke-width="3"/>`;
      svg += t.stops.map((s, i) => `<g class="marker" data-stop="${i}" transform="translate(${s.x} ${s.y})">${ui.focusStop === i ? `<circle r="14" fill="var(--blue)" opacity=".2"/>` : ""}<circle r="7" fill="${s.done ? "#1b2530" : "#fff"}" stroke="#1b2530" stroke-width="2"/><text y="-13" text-anchor="middle" font-size="10.5" font-weight="600" fill="#1b2530">${i + 1}. ${esc(s.name)}</text><text y="20" text-anchor="middle" font-size="10" fill="#6b7a70">${s.km ? "+" + s.km + " km" : esc(s.sub || "")}</text></g>`).join("");
      const p = vehiclePos(t);
      svg += truckIcon(p.x, p.y, colorOf(t, d), t.id, true);
      floats = `<div class="float" style="left:12px;top:12px"><div class="tag"><b class="mono">${esc(t.code)}</b> · Xe ${esc(t.vehicle)} · <span class="lo">${esc(t.driver)}</span></div></div>
        <div class="float" style="right:12px;bottom:12px"><div class="tag">${d.doneKm} / ${d.totalKm} km · ${d.doneStops}/${t.stops.length} điểm${d.late ? ` · <b style="color:var(--amber)">${d.days} ngày</b>` : ""}</div></div>`;
    }
    $("#map").innerHTML = `<svg viewBox="0 0 700 250" preserveAspectRatio="none">${MAP_BG}${svg}</svg>${floats}`;
  }

  /* ============ Mốc chặng ============ */
  function renderStepper() {
    const t = store.get(ui.selectedId);
    if (!t) { $("#stepper").innerHTML = ""; $("#stepfoot").innerHTML = ""; return; }
    const d = derive(t);
    $("#stepper").innerHTML = t.stops.map((s, i) => `<div class="step ${s.done ? "done" : i === d.nextStop ? "next" : ""}" data-stop="${i}" title="${esc(s.sub || "")}"><i>${s.done ? "✓" : i + 1}</i><b class="lo">${esc(s.name)}</b><small>${s.done ? esc(s.at || "") : s.km ? "+" + s.km + " km" : esc(s.sub || "")}</small></div>`).join("");
    $("#stepfoot").innerHTML = `<span>Tổng tuyến <b>${d.totalKm} km</b> · đã đi ${d.doneKm} km</span><span>Tới điểm <b>${d.doneStops}/${t.stops.length}</b>${d.nextStop >= 0 ? ` · tiếp theo: <span class="lo">${esc(t.stops[d.nextStop].name)}</span>` : " · đã hoàn tất tuyến"}</span>`;
  }

  /* ============ Tabs: Diễn biến / Chi phí / Chứng từ ============ */
  const TABS = [["events", "Diễn biến"], ["costs", "Chi phí sửa chữa"], ["docs", "Chứng từ"]];
  function renderTabs() {
    const t = store.get(ui.selectedId);
    if (!t) { $("#tabs").innerHTML = ""; $("#tab-actions").innerHTML = ""; $("#tabbody").innerHTML = `<div class="empty">Chọn một chuyến để xem chi tiết.</div>`; return; }
    const d = derive(t);
    $("#tabs").innerHTML = TABS.map(([id, label]) => `<button type="button" class="tab ${ui.tab === id ? "active" : ""}" data-tab="${id}">${label}<span class="n">${t[id].length}</span></button>`).join("");
    $("#tab-actions").innerHTML = ui.tab === "events" ? `<button type="button" class="btn btn--sm" data-act="note">+ Ghi chú diễn biến</button>`
      : ui.tab === "costs" ? `<button type="button" class="btn btn--sm btn--tan" data-act="cost">+ Khai sửa xe</button>`
      : `<button type="button" class="btn btn--sm" data-act="doc">+ Thêm chứng từ</button>`;

    let body = "", foot = "";
    if (ui.tab === "events") {
      const ev = [...t.events].sort((a, b) => (b.date + b.time).localeCompare(a.date + a.time));
      body = ev.length ? `<table><thead><tr><th style="width:96px">Thời gian</th><th style="width:96px">Loại</th><th>Nội dung</th><th style="width:130px">Người ghi</th></tr></thead><tbody>${ev.map((e) => { const ty = EVENT_TYPES[e.type] || EVENT_TYPES.note; return `<tr><td class="mono" style="font-size:12px">${fmtShort(e.date)} ${esc(e.time)}</td><td>${pill(ty.label, ty.pill)}</td><td class="lo">${esc(e.text)}${e.type === "incident" && !e.approved ? ` <span class="pill pill--amber" style="margin-left:6px">Chờ duyệt</span>` : ""}</td><td class="muted">${esc(e.by)}</td></tr>`; }).join("")}</tbody></table>` : `<div class="empty">Chưa có diễn biến.</div>`;
      foot = `<span>${ev.length} diễn biến</span><span>Cập nhật gần nhất: ${ev[0] ? fmtDate(ev[0].date) + " " + esc(ev[0].time) : "—"}</span>`;
    } else if (ui.tab === "costs") {
      body = t.costs.length ? `<table><thead><tr><th>Hạng mục</th><th class="num" style="width:50px">SL</th><th class="num" style="width:120px">Đơn giá</th><th class="num" style="width:130px">Thành tiền</th><th style="width:70px">Phiếu</th><th style="width:100px">Trạng thái</th><th style="width:70px"></th></tr></thead><tbody>${t.costs.map((c) => { const [lb, k] = COST_STATUS[c.status] || COST_STATUS.entered; return `<tr><td>${esc(c.item)}<div class="muted" style="font-size:11px">${fmtDate(c.date)}</div></td><td class="num">${c.qty}</td><td class="num mono" style="font-size:12px">${nf.format(c.price)}</td><td class="num mono" style="font-size:12px"><b>${nf.format(c.amount)}</b></td><td class="mono" style="font-size:12px">${esc(c.voucher)}</td><td>${pill(lb, k)}</td><td>${c.status !== "approved" ? `<button type="button" class="btn btn--sm" data-approve-cost="${c.id}">Duyệt</button>` : ""}</td></tr>`; }).join("")}</tbody></table>` : `<div class="empty">Chuyến này chưa có chi phí sửa chữa.</div>`;
      foot = `<span>Tổng chi phí: <b style="color:var(--ink)">${money(d.costTotal, t.currency)}</b> · ${t.costs.filter((c) => c.status === "check").length} khoản chờ kiểm</span><span>Ghi vào mục <b>V – Chi phí</b> của hồ sơ chuyến</span>`;
    } else {
      body = t.docs.length ? `<table><thead><tr><th>Chứng từ</th><th style="width:110px">Ngày</th><th style="width:110px">Trạng thái</th></tr></thead><tbody>${t.docs.map((x) => `<tr><td>${esc(x.name)}</td><td class="mono" style="font-size:12px">${fmtDate(x.date)}</td><td>${x.status === "ok" ? pill("Đã có", "green") : pill("Còn thiếu", "red")}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">Chưa có chứng từ.</div>`;
      const miss = t.docs.filter((x) => x.status !== "ok").length;
      foot = `<span>${t.docs.length - miss}/${t.docs.length} chứng từ đã có</span><span>${miss ? `<b style="color:var(--red)">Thiếu ${miss} chứng từ</b>` : "Đủ chứng từ để lập hóa đơn"}</span>`;
    }
    $("#tabbody").innerHTML = body + `<div class="tabfoot">${foot}</div>`;
  }

  /* ============ Hồ sơ chuyến (cột phải) ============ */
  function renderProfile() {
    const t = store.get(ui.selectedId);
    if (!t) { $("#profile").innerHTML = `<div class="empty">Chưa chọn chuyến.</div>`; return; }
    const d = derive(t); const st = STATUS[t.status];
    const kv = (k, v, cls) => `<div class="kv"><span>${k}</span><b class="${cls || ""}">${v}</b></div>`;
    const next = d.nextStop >= 0 ? t.stops[d.nextStop] : null;
    $("#profile").innerHTML = `
      <div>
        <div class="row" style="justify-content:space-between"><b class="mono" style="font-size:15px">${esc(t.code)}</b>${pill(st.label, st.pill)}</div>
        <div class="row" style="margin-top:8px;flex-wrap:wrap">${d.late ? pill(`Đi lâu · ${d.days} ngày`, "amber") : ""}${d.incidentOpen ? pill("Sự cố chờ duyệt", "red") : ""}${t.fuelTicket === "pending" ? pill("Phiếu lĩnh chờ cấp", "tan") : ""}${d.costTotal ? pill(`Sửa xe ${money(d.costTotal, t.currency)}`, "muted") : ""}</div>
      </div>
      <div>
        ${kv("Xe / biển số", `${esc(t.vehicle)} · <span class="lo">${esc(t.plate)}</span>`)}
        ${kv("Tài xế", `<span class="lo">${esc(t.driver)}</span>`)}
        ${kv("Khách hàng", `<span class="lo">${esc(t.customer)}</span>`)}
        ${kv("Hàng hóa", esc(t.cargo))}
        ${kv("Cân đầu / cân cuối", `${t.weightIn != null ? t.weightIn.toFixed(2).replace(".", ",") + " t" : "—"} / ${t.weightOut != null ? t.weightOut.toFixed(2).replace(".", ",") + " t" : "—"}`)}
        ${kv("Ngày đi", `${fmtDate(t.depart)}${t.status === "planned" ? " (dự kiến)" : ""}`)}
        ${kv("Số ngày", t.status === "planned" ? "—" : `${d.days} ngày`, d.late ? "late" : "")}
        ${kv("Chặng", `${d.doneStops}/${t.stops.length} · ${d.totalKm} km`)}
      </div>
      <div>
        <div class="sec-head" style="margin-bottom:8px"><span>Trình tự duyệt</span><span>${t.approvals.filter((a) => a === "done").length}/6</span></div>
        <div class="approvals">${APPROVAL_LABELS.map(([r, lb], i) => `<div class="ap ${t.approvals[i]}" data-ap="${i}" title="Bấm để đổi trạng thái"><b>${r}</b><span class="ring" style="${t.approvals[i] === "done" ? "background:var(--green);border-color:var(--green)" : t.approvals[i] === "check" ? "background:var(--amber);border-color:var(--amber)" : ""}"></span><small>${lb}</small></div>`).join("")}</div>
      </div>
      <div class="money"><div><small>Cước dự kiến</small><b>${money(t.fare, t.currency)}</b></div><div class="${d.due ? "due" : ""}"><small>${d.due ? "Chưa thu" : "Đã thu đủ"}</small><b>${money(d.due ? d.due : t.paid, t.currency)}</b></div></div>
      <div class="actions">
        ${next ? `<button type="button" class="btn btn--dark" data-act="confirm-stop">${t.status === "planned" ? "Xuất xe – ghi cân đầu" : `Xác nhận tới điểm ${d.nextStop + 1}: <span class="lo">${esc(next.name)}</span>`}</button>` : ""}
        ${t.fuelTicket === "pending" ? `<button type="button" class="btn btn--tan" data-act="fuel">Cấp phiếu lĩnh nhiên liệu</button>` : ""}
        ${!next && d.due > 0 ? `<button type="button" class="btn btn--dark" data-act="collect">Ghi nhận thu tiền ${money(d.due, t.currency)}</button>` : ""}
        <button type="button" class="btn btn--red" data-act="incident">Báo sự cố / sửa xe</button>
      </div>`;
  }

  function renderAll() { renderTiles(); renderList(); renderMap(); renderStepper(); renderTabs(); renderProfile(); }
  function renderDetail() { renderMap(); renderStepper(); renderTabs(); renderProfile(); }

  /* ============ Modal / toast ============ */
  function toast(msg) {
    const el = document.createElement("div"); el.className = "toast";
    el.innerHTML = `<svg viewBox="0 0 24 24"><path d="M5 12l4 4L19 6"/></svg>${esc(msg)}`;
    $("#toast-root").appendChild(el); setTimeout(() => el.remove(), 2600);
  }
  function modal(title, bodyHtml, footHtml, opts) {
    const root = $("#modal-root");
    root.innerHTML = `<div class="modal-backdrop"><div class="modal" style="${opts && opts.width ? "width:" + opts.width : ""}"><div class="modal__head"><h2>${esc(title)}</h2><button type="button" class="iconbtn" data-close><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div><div class="modal__body ${opts && opts.plain ? "plain" : ""}">${bodyHtml}</div>${footHtml ? `<div class="modal__foot">${footHtml}</div>` : ""}</div></div>`;
    root.querySelector("[data-close]").onclick = closeModal;
    root.querySelector(".modal-backdrop").addEventListener("click", (e) => { if (e.target.classList.contains("modal-backdrop")) closeModal(); });
    return root.querySelector(".modal");
  }
  function closeModal() { $("#modal-root").innerHTML = ""; }
  const field = (id, label, control, full) => `<div class="field ${full ? "field--full" : ""}"><label for="${id}">${label}</label>${control}</div>`;
  const tripSelect = (id, selected) => `<select id="${id}">${store.trips.filter((t) => t.status !== "closed").map((t) => `<option value="${t.id}" ${t.id === selected ? "selected" : ""}>${esc(t.code)} – xe ${esc(t.vehicle)}</option>`).join("")}</select>`;

  /* ============ Nghiệp vụ ============ */
  async function addEvent(tripId, ev) {
    const t = store.get(tripId); if (!t) return;
    ev = Object.assign({ date: todayISO(), time: nowHM(), by: "Điều độ", type: "note" }, ev);
    t.events.unshift(ev); store.save();
    if (typeof CONFIG.onEvent === "function") { try { await CONFIG.onEvent(tripId, ev); } catch (e) { console.warn("onEvent", e); } }
    return ev;
  }
  async function addCost(tripId, cost) {
    const t = store.get(tripId); if (!t) return;
    cost = Object.assign({ id: "c" + uid(), date: todayISO(), status: "check" }, cost);
    t.costs.push(cost);
    if (t.approvals[4] === "pending") t.approvals[4] = "check";
    store.save();
    if (typeof CONFIG.onCost === "function") { try { await CONFIG.onCost(tripId, cost); } catch (e) { console.warn("onCost", e); } }
    return cost;
  }

  function openNoteModal(tripId) {
    const m = modal("Ghi chú diễn biến", `
      ${field("f-trip", "Chuyến", tripSelect("f-trip", tripId))}
      ${field("f-type", "Loại", `<select id="f-type"><option value="note">Ghi chú</option><option value="warn">Cảnh báo</option><option value="fuel">Phiếu lĩnh</option><option value="stop">Tới điểm</option></select>`)}
      ${field("f-text", "Nội dung", `<textarea id="f-text" rows="3" placeholder="VD: Xe dừng nghỉ tại km 180, dự kiến tới cửa khẩu sáng mai"></textarea>`, true)}
      ${field("f-by", "Người ghi", `<input id="f-by" value="Điều độ (Vilay)">`)}
      ${field("f-time", "Giờ", `<input id="f-time" value="${nowHM()}">`)}`,
      `<button type="button" class="btn" data-close>Hủy</button><button type="button" class="btn btn--dark" id="f-ok">Lưu diễn biến</button>`);
    m.querySelector("[data-close]:not(.iconbtn)").onclick = closeModal;
    $("#f-ok").onclick = async () => {
      const text = $("#f-text").value.trim(); if (!text) { $("#f-text").focus(); return; }
      const id = $("#f-trip").value;
      await addEvent(id, { type: $("#f-type").value, text, by: $("#f-by").value.trim() || "Điều độ", time: $("#f-time").value });
      closeModal(); ui.selectedId = id; ui.tab = "events"; renderAll(); toast("Đã ghi diễn biến vào " + store.get(id).code);
    };
    setTimeout(() => $("#f-text").focus(), 30);
  }

  function openCostModal(tripId, asIncident) {
    const m = modal(asIncident ? "Báo sự cố / sửa xe" : "Khai chi phí sửa xe", `
      ${field("f-trip", "Chuyến", tripSelect("f-trip", tripId), true)}
      ${asIncident ? field("f-inc", "Mô tả sự cố", `<textarea id="f-inc" rows="2" placeholder="VD: Nổ lốp sau bên phải tại km 96, xe dừng an toàn"></textarea>`, true) : ""}
      ${field("f-item", "Hạng mục sửa chữa", `<input id="f-item" placeholder="VD: Lốp 11R22.5">`, true)}
      ${field("f-qty", "Số lượng", `<input id="f-qty" type="number" min="1" step="1" value="1">`)}
      ${field("f-price", "Đơn giá (LAK)", `<input id="f-price" type="number" min="0" step="1000" placeholder="0">`)}
      ${field("f-voucher", "Số phiếu / hóa đơn", `<input id="f-voucher" placeholder="V-03">`)}
      ${field("f-status", "Trạng thái", `<select id="f-status"><option value="check">Chờ kiểm</option><option value="entered">Đã nhập</option><option value="approved">Đã duyệt</option></select>`)}
      <div class="field field--full"><label>Thành tiền</label><div class="mono" id="f-total" style="font-size:16px;font-weight:600">0 LAK</div></div>`,
      `<button type="button" class="btn" data-close>Hủy</button><button type="button" class="btn btn--dark" id="f-ok">${asIncident ? "Ghi sự cố & chi phí" : "Lưu chi phí"}</button>`);
    m.querySelector("[data-close]:not(.iconbtn)").onclick = closeModal;
    const recalc = () => { $("#f-total").textContent = money((+$("#f-qty").value || 0) * (+$("#f-price").value || 0), "LAK"); };
    $("#f-qty").oninput = recalc; $("#f-price").oninput = recalc;
    $("#f-ok").onclick = async () => {
      const id = $("#f-trip").value; const item = $("#f-item").value.trim(); const price = +$("#f-price").value || 0; const qty = +$("#f-qty").value || 1;
      const incText = asIncident ? $("#f-inc").value.trim() : "";
      if (asIncident && !incText) { $("#f-inc").focus(); return; }
      if (!item && !asIncident) { $("#f-item").focus(); return; }
      if (incText) await addEvent(id, { type: "incident", text: incText, by: "Tài xế", approved: false });
      if (item) {
        const c = await addCost(id, { item, qty, price, amount: qty * price, voucher: $("#f-voucher").value.trim() || "—", status: $("#f-status").value });
        await addEvent(id, { type: "cost", text: `Khai chi phí sửa xe: ${item} ×${qty} = ${money(c.amount, "LAK")} (${c.voucher})`, by: "Điều độ" });
      }
      closeModal(); ui.selectedId = id; ui.tab = item ? "costs" : "events"; renderAll();
      toast(asIncident ? "Đã ghi sự cố vào sổ, chờ duyệt" : "Đã khai chi phí sửa xe");
    };
    setTimeout(() => $(asIncident ? "#f-inc" : "#f-item").focus(), 30);
  }

  function openDocModal(tripId) {
    const m = modal("Thêm chứng từ", `
      ${field("f-name", "Tên chứng từ", `<input id="f-name" placeholder="VD: Tờ khai hải quan">`, true)}
      ${field("f-date", "Ngày", `<input id="f-date" type="date" value="${todayISO()}">`)}
      ${field("f-status", "Trạng thái", `<select id="f-status"><option value="ok">Đã có</option><option value="missing">Còn thiếu</option></select>`)}`,
      `<button type="button" class="btn" data-close>Hủy</button><button type="button" class="btn btn--dark" id="f-ok">Lưu</button>`);
    m.querySelector("[data-close]:not(.iconbtn)").onclick = closeModal;
    $("#f-ok").onclick = () => {
      const name = $("#f-name").value.trim(); if (!name) return $("#f-name").focus();
      const t = store.get(tripId); t.docs.push({ name, date: $("#f-status").value === "ok" ? $("#f-date").value : "", status: $("#f-status").value }); store.save();
      closeModal(); renderDetail(); toast("Đã thêm chứng từ");
    };
  }

  async function confirmStop(tripId) {
    const t = store.get(tripId); const d = derive(t);
    if (d.nextStop < 0) return;
    const s = t.stops[d.nextStop];
    s.done = true; s.at = `${fmtShort(todayISO())} ${nowHM()}`;
    if (d.nextStop === 0) {
      t.status = "running"; t.approvals[0] = "done"; if (t.weightIn == null) t.weightIn = 41.5; t.approvals[1] = "done";
      if (t.depart > todayISO()) t.depart = todayISO();
      await addEvent(tripId, { type: "depart", text: `Xuất xe tại ${s.name}, cân đầu ${t.weightIn.toFixed(2).replace(".", ",")} t`, by: "Điều độ" });
    } else if (d.nextStop === t.stops.length - 1) {
      t.status = "arrived"; t.arrived = todayISO(); t.approvals[2] = "done"; t.approvals[3] = "done";
      if (t.weightOut == null) t.weightOut = Math.round((t.weightIn - 0.2) * 100) / 100;
      await addEvent(tripId, { type: "arrive", text: `Đã giao hàng tại ${s.name}, cân cuối ${t.weightOut.toFixed(2).replace(".", ",")} t`, by: "Tài xế" });
    } else {
      await addEvent(tripId, { type: "stop", text: `Xác nhận tới ${s.name}${s.km ? " – " + s.km + " km" : ""}`, by: "Tài xế" });
    }
    store.save(); ui.tab = "events"; renderAll(); toast(`Đã xác nhận tới ${s.name}`);
  }

  async function collect(tripId) {
    const t = store.get(tripId); const d = derive(t);
    t.paid = t.fare; t.status = "closed"; t.approvals[5] = "done";
    await addEvent(tripId, { type: "money", text: `Đã thu cước ${money(d.due, t.currency)} – PT-${String(300 + store.trips.length)}`, by: "Kế toán" });
    store.save(); renderAll(); toast("Đã ghi nhận thu tiền, chuyến chuyển sang Đã thu tiền");
  }

  function openIncidentsBook() {
    const rows = [];
    store.trips.forEach((t) => {
      t.events.filter((e) => e.type === "incident").forEach((e) => rows.push({ trip: t, kind: "Sự cố", date: e.date, time: e.time, text: e.text, status: e.approved ? ["Đã duyệt", "green"] : ["Chờ duyệt", "amber"], ev: e }));
      t.costs.forEach((c) => rows.push({ trip: t, kind: "Sửa xe", date: c.date, time: "", text: `${c.item} ×${c.qty} – ${money(c.amount, t.currency)} (${c.voucher})`, status: COST_STATUS[c.status] || COST_STATUS.entered, cost: c }));
    });
    rows.sort((a, b) => (b.date + b.time).localeCompare(a.date + a.time));
    const m = modal("Sổ sự cố & sửa chữa", rows.length ? `<table><thead><tr><th>Ngày</th><th>Chuyến</th><th>Loại</th><th>Nội dung</th><th>Trạng thái</th><th></th></tr></thead><tbody>${rows.map((r, i) => `<tr><td class="mono" style="font-size:12px">${fmtShort(r.date)} ${esc(r.time)}</td><td class="mono" style="font-size:12px">${esc(r.trip.code)}<div class="muted" style="font-size:11px">Xe ${esc(r.trip.vehicle)}</div></td><td>${pill(r.kind, r.kind === "Sự cố" ? "red" : "tan")}</td><td class="lo">${esc(r.text)}</td><td>${pill(r.status[0], r.status[1])}</td><td>${r.status[1] !== "green" ? `<button type="button" class="btn btn--sm" data-row="${i}">Duyệt</button>` : ""}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">Chưa có sự cố nào.</div>`,
      `<button type="button" class="btn" id="f-reset" style="margin-right:auto;color:var(--muted)">Đặt lại dữ liệu mẫu</button><button type="button" class="btn btn--dark" data-close>Đóng</button>`, { plain: true, width: "860px" });
    m.querySelector(".modal__foot [data-close]").onclick = closeModal;
    $("#f-reset").onclick = () => { store.reset(); ui.selectedId = null; closeModal(); renderAll(); toast("Đã khôi phục dữ liệu mẫu"); };
    m.querySelectorAll("[data-row]").forEach((b) => b.onclick = () => {
      const r = rows[+b.dataset.row];
      if (r.ev) r.ev.approved = true; if (r.cost) { r.cost.status = "approved"; if (r.trip.costs.every((c) => c.status === "approved")) r.trip.approvals[4] = "done"; }
      store.save(); openIncidentsBook(); renderAll(); toast("Đã duyệt");
    });
  }

  /* ============ Cập nhật / tự làm mới ============ */
  function stamp(note) { const d = new Date(); $("#stamp").textContent = `Cập nhật ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}${note ? " · " + note : ""}`; }
  function refresh(manual) { renderAll(); stamp(ui.timer ? "tự động 30 s" : ""); if (manual) toast("Đã cập nhật dữ liệu"); }
  function setAuto(on) { clearInterval(ui.timer); ui.timer = on ? setInterval(() => refresh(false), 30000) : null; stamp(on ? "tự động 30 s" : ""); }

  /* ============ Gắn sự kiện ============ */
  function bind() {
    $("#q").addEventListener("input", (e) => { ui.q = e.target.value; renderList(); renderDetail(); });
    $("#only-open").addEventListener("change", (e) => { ui.onlyOpen = e.target.checked; renderList(); renderDetail(); });
    $("#auto-refresh").addEventListener("change", (e) => setAuto(e.target.checked));
    $("#btn-refresh").addEventListener("click", () => refresh(true));
    $("#btn-incidents").addEventListener("click", openIncidentsBook);
    $("#btn-incident").addEventListener("click", () => openCostModal(ui.selectedId, true));
    $("#btn-open").addEventListener("click", () => {
      const t = store.get(ui.selectedId); if (!t) return;
      if (typeof CONFIG.openTicketUrl === "function") { const url = CONFIG.openTicketUrl(t); if (url) { window.location.href = url; return; } }
      toast(`Mở phiếu ${t.code} – nối openTicketUrl trong TRIPS_CONFIG`);
    });
    $("#tiles").addEventListener("click", (e) => { const el = e.target.closest(".tile"); if (!el) return; ui.tileFilter = ui.tileFilter === el.dataset.tile ? null : el.dataset.tile; renderTiles(); renderList(); renderDetail(); });
    $("#sort-seg").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; ui.sort = b.dataset.sort; $("#sort-seg").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b)); renderList(); });
    $("#map-seg").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; ui.mapView = b.dataset.view; $("#map-seg").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b)); renderMap(); });
    $("#trip-list").addEventListener("click", (e) => { const el = e.target.closest(".trip"); if (!el) return; ui.selectedId = el.dataset.id; ui.focusStop = -1; renderList(); renderDetail(); });
    $("#map").addEventListener("click", (e) => {
      const m = e.target.closest(".marker"); if (!m) return;
      if (m.dataset.id) { ui.selectedId = m.dataset.id; ui.mapView = "route"; $("#map-seg").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x.dataset.view === "route")); renderList(); renderDetail(); }
      else if (m.dataset.stop != null) { ui.focusStop = +m.dataset.stop; renderMap(); }
    });
    $("#stepper").addEventListener("click", (e) => {
      const s = e.target.closest(".step"); if (!s) return; const i = +s.dataset.stop; const t = store.get(ui.selectedId); const d = derive(t);
      ui.focusStop = i; ui.mapView = "route"; $("#map-seg").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x.dataset.view === "route")); renderMap();
      if (i === d.nextStop) toast(`Chặng ${i + 1} là điểm tiếp theo – bấm "Xác nhận tới điểm" ở hồ sơ chuyến`);
    });
    $("#tabs").addEventListener("click", (e) => { const b = e.target.closest(".tab"); if (!b) return; ui.tab = b.dataset.tab; renderTabs(); });
    $("#tab-actions").addEventListener("click", (e) => { const b = e.target.closest("[data-act]"); if (!b) return; ({ note: openNoteModal, cost: openCostModal, doc: openDocModal })[b.dataset.act](ui.selectedId); });
    $("#tabbody").addEventListener("click", (e) => {
      const b = e.target.closest("[data-approve-cost]"); if (!b) return; const t = store.get(ui.selectedId);
      const c = t.costs.find((x) => x.id === b.dataset.approveCost); c.status = "approved";
      if (t.costs.every((x) => x.status === "approved")) t.approvals[4] = "done";
      store.save(); renderDetail(); toast(`Đã duyệt ${c.item}`);
    });
    $("#profile").addEventListener("click", async (e) => {
      const ap = e.target.closest(".ap");
      if (ap) { const t = store.get(ui.selectedId); const i = +ap.dataset.ap; const cur = t.approvals[i]; t.approvals[i] = cur === "done" ? "pending" : "done"; store.save(); renderProfile(); toast(`${APPROVAL_LABELS[i][0]} – ${APPROVAL_LABELS[i][1]}: ${t.approvals[i] === "done" ? "đã duyệt" : "bỏ duyệt"}`); return; }
      const b = e.target.closest("[data-act]"); if (!b) return;
      if (b.dataset.act === "confirm-stop") confirmStop(ui.selectedId);
      else if (b.dataset.act === "incident") openCostModal(ui.selectedId, true);
      else if (b.dataset.act === "collect") collect(ui.selectedId);
      else if (b.dataset.act === "fuel") { const t = store.get(ui.selectedId); t.fuelTicket = "issued"; await addEvent(t.id, { type: "fuel", text: "Cấp phiếu lĩnh nhiên liệu 400 L", by: "Kế toán" }); renderAll(); toast("Đã cấp phiếu lĩnh"); }
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  }

  /* ============ Khởi động ============ */
  store.load();
  ui.selectedId = (store.trips.find((t) => t.id === "t432") || store.trips[0] || {}).id || null;
  bind(); renderAll(); stamp("");

  window.Trips = { store, ui, render: renderAll, addEvent, addCost, confirmStop, CONFIG };
})();
