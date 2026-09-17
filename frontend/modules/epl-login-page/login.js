/* login.js — trang đăng nhập EPL: ngôn ngữ (vi / lo / en / vi+lo), chọn nhanh theo vai trò, demo đăng nhập */
(function () {
  "use strict";
  /* ---------- CẤU HÌNH TÍCH HỢP ----------
     Đặt window.EPL_LOGIN_CONFIG trước khi nạp file này (xem README):
       redirect      : URL chuyển đến sau khi đăng nhập thành công (mặc định "index.html")
       authenticate  : async (username, password) => user | null   — gọi API thật; trả về object user
                       ({ u, name, role }) nếu đúng, null nếu sai. Không đặt → dùng danh sách demo + mật khẩu 1234.
       users         : mảng tài khoản hiển thị ở "Chọn nhanh theo vai trò" (mặc định danh sách demo bên dưới)
       storageKey    : khóa lưu phiên (mặc định "epl_user")
       showQuickPick : false để ẩn khung chọn nhanh khi lên môi trường thật */
  const CONFIG = Object.assign({ redirect: "index.html", authenticate: null, users: null, storageKey: "epl_user", showQuickPick: true }, window.EPL_LOGIN_CONFIG || {});
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const STR = {
    vi: { brand_sub: "Vận tải · Vientiane – Việt Nam", title: "Quản lý vận tải EPL", desc: "Mỗi người dùng đăng nhập bằng tài khoản riêng. Quyền nhập, kiểm tra, ghi sổ, chi tiền và lập hóa đơn phụ thuộc vào vai trò của tài khoản.",
      stop1: "Kho chính", stop2: "Cửa khẩu", stop3: "Xe KM-7781 · đang giao", badge: "2 xe", f1: "Phiếu xuất xe", f2: "Theo dõi tuyến", f3: "Phiếu chi · Phiếu thu",
      login: "Đăng nhập", demo: "Bản demo — mật khẩu mọi tài khoản là 1234", user: "Tên đăng nhập", pass: "Mật khẩu", remember: "Ghi nhớ đăng nhập", forgot: "Quên mật khẩu?", quick: "Hoặc chọn nhanh theo vai trò",
      err: "Sai tên đăng nhập hoặc mật khẩu.", welcome: "Xin chào", roles: { admin: "Quản trị", acct: "Kế toán", wh: "Kho", cash: "Quỹ", drv: "Tài xế" } },
    lo: { brand_sub: "ຂົນສົ່ງ · ວຽງຈັນ – ຫວຽດນາມ", title: "ຄຸ້ມຄອງການຂົນສົ່ງ EPL", desc: "ຜູ້ໃຊ້ແຕ່ລະຄົນເຂົ້າລະບົບດ້ວຍບັນຊີຂອງຕົນ. ສິດປ້ອນ, ກວດ, ບັນທຶກ, ຈ່າຍ ແລະ ອອກໃບເກັບເງິນ ຂຶ້ນກັບໜ້າທີ່ຂອງບັນຊີ.",
      stop1: "ສາງຫຼັກ", stop2: "ດ່ານຊາຍແດນ", stop3: "ລົດ KM-7781 · ກຳລັງສົ່ງ", badge: "2 ຄັນ", f1: "ໃບເບີກລົດ", f2: "ຕິດຕາມເສັ້ນທາງ", f3: "ໃບຈ່າຍ · ໃບຮັບ",
      login: "ເຂົ້າລະບົບ", demo: "ລະບົບທົດລອງ: ລະຫັດທຸກບັນຊີ 1234", user: "ຊື່ຜູ້ໃຊ້", pass: "ລະຫັດຜ່ານ", remember: "ຈື່ຂ້ອຍ", forgot: "ລືມລະຫັດຜ່ານ?", quick: "ຫຼື ເລືອກຕາມໜ້າທີ່",
      err: "ຊື່ຜູ້ໃຊ້ ຫຼື ລະຫັດຜ່ານບໍ່ຖືກ.", welcome: "ສະບາຍດີ", roles: { admin: "ຜູ້ບໍລິຫານ", acct: "ບັນຊີ", wh: "ສາງ", cash: "ເງິນສົດ", drv: "ຄົນຂັບ" } },
    en: { brand_sub: "Freight · Vientiane – Vietnam", title: "EPL Transport Management", desc: "Everyone signs in with their own account. Permissions to enter, check, post, pay and invoice depend on the account's role.",
      stop1: "Main warehouse", stop2: "Border crossing", stop3: "Truck KM-7781 · delivering", badge: "2 trucks", f1: "Dispatch notes", f2: "Route tracking", f3: "Payments · Receipts",
      login: "Sign in", demo: "Demo — every account's password is 1234", user: "Username", pass: "Password", remember: "Remember me", forgot: "Forgot password?", quick: "Or pick an account by role",
      err: "Wrong username or password.", welcome: "Welcome", roles: { admin: "Admin", acct: "Accounting", wh: "Warehouse", cash: "Cashier", drv: "Drivers" } },
  };
  // Tài khoản demo (mật khẩu 1234). roleKey → nhóm hiển thị
  const USERS = [
    { u: "admin", ini: "AD", name: "Admin", sub: "Quản trị · xem toàn bộ", role: "admin" },
    { u: "ketoan", ini: "PH", name: "ນາງ ພອນ (Phone)", sub: "Kế toán Viêng Chăn", role: "acct" }, { u: "doanhthu", ini: "KH", name: "ທ້າວ ຄຳ (Kham)", sub: "Kế toán thu", role: "acct" },
    { u: "khonl", ini: "VI", name: "ທ້າວ ວິໄລ (Vilay)", sub: "Kho nguyên liệu", role: "wh" }, { u: "khoth", ini: "BM", name: "ທ້າວ ບຸນມາ (Bounma)", sub: "Thủ kho nhiên liệu", role: "wh" }, { u: "thabok", ini: "SC", name: "ສົມໄຊ (Somchai)", sub: "Bãi Thà Bốc", role: "wh" },
    { u: "quyvc", ini: "MN", name: "ນາງ ມະນີ (Manee)", sub: "Quỹ Viêng Chăn", role: "cash" }, { u: "quytb", ini: "DA", name: "ນາງ ດາວ (Dao)", sub: "Tiền mặt lẻ Thà Bốc", role: "cash" }, { u: "khovc", ini: "SD", name: "ນາງ ສີດາ (Sida)", sub: "Thủ kho nhiên liệu", role: "cash" },
    { u: "tx01", ini: "TS", name: "ທ້າວ ທັດສະດາພອນ", sub: "Tài xế · chỉ phiếu xuất xe", role: "drv" }, { u: "tx02", ini: "BN", name: "ທ້າວ ບຸນມີ", sub: "Tài xế", role: "drv" }, { u: "tx03", ini: "SP", name: "ທ້າວ ສົມພອນ", sub: "Tài xế", role: "drv" },
  ];
  const ROLE_ORDER = ["admin", "acct", "wh", "cash", "drv"];
  const users = () => CONFIG.users || USERS;

  let lang = (() => { try { return localStorage.getItem("epl_lang") || "vi+lo"; } catch (_) { return "vi+lo"; } })();
  const primary = () => (lang === "vi+lo" ? "vi" : lang), secondary = () => (lang === "vi+lo" ? "lo" : null);
  const t = (k) => STR[primary()][k];

  function applyLang() {
    document.body.classList.toggle("bilingual", !!secondary());
    document.documentElement.lang = primary();
    $$("[data-t]").forEach((el) => (el.textContent = t(el.dataset.t)));
    $$("[data-t2]").forEach((el) => (el.textContent = secondary() ? STR[secondary()][el.dataset.t2] : ""));
    $$("#langs button").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
    renderRoles();
    try { localStorage.setItem("epl_lang", lang); } catch (_) {}
  }
  function renderRoles() {
    const cur = $("#username").value;
    $("#roles").innerHTML = ROLE_ORDER.map((r) => `<div class="role__head"><b>${t("roles")[r]}</b>${secondary() ? `<i class="lo">${STR[secondary()].roles[r]}</i>` : ""}</div>` +
      users().filter((x) => x.role === r).map((x) => `<button type="button" class="person lo ${x.u === cur ? "active" : ""}" data-u="${x.u}"><span class="person__ini">${x.ini}</span><div><span>${x.name}</span><small>${x.u} · ${x.sub}</small></div><svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg></button>`).join("")).join("");
    $$(".person").forEach((b) => (b.onclick = () => { $("#username").value = b.dataset.u; $("#password").value = "1234"; $$(".person").forEach((p) => p.classList.toggle("active", p === b)); $("#error").hidden = true; $("#password").focus(); }));
  }

  $("#langs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { lang = b.dataset.lang; applyLang(); } });
  $("#eye").onclick = () => { const p = $("#password"); p.type = p.type === "password" ? "text" : "password"; };
  $("#username").addEventListener("input", renderRoles);
  const demoAuth = async (u, p) => { const x = users().find((y) => y.u === u); return x && p === "1234" ? x : null; };
  $("#form").onsubmit = async (e) => {
    e.preventDefault();
    const u = $("#username").value.trim(), p = $("#password").value; const btn = $(".submit");
    btn.disabled = true; $("#error").hidden = true;
    let user = null;
    try { user = await (CONFIG.authenticate || demoAuth)(u, p); } catch (err) { user = null; }
    if (!user) { $("#error").textContent = t("err"); $("#error").hidden = false; btn.disabled = false; return; }
    try { (($("#remember").checked ? localStorage : sessionStorage)).setItem(CONFIG.storageKey, JSON.stringify({ u: user.u, name: user.name, role: user.role, token: user.token || null, lang })); } catch (_) {}
    btn.querySelector("[data-t]").textContent = `${t("welcome")}, ${user.name}…`;
    setTimeout(() => { location.href = CONFIG.redirect; }, 600);
  };
  if (!CONFIG.showQuickPick) { $("#roles").hidden = true; $(".divider").hidden = true; }
  applyLang();
})();
