/* Phiếu của tôi — màn tài xế. Máy chủ chỉ trả phiếu của chính tài xế đang đăng nhập.
 *
 * Giao diện theo bản mẫu chủ dự án gửi chiều 30/09 ("Chuyến của tôi – Cổng tài xế"): lời chào + bốn ô số, sáu tab, thẻ
 * chuyến có đường chạy và các bước, một nút lớn cho bước tiếp theo, ô bấm cho việc phụ, hộp nhập dạng tấm.
 * Giữ nguyên các luồng của màn cũ: ký giao nhận trên máy (POD), báo cân ở mỏ, mã QR phiếu đề nghị, chia sẻ vị trí, và
 * MẤT MẠNG VẪN BÁO ĐƯỢC cho ký giao nhận / báo cân (hàng đợi trong máy, ảnh đã nén, `ma_gui` chống ghi hai lần).
 * Luật đã chốt: tài xế không nhập đơn giá dầu (C5.1); dầu kho EPL lấy theo phiếu đề nghị, không tự khai; báo sự cố có ô
 * "Có chi tiền" giống màn Theo dõi — tổ sửa chữa duyệt thì khoản chi vào mục V rồi đi tiếp thành phiếu chi như bình
 * thường (không có tờ đề nghị chi riêng cho sửa chữa, anh chốt 30/09).
 */
(function () {
  const { API, NN, esc, so } = EPL;
  let root, DS = [], DIEM = [], CUR = null, TAB = 'trip', SO = {};
  let theoDoiId = null, phieuChiaSe = null, lanGuiCuoi = 0, boNghe = null, matMang = false, henTim = null;
  // napXong: lần tải đầu đã xong (trước đó các tab hiện "Đang tải…", không phải "chưa có phiếu") · napDu: chi tiết MỌI phiếu
  // đã về (tải nền xong) · luotTai: lượt tải mới nhất — lượt cũ về muộn thì bỏ, không đè dữ liệu mới
  let napXong = false, napDu = false, luotTai = 0;
  const CO_TRANG = 6;
  const LS_GOC = { q: '', thang: '', xe: '', sap: 'moi', tt: 'all', loai: 'all', trang: 1 };
  let LS = Object.assign({}, LS_GOC), LSDS = null, LSDEM = {};
  const q = (s) => root.querySelector(s);
  const qa = (s) => Array.from(root.querySelectorAll(s));
  const h = (k, p) => NN.h(k, p);
  const t = (k, p) => NN.t(k, p);
  const ic = (k, cls) => '<svg class="icon' + (cls ? ' ' + cls : '') + '" aria-hidden="true"><use href="#tx-i-' + k + '"/></svg>';
  const thangNay = () => EPL.homNay().slice(0, 7);
  const nhanThang = (m) => m.slice(5, 7) + '/' + m.slice(0, 4);

  /* ================================================================ hàng đợi khi mất mạng (giữ như màn cũ)
   * Người nhận ký ngay trên điện thoại tài xế; phiếu gom thì tài xế báo cân ở mỏ. Mất mạng vẫn làm được: lần gửi nằm
   * trong hàng đợi của máy (localStorage, ảnh đã nén), có mạng lại thì tự gửi; `ma_gui` giúp máy chủ không ghi hai lần
   * khi gửi lại. Mỗi lần gửi mang `loai` ('giao_nhan' · 'can_mo'); lần gửi cũ không có `loai` là giao nhận. */
  const uid = () => (EPL.AUTH.user ? EPL.AUTH.user.id : 'x');
  const K_HANG = () => 'epl_lao_giao_nhan_' + uid(), K_DS = () => 'epl_lao_pct_ds_' + uid(), K_SO = () => 'epl_lao_pct_so_' + uid();
  const K_DIEM = () => 'epl_lao_pct_diem_' + uid();          // danh sách trạm dầu — khai dầu lúc mất mạng (06/10)
  let henGui = null;                                          // nhịp 30 giây thử gửi hàng đợi / điểm GPS chờ (06/10)
  const doc = (k, md) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : md; } catch (e) { return md; } };
  const ghi = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } };
  const hangDoi = () => doc(K_HANG(), []);
  const loaiGui = (x) => x.loai || 'giao_nhan';
  const choGui = (id, loai = 'giao_nhan') => hangDoi().some(x => x.trip_id === id && loaiGui(x) === loai);
  const laMatMang = (e) => !(e instanceof EPL.LoiAPI) || !e.status;
  /* 06/10 (chủ dự án: "làm hàng đợi mất mạng luôn"): thêm XUẤT PHÁT · BÁO HỎNG · KHAI ĐỔ DẦU vào cùng hàng đợi, cùng cách — lần bấm
   * lúc mất mạng nằm trong máy kèm `luc` (GIỜ MÁY lúc bấm = thời điểm thật) và `ma_gui` (khoá thao tác); có mạng lại tự gửi theo
   * đúng thứ tự đã bấm; máy chủ ghi theo giờ máy và gửi lại không ghi trùng (routes/phieu.py · _lan_gui_tai_xe). Ba loại này gửi JSON
   * (không ảnh). Mất phiên (401) hay máy chủ đang khởi động lại (502–504) cũng giữ trong hàng — đăng nhập / có máy chủ lại thì gửi. */
  const LOAI_JSON = { xuat_phat: 'transport-status', bao_hong: 'bao-hong', khai_dau: 'bao-nhien-lieu' };
  const nenThuLai = (e) => laMatMang(e) || [401, 502, 503, 504].includes(e.status);
  const choCua = (p, loai) => (p ? hangDoi().filter(x => x.trip_id === p.id && loaiGui(x) === loai) : []);
  const choDi = (p) => !!p && p.transport_status === 'dispatched' && choGui(p.id, 'xuat_phat');   // đã bấm xuất phát, chờ gửi
  const maMoi = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  const sangBlob = (url) => { const [dau, b64] = url.split(','); const kieu = (dau.match(/:(.*?);/) || [])[1] || 'application/octet-stream';
    const bin = atob(b64); const u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i); return new Blob([u8], { type: kieu }); };

  /** Ảnh nén bằng hàm chung (js/nen_anh.js, ≤ 200 KB) rồi đổi sang dataURL — để nằm được trong hàng đợi khi mất mạng. */
  async function nenAnh(f) {
    const nen = await EPL.nenTep(f);
    const url = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(nen); });
    return { name: nen.name, type: nen.type, url };
  }
  /** Ô ký: vẽ bằng ngón tay / chuột (Pointer Events), nét mịn theo mật độ điểm ảnh của màn. */
  function oKy(cv) {
    let dangVe = false, co = false, truoc = null;
    const ctx = cv.getContext('2d');
    const dung = () => {
      const r = cv.getBoundingClientRect(), d = window.devicePixelRatio || 1;
      cv.width = Math.max(1, Math.round(r.width * d)); cv.height = Math.max(1, Math.round(r.height * d));
      ctx.setTransform(d, 0, 0, d, 0, 0); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, r.width, r.height);
      ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#11161b'; co = false;
    };
    const diem = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    cv.onpointerdown = (e) => { dangVe = true; truoc = diem(e); cv.setPointerCapture(e.pointerId); e.preventDefault(); };
    cv.onpointermove = (e) => { if (!dangVe) return; const p = diem(e); ctx.beginPath(); ctx.moveTo(...truoc); ctx.lineTo(...p); ctx.stroke(); truoc = p; co = true; e.preventDefault(); };
    cv.onpointerup = cv.onpointercancel = () => { dangVe = false; };
    return { dung, anh: () => (co ? cv.toDataURL('image/png') : null) };
  }
  function veAnh(khung, ds) {
    const o = q(khung);
    o.innerHTML = ds.map((a, i) => '<div class="a">' + (a.type.startsWith('image/') ? '<img src="' + a.url + '" alt="">' : '<span class="pdf">PDF</span>') +
      '<button type="button" class="x" data-bo-anh="' + i + '" aria-label="' + esc(t('delete')) + '">×</button></div>').join('');
    o.querySelectorAll('[data-bo-anh]').forEach(b => b.addEventListener('click', () => { ds.splice(+b.dataset.boAnh, 1); veAnh(khung, ds); }));
  }
  async function themAnh(input, ds, khung) {
    for (const f of [...input.files].slice(0, Math.max(0, 5 - ds.length))) {
      try { ds.push(await nenAnh(f)); } catch (loi) { EPL.baoLoi(loi); }
    }
    input.value = ''; veAnh(khung, ds);
  }
  async function guiMot(x) {
    if (LOAI_JSON[loaiGui(x)]) return API.post('/api/trips/' + x.trip_id + '/' + LOAI_JSON[loaiGui(x)], x.body);
    const fd = new FormData();
    Object.entries(x.truong).forEach(([k, v]) => { if (v !== null && v !== undefined) fd.append(k, v); });
    if (x.chu_ky) fd.append('chu_ky', sangBlob(x.chu_ky), 'chu-ky-' + x.ma_gui + '.png');
    (x.anh || []).forEach(a => fd.append('anh', sangBlob(a.url), a.name));
    return API.tep('/api/trips/' + x.trip_id + '/' + (loaiGui(x) === 'can_mo' ? 'bao-can-mo' : 'giao-nhan'), fd);
  }
  /** Gửi ngay; mất mạng thì cất vào hàng đợi của máy. Trả true khi xong (đã gửi hoặc đã cất). `hop`: hộp nhập đóng khi xong
   *  (xuất phát không có hộp — null). Còn thao tác CŨ HƠN đang chờ (của cùng phiếu) thì xếp sau luôn, không gửi vượt: máy chủ phải
   *  nhận "xuất phát" trước "báo hỏng" bấm sau nó. */
  async function guiHoacCat(x, hop, daGui) {
    const cat = () => {
      const hd = hangDoi(); hd.push(x);
      if (!ghi(K_HANG(), hd)) { EPL.toast(t('gh_day_bo_nho'), 'loi'); return false; }
      if (hop) q(hop).close();
      EPL.toast(t('gh_cho_gui'), 'ok'); ve();
      guiHangDoi().catch(() => {});                  // mạng chập chờn: thử gửi luôn cả hàng (đúng thứ tự)
      return true;
    };
    if (hangDoi().some(y => y.trip_id === x.trip_id)) return cat();
    try {
      await guiMot(x);
      if (hop) q(hop).close();
      EPL.toast(t(daGui), 'ok'); await tai();
      return true;
    } catch (e) {
      if (!nenThuLai(e)) { EPL.baoLoi(e); return false; }
      return cat();
    }
  }
  /** Có mạng lại (hoặc mở màn, hoặc mỗi 30 giây) → gửi hết hàng đợi theo thứ tự đã bấm. Lỗi nghiệp vụ (phiếu đã khoá, đã ký…) thì bỏ
   *  khỏi hàng và báo; mất mạng thì dừng, lần sau gửi tiếp từ chỗ đó. Một lượt gửi một lúc (`dangGuiHang`) — hai lượt chạy song song
   *  là gửi một thao tác hai lần. Mỗi thao tác xong là gỡ ngay khỏi hàng trong máy (thao tác mới bấm trong lúc gửi không bị mất). */
  let dangGuiHang = false;
  async function guiHangDoi() {
    if (dangGuiHang || !hangDoi().length) return;
    dangGuiHang = true;
    const dem = {};
    const go = (ma) => ghi(K_HANG(), hangDoi().filter(y => y.ma_gui !== ma));
    try {
      const da = new Set();                          // đọc lại hàng sau mỗi lần: thao tác vừa bấm trong lúc gửi cũng đi luôn, đúng thứ tự
      for (;;) {
        const x = hangDoi().find(y => !da.has(y.ma_gui)); if (!x) break;
        da.add(x.ma_gui);
        try { await guiMot(x); dem[loaiGui(x)] = (dem[loaiGui(x)] || 0) + 1; go(x.ma_gui); }
        catch (e) {
          if (nenThuLai(e)) break;
          go(x.ma_gui); EPL.toast(x.doc_no + ': ' + e.message, 'loi');
        }
      }
    } finally { dangGuiHang = false; }
    if (dem.giao_nhan) EPL.toast(t('gh_da_gui_hang', { n: dem.giao_nhan }), 'ok');
    if (dem.can_mo) EPL.toast(t('cm_da_gui_hang', { n: dem.can_mo }), 'ok');
    const nJson = (dem.xuat_phat || 0) + (dem.bao_hong || 0) + (dem.khai_dau || 0);
    if (nJson) EPL.toast(t('tx_da_gui_hang', { n: nJson }), 'ok');
    if (Object.keys(dem).length) await tai().catch(() => {});
    else if (root) ve();
  }

  /* ================================================================ số của một chuyến */
  function tamUng(p) {
    // Khoản tiền mặt tài xế cầm đi: EPL ứng, không phải từ kho. Trạng thái = mục IV. Máy chủ nói thẳng dòng nào là tiền mặt
    // tài xế cầm đi (tien_mat_tx, kể cả cách trả — Excel anh Khampla 29/09); bản lưu cũ trong máy chưa có cờ đó thì dùng luật cũ.
    // 06/10 (chạy thử kịch bản): dòng sinh từ BÁO CÁO DỌC ĐƯỜNG của tài xế (khai đổ dầu «tài xế trả tiền túi», báo hỏng «Tôi đã tự
    // trả») là tiền tài xế ứng ra sau khi xe đi — không phải tiền quỹ đưa lúc xe đi; chúng đã hiện riêng ở danh sách bên dưới
    // (sự cố / lần đổ dầu) và vào Tất toán ở cột Đã chi thật. Trước đây bị cộng vào «Đã nhận tiền» (CA-1: 880.000 thay vì 450.000).
    const tuBao = new Set((p.events || []).filter(e => e.expense_id && ['refuel', 'incident', 'repair'].includes(e.kind)).map(e => e.expense_id));
    const dong = (p.expenses || []).filter(d => !tuBao.has(d.id) && (d.tien_mat_tx !== undefined ? d.tien_mat_tx
      : (d.paid_by_epl && d.source !== 'kho' && !d.ghi_no && !d.toll_card_id && ['fuel', 'travel', 'other'].includes(d.section))));
    const r = { USD: p.rate_usd, THB: p.rate_thb, VND: p.rate_vnd, CNY: p.rate_cny || 3000, LAK: 1 };
    const tong = dong.reduce((a, d) => a + d.qty * d.unit_price * (r[d.currency] || 1), 0);
    return { co: dong.length > 0, tong, tt: (p.sections || {}).travel || 'wait' };
  }
  const dangChay = (p) => ['dispatched', 'transit'].includes(p.transport_status);
  const conMo = (p) => dangChay(p) || (p.transport_status === 'arrived' && !p.locked);
  const daXong = (p) => p.transport_status === 'arrived' || p.locked;
  const coCan = (p) => (p.weight_origin || 0) > 0;
  const daKy = (p) => !!(p.pod_signed || p.pod_no);
  const coTheBaoCan = (p) => p.kind === 'gom' && dangChay(p) && !p.locked && !choGui(p.id, 'can_mo')
    && ['wait', 'entered'].includes((p.sections || {}).trans || 'wait');
  const coTheGiao = (p) => p.kind === 'giao' && (['transit', 'arrived'].includes(p.transport_status) || choDi(p)) && !p.locked && !p.pod_signed && !choGui(p.id);
  const suKien = (p, loai) => (p.events || []).filter(e => loai.includes(e.kind));
  const phieuDN = (p) => (p._v || []).filter(v => v.status !== 'huy');
  const soLitDN = (v) => (v.status === 'da_cap' && v.granted_qty != null ? v.granted_qty : v.qty_l);
  const tenLoai = (p) => h(p.kind === 'gom' ? 'do_gom' : 'do_giao');
  const tenSuCo = (e) => t('inc_' + (e.incident_type || 'other'));
  const lopTT = (p) => p.transport_status === 'transit' ? 's-van' : p.transport_status === 'arrived' ? 's-giao' : 's-xuat';
  const hienCan = (p) => esc(so(p.weight_origin, 2)) + ' ' + h('ton');

  function chonMacDinh() {
    if (DS.some(p => p.id === CUR)) return;
    const x = DS.find(p => p.transport_status === 'transit') || DS.find(dangChay) || DS.find(conMo) || DS[0];
    CUR = x ? x.id : null;
  }
  /** Các bước của chuyến (mẫu: Nhận tạm ứng → Xuất phát → Báo cân / Giao hàng → Về tới), kèm dòng nhỏ dưới mỗi bước. */
  function cacBuoc(p, tu) {
    const di = p.transport_status !== 'dispatched' || choDi(p);
    const giua = p.kind === 'gom'
      ? { k: 'pct_b_can', xong: coCan(p) || choGui(p.id, 'can_mo'),
          phu: coCan(p) ? so(p.weight_origin, 2) + ' ' + t('ton') : choGui(p.id, 'can_mo') ? t('gh_cho_gui') : t('tx_s_bao_tan') }
      : { k: 'pct_b_giao', xong: daKy(p) || choGui(p.id),
          phu: daKy(p) ? t('gh_da_ky') : choGui(p.id) ? t('gh_cho_gui') : t('tx_s_ky_nhan') };
    const ds = [
      ...(tu.co ? [{ k: 'pct_b_tam_ung', xong: tu.tt === 'paid', phu: t(tu.tt === 'paid' ? 'tx_s_da_nhan' : 'tx_s_cho_chi') }] : []),
      { k: 'depart', xong: di, phu: choDi(p) ? t('tx_dang_cho_gui_1') : di ? t('tx_s_da_di') : t('tx_s_san_sang') },
      giua,
      { k: 'pct_b_ve', xong: p.transport_status === 'arrived',
        phu: p.transport_status === 'arrived' ? t('tx_s_da_toi') : p.back_date ? t('tx_s_da_bao_ve') : t('tx_s_bao_ve') },
    ];
    const dang = ds.findIndex(b => !b.xong);
    return { ds, dang: dang < 0 ? ds.length : dang };
  }
  /** Việc tiếp theo: {nut, act, ico, loi} · {nut, tat, ly, ico} (chưa làm được, nói vì sao) · {xong}. */
  function viecTiep(p, tu) {
    if (p.locked || (p.transport_status === 'arrived' && !coTheGiao(p))) return { xong: true };
    const can = coTheBaoCan(p) && !coCan(p);
    if (p.transport_status === 'dispatched' && !choDi(p)) {
      if (tu.co && tu.tt !== 'paid') return { nut: 'depart', tat: true, ly: 'depart_blocked', ico: 'lock' };
      if (can) return { nut: 'cm_nut', act: 'cm', ico: 'scale', loi: 'tx_n_can' };
      return { nut: 'depart', act: 'di', ico: 'truck', loi: 'tx_n_di' };
    }
    if (can) return { nut: 'cm_nut', act: 'cm', ico: 'scale', loi: 'tx_n_can' };
    if (coTheGiao(p)) return { nut: 'gh_nut', act: 'gh', ico: 'sign', loi: 'tx_n_gh' };
    // xuất phát đang chờ gửi (mất mạng, 06/10): bước tiếp là báo về — nhưng báo về cần mạng, nói rõ đang chờ gửi xuất phát
    if (choDi(p)) return { nut: 'report_back', tat: true, ly: 'tx_n_cho_di', ico: 'wifi' };
    if (p.transport_status === 'transit') return { nut: 'report_back', act: 've', ico: 'flag', loi: p.back_date ? 'tx_n_ve_lai' : 'tx_n_ve' };
    return { xong: true };
  }

  /* ================================================================ lời chào, ô số, tab */
  function veChao() {
    const u = EPL.AUTH.user || {}, p = DS.find(x => x.id === CUR), hd = hangDoi().length, gpsN = gpsCho().length;
    q('#tx-chao').innerHTML = h('tx_chao', { ten: u.full_name || u.username || '' });
    const chip = (noi, cls) => '<span class="info-chip' + (cls ? ' ' + cls : '') + '">' + noi + '</span>';
    // 06/10: chip mạng nói rõ "Đang chờ gửi (n)" / "Đã gửi hết"; điểm GPS giữ lúc mất sóng đếm riêng
    const mang = matMang ? t('tx_mat_mang_ngan') + (hd ? ' · ' + t('tx_dang_cho_gui_n', { n: hd }) : '')
      : hd ? t('tx_dang_cho_gui_n', { n: hd }) : t('tx_da_gui_het');
    q('#tx-chips').innerHTML =
      (p && p.truck_no ? chip(ic('truck', 'icon-sm') + esc(t('tx_xe_so', { xe: p.truck_no }))) : '') +
      (p && (p.plate_head || p.plate_trailer) ? chip('<span lang="lo">' + esc(p.plate_head || '—') + '</span><span class="sep">/</span><span lang="lo">' + esc(p.plate_trailer || '—') + '</span>') : '') +
      chip('<span class="x2-dot"></span>' + esc(mang), 'net-chip' + (matMang || hd ? ' offline' : '')) +
      (phieuChiaSe ? chip(ic('pin', 'icon-sm') + esc(t('tx_dang_chia_vt')) + (lanGuiCuoi ? ' · ' + esc(new Date(lanGuiCuoi).toTimeString().slice(0, 5)) : ''), 'net-chip') : '') +
      (gpsN ? chip(ic('pin', 'icon-sm') + esc(t('tx_gps_cho_n', { n: gpsN })), 'net-chip offline') : '');
    // đếm trên chi tiết phiếu (dòng chi): chi tiết các phiếu còn đang tải nền thì để "·", đừng hiện số thiếu
    const choChi = matMang || napDu ? DS.filter(dangChay).filter(x => { const tu = tamUng(x); return tu.co && tu.tt !== 'paid'; }).length : null;
    // còn đang tải nền: ba chấm nhấp nháy kèm chữ "Đang tải" khi rê chuột — trước đây một dấu "·" trơ trọi trông như lỗi (rà 01/10)
    const choSo = '<span class="x2-cho" role="img" title="' + esc(t('loading')) + '" aria-label="' + esc(t('loading')) + '"><i></i><i></i><i></i></span>';
    const o = (k, v, cls) => '<div class="stat' + (cls ? ' ' + cls : '') + '"><span>' + h(k, { thang: nhanThang(thangNay()) }) + '</span><strong>' + (v == null ? choSo : esc(so(v))) + '</strong></div>';
    q('#tx-so').innerHTML = o('tx_so_thang', SO.thang) + o('tx_so_mo', SO.mo) + o('tx_so_khoa', SO.khoa) + o('tx_so_cho_chi', choChi, choChi ? 'x2-warn' : '');
  }
  function veTab() {
    const p = DS.find(x => x.id === CUR);
    const tu = p ? tamUng(p) : { co: false };
    const nDau = p ? suKien(p, ['refuel']).length + phieuDN(p).filter(v => v.kind === 'fuel').length + choCua(p, 'khai_dau').length : 0;
    const nSuCo = p ? suKien(p, ['incident', 'repair']).length + choCua(p, 'bao_hong').length : 0;
    const nChi = (tu.co && tu.tt !== 'paid' ? 1 : 0) + (p ? suKien(p, ['incident']).filter(e => e.reported_cost && e.status === 'reported').length : 0);
    const ds = [
      ['trip', ic('truck', 'icon-sm') + h('tx_tab_chuyen'), null],
      ['history', h('tx_tab_lich_su'), SO.tat],
      ['costs', h('tx_tab_chi_phi'), nChi, 'x2-warn'],
      ['fuel', h('e_fuel'), nDau],
      ['issues', h('tx_tab_su_co'), nSuCo],
      ['truck', h('tx_tab_xe'), null],
    ];
    q('#tx-tabs').innerHTML = ds.map(([id, nhan, n, cls]) => '<button role="tab" type="button" id="tx-t-' + id + '" aria-controls="tx-p-' + id + '" data-tab="' + id + '" aria-selected="' + (TAB === id) + '"' + (TAB === id ? '' : ' tabindex="-1"') + '>' +
      nhan + (n != null ? ' <span class="tab-n' + (cls && n ? ' ' + cls : '') + '"' + (n ? '' : ' data-zero') + '>' + esc(so(n)) + '</span>' : '') + '</button>').join('');
    ['trip', 'history', 'costs', 'fuel', 'issues', 'truck'].forEach(id => { q('#tx-p-' + id).hidden = TAB !== id; });
    // điện thoại: dải tab cuộn ngang, tab đang chọn có thể nằm khuất bên phải — kéo nó vào tầm nhìn
    const dai = q('#tx-tabs'), chon = q('#tx-t-' + TAB);
    if (chon && dai.scrollWidth > dai.clientWidth) {
      const trai = chon.offsetLeft, phai = trai + chon.offsetWidth;
      if (trai < dai.scrollLeft) dai.scrollLeft = trai - 8;
      else if (phai > dai.scrollLeft + dai.clientWidth) dai.scrollLeft = phai - dai.clientWidth + 8;
    }
  }
  const trong = (ico, chu, phu) => '<div class="x2-empty"><span class="x2-empty-ico">' + ic(ico, 'icon-lg') + '</span><strong>' + h(chu) + '</strong>' + (phu ? '<p>' + h(phu) + '</p>' : '') + '</div>';
  /** Chưa có phiếu nào để hiện: lần tải đầu chưa xong thì nói "Đang tải…" — trước đây khung trắng hoặc báo "không có phiếu". */
  const chuaCo = (ico, phu) => '<div class="x2-card">' + (napXong ? trong(ico, 'no_my_slips', phu) : '<div class="x2-empty"><strong>' + h('loading') + '</strong></div>') + '</div>';

  /** Thẻ "Mất mạng vẫn báo được" (06/10): từng thao tác đang chờ gửi — việc gì, DO nào, bấm lúc mấy giờ (giờ máy) — và số điểm GPS
   *  giữ lúc mất sóng; nút «Gửi ngay» thử lại liền, không phải đợi trình duyệt tự báo có mạng. Hết chờ thì nói rõ cái gì được giữ. */
  const TEN_VIEC = { xuat_phat: 'depart', bao_hong: 'report_breakdown', khai_dau: 'df_declare', giao_nhan: 'gh_nut', can_mo: 'cm_nut' };
  function theHangDoi() {
    const hd = hangDoi(), gpsN = gpsCho().length;
    const gio = (x) => x.luc || (x.truong && x.truong.luc) || '';
    const ds = hd.map(x => '<li><b>' + h(TEN_VIEC[loaiGui(x)] || 'gh_nut') + '</b> · <span class="mono">' + esc(x.doc_no || '') + '</span>' +
      (gio(x) ? ' · ' + esc(EPL.ngayGio(gio(x))) : '') + ' <span class="x2-tag-sm x2-tag-amber">' + h('tx_dang_cho_gui_1') + '</span></li>').join('');
    return '<section class="x2-card offline-card"><span class="action-ico">' + ic('wifi') + '</span><div><strong>' + h('tx_mat_mang_van_bao') + '</strong>' +
      (hd.length || gpsN
        ? '<p>' + esc(t('tx_dang_cho_gui_n', { n: hd.length })) + (gpsN ? ' · ' + esc(t('tx_gps_cho_n', { n: gpsN })) : '') + '</p>' +
          (ds ? '<ul class="tx-cho-ds">' + ds + '</ul>' : '') +
          '<button class="btn-outline" type="button" data-act="gui-ngay"' + (dangGuiHang || dangGuiGPS ? ' disabled' : '') + '>' + ic('wifi', 'icon-sm') + h('tx_gui_ngay') + '</button>'
        : '<p>' + h('tx_hang_doi_trong2') + '</p>') + '</div></section>';
  }

  /* ================================================================ tab: Chuyến đang chạy */
  function veChuyen() {
    const o = q('#tx-p-trip'), p = DS.find(x => x.id === CUR);
    o.classList.remove('tx-dang-tai');
    if (!p) { o.innerHTML = chuaCo('truck', matMang ? 'gh_mat_mang' : ''); return; }
    const tu = tamUng(p), tiep = viecTiep(p, tu), xong = daXong(p), b = cacBuoc(p, tu);
    const tienDo = b.ds.length > 1 ? Math.min(b.dang, b.ds.length - 1) / (b.ds.length - 1) : 0;
    const vs = phieuDN(p), tuV = vs.find(v => v.kind === 'advance');
    const mo = DS.filter(conMo);
    // tài xế có thể có nhiều phiếu còn mở (DO kế tiếp đã lập sẵn): chuyển qua lại ngay trên đầu thẻ
    // (quá 5 phiếu thì đổi sang ô chọn cho gọn — hàng nút dài đẩy thẻ chuyến xuống dưới)
    const chon = mo.length > 1 || (mo.length && !mo.some(x => x.id === p.id))
      ? '<div class="tx-chon"><span>' + h('tx_phieu_dang_mo') + '</span>' + (mo.length > 5
        ? '<select class="select" id="tx-chon" aria-label="' + esc(t('tx_phieu_dang_mo')) + '">' + (mo.some(x => x.id === p.id) ? '' : '<option value="" selected>' + esc(p.doc_no) + '</option>') +
          mo.map(x => '<option value="' + esc(x.id) + '"' + (x.id === p.id ? ' selected' : '') + '>' + esc(x.doc_no + ' · ' + t('s_' + x.transport_status) + (x.destination ? ' · ' + x.destination : '')) + '</option>').join('') + '</select>'
        : '<div class="quick">' + mo.map(x => '<button type="button" data-chon="' + esc(x.id) + '" aria-pressed="' + (x.id === p.id) + '">' + esc(x.doc_no) + '</button>').join('') + '</div>') + '</div>'
      : '';
    const oBam = [];
    const nutO = (act, icon, k, phu, daLam, cls) => '<button class="action' + (cls ? ' ' + cls : '') + (daLam ? ' is-done' : '') + '" type="button"' + (act ? ' data-act="' + act + '"' : ' disabled') + '>' +
      '<span class="action-ico">' + ic(icon, 'icon-lg') + '</span><span><strong>' + h(k) + '</strong><small>' + h(phu) + '</small><span class="done-mark">' + h('tx_da_bao') + '</span></span></button>';
    // việc đã là nút lớn "Bước tiếp theo" thì không lặp lại thành ô bấm (rà 01/10: hai nút "Giao hàng hoàn tất" liền nhau,
    // thêm một hàng ô làm thẻ chuyến dài ra) — giống ô "Báo đã về" ở dưới
    if (p.kind === 'gom' && tiep.act !== 'cm' && (coTheBaoCan(p) || coCan(p) || choGui(p.id, 'can_mo')))
      oBam.push(nutO(coTheBaoCan(p) ? 'cm' : '', 'scale', 'cm_nut', 'tx_o_can', coCan(p) || choGui(p.id, 'can_mo')));
    if (p.kind === 'giao' && tiep.act !== 'gh' && (coTheGiao(p) || daKy(p) || choGui(p.id)))
      oBam.push(nutO(coTheGiao(p) ? 'gh' : daKy(p) ? 'bb' : '', 'sign', daKy(p) ? 'gh_xem' : 'gh_nut', 'tx_o_giao', daKy(p) || choGui(p.id)));
    if (!xong) oBam.push(nutO('dau', 'fuel', 'df_declare', 'tx_o_dau', suKien(p, ['refuel']).length > 0));
    if (p.transport_status === 'transit' && tiep.act !== 've') oBam.push(nutO('ve', 'flag', 'report_back', 'tx_o_ve', !!p.back_date));
    if (!xong) oBam.push(nutO('bao', 'alert', 'report_breakdown', 'tx_o_bao', false, 'x2-danger'));
    // nhãn "Mã QR" chỉ khi còn tờ DẦU chờ cấp — tờ tạm ứng không còn QR (01/10), chỉ còn tạm ứng chờ thì là "Xem phiếu đề nghị"
    if (vs.some(v => v.status === 'cho')) oBam.push(nutO('qr', 'qr', vs.some(v => v.kind === 'fuel' && v.status === 'cho') ? 'pct_qr' : 'tx_xem_de_nghi', 'tx_o_qr', false));
    if (p.transport_status === 'transit' || choDi(p)) oBam.push(nutO('gps', 'pin', phieuChiaSe === p.id ? 'gps_stop' : 'gps_share', 'tx_o_gps', phieuChiaSe === p.id));
    const fact = (k, v, cls) => '<div><dt>' + h(k) + '</dt><dd' + (cls ? ' class="' + cls + '"' : '') + '>' + v + '</dd></div>';
    const oCan = p.kind === 'gom'
      ? (coCan(p) ? fact('w_origin_gom', hienCan(p))
        : fact('w_origin_gom', h(choGui(p.id, 'can_mo') ? 'gh_cho_gui' : 'tx_chua_bao') + (coTheBaoCan(p) ? ' <button class="link-btn" type="button" data-act="cm">' + h('tx_bao_ngay') + '</button>' : ''), 'pending'))
      : fact('w_origin', coCan(p) ? hienCan(p) : '—');
    const log = (k, chu, ok, nut) => '<div class="log"><div><strong>' + h(k) + '</strong><small' + (ok ? ' class="x2-ok"' : '') + '>' + chu + '</small></div>' + (nut || '') + '</div>';
    const link = (act, nhan, cls) => act ? '<button class="link-btn' + (cls ? ' ' + cls : '') + '" type="button" data-act="' + act + '">' + h(nhan) + '</button>' : '';
    const doDau = suKien(p, ['refuel']), baoS = suKien(p, ['incident', 'repair']);
    const choDau = choCua(p, 'khai_dau'), choBao = choCua(p, 'bao_hong');      // bấm lúc mất mạng, đang chờ gửi (06/10)
    const themCho = (truoc, n) => (n ? (truoc ? truoc + ' · ' : '') + esc(t('tx_dang_cho_gui_n', { n })) : truoc);
    const buocTu = [['tx_v_gui', !!tuV || tu.tt !== 'wait'], ['tx_v_duyet', ['verified', 'booked', 'paid'].includes(tu.tt)], ['tx_v_nhan', tu.tt === 'paid']];
    const dangTu = buocTu.findIndex(x => !x[1]);
    o.innerHTML = chon + '<div class="layout">' +
      '<article class="x2-card trip">' +
        '<div class="trip-band"><div class="trip-top"><div class="trip-id">' +
            '<span class="label">' + h(dangChay(p) ? 'tx_chuyen_dang_chay' : 'tx_chuyen') + '</span><span class="code">' + esc(p.doc_no) + '</span>' +
            '<span class="x2-tag x2-tag-gold">' + tenLoai(p) + '</span><span class="status ' + lopTT(p) + '">' + h('s_' + p.transport_status) + '</span>' +
            (p.locked ? '<span class="lock">' + ic('lock') + h('s_locked') + '</span>' : '') + '</div>' +
          '<span class="trip-date">' + h('d_out') + ' <strong>' + esc(EPL.ngay(p.out_date || p.doc_date)) + '</strong></span></div>' +
          '<div class="x2-route"><div class="x2-route-end"><span>' + h('origin') + '</span><strong lang="lo">' + esc(p.origin || '—') + '</strong></div>' +
            '<div class="road" style="--p:' + tienDo.toFixed(3) + '" aria-hidden="true"><span class="pin a"></span><span class="x2-truck">' + ic('truck') + '</span><span class="pin b"></span></div>' +
            '<div class="x2-route-end to"><span>' + h('dest') + '</span><strong lang="lo">' + esc(p.destination || '—') + '</strong></div></div></div>' +
        '<ol class="steps" style="grid-template-columns:repeat(' + b.ds.length + ',minmax(0,1fr))">' + b.ds.map((x, i) => '<li class="step' + (x.xong ? ' done' : i === b.dang ? ' current' : '') + '"' + (i === b.dang ? ' aria-current="step"' : '') + '>' +
          '<div class="step-head"><span class="step-num">' + (x.xong ? ic('check', 'icon-sm') : i + 1) + '</span><span class="step-bar"></span></div>' +
          '<div><span class="step-title">' + h(x.k) + '</span><span class="step-sub">' + esc(x.phu) + '</span></div></li>').join('') + '</ol>' +
        '<dl class="facts">' + fact('truck_no', esc(p.truck_no || '—')) +
          fact('tx_dau_keo_ro_mooc', '<span lang="lo">' + esc(p.plate_head || '—') + ' / ' + esc(p.plate_trailer || '—') + '</span>') +
          fact('customer', '<span lang="lo">' + esc(p.customer_name || '—') + '</span>') + fact('d_out', esc(EPL.ngay(p.out_date || p.doc_date))) +
          oCan + (p.weight_dest != null ? fact('w_dest', esc(so(p.weight_dest, 2)) + ' ' + h('ton')) : fact('do_kind', tenLoai(p))) + '</dl>' +
        '<div class="next"><span class="next-label">' + h('pct_buoc_tiep') + '</span><div class="next-row">' +
          (tiep.xong
            ? '<button class="btn-go" type="button" disabled>' + ic('check') + '<span>' + h('tx_hoan_tat') + '</span></button><div class="notice x2-ok">' + ic('info', 'icon-lg') + '<span>' + h(p.locked ? 'pct_xong_khoa' : 'pct_xong') + '</span></div>'
            : '<button class="btn-go" type="button"' + (tiep.tat ? ' disabled' : ' data-act="' + tiep.act + '"') + '>' + ic(tiep.ico) + '<span>' + h(tiep.nut) + '</span></button>' +
              '<div class="notice' + (tiep.tat ? '' : ' x2-ok') + '">' + ic('info', 'icon-lg') + '<span>' + h(tiep.ly || tiep.loi) + '</span></div>') +
          '</div>' + (oBam.length ? '<div class="actions">' + oBam.join('') + '</div>' : '') + '</div>' +
      '</article>' +
      '<aside class="x2-side">' +
        '<section class="x2-card"><div class="x2-side-head"><h2>' + h('tx_tam_ung_chuyen') + '</h2>' +
          (tu.co ? '<span class="x2-tag-sm ' + (tu.tt === 'paid' ? 'x2-tag-green">' + h('advance_received') : 'x2-tag-amber">' + h('advance_pending')) + '</span>' : '') + '</div>' +
          (tu.co
            ? '<div class="money"><strong>' + esc(so(tu.tong)) + '</strong><span>LAK</span></div>' +
              '<ol class="vsteps">' + buocTu.map((x, i) => '<li class="' + (x[1] ? 'done' : i === dangTu ? 'current' : '') + '"><div class="vrail"><span class="vdot">' + (x[1] ? ic('check', 'icon-sm') : '') + '</span>' +
                (i < buocTu.length - 1 ? '<span class="vline"></span>' : '') + '</div><span>' + h(x[0]) + '</span></li>').join('') + '</ol>' +
              (tuV ? '<button class="btn-outline" type="button" data-qr="' + esc(tuV.id) + '">' + ic('qr', 'icon-sm') + h('tx_xem_de_nghi') + '</button>' : '')
            : '<p class="tx-it">' + h('tx_khong_tam_ung') + '</p>') +
          (vs.some(v => v.kind === 'fuel') ? '<div class="logs">' + vs.filter(v => v.kind === 'fuel').map(v => log('v_fuel',
            '<span lang="lo">' + esc(v.place_name || '') + '</span> · ' + esc(so(soLitDN(v), 0)) + ' L · ' + h('v_' + v.status), v.status === 'da_cap',
            v.status !== 'da_cap' ? '<button class="link-btn" type="button" data-qr="' + esc(v.id) + '">' + h('pct_mo_qr') + '</button>' : '')).join('') + '</div>' : '') +
        '</section>' +
        '<section class="x2-card"><h2>' + h('tx_da_khai') + '</h2><div class="logs">' +
          (p.kind === 'gom'
            ? log('w_origin_gom', coCan(p) ? hienCan(p) : h(choGui(p.id, 'can_mo') ? 'gh_cho_gui' : 'tx_chua_bao'), coCan(p), link(coTheBaoCan(p) ? 'cm' : '', 'tx_bao_can'))
            : log('gh_nut', daKy(p) ? h('gh_da_ky') + (p.pod_receiver ? ': <span lang="lo">' + esc(p.pod_receiver) + '</span>' : '') : h(choGui(p.id) ? 'gh_cho_gui' : 'tx_chua_ky'), daKy(p),
              coTheGiao(p) ? link('gh', 'tx_ky_ngay') : link(daKy(p) ? 'bb' : '', 'gh_xem'))) +
          log('e_fuel', themCho(doDau.length ? esc(t('tx_dau_n', { n: doDau.length, l: so(doDau.reduce((a, e) => a + (e.qty_l || 0), 0), 0) })) : choDau.length ? '' : h('tx_chua_do'), choDau.length),
            doDau.length > 0, link(xong ? '' : 'dau', 'tx_khai_dau')) +
          log('tx_tab_su_co', themCho(baoS.length ? esc(t('tx_bao_n', { n: baoS.length, loai: tenSuCo(baoS[baoS.length - 1]) })) : choBao.length ? '' : h('tx_khong_co'), choBao.length),
            false, link(xong ? '' : 'bao', 'report_breakdown', 'x2-danger')) +
        '</div></section>' + theHangDoi() +
      '</aside></div>';
    const oChon = q('#tx-chon');
    if (oChon) oChon.addEventListener('change', (e) => { if (e.target.value) chonPhieu(e.target.value); });
  }

  /* ================================================================ tab: Lịch sử phiếu (lọc, phân trang ở máy chủ) */
  const CHIP_TT = [['all', 'all'], ['transit', 's_transit'], ['dispatched', 's_dispatched'], ['arrived', 's_arrived'], ['khoa', 's_locked']];
  function duongLS(them, co) {
    const o = Object.assign({}, LS, them || {});
    const ds = ['co=' + (co || CO_TRANG), 'trang=' + o.trang];
    if (o.q) ds.push('q=' + encodeURIComponent(o.q));
    if (o.thang) ds.push('thang=' + o.thang);
    if (o.xe) ds.push('vehicle_id=' + encodeURIComponent(o.xe));
    if (o.loai !== 'all') ds.push('kind=' + o.loai);
    if (o.sap === 'cu') ds.push('sap=cu');
    if (o.tt === 'khoa') ds.push('locked=true');
    else if (o.tt !== 'all') ds.push('transport_status=' + o.tt);
    return '/api/trips?' + ds.join('&');
  }
  const demLS = (x) => (x.tong != null ? x.tong : x.length);
  async function taiLichSu() {
    LSDS = null; if (TAB === 'history') veLichSu();
    try {
      const [ds, ...dem] = await Promise.all([API.get(duongLS()), ...CHIP_TT.map(([k]) => API.get(duongLS({ tt: k, trang: 1 }, 1)))]);
      LSDS = ds; LSDEM = {}; CHIP_TT.forEach(([k], i) => { LSDEM[k] = demLS(dem[i]); });
    } catch (e) {
      if (!laMatMang(e)) { EPL.baoLoi(e); LSDS = []; }
      else {                                   // mất mạng: chỉ xem được các phiếu đã lưu trong máy
        const tim = LS.q.toLowerCase();
        const loc = DS.filter(p => (!tim || [p.doc_no, p.origin, p.destination, p.truck_no].join(' ').toLowerCase().includes(tim))
          && (LS.loai === 'all' || p.kind === LS.loai) && (LS.tt === 'all' || (LS.tt === 'khoa' ? p.locked : p.transport_status === LS.tt)));
        LSDS = loc; LSDS.ngoaiMang = true; LSDEM = {};
      }
    }
    if (root && TAB === 'history') veLichSu();
  }
  function veLichSu() {
    const o = q('#tx-p-history');
    const thang = [];
    for (let i = 0; i < 12; i++) { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i); thang.push(d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0')); }
    const xe = [...new Map(DS.filter(p => p.vehicle_id).map(p => [p.vehicle_id, p.truck_no || p.vehicle_id])).entries()];
    const ds = LSDS || [], tong = LSDS ? demLS(ds) : 0, soTrang = Math.max(1, Math.ceil(tong / CO_TRANG)), dau = (LS.trang - 1) * CO_TRANG;
    let pager = '<button type="button" data-trang="' + (LS.trang - 1) + '"' + (LS.trang <= 1 ? ' disabled' : '') + ' aria-label="‹">‹</button>';
    const tu = Math.max(1, Math.min(LS.trang - 2, soTrang - 4)), den = Math.min(soTrang, tu + 4);
    for (let i = tu; i <= den; i++) pager += '<button type="button" data-trang="' + i + '"' + (i === LS.trang ? ' aria-current="page"' : '') + '>' + i + '</button>';
    pager += '<button type="button" data-trang="' + (LS.trang + 1) + '"' + (LS.trang >= soTrang ? ' disabled' : '') + ' aria-label="›">›</button>';
    const coLoc = LS.q || LS.thang || LS.xe || LS.tt !== 'all' || LS.loai !== 'all';
    o.innerHTML = '<div class="x2-card history">' +
      '<div class="history-head"><div><h2>' + h('tx_tab_lich_su') + '</h2><p>' + h('tx_ls_mo_ta') + '</p></div>' +
        '<button class="btn-outline" type="button" data-act="xuat">' + ic('download', 'icon-sm') + h('tx_tai_ds') + '</button></div>' +
      '<div class="x2-toolbar">' +
        '<div class="search' + (LS.q ? ' has-value' : '') + '">' + ic('search') + '<input id="tx-ls-q" type="search" autocomplete="off" value="' + esc(LS.q) + '" placeholder="' + esc(t('tx_ls_tim')) + '" aria-label="' + esc(t('tx_ls_tim')) + '">' +
          '<button class="search-clear" type="button" data-act="xoa-q" aria-label="' + esc(t('delete')) + '">' + ic('x', 'icon-sm') + '</button></div>' +
        '<select class="select" id="tx-ls-thang" aria-label="' + esc(t('month')) + '"><option value="">' + esc(t('tx_moi_thang')) + '</option>' + thang.map(m => '<option value="' + m + '"' + (m === LS.thang ? ' selected' : '') + '>' + nhanThang(m) + '</option>').join('') + '</select>' +
        '<select class="select" id="tx-ls-xe" aria-label="' + esc(t('c_truck')) + '"><option value="">' + esc(t('tx_moi_xe')) + '</option>' + xe.map(([id, soXe]) => '<option value="' + esc(id) + '"' + (id === LS.xe ? ' selected' : '') + '>' + esc(soXe) + '</option>').join('') + '</select>' +
        '<div class="sort"><select class="select" id="tx-ls-sap" aria-label="' + esc(t('tx_sap_xep')) + '"><option value="moi">' + esc(t('tx_moi_truoc')) + '</option><option value="cu"' + (LS.sap === 'cu' ? ' selected' : '') + '>' + esc(t('tx_cu_truoc')) + '</option></select></div>' +
      '</div>' +
      '<div class="filters"><div class="chip-group">' + CHIP_TT.map(([k, nhan]) => '<button type="button" class="chip" data-ls-tt="' + k + '" aria-pressed="' + (LS.tt === k) + '">' + h(nhan) +
          (LSDEM[k] != null ? '<span class="x2-n">' + esc(so(LSDEM[k])) + '</span>' : '') + '</button>').join('') + '</div>' +
        '<div class="x2-seg" role="group">' + [['all', 'tx_moi_loai'], ['gom', 'do_gom'], ['giao', 'do_giao']].map(([k, nhan]) => '<button type="button" data-ls-loai="' + k + '" aria-pressed="' + (LS.loai === k) + '">' + h(nhan) + '</button>').join('') + '</div></div>' +
      (LSDS && LSDS.ngoaiMang ? '<div class="note tx-ls-note">' + ic('wifi', 'icon-sm') + '<span>' + h('tx_ls_ngoai_mang') + '</span></div>' : '') +
      '<div class="table-head" aria-hidden="true"><span>' + h('doc_no') + '</span><span>' + h('do_kind') + '</span><span>' + h('route') + '</span><span>' + h('c_truck') + '</span><span>' + h('d_out') + '</span><span>' + h('status') + '</span><span></span></div>' +
      '<div role="list">' + (LSDS === null ? '<div class="x2-empty"><strong>' + h('loading') + '</strong></div>'
        : ds.length ? ds.map(p => '<div class="trow" role="listitem" data-mo="' + esc(p.id) + '">' +
            '<span class="t-code">' + esc(p.doc_no) + '</span>' +
            '<span class="t-status"><span class="status ' + lopTT(p) + '">' + h('s_' + p.transport_status) + '</span>' + (p.locked ? '<span class="lock">' + ic('lock') + h('s_locked') + '</span>' : '') + '</span>' +
            '<span class="t-route" lang="lo"><span>' + esc(p.origin || '—') + '</span>' + ic('arrow') + '<span>' + esc(p.destination || '—') + '</span></span>' +
            '<span class="t-meta"><span class="t-type"><span class="type-tag type-' + esc(p.kind) + '">' + tenLoai(p) + '</span></span>' +
              '<span class="t-truck">' + ic('truck', 'icon-sm') + esc(p.truck_no || '—') + '</span><span class="t-date">' + esc(EPL.ngay(p.out_date || p.doc_date)) + '</span></span>' +
            '<button class="icon-btn" type="button" data-mo="' + esc(p.id) + '" aria-label="' + esc(p.doc_no) + '">' + ic('chev', 'icon-sm') + '</button></div>').join('')
          : '<div class="x2-empty"><span class="x2-empty-ico">' + ic('search', 'icon-lg') + '</span><strong>' + h('tx_ls_trong') + '</strong>' +
            (coLoc ? '<p>' + h('tx_ls_trong_goi_y') + '</p><button class="btn-primary" type="button" data-act="xoa-loc">' + h('tx_xoa_loc') + '</button>' : '') + '</div>') + '</div>' +
      '<div class="table-foot"><span>' + (tong ? h('tx_ls_dem', { tu: dau + 1, den: dau + ds.length, n: so(tong) }) : '') + '</span>' +
        (LSDS && !LSDS.ngoaiMang && soTrang > 1 ? '<div class="pager">' + pager + '</div>' : '') + '</div>' +
    '</div>';
    const tim = q('#tx-ls-q');
    tim.addEventListener('input', () => {
      tim.parentElement.classList.toggle('has-value', !!tim.value);
      clearTimeout(henTim);
      henTim = setTimeout(async () => {
        LS.q = tim.value.trim(); LS.trang = 1; await taiLichSu();
        const x = root && q('#tx-ls-q'); if (x) { x.focus(); x.setSelectionRange(x.value.length, x.value.length); }
      }, 350);
    });
    const doi = (id, truong) => q(id).addEventListener('change', (e) => { LS[truong] = e.target.value; LS.trang = 1; taiLichSu(); });
    doi('#tx-ls-thang', 'thang'); doi('#tx-ls-xe', 'xe'); doi('#tx-ls-sap', 'sap');
  }

  /* ================================================================ tab: Tạm ứng và chi phí · Nhiên liệu · Sự cố · Hồ sơ xe */
  const dongDs = (ico, tieuDe, phu, tien, cls) => '<div class="list-row' + (cls ? ' ' + cls : '') + '"><span class="action-ico">' + ic(ico) + '</span>' +
    '<div><strong>' + tieuDe + '</strong><small>' + phu + '</small></div><div class="amount">' + tien + '</div></div>';
  const tienHien = (v, tt) => esc(so(v)) + ' <small>' + esc(tt || 'LAK') + '</small>';
  const ttSuKien = (e) => h(e.status === 'reported' ? 'st_reported' : e.status === 'rejected' ? 'st_rejected' : 'st_approved');
  const dauPanel = (tieuDe, moTa, nut) => '<div class="panel-head"><div><h2>' + h(tieuDe) + '</h2><p>' + moTa + '</p></div>' + (nut || '') + '</div>';
  function veChiPhi() {
    const o = q('#tx-p-costs'), p = DS.find(x => x.id === CUR);
    if (!p) { o.innerHTML = chuaCo('wallet'); return; }
    const tu = tamUng(p), tong = {}, rows = [];
    const cong = (m, v) => { tong[m] = (tong[m] || 0) + (v || 0); };
    if (tu.co) { rows.push(dongDs('wallet', h('tx_tam_ung_chuyen'), h(tu.tt === 'paid' ? 'advance_received' : 'advance_pending'), tienHien(tu.tong, 'LAK'))); cong('LAK', tu.tong); }
    suKien(p, ['incident', 'repair']).filter(e => e.reported_cost != null).forEach(e => {
      if (e.status !== 'rejected') cong(e.currency || 'LAK', e.reported_cost);
      rows.push(dongDs('alert', esc(tenSuCo(e)), ttSuKien(e) + (e.paid_by_driver ? ' · ' + h('pct_da_tu_tra') : '') + (e.note ? ' · <span lang="lo">' + esc(EPL.chuTheo(e, 'note')) + '</span>' : ''),
        tienHien(e.reported_cost, e.currency), 'x2-danger'));
    });
    suKien(p, ['refuel']).forEach((e, i) => rows.push(dongDs('fuel', esc(t('tx_dau_lan', { n: i + 1 })), ttSuKien(e) + ' · ' + h('tx_gia_ke_toan'), esc(so(e.qty_l || 0, 0)) + ' <small>L</small>')));
    o.innerHTML = '<div class="x2-card">' + dauPanel('tx_tab_chi_phi', h('tx_chi_mo_ta', { so: p.doc_no })) +
      '<div class="list">' + (rows.join('') || trong('wallet', 'tx_chi_trong')) + '</div>' +
      (Object.keys(tong).length ? '<div class="sum">' + Object.entries(tong).map(([m, v]) => '<span>' + h('total') + ' ' + esc(m) + '<strong>' + esc(so(v)) + '</strong></span>').join('') + '</div>' : '') + '</div>';
  }
  function veNhienLieu() {
    const o = q('#tx-p-fuel'), p = DS.find(x => x.id === CUR);
    if (!p) { o.innerHTML = chuaCo('fuel'); return; }
    const xong = daXong(p), tenDiem = (id) => (DIEM.find(x => x.id === id) || {}).name || '';
    const rows = phieuDN(p).filter(v => v.kind === 'fuel').map(v => dongDs('qr', h('v_fuel') + ' · <span lang="lo">' + esc(v.place_name || '') + '</span>',
        h('v_' + v.status) + (v.status !== 'da_cap' ? ' · <button class="link-btn" type="button" data-qr="' + esc(v.id) + '">' + h('pct_mo_qr') + '</button>' : ''),
        esc(so(soLitDN(v), 0)) + ' <small>L</small>'))
      .concat(suKien(p, ['refuel']).map((e, i) => dongDs('fuel', esc(t('tx_dau_lan', { n: i + 1 })) + (e.place_id ? ' · <span lang="lo">' + esc(tenDiem(e.place_id)) + '</span>' : ''),
        ttSuKien(e) + (e.note ? ' · <span lang="lo">' + esc(EPL.chuTheo(e, 'note')) + '</span>' : ''), esc(so(e.qty_l || 0, 0)) + ' <small>L</small>')))
      // khai lúc mất mạng (06/10): nằm trong máy, đang chờ gửi — giờ là giờ máy lúc bấm
      .concat(choCua(p, 'khai_dau').map(x => dongDs('fuel', h('df_declare') + (x.body.place_id ? ' · <span lang="lo">' + esc(tenDiem(x.body.place_id)) + '</span>' : ''),
        h('tx_dang_cho_gui_1') + ' · ' + esc(EPL.ngayGio(x.luc)) + (x.body.note ? ' · <span lang="lo">' + esc(x.body.note) + '</span>' : ''),
        esc(so(x.body.qty_l || 0, 0)) + ' <small>L</small>', 'x2-cho-gui')));
    o.innerHTML = '<div class="x2-card">' + dauPanel('e_fuel', h('tx_dau_mo_ta'), xong ? '' : '<button class="btn-primary" type="button" data-act="dau">' + ic('fuel', 'icon-sm') + h('df_declare') + '</button>') +
      '<div class="list">' + (rows.join('') || trong('fuel', 'tx_dau_trong')) + '</div></div>';
  }
  function veSuCo() {
    const o = q('#tx-p-issues'), p = DS.find(x => x.id === CUR);
    if (!p) { o.innerHTML = chuaCo('alert'); return; }
    const xong = daXong(p), diem = (s) => ((p.route_stops || []).find(x => x.seq === s) || {}).name;
    const rows = choCua(p, 'bao_hong').map(x => dongDs('alert', esc(t('inc_' + (x.body.incident_type || 'other'))) + ' · ' + h('tx_dang_cho_gui_1'),
      '<span lang="lo">' + esc(x.body.note || '') + '</span>' + (x.body.can_run === false ? ' · <b>' + h('pct_phai_dung') + '</b>' : '') + ' · ' + esc(EPL.ngayGio(x.luc)),
      x.body.reported_cost != null ? tienHien(x.body.reported_cost, x.body.currency) : '<small>—</small>', 'x2-danger x2-cho-gui'))     // bấm lúc mất mạng (06/10)
      .concat(suKien(p, ['incident', 'repair']).map(e => dongDs('alert', esc(tenSuCo(e)) + ' · ' + ttSuKien(e),
      '<span lang="lo">' + esc(EPL.chuTheo(e, 'note')) + '</span>' + (e.stop_seq && diem(e.stop_seq) ? ' · <span lang="lo">' + esc(diem(e.stop_seq)) + '</span>' : '') +
        (e.can_run === false ? ' · <b>' + h('pct_phai_dung') + '</b>' : '') + (e.paid_by_driver ? ' · ' + h('pct_da_tu_tra') : '') + ' · ' + esc(EPL.ngayGio(e.ts)),
      e.reported_cost != null ? tienHien(e.reported_cost, e.currency) : '<small>—</small>', 'x2-danger')));
    o.innerHTML = '<div class="x2-card">' + dauPanel('tx_tab_su_co', h('tx_su_co_mo_ta'), xong ? '' : '<button class="btn-primary btn-danger" type="button" data-act="bao">' + ic('alert', 'icon-sm') + h('report_breakdown') + '</button>') +
      '<div class="list">' + (rows.join('') || trong('shield', 'tx_su_co_trong')) + '</div></div>';
  }
  function veXe() {
    const o = q('#tx-p-truck'), p = DS.find(x => x.id === CUR), u = EPL.AUTH.user || {};
    if (!p) { o.innerHTML = chuaCo('truck'); return; }
    const cungXe = DS.filter(x => x.vehicle_id && x.vehicle_id === p.vehicle_id);
    const km = Math.max(0, ...cungXe.map(x => Math.max(x.odo_back || 0, x.odo_out || 0)));
    const fact = (k, v, cls) => '<div><dt>' + h(k) + '</dt><dd' + (cls ? ' class="' + cls + '"' : '') + '>' + v + '</dd></div>';
    o.innerHTML = '<div class="x2-card">' + dauPanel('tx_tab_xe', h('tx_xe_mo_ta')) +
      '<dl class="facts x2-truck-facts">' + fact('truck_no', esc(p.truck_no || '—')) + fact('plate_head', '<span lang="lo">' + esc(p.plate_head || '—') + '</span>') +
        fact('plate_trailer', '<span lang="lo">' + esc(p.plate_trailer || '—') + '</span>') + fact('c_driver', '<span lang="lo">' + esc(u.full_name || '') + '</span>') +
        fact('tx_chuyen_xe_nay', esc(so(cungXe.length))) + fact('tx_km_gan_nhat', km ? esc(so(km)) + ' km' : h('tx_chua_co'), km ? '' : 'pending') + '</dl></div>';
  }

  /** Thanh tab dính ngay dưới thanh tiêu đề của khung — đo thật, vì chiều cao đổi theo ngôn ngữ và kiểu xem. */
  function datDinh() {
    if (!root) return;
    const cao = ['.topbar', '.tbar'].map(s => document.querySelector(s)).filter(el => el && el.offsetHeight && getComputedStyle(el).position === 'sticky').map(el => el.offsetHeight);
    root.style.setProperty('--tx-dinh', (cao.length ? Math.max(...cao) : 0) + 'px');
  }
  function ve() {
    if (!root) return;
    chonMacDinh(); datDinh();
    veChao(); veTab();
    if (TAB === 'trip') veChuyen();
    else if (TAB === 'history') { if (LSDS === null) taiLichSu(); else veLichSu(); }
    else if (TAB === 'costs') veChiPhi();
    else if (TAB === 'fuel') veNhienLieu();
    else if (TAB === 'issues') veSuCo();
    else veXe();
  }

  /* ================================================================ nạp dữ liệu */
  /** Chạy fn cho từng phần tử, tối đa `n` lượt gọi cùng lúc. Bắn hết một lúc (admin thấy mọi phiếu đang chạy: ~130 lượt)
   *  làm máy chủ DB ở xa hết giờ kết nối (lỗi thật khi chạy bộ kiểm 30/09). Đo 01/10 trên máy thử, 45 phiếu: 3 lượt cùng
   *  lúc 19 s không lỗi · 6 lượt 20–28 s, DB cắt 2/45 kết nối · 10 lượt 25 s, cắt 4/45 — nên 3 là đủ nhanh và không rớt. */
  async function theoLo(ds, n, fn) {
    const ra = new Array(ds.length);
    let i = 0;
    await Promise.all(Array.from({ length: Math.min(n, ds.length) }, async () => {
      while (i < ds.length) { const j = i++; ra[j] = await fn(ds[j], j); }
    }));
    return ra;
  }
  /** Chi tiết một phiếu, kèm phiếu đề nghị (mã QR) khi chuyến còn mở — lưu cùng bản trong máy để mất mạng vẫn đưa QR cho
   *  người cấp quét. `_du`: đủ trường (diễn biến, dòng chi…), không phải bản tóm tắt của danh sách. */
  async function chiTiet(p) {
    const x = await API.get('/api/trips/' + p.id);
    if (p._ngoai) x._ngoai = true;
    if (conMo(x)) x._v = await API.get('/api/trips/' + p.id + '/vouchers').catch(() => []);
    x._du = true;
    return x;
  }
  const thayPhieu = (x) => { DS = DS.map(p => (p.id === x.id ? x : p)); };
  async function tai() {
    const luot = ++luotTai;
    try {
      // Một năm mỗi tài xế ~700 phiếu: chỉ nạp MỌI phiếu còn chạy + 15 phiếu gần nhất (không phải cả năm, rồi mỗi
      // phiếu một lượt gọi nữa — trên điện thoại ngoài đường là đứng hình). Phiếu cũ hơn mở từ tab Lịch sử.
      const m = thangNay();
      const [chay, gan, sThang, sMo, sKhoa, sTat] = await Promise.all([
        API.get('/api/trips?transport_status=dispatched,transit&co=50'), API.get('/api/trips?co=15'),
        API.get('/api/trips?thang=' + m + '&co=1'), API.get('/api/trips?locked=false&co=1'),
        API.get('/api/trips?locked=true&thang=' + m + '&co=1'), API.get('/api/trips?co=1')]);
      if (luot !== luotTai) return;
      const ds = [...chay, ...gan.filter(p => !chay.some(x => x.id === p.id))];
      const them = DS.filter(p => p._ngoai && !ds.some(x => x.id === p.id));      // phiếu cũ đang mở từ tab Lịch sử
      // Vẽ NGAY khi có chi tiết của phiếu đang xem; chi tiết các phiếu khác tải nền (taiNen). Rà 01/10: tx01 có 42 phiếu,
      // chờ đủ chi tiết mọi phiếu (mỗi lượt ~1 s, 3 lượt cùng lúc) thì màn trắng 6–11 s, mỗi lần báo xong lại chờ chừng ấy.
      // Trong lúc chờ, phiếu nào đã có chi tiết từ lần trước thì giữ bản đó, còn lại là bản tóm tắt của danh sách.
      const cu = new Map(DS.map(p => [p.id, p]));
      DS = [...ds.map(p => (cu.has(p.id) && cu.get(p.id)._du ? cu.get(p.id) : p)), ...them];
      SO = { thang: demLS(sThang), mo: demLS(sMo), khoa: demLS(sKhoa), tat: demLS(sTat) };
      chonMacDinh();
      const dang = DS.find(p => p.id === CUR);
      if (dang) { const x = await chiTiet(dang); if (luot !== luotTai) return; thayPhieu(x); }
      matMang = false;                     // napDu giữ nguyên: các phiếu khác vẫn là bản chi tiết của lần trước
      LSDS = null;
    } catch (e) {
      if (luot !== luotTai) return;
      if (!laMatMang(e)) throw e;
      DS = doc(K_DS(), []); SO = doc(K_SO(), {}); matMang = true;
    }
    napXong = true;
    ve();
    if (!matMang) taiNen(luot);
  }
  /** Chi tiết các phiếu còn lại, chạy nền (3 lượt cùng lúc — xem theoLo); xong thì lưu bản trong máy cho lúc mất mạng.
   *  Chỉ vẽ lại lời chào + ô số (ô "Tạm ứng chờ chi" cần dòng chi của mọi phiếu): vẽ lại cả màn thì ô tìm ở tab Lịch sử
   *  đang gõ dở sẽ mất chữ. Mất mạng giữa chừng thì thôi — giữ bản đang có, lần tải sau làm tiếp. */
  async function taiNen(luot) {
    const dangXem = CUR;
    try {
      const ra = await theoLo(DS.filter(p => p.id !== dangXem), 3, p => chiTiet(p).catch(e => { if (laMatMang(e)) throw e; return null; }));
      if (luot !== luotTai || !root) return;
      ra.forEach(x => { if (x && x.id !== CUR) thayPhieu(x); });
      napDu = true;
      ghi(K_DS(), DS); ghi(K_SO(), SO);
      veChao();
    } catch (e) { /* mất mạng giữa chừng */ }
  }
  /** Chuyển sang phiếu khác (nút trên đầu thẻ, ô chọn). Phiếu mới chỉ có bản tóm tắt thì lấy chi tiết trước khi vẽ — bản tóm
   *  tắt không có diễn biến, dòng chi, phiếu đề nghị, thẻ sẽ báo sai "chưa khai". Mất mạng thì lấy bản lưu trong máy. */
  async function chonPhieu(id) {
    CUR = id;
    const p = DS.find(x => x.id === id);
    if (p && !p._du) {
      q('#tx-p-trip').classList.add('tx-dang-tai');
      qa('#tx-p-trip [data-chon]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.chon === id)));
      try { thayPhieu(await chiTiet(p)); } catch (e) {
        const luu = doc(K_DS(), []).find(x => x.id === id);
        if (luu) thayPhieu(luu); else if (!laMatMang(e)) EPL.baoLoi(e);
      }
      if (!root || CUR !== id) return;                 // đã bấm sang phiếu khác trong lúc chờ
    }
    ve();
  }
  async function moPhieu(id) {
    const co = DS.find(p => p.id === id);
    if (!co || !co._du) {
      try {
        const x = await chiTiet(co || { id, _ngoai: true });
        if (co) thayPhieu(x); else DS.push(x);
      } catch (e) { if (!co) return EPL.baoLoi(e); }
    }
    CUR = id; TAB = 'trip'; ve();
    const tab = q('#tx-tabs'); if (tab) tab.scrollIntoView({ block: 'nearest' });
  }

  /* ================================================================ thao tác trên chuyến */
  const PHIEU = () => DS.find(x => x.id === CUR);
  const bat = (sel, tren) => qa(sel).forEach(b => b.setAttribute('aria-pressed', String(b === tren)));
  const chonTrong = (sel, attr) => { const b = q(sel + ' [aria-pressed="true"]'); return b ? b.dataset[attr] : null; };
  const loiO = (o, co) => { const f = q(o).closest('.x2-field'); if (f) f.classList.toggle('invalid', !!co); return !co; };
  const moTam = (id) => { const d = q(id); qa(id + ' .x2-field.invalid').forEach(f => f.classList.remove('invalid')); NN.apDung(d); d.showModal(); return d; };
  const dongPhieu = (p) => esc(p.doc_no) + ' · <span lang="lo">' + esc(p.origin || '') + '</span> → <span lang="lo">' + esc(p.destination || '') + '</span>';

  /** Một thao tác gửi JSON qua hàng đợi (06/10): `luc` = giờ máy LÚC BẤM (thời điểm thật, máy chủ ghi theo giờ này), `ma_gui` = khoá
   *  thao tác (gửi lại không ghi trùng). Còn mạng thì gửi ngay như trước; mất mạng thì nằm trong máy, có mạng tự gửi. */
  const thaoTac = (loai, p, body) => {
    const ma = maMoi(), luc = new Date().toISOString();
    return { loai, trip_id: p.id, doc_no: p.doc_no, ma_gui: ma, luc, body: Object.assign({}, body, { ma_gui: ma, luc }) };
  };
  async function xuatPhat() {
    const p = PHIEU(); if (!p || choDi(p)) return;
    if (!await EPL.hoi(t('depart'), h('tx_hoi_xuat_phat', { so: p.doc_no }))) return;
    await guiHoacCat(thaoTac('xuat_phat', p, { status: 'transit' }), null, 'saved');
  }

  // ---- báo cân ở mỏ (phiếu gom, 29/09): số tấn theo phiếu cân + ảnh phiếu (không bắt buộc — phiếu nhập tay được)
  let ANH_CM = [];
  function moCanMo() {
    const p = PHIEU(); if (!p) return;
    ANH_CM = [];
    moTam('#tx-d-can');
    q('#tx-can-phieu').innerHTML = dongPhieu(p);
    q('#tx-can-tan').value = p.weight_origin || ''; q('#tx-can-ghi').value = '';
    veAnh('#tx-can-xem-anh', ANH_CM);
    q('#tx-can-tan').focus();
  }
  async function guiCanMo() {
    const p = PHIEU(); if (!p) return;
    const tan = EPL.doc(q('#tx-can-tan').value);
    if (!loiO('#tx-can-tan', !(tan > 0))) return q('#tx-can-tan').focus();
    const x = { loai: 'can_mo', trip_id: p.id, doc_no: p.doc_no, ma_gui: maMoi(), anh: ANH_CM.slice(),
      truong: { tan: String(tan), ghi_chu: q('#tx-can-ghi').value.trim(), luc: new Date().toISOString(), ma_gui: '' } };
    x.truong.ma_gui = x.ma_gui;
    const nut = q('#tx-d-can [type="submit"]'); nut.disabled = true;
    try { await guiHoacCat(x, '#tx-d-can', 'cm_da_gui'); } finally { nut.disabled = false; }
  }

  // ---- giao hàng hoàn tất: người nhận ký ngay trên máy tài xế (chốt 24/09)
  let KY = null, ANH = [], VT = null;
  function moGiaoHang() {
    const p = PHIEU(); if (!p) return;
    ANH = []; VT = null;
    moTam('#tx-d-gh');
    q('#tx-gh-phieu').innerHTML = esc(p.doc_no) + ' · <span lang="lo">' + esc(p.customer_name || '') + '</span> · <span lang="lo">' + esc(p.destination || '') + '</span>';
    q('#tx-gh-ten').value = p.pod_receiver || ''; q('#tx-gh-sdt').value = p.pod_phone || ''; q('#tx-gh-ghi').value = '';
    bat('#tx-gh-tt button', q('#tx-gh-tt [data-tt="du"]'));
    veAnh('#tx-gh-xem-anh', ANH);
    KY = oKy(q('#tx-gh-canvas')); requestAnimationFrame(() => KY.dung());
    const gps = q('#tx-gh-gps'); gps.className = 'tx-gps-dong'; gps.innerHTML = ic('pin', 'icon-sm') + esc(t('gh_gps_dang'));
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((vt) => {
        VT = { lat: vt.coords.latitude, lng: vt.coords.longitude };
        gps.className = 'tx-gps-dong co'; gps.innerHTML = ic('pin', 'icon-sm') + esc(t('gh_gps_co') + ' · ' + VT.lat.toFixed(5) + ', ' + VT.lng.toFixed(5));
      }, () => { gps.innerHTML = ic('pin', 'icon-sm') + esc(t('gh_gps_khong')); }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    } else gps.innerHTML = ic('pin', 'icon-sm') + esc(t('gh_gps_khong'));
  }
  async function guiGiaoHang() {
    const p = PHIEU(); if (!p) return;
    const ten = q('#tx-gh-ten').value.trim(), chuKy = KY && KY.anh(), tt = chonTrong('#tx-gh-tt', 'tt') || 'du', ghiChu = q('#tx-gh-ghi').value.trim();
    if (!chuKy && !ANH.length) return EPL.toast(t('gh_thieu'), 'loi');
    if (chuKy && !ten) { q('#tx-gh-ten').focus(); return EPL.toast(t('gh_thieu_ten'), 'loi'); }
    if (tt !== 'du' && !ghiChu) { q('#tx-gh-ghi').focus(); return EPL.toast(t('gh_thieu_ghi'), 'loi'); }
    const x = { trip_id: p.id, doc_no: p.doc_no, ma_gui: maMoi(), chu_ky: chuKy, anh: ANH.slice(),
      truong: { nguoi_nhan: ten, sdt: q('#tx-gh-sdt').value.trim(), tinh_trang: tt, ghi_chu: ghiChu, luc: new Date().toISOString(),
        lat: VT ? String(VT.lat) : '', lng: VT ? String(VT.lng) : '', ma_gui: '' } };
    x.truong.ma_gui = x.ma_gui;
    const nut = q('#tx-d-gh [type="submit"]'); nut.disabled = true;
    try { await guiHoacCat(x, '#tx-d-gh', 'gh_da_gui'); } finally { nut.disabled = false; }
  }
  async function xemBienBan() {
    const p = PHIEU(); if (!p) return;
    let tep = [];
    try { tep = await API.get('/api/trips/' + p.id + '/tep'); } catch (e) { return EPL.baoLoi(e); }
    EPL.bienBan.in(p, tep);
  }

  // ---- báo đã về: ngày về + km về (C2.1). Máy chủ chỉ ghi hai số và đánh mốc tới điểm cuối; Bãi cân rồi bấm
  //      "Xe đã tới" mới là xong — nên nút này KHÔNG làm phiếu chuyển sang "đã tới".
  const ngayCach = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  function tinhKm() {
    const p = PHIEU(); if (!p) return true;
    const km = q('#tx-ve-km').value.trim() === '' ? null : EPL.doc(q('#tx-ve-km').value);
    const di = p.odo_out;
    q('#tx-ve-km-di').textContent = di != null ? so(di) + ' km' : '—';
    q('#tx-ve-km-qd').textContent = km != null && di != null && km >= di ? so(km - di) + ' km' : '—';
    const sai = km != null && di != null && km < di;
    q('#tx-ve-km-loi').textContent = sai ? t('tx_km_nho_hon', { km: so(di) }) : '';
    return loiO('#tx-ve-km', sai);
  }
  function datNgayNhanh() {
    const v = q('#tx-ve-ngay').value;
    qa('#tx-ve-nhanh [data-ngay]').forEach(b => b.setAttribute('aria-pressed', String(ngayCach(+b.dataset.ngay) === v)));
  }
  function moVe() {
    const p = PHIEU(); if (!p) return;
    moTam('#tx-d-ve');
    q('#tx-ve-phieu').innerHTML = dongPhieu(p);
    q('#tx-ve-ngay').value = p.back_date || ngayCach(0);
    q('#tx-ve-km').value = p.odo_back != null ? p.odo_back : '';
    datNgayNhanh(); tinhKm();
    q('#tx-ve-km').focus();
  }
  async function guiVe() {
    const p = PHIEU(); if (!p) return;
    if (!tinhKm()) return q('#tx-ve-km').focus();
    const body = { back_date: q('#tx-ve-ngay').value || ngayCach(0) };
    if (q('#tx-ve-km').value.trim() !== '') body.odo_back = EPL.doc(q('#tx-ve-km').value);
    const nut = q('#tx-d-ve [type="submit"]'); nut.disabled = true;
    try { await API.post('/api/trips/' + p.id + '/bao-ve', body); q('#tx-d-ve').close(); EPL.toast(t('report_back_ok'), 'ok'); await tai(); }
    catch (e) { EPL.baoLoi(e); } finally { nut.disabled = false; }
  }

  // ---- báo hỏng / sự cố: giống màn Theo dõi — có ô "Có chi tiền"; tổ sửa chữa duyệt thì vào mục V → phiếu chi
  const LOAI = [['breakdown', 'wrench'], ['tire', 'tire'], ['accident', 'alert'], ['delay', 'road'], ['held', 'shield'], ['other', 'dots']];
  function moBao() {
    const p = PHIEU(); if (!p) return;
    q('#tx-bao-loai').innerHTML = LOAI.map(([k, icon], i) => '<button type="button" class="tile" data-loai="' + k + '" aria-pressed="' + (i === 0) + '">' + ic(icon, 'icon-lg') + '<span>' + h('inc_' + k) + '</span></button>').join('');
    q('#tx-bao-diem').innerHTML = '<option value="">—</option>' + (p.route_stops || []).map(s => '<option value="' + s.seq + '"' + (s.seq === (p.stop_reached || 0) + 1 ? ' selected' : '') + '>' + s.seq + '. ' + esc(s.name) + '</option>').join('');
    q('#tx-bao-ghi').value = ''; q('#tx-bao-tien').value = ''; q('#tx-bao-co-chi').checked = false; q('#tx-bao-chi').hidden = true;
    bat('#tx-bao-chay button', q('#tx-bao-chay [data-chay="1"]'));
    bat('#tx-bao-tt button', q('#tx-bao-tt [data-tt="LAK"]'));
    bat('#tx-bao-tra button', q('#tx-bao-tra [data-tra="0"]'));
    moTam('#tx-d-bao');
  }
  async function guiBao() {
    const p = PHIEU(); if (!p) return;
    const ghiChu = q('#tx-bao-ghi').value.trim(), coChi = q('#tx-bao-co-chi').checked, tien = EPL.doc(q('#tx-bao-tien').value);
    const ok1 = loiO('#tx-bao-ghi', !ghiChu), ok2 = loiO('#tx-bao-tien', coChi && !(tien > 0));
    if (!ok1) return q('#tx-bao-ghi').focus();
    if (!ok2) return q('#tx-bao-tien').focus();
    const body = { incident_type: chonTrong('#tx-bao-loai', 'loai') || 'other', note: ghiChu, can_run: chonTrong('#tx-bao-chay', 'chay') !== '0' };
    if (q('#tx-bao-diem').value) body.stop_seq = +q('#tx-bao-diem').value;
    if (coChi) { body.reported_cost = tien; body.currency = chonTrong('#tx-bao-tt', 'tt') || 'LAK'; body.paid_by_driver = chonTrong('#tx-bao-tra', 'tra') === '1'; }
    const nut = q('#tx-d-bao [type="submit"]'); nut.disabled = true;
    try { await guiHoacCat(thaoTac('bao_hong', p, body), '#tx-d-bao', coChi ? 'tx_da_bao_chi' : 'saved'); }      // mất mạng → hàng đợi (06/10)
    finally { nut.disabled = false; }
  }

  // ---- khai đổ dầu DỌC ĐƯỜNG: chỉ trạm bán dầu bên ngoài (dầu kho công ty đi theo phiếu đề nghị xuất kho), không có giá
  function moDau() {
    const p = PHIEU(); if (!p) return;
    const ngoai = DIEM.filter(x => x.owner_type === 'ngoai');
    if (!ngoai.length) return EPL.toast(t('tx_chua_co_tram'), 'loi');
    q('#tx-dau-diem').innerHTML = ngoai.map(x => '<option value="' + esc(x.id) + '">' + esc(x.name) + (x.country === 'VN' ? ' · ' + esc(t('fp_vn2')) : '') + '</option>').join('');
    q('#tx-dau-lit').value = ''; q('#tx-dau-ghi').value = '';
    bat('#tx-dau-tt button', q('#tx-dau-tt [data-tt="VND"]'));
    moTam('#tx-d-dau');
    q('#tx-dau-lit').focus();
  }
  async function guiDau() {
    const p = PHIEU(); if (!p) return;
    const lit = EPL.doc(q('#tx-dau-lit').value);
    if (!loiO('#tx-dau-lit', !(lit > 0))) return q('#tx-dau-lit').focus();
    // C5.1 (anh Khampla 23/09): tài xế chỉ báo số lít và trạm; giá do KT kho xăng dầu nhập — không gửi giá
    const body = { qty_l: lit, place_id: q('#tx-dau-diem').value, currency: chonTrong('#tx-dau-tt', 'tt') || 'VND', note: q('#tx-dau-ghi').value.trim() };
    const nut = q('#tx-d-dau [type="submit"]'); nut.disabled = true;
    try { await guiHoacCat(thaoTac('khai_dau', p, body), '#tx-d-dau', 'saved'); }                                  // mất mạng → hàng đợi (06/10)
    finally { nut.disabled = false; }
  }

  // ---- phiếu đề nghị trên máy tài xế: tờ xuất kho nhiên liệu có mã QR cho thủ kho quét; tờ tạm ứng không QR (01/10) — đưa số DO cho quỹ
  function moQR(vid) {
    const p = PHIEU(); if (!p) return;
    const vs = phieuDN(p);
    if (!vs.length) return EPL.toast(t('v_none'), 'loi');
    const nhan = (v) => h(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung');
    const hien = (v) => {
      q('#tx-qr-tieu').innerHTML = h(v.kind === 'fuel' ? 'v_fuel' : 'voucher_payment');
      // Tờ tạm ứng KHÔNG còn mã QR (chủ dự án đồng ý 01/10): máy chủ gửi qr = null, ảnh QR trả 404 — tài xế lĩnh tiền ở quỹ kế
      // toán bằng số DO. Trước đây gán thẳng src = v.qr → ảnh vỡ và lỗi 404 "/null" ở bảng điều khiển. Tờ dầu giữ nguyên QR.
      const coQR = v.kind !== 'advance' && !!v.qr, anh = q('#tx-qr-anh'), goiY = q('#tx-d-qr .sheet-title p');
      anh.hidden = !coQR;
      if (coQR) anh.src = v.qr; else anh.removeAttribute('src');
      if (goiY) goiY.hidden = !coQR;
      q('#tx-qr-ma').innerHTML = coQR
        ? esc(v.doc_no) + '<br>' + h('v_code') + ': <b>' + esc(v.token) + '</b>' +
          (v.kind === 'fuel' ? '<br>' + esc(so(v.qty_l, 0)) + ' L · <span lang="lo">' + esc(v.place_name || '') + '</span>' : '')
        : esc(v.doc_no) + '<div class="tx-qr-quy">' + h('dnc_linh_quy', { do: p.doc_no }) + '</div>' +
          (v.hinh_thuc ? '<div class="tx-qr-bc">' + EPL.banChat('tam_ung', v.hinh_thuc, v.owner_name) + '</div>' : '');
      qa('#tx-qr-chon button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === v.id)));
    };
    q('#tx-qr-chon').innerHTML = vs.length > 1 ? vs.map(v => '<button type="button" data-v="' + esc(v.id) + '" aria-pressed="false">' + nhan(v) + (v.kind === 'fuel' ? ' · ' + esc(so(v.qty_l, 0)) + ' L' : '') + '</button>').join('') : '';
    qa('#tx-qr-chon button').forEach(b => b.addEventListener('click', () => hien(vs.find(v => v.id === b.dataset.v))));
    moTam('#tx-d-qr');
    hien(vs.find(v => v.id === vid) || vs.find(v => v.status === 'cho') || vs[0]);
  }

  /* ================================================================ chia sẻ vị trí
   * Không cần cài app từ chợ ứng dụng: trình duyệt điện thoại có sẵn Geolocation. Tài xế bấm bật, máy theo dõi vị trí
   * và gửi về; văn phòng thấy xe chạy thật trên bản đồ màn Theo dõi tuyến. Giữ trang mở thì mới gửi được — trình duyệt
   * dừng nền khi đóng tab, và đó là giới hạn phải nói thật với người dùng chứ không giấu. */
  const NHIP_GIAY = 25;                    // gửi thưa lại cho đỡ tốn pin và sóng
  /* 06/10 (chủ dự án: "làm hàng đợi mất mạng luôn"): mất sóng thì điểm KHÔNG bỏ nữa — giữ trong máy kèm GIỜ MÁY lúc lấy điểm (K_GPS,
   * tối đa GPS_TOI_DA điểm ≈ 20 giờ, đầy thì bỏ điểm cũ nhất), có sóng lại gửi bù theo lô GPS_LO điểm (POST /vi-tri/lo — máy chủ
   * ghi theo giờ máy, gửi lại không trùng; routes/vi_tri.py). Còn điểm chờ thì điểm mới cũng xếp sau cho đúng thứ tự. Đang chia sẻ
   * thì giữ màn hình sáng (Wake Lock — khoá máy là trình duyệt dừng trang, không lấy được điểm nào); bật chia sẻ được nhớ trong máy:
   * tải lại trang / quay lại màn là chia sẻ tiếp, không phải bấm lại. Đóng hẳn trình duyệt thì vẫn dừng — giới hạn của trang web. */
  const GPS_TOI_DA = 3000, GPS_LO = 200;
  const K_GPS = () => 'epl_lao_gps_cho_' + uid(), K_GPS_BAT = () => 'epl_lao_gps_bat_' + uid();
  const gpsCho = () => doc(K_GPS(), []);
  let khoaSang = null, dangGuiGPS = false, daBaoVt = false;
  function catDiem(tid, d) {
    const ds = gpsCho(); ds.push(Object.assign({ trip_id: tid }, d));
    if (ds.length > GPS_TOI_DA) ds.splice(0, ds.length - GPS_TOI_DA);
    if (!ghi(K_GPS(), ds)) { ds.splice(0, Math.ceil(ds.length / 2)); ghi(K_GPS(), ds); }      // bộ nhớ máy đầy: bỏ nửa cũ
  }
  /** Gửi bù điểm đã giữ, từng lô một phiếu (đúng thứ tự giờ). Lô gửi xong (kể cả bị máy chủ bỏ vì trùng / quá dày) thì gỡ khỏi máy;
   *  lỗi nghiệp vụ (phiếu không còn, không có quyền) thì bỏ lô đó; mất mạng thì dừng, lần sau gửi tiếp. */
  async function guiBuGPS() {
    if (dangGuiGPS || !gpsCho().length) return;
    dangGuiGPS = true;
    try {
      for (;;) {
        const ds = gpsCho(); if (!ds.length) break;
        const tid = ds[0].trip_id, lo = ds.filter(x => x.trip_id === tid).slice(0, GPS_LO);
        const khoa = new Set(lo.map(x => x.trip_id + '|' + x.ts));
        try { await API.post('/api/trips/' + encodeURIComponent(tid) + '/vi-tri/lo', { diem: lo.map(x => { const y = Object.assign({}, x); delete y.trip_id; return y; }) }); }
        catch (e) { if (nenThuLai(e)) break; }
        ghi(K_GPS(), gpsCho().filter(x => !khoa.has(x.trip_id + '|' + x.ts)));
      }
    } finally { dangGuiGPS = false; }
    if (root) veChao();
  }
  async function giuSang() {
    try {
      if (navigator.wakeLock && !khoaSang && document.visibilityState === 'visible') {
        khoaSang = await navigator.wakeLock.request('screen');
        khoaSang.addEventListener('release', () => { khoaSang = null; });
      }
    } catch (e) { khoaSang = null; }                // trình duyệt không cho (pin yếu, chưa bấm gì) — vẫn chia sẻ bình thường
  }
  function boSang() { try { if (khoaSang) khoaSang.release(); } catch (e) { /* bỏ qua */ } khoaSang = null; }
  /** Quay lại trang (mở khoá máy, chuyển tab về): giữ sáng lại (trình duyệt tự nhả khi ẩn) và gửi những gì đang chờ. */
  const khiHien = () => {
    if (document.visibilityState !== 'visible') return;
    if (phieuChiaSe) giuSang();
    guiHangDoi().catch(() => {}); guiBuGPS();
  };
  /** `quen` = xoá dấu "đang chia sẻ" trong máy (tài xế bấm ngưng, đăng xuất). Rời màn thì giữ dấu — quay lại là chia sẻ tiếp. */
  function ngungGPS(veLai = true, quen = true) {
    if (theoDoiId != null && navigator.geolocation) navigator.geolocation.clearWatch(theoDoiId);
    theoDoiId = null; phieuChiaSe = null; lanGuiCuoi = 0; boSang();
    if (quen) { try { localStorage.removeItem(K_GPS_BAT()); } catch (e) { /* bỏ qua */ } }
    if (root && veLai) ve();
  }
  function batGPS(id, nhac) {
    if (!navigator.geolocation) { if (nhac) EPL.toast(t('gps_nosupport'), 'loi'); return; }
    ngungGPS(false, false);
    phieuChiaSe = id; ghi(K_GPS_BAT(), id); daBaoVt = false;
    if (nhac) EPL.toast(t('gps_hint2'), 'ok');
    giuSang();
    theoDoiId = navigator.geolocation.watchPosition(async (vt) => {
      const gio = Date.now();
      if (gio - lanGuiCuoi < NHIP_GIAY * 1000) return;
      lanGuiCuoi = gio;
      const c = vt.coords;
      const d = { lat: c.latitude, lng: c.longitude, accuracy_m: c.accuracy,
        speed_kmh: c.speed == null ? null : Math.round(c.speed * 3.6 * 10) / 10, heading: c.heading,
        ts: new Date(vt.timestamp || gio).toISOString() };          // giờ máy lúc lấy điểm — thời điểm thật, máy chủ ghi theo giờ này
      if (navigator.onLine === false || gpsCho().length) {           // mất mạng, hoặc còn điểm cũ chờ → xếp sau cho đúng thứ tự
        catDiem(id, d);
        if (navigator.onLine !== false) guiBuGPS(); else if (root) veChao();
        return;
      }
      try {
        await API.post('/api/trips/' + id + '/vi-tri', d);
        if (root) veChao();
      } catch (e) {
        if (nenThuLai(e)) { catDiem(id, d); if (root) veChao(); return; }       // mất sóng giữa đường: giữ điểm, có sóng gửi bù
        EPL.baoLoi(e); ngungGPS();                                               // phiếu đã tới / không có quyền: ngưng
      }
    }, (loi) => {
      if (loi && loi.code === 1) { EPL.toast(t('gps_denied'), 'loi'); return ngungGPS(); }
      // chưa bắt được vệ tinh / hết giờ một lần đo (hầm, núi): đo tiếp, không ngưng — báo một lần cho tài xế biết
      if (loi && loi.code === 2 && !daBaoVt) { daBaoVt = true; EPL.toast(t('gps_nosupport'), 'loi'); }
    }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 });
    if (root) ve();
  }
  function batTatGPS() {
    const p = PHIEU(); if (!p) return;
    if (phieuChiaSe === p.id) return ngungGPS();
    batGPS(p.id, true);
  }

  /* ================================================================ bấm trên màn (uỷ quyền một chỗ) */
  const LAM = { di: xuatPhat, ve: moVe, cm: moCanMo, gh: moGiaoHang, bao: moBao, dau: moDau, gps: batTatGPS, qr: () => moQR(), bb: xemBienBan,
    xuat: () => EPL.xuatExcel(),
    'gui-ngay': () => { guiHangDoi().catch(() => {}); guiBuGPS(); if (root) ve(); },     // thẻ hàng đợi (06/10)
    'xoa-q': () => { LS.q = ''; LS.trang = 1; taiLichSu(); },
    'xoa-loc': () => { LS = Object.assign({}, LS_GOC, { sap: LS.sap }); taiLichSu(); } };
  function onClick(e) {
    const el = e.target.closest('[data-act],[data-qr],[data-tab],[data-mo],[data-chon],[data-ls-tt],[data-ls-loai],[data-trang]');
    if (!el || !root || !root.contains(el) || el.closest('dialog') || el.disabled) return;
    const d = el.dataset;
    if (d.act !== undefined) { if (LAM[d.act]) LAM[d.act](); return; }
    if (d.qr) return moQR(d.qr);
    if (d.tab) { TAB = d.tab; ve(); const b = q('#tx-t-' + TAB); if (b) b.focus(); return; }
    if (d.chon) return chonPhieu(d.chon);
    if (d.mo) return moPhieu(d.mo);
    if (d.lsTt) { LS.tt = d.lsTt; LS.trang = 1; return taiLichSu(); }
    if (d.lsLoai) { LS.loai = d.lsLoai; LS.trang = 1; return taiLichSu(); }
    if (d.trang) { LS.trang = +d.trang; return taiLichSu(); }
  }
  function onKey(e) {                       // mũi tên trái / phải chuyển tab (bàn phím, theo mẫu ARIA tablist)
    if (!e.target.matches('#tx-tabs [role="tab"]') || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    const ds = qa('#tx-tabs [role="tab"]'), i = ds.indexOf(e.target);
    const j = e.key === 'Home' ? 0 : e.key === 'End' ? ds.length - 1 : (i + (e.key === 'ArrowRight' ? 1 : -1) + ds.length) % ds.length;
    TAB = ds[j].dataset.tab; ve(); q('#tx-t-' + TAB).focus(); e.preventDefault();
  }
  function ganHop() {
    qa('dialog.sheet [data-close]').forEach(b => b.addEventListener('click', () => b.closest('dialog').close()));
    const nop = (id, fn) => q(id + ' form').addEventListener('submit', (e) => { e.preventDefault(); fn(); });
    nop('#tx-d-can', guiCanMo); nop('#tx-d-gh', guiGiaoHang); nop('#tx-d-ve', guiVe); nop('#tx-d-bao', guiBao); nop('#tx-d-dau', guiDau);
    nop('#tx-d-qr', () => q('#tx-d-qr').close());
    // nút bật một-trong-nhiều (tiền tệ, tình trạng hàng, còn chạy được, đã tự trả, loại sự cố)
    ['#tx-dau-tt', '#tx-bao-tt', '#tx-gh-tt', '#tx-bao-chay', '#tx-bao-tra', '#tx-bao-loai'].forEach(nhom =>
      q(nhom).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) bat(nhom + ' button', b); }));
    q('#tx-bao-co-chi').addEventListener('change', (e) => { q('#tx-bao-chi').hidden = !e.target.checked; if (e.target.checked) q('#tx-bao-tien').focus(); else loiO('#tx-bao-tien', false); });
    qa('[data-buoc-tan]').forEach(b => b.addEventListener('click', () => {
      const v = Math.max(0, Math.round((EPL.doc(q('#tx-can-tan').value) + +b.dataset.buocTan) * 100) / 100);
      q('#tx-can-tan').value = v ? v.toFixed(2) : ''; loiO('#tx-can-tan', false);
    }));
    q('#tx-ve-km').addEventListener('input', tinhKm);
    q('#tx-ve-ngay').addEventListener('change', datNgayNhanh);
    qa('#tx-ve-nhanh [data-ngay]').forEach(b => b.addEventListener('click', () => { q('#tx-ve-ngay').value = ngayCach(+b.dataset.ngay); datNgayNhanh(); }));
    ['#tx-can-tan', '#tx-dau-lit', '#tx-bao-ghi', '#tx-bao-tien'].forEach(id => q(id).addEventListener('input', () => loiO(id, false)));
    q('#tx-gh-xoa-ky').addEventListener('click', () => KY && KY.dung());
    q('#tx-can-anh').addEventListener('change', (e) => themAnh(e.target, ANH_CM, '#tx-can-xem-anh'));
    q('#tx-gh-anh').addEventListener('change', (e) => themAnh(e.target, ANH, '#tx-gh-xem-anh'));
  }

  EPL.modules['phieu-cua-toi'] = {
    async init(r) {
      root = r; CUR = null; TAB = 'trip'; DS = []; SO = {}; LS = Object.assign({}, LS_GOC); LSDS = null; LSDEM = {};
      napXong = false; napDu = false; DIEM = [];
      ganHop();
      root.addEventListener('click', onClick);
      root.addEventListener('keydown', onKey);
      ve();                                    // lời chào, tab và chữ "Đang tải…" hiện ngay, không để khung trắng
      // danh sách trạm dầu chỉ cần khi mở hộp khai dầu — tải song song, không bắt cả màn chờ. Lưu trong máy (06/10): mất mạng vẫn
      // khai dầu được (hàng đợi) thì phải có danh sách trạm để chọn
      API.get('/api/fuel-places').then(x => { DIEM = x || []; ghi(K_DIEM(), DIEM); }).catch(() => { if (!DIEM.length) DIEM = doc(K_DIEM(), []); });
      boNghe = () => { guiHangDoi().catch(() => {}); guiBuGPS(); };
      window.addEventListener('online', boNghe);
      window.addEventListener('resize', datDinh);
      document.addEventListener('visibilitychange', khiHien);
      // trình duyệt điện thoại không phải lúc nào cũng báo "có mạng lại" — cứ 30 giây thử gửi những gì đang chờ
      clearInterval(henGui); henGui = setInterval(() => { if (hangDoi().length) guiHangDoi().catch(() => {}); if (gpsCho().length) guiBuGPS(); }, 30000);
      await tai();
      // đang chia sẻ vị trí lúc rời màn / tải lại trang (06/10) → chia sẻ tiếp: quyền vị trí đã cho thì không hỏi lại
      const bat = doc(K_GPS_BAT(), null), pb = bat && DS.find(x => x.id === bat);
      if (bat && phieuChiaSe !== bat) {
        if (pb && (pb.transport_status === 'transit' || choDi(pb))) batGPS(bat, false); else if (!matMang) ngungGPS(false);
      }
      await guiHangDoi().catch(() => {});
      guiBuGPS();
    },
    /** Tải danh sách: đúng bộ lọc đang chọn ở tab Lịch sử phiếu (tối đa 500 dòng). */
    async xuatExcel() {
      const ds = await API.get(duongLS({ trang: 1 }, 500));
      return [EPL.xuatSheet(t('tx_tab_lich_su'),
        [t('doc_no'), t('do_kind'), t('origin'), t('dest'), t('c_truck'), t('d_out'), t('status'), t('s_locked')],
        ds.map(p => [p.doc_no, t(p.kind === 'gom' ? 'do_gom' : 'do_giao'), p.origin || '', p.destination || '', p.truck_no || '',
          EPL.oNgay(p.out_date || p.doc_date), t('s_' + p.transport_status), p.locked ? '✓' : '']))];
    },
    destroy() {
      // rời màn: dừng đo GPS nhưng giữ dấu "đang chia sẻ" (quay lại là chia sẻ tiếp); đăng xuất (không còn người dùng) thì quên hẳn
      ngungGPS(false, !EPL.AUTH.user); clearTimeout(henTim); clearInterval(henGui); henGui = null; luotTai++;   // lượt tải nền về sau thì bỏ
      if (boNghe) window.removeEventListener('online', boNghe);
      window.removeEventListener('resize', datDinh);
      document.removeEventListener('visibilitychange', khiHien);
      boNghe = null; root = null;
    },
    onLang() { if (root) ve(); },
  };
})();
