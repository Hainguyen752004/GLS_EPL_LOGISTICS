/* Thử giao diện EPL Lào trên jsdom, nối vào MÁY CHỦ THẬT đang chạy (mặc định :8010).
 *
 *   node kiem/thu_giao_dien.js [http://127.0.0.1:8010]
 *
 * Kiểm: đăng nhập từng vai → nạp đủ 14 module không lỗi → đổi 4 ngôn ngữ không lộ khoá thô
 * (kiểu "nav_dash") và không còn chữ "undefined" → mở phiếu thật, số trên màn khớp số máy chủ
 * → vai Bãi không thấy nút kiểm/chi. Không phải bộ kiểm đơn vị: nó cần máy chủ và DB thật.
 * Dùng jsdom của EPL_System (đã cài).
 */
const path = require('path');
const assert = require('assert');
const { JSDOM, ResourceLoader } = require(path.join(__dirname, '..', '..', 'EPL_System', 'frontend', 'node_modules', 'jsdom'));

const GOC = process.argv[2] || 'http://127.0.0.1:8010';
const MODULES = ['tong-quan', 'theo-doi', 'theo-doi-tuyen', 'phieu-xuat-xe', 'hoa-don', 'chung-tu',
  'phieu-cua-toi', 'cap-phat', 'xe-lien-ket', 'tien-tai-xe', 'tat-toan', 'nha-cung-cap', 'kho-hang', 'kho-nhien-lieu',
  'diem-do', 'kho-phu-tung', 'ban-hang', 'khach-hang', 'xe', 'tai-xe', 'tuyen-duong', 'quy-trinh', 'tai-khoan'];

/** Chỉ tải tài nguyên từ máy chủ mình; Google Fonts và mọi thứ ngoài trả rỗng. */
class ChiNoiBo extends ResourceLoader {
  fetch(url, options) {
    if (!url.startsWith(GOC)) return Promise.resolve(Buffer.from(''));
    return super.fetch(url, options);
  }
}

const cho = (ms) => new Promise(r => setTimeout(r, ms));
async function choDen(dk, mo_ta, toi_da = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < toi_da) { if (dk()) return; await cho(60); }
  throw new Error('Hết giờ chờ: ' + mo_ta);
}

async function main() {
  const html = await (await fetch(GOC + '/')).text();
  const dom = new JSDOM(html, { url: GOC + '/', runScripts: 'dangerously', resources: new ChiNoiBo(), pretendToBeVisual: true });
  const w = dom.window;
  // jsdom thiếu fetch và <dialog>.showModal — vá tối thiểu
  w.fetch = (u, o) => fetch(new URL(u, GOC).href, o);
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function (v) { this.returnValue = v || this.returnValue; this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); };
  const loiJS = []; w.addEventListener('error', e => loiJS.push(String(e.message || e.error)));
  w.console.error = (...a) => loiJS.push(a.join(' '));
  const d = w.document;
  /** Đổi hash rồi chờ đúng lượt nạp module đó xong (EPL.sanSang), không đoán bằng setTimeout. */
  async function di(hash) {
    const cu = w.EPL.sanSang;
    if (w.location.hash === hash) w.dispatchEvent(new w.HashChangeEvent('hashchange'));   // cùng hash thì trình duyệt không bắn sự kiện
    else w.location.hash = hash;
    await choDen(() => w.EPL.sanSang && w.EPL.sanSang !== cu, 'bắt đầu nạp ' + hash); await w.EPL.sanSang; await cho(80);
  }
  /** Chờ tới khi khung KHÔNG còn lượt nạp nào nữa. Đổi location.hash chỉ bắn hashchange ở lượt sau,
   *  nên phải để trống một nhịp rồi mới kết luận là đã xong, không thì đo đúng lúc màn còn trắng. */
  async function xongHet() {
    for (let i = 0; i < 60; i++) {
      const pr = w.EPL.sanSang;
      await pr; await cho(70);
      if (pr === w.EPL.sanSang) return;
    }
  }
  const goc = () => d.getElementById('noi-dung');

  // Một ký tự lạc trong CSS (có lần là một dấu nháy thừa) làm trình duyệt bỏ luôn cả khối quy tắc
  // ngay sau nó, mà màn vẫn dựng được nên bộ kiểm DOM không thấy gì. Soát thô tệp kiểu ở đây.
  {
    const css = await (await fetch(GOC + '/css/chung.css')).text();
    assert.strictEqual((css.match(/\{/g) || []).length, (css.match(/\}/g) || []).length, 'chung.css lệch ngoặc { }');
    const lac = css.split(/\r?\n/).map((l, i) => [i + 1, l.trim()]).filter(([, l]) => /^["']/.test(l));
    assert.deepStrictEqual(lac, [], 'chung.css có dòng bắt đầu bằng dấu nháy (ký tự lạc): ' + JSON.stringify(lac));
    ['.ln-nut{', '.tbar-phai .ln-nut{', '.lang button.active{', '.nav .muc{'].forEach(k =>
      assert.ok(css.includes(k), 'chung.css thiếu quy tắc ' + k));
    console.log('✓ tệp kiểu: ngoặc cân, không ký tự lạc, đủ các quy tắc chính');
  }

  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'màn đăng nhập tải tài khoản mẫu');
  // Lối tắt demo phải hiện ĐỦ tài khoản, và Admin Thà Bốc (vai chính của nhóm kho) phải đứng đầu nhóm
  // của nó — trước đây máy chủ trả theo chữ cái nên thabok rơi xuống cuối, bị khuất trong ô cuộn.
  {
    const ten = [...d.querySelectorAll('#acctList .person')].map(b => b.dataset.u);
    const may = await (await fetch(GOC + '/api/tai-khoan-mau')).json();
    assert.strictEqual(ten.length, may.length, `lối tắt phải có đủ ${may.length} tài khoản, đang có ${ten.length}`);
    assert.ok(ten.includes('thabok'), 'phải có tài khoản Admin Thà Bốc (thabok): ' + ten.join(','));
    const kho = ten.filter(u => ['thabok', 'khonl', 'khotb', 'khovc'].includes(u));
    assert.strictEqual(kho[0], 'thabok', 'Admin Thà Bốc phải đứng đầu nhóm Bãi và kho: ' + kho.join(','));
  }
  console.log('✓ màn đăng nhập: %d tài khoản mẫu · Admin Thà Bốc đứng đầu nhóm kho', d.querySelectorAll('#acctList .person').length);
  // Màn đăng nhập dựng theo bản mẫu đăng nhập anh gửi (đã bỏ khỏi dự án): nửa trái thương hiệu kèm sơ đồ tuyến, nửa phải
  // biểu mẫu và khung chọn nhanh gom theo nhóm vai.
  assert.ok(d.querySelector('#login .hero') && d.querySelector('#login .panel'),
    'màn đăng nhập phải có hai nửa: thương hiệu và biểu mẫu');
  assert.ok(d.querySelector('#login .hero__logo'), 'nửa trái phải có ảnh logo EPL');
  assert.ok(d.querySelector('#login svg.route'), 'nửa trái phải có sơ đồ tuyến');
  assert.ok(d.getElementById('lgMat'), 'màn đăng nhập phải có nút hiện/ẩn mật khẩu');
  assert.strictEqual(d.getElementById('lgP').type, 'password', 'mật khẩu mặc định phải ẩn');
  d.getElementById('lgMat').dispatchEvent(new w.Event('click'));
  assert.strictEqual(d.getElementById('lgP').type, 'text', 'bấm con mắt thì mật khẩu phải hiện');
  d.getElementById('lgMat').dispatchEvent(new w.Event('click'));
  assert.strictEqual(d.getElementById('lgP').type, 'password', 'bấm lần nữa thì mật khẩu phải ẩn lại');
  const goiY = [...d.querySelectorAll('#acctList .person')];
  assert.ok(goiY.length >= 10, 'phải gợi ý đủ tài khoản demo, đang có ' + goiY.length);
  assert.strictEqual(goiY[0].dataset.u, 'admin', 'gợi ý phải xếp quản trị lên đầu');
  assert.ok(goiY.some(b => b.dataset.u === 'tx01'), 'phải có tài khoản tài xế tx01');
  const nhom = [...d.querySelectorAll('#acctList .role__head')];
  assert.ok(nhom.length >= 4, 'tài khoản phải gom theo nhóm vai, đang có ' + nhom.length);
  assert.ok(nhom.every(x => x.textContent.trim() && !/^lg_g_/.test(x.textContent.trim())),
    'tên nhóm vai không được lộ khoá thô');
  console.log('✓ màn đăng nhập: hai nửa · logo · sơ đồ tuyến · %d thẻ gợi ý trong %d nhóm vai',
    goiY.length, nhom.length);

  // 0b. Bấm thẻ tài khoản rồi bấm NÚT đăng nhập — đúng đường người dùng đi. Trước đây bộ kiểm gọi
  // thẳng AUTH.dangNhap nên một lỗi ở nút (thiếu biến `dangBan`) lọt qua mà không ai biết.
  d.getElementById('lgU').value = 'admin';
  d.getElementById('lgP').value = 'sai-mat-khau';
  d.getElementById('lgBtn').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await choDen(() => !d.getElementById('lgErr').hidden, 'bấm nút với mật khẩu sai phải hiện lỗi');
  assert.ok(d.getElementById('app').hidden, 'sai mật khẩu thì không được vào ứng dụng');
  assert.ok(d.getElementById('lgErr').textContent.trim(), 'phải có câu báo lỗi, không để trống');
  console.log('✓ bấm nút với mật khẩu sai: hiện lỗi, không vào được');

  d.getElementById('lgP').value = '1234';
  d.getElementById('lgBtn').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await choDen(() => !d.getElementById('app').hidden, 'bấm nút với mật khẩu đúng phải vào được', 15000);
  await w.EPL.sanSang;
  console.log('✓ bấm nút với mật khẩu đúng: vào được ứng dụng');
  w.EPL.AUTH.dangXuat(false);
  await choDen(() => d.querySelectorAll('#acctList .person').length > 0, 'về lại màn đăng nhập');

  // 0c. Bấm thẳng vào thẻ tài khoản là vào luôn, không phải bấm nút nữa
  [...d.querySelectorAll('#acctList .person')].find(x => x.dataset.u === 'admin')
    .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await choDen(() => !d.getElementById('app').hidden, 'bấm thẻ tài khoản phải vào thẳng', 15000);
  console.log('✓ bấm thẻ tài khoản: vào thẳng, không cần bấm nút');

  // 1. đã ở trong ứng dụng với vai admin, đi hết module
  await choDen(() => !d.getElementById('app').hidden, 'vào ứng dụng');
  await w.EPL.sanSang;
  const nav = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
  assert.deepStrictEqual(nav, MODULES, 'thanh điều hướng phải đủ ' + MODULES.length + ' module đúng thứ tự');
  console.log('✓ admin: thanh điều hướng đủ %d module', nav.length);

  for (const m of MODULES) {
    await di('#/' + m);
    const chu = goc().textContent;
    assert.ok(!chu.includes(w.EPL.NN.t('err_generic')), 'module ' + m + ' báo lỗi: ' + chu.slice(0, 200));
    assert.ok(!/\bundefined\b|\bNaN\b/.test(chu), 'module ' + m + ' có chữ undefined/NaN');
    assert.ok(goc().querySelector('table, .kpis, .tq-kpis, .px-phieu, .pct-ds'), 'module ' + m + ' không có bảng/thẻ nào');
    console.log(`  ✓ ${m.padEnd(16)} ${chu.length} ký tự`);
  }

  // Màn Xe bản thiết kế lại: hai tab đầu kéo / rơ-moóc, thanh chip lọc, bảng, thẻ hồ sơ bên phải,
  // và hộp hồ sơ bảy tab. Số liệu lấy từ /api/vehicles và /api/trailers, không có gì viết cứng.
  {
    await di('#/xe');
    const gx = goc();
    const dsXe = await (await fetch(GOC + '/api/vehicles', { headers: { Authorization: 'Bearer ' + w.EPL.API.token() } })).json();
    assert.strictEqual(gx.querySelectorAll('#xe-tbl tbody tr').length, dsXe.length, 'bảng xe phải đủ số xe của máy chủ');
    assert.ok(gx.querySelectorAll('.xe-chip').length >= 6, 'phải có thanh chip lọc');
    assert.ok(gx.querySelector('.xe-head'), 'phải có thẻ hồ sơ xe bên phải');
    gx.querySelector('[data-act="open"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await choDen(() => !!goc().querySelector('.xe-modal'), 'mở hộp hồ sơ xe');
    const tabs = [...goc().querySelectorAll('.xe-modal [data-mt]')].map(b => b.dataset.mt);
    assert.deepStrictEqual(tabs, ['chung', 'phaply', 'kythuat', 'romooc', 'lich', 'sua', 'phieu'], 'hộp hồ sơ xe phải đủ bảy tab: ' + tabs);
    goc().querySelector('.xe-modal [data-mt="lich"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await choDen(() => goc().querySelectorAll('.xe-modal .xe-day').length === 7, 'tab Lịch xe phải vẽ đủ 7 ngày');
    goc().querySelector('.xe-modal [data-close]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    gx.querySelector('#xe-loai button[data-v="ro-mooc"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    const dsRM = await (await fetch(GOC + '/api/trailers', { headers: { Authorization: 'Bearer ' + w.EPL.API.token() } })).json();
    await choDen(() => goc().querySelectorAll('#xe-tbl tbody tr').length === dsRM.length, 'bảng rơ-moóc phải đủ số rơ-moóc của máy chủ');
    console.log('✓ màn Xe: %d đầu kéo · %d rơ-moóc · hộp hồ sơ 7 tab · lịch tuần 7 ngày', dsXe.length, dsRM.length);
  }

  // Tổng quan bản thiết kế lại: bốn ô số, thanh xem nhanh, dòng thời gian, hiệu suất xe, cơ cấu chi
  // — tất cả lấy từ /api/bao-cao/tong-quan và /api/bao-cao/xu-huong, không có số viết cứng.
  {
    await di('#/tong-quan');
    const g = goc();
    assert.strictEqual(g.querySelectorAll('.tq-kpi').length, 4, 'Tổng quan phải có đúng 4 ô số');
    assert.ok(g.querySelectorAll('.tq-chip').length >= 6, 'thanh xem nhanh phải có ít nhất 6 chip');
    assert.ok(g.querySelectorAll('#tq-gantt .row').length > 0, 'dòng thời gian phải có chuyến');
    assert.ok(g.querySelectorAll('.tq-veh').length > 0, 'hiệu suất xe phải có xe');
    assert.ok(g.querySelectorAll('#tq-co-cau .row').length === 4, 'cơ cấu chi phải đủ 4 mục');
    const xh = await (await fetch(GOC + '/api/bao-cao/xu-huong?thang=' + g.querySelector('#tq-thang').value,
      { headers: { Authorization: 'Bearer ' + w.EPL.API.token() } })).json();
    assert.strictEqual(g.querySelectorAll('#tq-gantt .row').length, xh.dong_thoi_gian.length, 'số dòng thời gian phải khớp máy chủ');
    assert.ok(g.querySelector('#tq-ops').textContent.includes(String(xh.van_hanh.nguong_ngay)),
      'nhãn "đúng hạn" phải lấy ngưỡng ngày từ máy chủ, không viết cứng');
    console.log('✓ tổng quan: 4 ô số · %d chip · %d dòng thời gian · %d xe · ngưỡng đúng hạn %d ngày',
      g.querySelectorAll('.tq-chip').length, xh.dong_thoi_gian.length, g.querySelectorAll('.tq-veh').length, xh.van_hanh.nguong_ngay);
  }
  // Co giãn theo zoom: đổi bề rộng cửa sổ (đúng thứ trình duyệt làm khi zoom) thì --ty-le phải đổi theo
  const tyLe = () => Number(d.documentElement.style.getPropertyValue('--ty-le'));
  assert.ok(tyLe() > 0, 'phải đặt --ty-le ngay khi tải: ' + tyLe());
  const doTyLe = (w2, h2) => { w.innerWidth = w2; w.innerHeight = h2 === undefined ? Math.round(w2 * 9 / 16) : h2; w.EPL.coGian(); return tyLe(); };
  assert.strictEqual(doTyLe(1600, 900), 1, 'đúng khung thiết kế 1600×900 thì tỷ lệ phải là 1');
  assert.ok(doTyLe(2400, 1350) > 1, 'zoom ra (cửa sổ lớn hơn) thì --ty-le phải tăng: ' + doTyLe(2400, 1350));
  assert.ok(doTyLe(1400, 790) < 1, 'zoom vào thì --ty-le phải giảm: ' + doTyLe(1400, 790));
  assert.strictEqual(doTyLe(2560, 900), 1, 'màn rộng mà thấp thì theo chiều thấp, không phóng cho tràn đáy');
  assert.strictEqual(doTyLe(300, 200), 0.85, 'màn rất nhỏ vẫn dừng ở 0,85');
  assert.strictEqual(doTyLe(9000, 5000), 2, 'màn rất lớn vẫn dừng ở 2');
  console.log('✓ co giãn theo zoom: 1600×900→1 · 2400×1350→%s · 1400×790→%s · 2560×900→1, kẹp 0,85–2', doTyLe(2400, 1350), doTyLe(1400, 790));
  doTyLe(1600, 900);

  assert.deepStrictEqual(loiJS, [], 'không được có lỗi JS: ' + loiJS.join(' | '));

  // 2. bốn ngôn ngữ trên màn phiếu — không lộ khoá thô, không lai
  await di('#/phieu-xuat-xe');
  for (const ng of ['vi', 'lo', 'en', 'both']) {
    w.EPL.NN.dat(ng); await cho(150);
    const chu = d.body.textContent;
    const lo_khoa = chu.match(/\b(nav|title|sec|stt|a|s|c|r|hint|wf|sg|st|x|fp|pm|u|pt|acct)_[a-z0-9_]+\b/g) || [];
    assert.deepStrictEqual(lo_khoa, [], 'ngôn ngữ ' + ng + ' lộ khoá thô: ' + lo_khoa.slice(0, 5));
    // Thẻ HTML trong từ điển phải được DỰNG, không hiện ra chữ — lỗi thật ngày 14/09: tiêu đề in "<span class="sub">"
    assert.ok(!/<(span|small|b|br)\b/.test(chu), 'ngôn ngữ ' + ng + ' hiện thẻ HTML ra chữ: ' + (chu.match(/<(span|small|b|br)[^>]*>/) || [''])[0]);
    assert.ok(!/ \/ [຀-໿]/.test(d.getElementById('pageTitle').textContent), 'tiêu đề trang không được nối hai thứ tiếng bằng " / "');
    if (ng === 'lo') assert.ok(/[຀-໿]/.test(goc().textContent), 'chọn tiếng Lào mà không thấy chữ Lào');
    if (ng === 'both') assert.ok(goc().querySelector('.lo-sub'), 'chế độ VI+ລາວ phải có dòng Lào phụ');
    console.log(`  ✓ ngôn ngữ ${ng.padEnd(4)} không lộ khoá`);
  }
  w.EPL.NN.dat('vi'); await cho(100);

  // 3. số trên màn phiếu khớp máy chủ
  const dsPhieu = await (await fetch(GOC + '/api/trips', { headers: { Authorization: 'Bearer ' + w.EPL.API.token() } })).json();
  const p0 = dsPhieu.find(p => p.doc_no === 'T4-0428-08/EPL');
  await di('#/phieu-xuat-xe?id=' + p0.id);
  assert.strictEqual(d.getElementById('px-doc-no').value, 'T4-0428-08/EPL', 'phải mở đúng phiếu T4-0428');
  const val = d.getElementById('v-val-usd').textContent;
  assert.ok(val.startsWith(w.EPL.so(p0.tinh.doanh_thu, w.EPL.leTien(p0.tinh.ccy))), 'thành tiền trên màn (' + val + ') phải khớp máy chủ ' + p0.tinh.doanh_thu + ' ' + p0.tinh.ccy);
  const tongChi = d.querySelector('.px-tong .o:nth-child(2) .v').textContent;
  assert.ok(tongChi.includes(w.EPL.so(p0.tinh.tong_chi_lak)), 'tổng chi trên màn (' + tongChi + ') phải khớp máy chủ ' + p0.tinh.tong_chi_lak);
  const soDongChi = goc().querySelectorAll('.px-chi tbody tr[data-i]').length;
  assert.strictEqual(soDongChi, p0.tinh ? (await (await fetch(GOC + '/api/trips/' + p0.id, { headers: { Authorization: 'Bearer ' + w.EPL.API.token() } })).json()).expenses.length : 0, 'số dòng chi trên màn phải bằng máy chủ');
  console.log('✓ phiếu T4-0428: thành tiền %s · tổng chi khớp · %d dòng chi', val, soDongChi);

  // 3b. xe liên kết: bảng thanh toán chủ xe hiện ra và khớp
  const pj = dsPhieu.find(p => p.company === 'joint');
  await di('#/phieu-xuat-xe?id=' + pj.id);
  assert.ok(goc().querySelector('.px-phieu').classList.contains('is-joint'), 'phiếu xe liên kết phải bật lớp is-joint');
  const tt = goc().querySelector('.px-tt'); assert.ok(tt, 'phiếu xe liên kết phải có bảng thanh toán chủ xe');
  assert.ok(tt.textContent.includes(w.EPL.so(pj.tinh.tra_chu_xe, w.EPL.leTien(pj.tinh.hire_ccy || pj.tinh.ccy))), 'tiền trả chủ xe trên màn phải khớp máy chủ ' + pj.tinh.tra_chu_xe);
  console.log('✓ phiếu xe liên kết %s: trả chủ xe %s %s khớp máy chủ', pj.doc_no, w.EPL.so(pj.tinh.tra_chu_xe, 2), pj.tinh.hire_ccy || pj.tinh.ccy);

  // Phiếu còn đang chạy (chưa tới nơi) — dùng cho hai bước phân vai bên dưới.
  const pDang = dsPhieu.find(p => p.transport_status !== 'arrived') || dsPhieu[0];
  // 3c. Màn Theo dõi tuyến dựng theo trung tâm điều hành: dải ô số · ba cột · bấm ô là lọc
  await di('#/theo-doi-tuyen');
  const oSo = [...goc().querySelectorAll('#tdt-o-so .tdt2-tile')];
  assert.strictEqual(oSo.length, 8, 'dải ô số phải có đủ 8 ô, đang có ' + oSo.length);
  assert.ok(oSo.every(o => /^\d/.test(o.querySelector('.v').textContent.trim())), 'mỗi ô phải hiện một con số');
  assert.strictEqual(goc().querySelectorAll('#tdt-cols > .tdt2-card').length, 3, 'phải đủ ba cột: danh sách · giữa · hồ sơ chuyến');
  const the = [...goc().querySelectorAll('#tdt-the-ds .tdt2-the')];
  assert.ok(the.length, 'cột trái phải liệt kê chuyến đang theo dõi');
  assert.ok(goc().querySelector('#tdt-xe').textContent.trim().length > 20, 'hồ sơ chuyến phải có nội dung');
  assert.strictEqual(goc().querySelectorAll('#tdt-xe .tdt2-ap').length, 6, 'hồ sơ chuyến phải hiện trạng thái sáu mục');
  // mốc chặng và ba tab của bản mẫu
  assert.ok(goc().querySelectorAll('#tdt-moc .m').length >= 2, 'phải vẽ mốc chặng của tuyến');
  const tabs = [...goc().querySelectorAll('#tdt-tabs .tdt2-tab')].map(b => b.dataset.tab);
  assert.deepStrictEqual(tabs, ['dien-bien', 'chi-phi', 'chung-tu'], 'phải đủ ba tab: ' + tabs.join(','));
  assert.ok(goc().querySelector('#tdt-tab-than').textContent.trim().length > 0, 'tab đang mở phải có nội dung');
  goc().querySelector('#tdt-tabs [data-tab="chi-phi"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await cho(120);
  assert.ok(goc().querySelector('#tdt-tabs [data-tab="chi-phi"]').classList.contains('active'), 'bấm tab phải đổi tab');
  goc().querySelector('#tdt-tabs [data-tab="dien-bien"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await cho(120);
  // bấm ô "chưa xuất bến" thì danh sách chỉ còn phiếu chưa xuất bến
  const soTruoc = the.length;
  goc().querySelector('.tdt2-tile[data-o="chua_xuat_ben"]').dispatchEvent(new w.Event('click'));
  await cho(120);
  const soSau = goc().querySelectorAll('#tdt-the-ds .tdt2-the').length;
  assert.ok(soSau <= soTruoc, 'bấm ô số phải lọc bớt danh sách: ' + soTruoc + ' → ' + soSau);
  goc().querySelector('.tdt2-tile[data-o="chua_xuat_ben"]').dispatchEvent(new w.Event('click'));
  await cho(120);
  assert.strictEqual(goc().querySelectorAll('#tdt-the-ds .tdt2-the').length, soTruoc, 'bấm lại chính ô đó phải bỏ lọc');
  // Thanh xem nhanh: bấm một phiếu thì trượt ra, bấm × thì thu lại (bản đồ ăn hết chỗ trống).
  const cols = goc().querySelector('#tdt-cols');
  assert.ok(cols.classList.contains('mo-ho-so'), 'bấm một phiếu phải mở thanh xem nhanh');
  goc().querySelector('#tdt-dong-hs').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await cho(150);
  assert.ok(!cols.classList.contains('mo-ho-so'), 'bấm × phải thu thanh xem nhanh');
  goc().querySelector('#tdt-the-ds .tdt2-the').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await choDen(() => cols.classList.contains('mo-ho-so'), 'bấm lại một phiếu phải mở lại thanh xem nhanh', 6000);
  console.log('✓ theo dõi tuyến: 8 ô số · 3 cột · mốc chặng · 3 tab · %d chuyến · bấm ô lọc được (%d → %d)', soTruoc, soTruoc, soSau);

  // Bản đồ: Leaflet để sẵn trong dự án nên phải vẽ được cả khi không ra Internet (ảnh nền thì
  // không có, nhưng đường tuyến và chấm xe lấy từ toạ độ trong DB nên vẫn phải hiện).
  await choDen(() => goc().querySelectorAll('#tdt-map .leaflet-pane').length > 0, 'bản đồ dựng xong', 15000);
  const oMap = goc().querySelector('#tdt-map');
  assert.ok(oMap.querySelectorAll('path').length >= 2, 'bản đồ phải vẽ đường tuyến và các mốc');
  assert.ok(oMap.querySelector('.tdt-xe-cham'), 'bản đồ phải có chấm xe ở mốc đã xác nhận tới');
  console.log('✓ bản đồ tuyến: %d lớp · %d hình vẽ · có chấm xe',
    oMap.querySelectorAll('.leaflet-pane').length, oMap.querySelectorAll('path').length);


  // 4. vai Bãi: không thấy Tài khoản, không thấy nút kiểm/chi
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('thabok', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào lại với vai Bãi'); await w.EPL.sanSang;
  assert.ok(![...d.querySelectorAll('#nav [data-mod]')].some(b => b.dataset.mod === 'tai-khoan'), 'vai Bãi không được thấy module Tài khoản');
  {
    const modBai = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
    // Bãi không thấy TIỀN BÁN: hoá đơn khách và bảng lãi xe liên kết. Tiền chi thì thấy — chính họ chi.
    ['hoa-don', 'xe-lien-ket'].forEach(m => assert.ok(!modBai.includes(m), 'vai Bãi không được thấy module tiền bán ' + m));
    ['tien-tai-xe', 'nha-cung-cap', 'kho-nhien-lieu'].forEach(m => assert.ok(modBai.includes(m), 'vai Bãi phải thấy module chi phí ' + m));
    assert.ok(d.body.classList.contains('vai-yard'), 'thân trang phải mang lớp vai-yard');
    await di('#/tong-quan');
    const nhanKPI = [...goc().querySelectorAll('.tq-kpi .l')].map(e => e.textContent.trim()).join(' | ');
    assert.ok(!/doanh thu|chưa thanh toán/i.test(nhanKPI), 'Tổng quan của Bãi không được có ô doanh thu / khách chưa trả: ' + nhanKPI);
    assert.ok(![...goc().querySelectorAll('.tq-chip')].some(b => /chưa thu/i.test(b.textContent)), 'Bãi không được thấy chip Chưa thu');
    console.log('✓ tổng quan vai Bãi: %s', nhanKPI);
    await di('#/theo-doi');
    const thTien = [...goc().querySelectorAll('th.tien')];
    assert.ok(thTien.length >= 6, 'bảng theo dõi phải đánh dấu các cột tiền bán: ' + thTien.length);
    assert.ok(thTien.every(th => w.getComputedStyle(th).display === 'none'), 'với Bãi mọi cột tiền bán của bảng theo dõi phải ẩn');
    // ... nhưng cột chi phí thì PHẢI còn, vì Bãi là người chi và người nhập các khoản đó
    const thChi = [...goc().querySelectorAll('th')].filter(th => /c_fuel|c_travel|c_totexp/.test(th.dataset.i18n || ''));
    assert.strictEqual(thChi.length, 3, 'phải tìm thấy ba cột chi phí trong bảng theo dõi');
    assert.ok(thChi.every(th => w.getComputedStyle(th).display !== 'none'), 'vai Bãi vẫn phải thấy cột chi phí (họ nhập và họ chi)');
    console.log('✓ vai Bãi: ẩn %d cột tiền bán, vẫn thấy 3 cột chi phí', thTien.length);
  }
  await di('#/phieu-xuat-xe?id=' + pDang.id);
  const nut = [...goc().querySelectorAll('[data-muc-act]')].map(b => b.dataset.hd);
  assert.ok(!nut.includes('verify') && !nut.includes('pay') && !nut.includes('book'), 'vai Bãi không được thấy nút kiểm/ghi sổ/chi: ' + nut);
  assert.ok(goc().querySelector('#px-phieu').classList.contains('px-an-tien'), 'vai Bãi phải có lớp px-an-tien để ẩn đơn giá/thành tiền/quy đổi');
  // Tab theo vai: Bãi vào phải rơi vào MỘT mục (mục đầu còn việc), không phải Toàn phiếu; chỉ mục đó hiện
  {
    const tabs = [...goc().querySelectorAll('#px-tabs .px-tab')].map(b => b.dataset.tab);
    assert.deepStrictEqual(tabs, ['info', 'trans', 'fuel', 'travel', 'repair', 'other', 'all'], 'phải đủ 6 tab mục + Toàn phiếu: ' + tabs);
    const dang = goc().querySelector('#px-phieu').dataset.tab;
    assert.ok(dang && dang !== 'all', 'vai Bãi phải mở sẵn một tab mục, đang: ' + dang);
    const hien = [...goc().querySelectorAll('.px-muc.px-muc-hien')].map(x => x.dataset.muc);
    assert.deepStrictEqual(hien, [dang], 'chỉ mục của tab đang mở được hiện: ' + hien);
    goc().querySelector('#px-tabs .px-tab[data-tab="all"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.strictEqual(goc().querySelectorAll('.px-muc.px-muc-hien').length, 6, 'Toàn phiếu phải hiện cả 6 mục');
    assert.ok(goc().querySelector('#px-luu').hidden, 'Toàn phiếu là để xem — nút Lưu phải ẩn');
    goc().querySelector('#px-tabs .px-tab[data-tab="fuel"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.deepStrictEqual([...goc().querySelectorAll('.px-muc.px-muc-hien')].map(x => x.dataset.muc), ['fuel'], 'bấm tab III chỉ còn mục III');
    console.log('✓ phiếu dạng tab: Bãi mở sẵn tab %s · Toàn phiếu chỉ xem · đổi tab được', dang);
  }
  assert.ok(goc().querySelector('#v-odo_est'), 'phiếu phải có ô Km về ước tính');
  console.log('✓ vai Bãi: không thấy Tài khoản; nút thấy được: %s', nut.join(',') || '(không có)');
  // K3: Bãi mở Khách hàng không thấy nút Bảng giá (tiền); kế toán thì thấy, bấm ra bảng có dòng giá gieo sẵn
  await di('#/khach-hang');
  assert.strictEqual(goc().querySelectorAll('[data-gia]').length, 0, 'vai Bãi không được thấy nút Bảng giá');
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('ketoan', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai KT Thu/Chi'); await w.EPL.sanSang;
  await di('#/khach-hang');
  const nutGia = goc().querySelectorAll('[data-gia]');
  assert.ok(nutGia.length >= 2, 'kế toán phải thấy nút Bảng giá ở từng khách');
  nutGia[0].dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await choDen(() => !goc().querySelector('#kh-gia').hidden && goc().querySelectorAll('#kh-gia-than tr').length > 0, 'bảng giá hiện ra');
  const dongGia = [...goc().querySelectorAll('#kh-gia-than tr')].filter(tr => !tr.querySelector('.empty'));
  assert.ok(dongGia.length >= 2, 'khách gieo sẵn phải có ít nhất 2 dòng giá: ' + dongGia.length);
  assert.ok(!goc().querySelector('#kh-gia-them').hidden, 'kế toán phải có nút thêm giá');
  console.log('✓ bảng giá khách × tuyến: Bãi không thấy · kế toán thấy %d dòng', dongGia.length);

  // 5. vai kho nhiên liệu: chỉ mục III có nút
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('khonl', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai kho NL'); await w.EPL.sanSang;
  await di('#/phieu-xuat-xe?id=' + pDang.id);
  const mucCoNut = [...new Set([...goc().querySelectorAll('[data-muc-act]')].map(b => b.dataset.mucAct))];
  assert.deepStrictEqual(mucCoNut, ['fuel'], 'vai kho nhiên liệu chỉ được có nút ở mục III: ' + mucCoNut);
  await di('#/xe');
  assert.ok(goc().querySelector('#xe-them').hidden, 'vai không sửa danh mục thì màn Xe không được có nút Thêm');
  await di('#/phieu-xuat-xe?id=' + pDang.id);
  assert.strictEqual(goc().querySelector('#px-phieu').dataset.tab, 'fuel', 'KT kho xăng dầu vào phải mở sẵn tab III');
  assert.ok(!goc().querySelector('#px-phieu').classList.contains('px-an-tien'), 'vai khác Bãi phải thấy ô tiền');
  console.log('✓ vai kho nhiên liệu: chỉ mục III có nút hành động');

  // 5b. Đăng nhập khi địa chỉ còn hash của module vai này KHÔNG có quyền: khung tự chuyển sang màn
  // đầu, và lượt chuyển đó từng chồng lên lượt nạp đang chạy làm màn trắng trơn. Kiểm để không tái diễn.
  {
    w.EPL.AUTH.dangXuat(false);
    assert.strictEqual(d.getElementById('noi-dung').children.length, 0, 'đăng xuất phải xoá nội dung màn, không để người sau thấy số của người trước');
    w.location.hash = '#/tai-khoan';                 // màn chỉ Sếp mới có
    await w.EPL.AUTH.dangNhap('thabok', '1234');
    await choDen(() => !d.getElementById('app').hidden, 'vào lại với vai Bãi');
    await xongHet();
    await choDen(() => goc().textContent.trim().length > 60, 'màn phải có nội dung sau khi khung tự chuyển');
    assert.notStrictEqual(w.location.hash, '#/tai-khoan', 'phải tự chuyển khỏi màn không có quyền');
    console.log('✓ vào bằng địa chỉ không có quyền: tự chuyển màn, màn mới có nội dung (%d ký tự)', goc().textContent.trim().length);
  }

  // 6. vai tài xế: chỉ thấy "Phiếu của tôi", có nút xuất phát / báo hỏng
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('tx01', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai tài xế');
  await xongHet();
  const navTx = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
  assert.deepStrictEqual(navTx, ['phieu-cua-toi'], 'tài xế chỉ được thấy Phiếu của tôi: ' + navTx);
  const chuTx = goc().textContent;
  assert.ok(!chuTx.includes(w.EPL.NN.t('err_generic')), 'màn tài xế báo lỗi: ' + chuTx.slice(0, 200));
  assert.ok(!/\bundefined\b|\bNaN\b/.test(chuTx), 'màn tài xế có chữ undefined/NaN');
  console.log('✓ vai tài xế: chỉ thấy Phiếu của tôi · %d ký tự', chuTx.length);

  // 7. vai thủ kho nhiên liệu: chỉ thấy hàng chờ cấp và tồn kho dầu
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('khotb', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai thủ kho'); await w.EPL.sanSang;
  const navKho = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
  assert.deepStrictEqual(navKho, ['cap-phat', 'kho-nhien-lieu'], 'thủ kho chỉ được thấy Cấp phát và Kho nhiên liệu: ' + navKho);
  const chuKho = goc().textContent;
  assert.ok(!chuKho.includes(w.EPL.NN.t('err_generic')), 'màn thủ kho báo lỗi: ' + chuKho.slice(0, 200));
  console.log('✓ vai thủ kho: chỉ thấy %s', navKho.join(', '));

  // Hai kiểu xem: thanh bên và thanh trên. Đổi kiểu thì khối ngôn ngữ và khối người dùng phải CHUYỂN
  // CHỖ chứ không nhân đôi — nhân đôi là hai nút cùng id, bấm cái nào cũng sai.
  {
    // vào lại bằng vai xem được mọi module, vì đây là phép thử của khung chứ không phải của phân vai
    w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('admin', '1234');
    await choDen(() => !d.getElementById('app').hidden, 'vào lại với vai Sếp'); await w.EPL.sanSang;
    await di('#/theo-doi');
    const app = d.getElementById('app');
    w.EPL.datKieuXem('top');
    assert.strictEqual(app.dataset.view, 'top');
    assert.ok(!d.getElementById('tbar').hidden, 'kiểu thanh trên phải hiện thanh hai tầng');
    assert.ok(d.querySelectorAll('#tbar2 .mn[data-nhom]').length >= 2, 'hàng menu phải có các nhóm');
    assert.ok(d.querySelectorAll('#tbar2 .mn-panel .mn-muc[data-mod]').length >= 5, 'mỗi menu phải thả xuống danh sách màn');
    // mỗi dòng trong menu phải có tên VÀ một câu mô tả — đó là điểm khác của kiểu này
    const mucMenu = [...d.querySelectorAll('#tbar2 .mn-muc')];
    assert.ok(mucMenu.every(b => b.querySelector('b') && b.querySelector('small') && b.querySelector('small').textContent.trim()),
      'dòng menu nào cũng phải có tên và câu mô tả');
    assert.ok(mucMenu.every(b => !/^[a-z_]+$/.test(b.querySelector('small').textContent.trim())), 'mô tả không được lộ khoá từ điển');
    // bấm mở menu rồi bấm ra ngoài phải đóng
    const mnNhom = d.querySelector('#tbar2 .mn[data-nhom]');
    mnNhom.querySelector('.mn-nut').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.ok(mnNhom.classList.contains('mo') && !mnNhom.querySelector('.mn-panel').hidden, 'bấm tên nhóm phải mở bảng');
    d.body.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.ok(!mnNhom.classList.contains('mo'), 'bấm ra ngoài phải đóng bảng');
    assert.strictEqual(d.querySelectorAll('#langApp').length, 1, 'khối ngôn ngữ của ứng dụng chỉ được có MỘT bản');
    assert.strictEqual(d.querySelectorAll('#userbox').length, 1, 'khối người dùng chỉ được có MỘT bản');
    assert.ok(d.getElementById('tbarPhai').contains(d.getElementById('langApp')), 'kiểu thanh trên: ngôn ngữ nằm ở tầng 1');
    w.EPL.datKieuXem('side');
    assert.strictEqual(app.dataset.view, 'side');
    assert.ok(d.getElementById('tbar').hidden, 'kiểu thanh bên thì ẩn thanh trên');
    assert.ok(d.getElementById('chanOi').contains(d.getElementById('userbox')), 'kiểu thanh bên: người dùng nằm ở chân thanh');
    assert.ok(d.querySelectorAll('#nav [data-nhom]').length >= 2, 'thanh bên phải có tiêu đề nhóm gấp được');
    const tim = d.getElementById('navTim');
    tim.value = 'kho'; tim.dispatchEvent(new w.Event('input'));
    const loc = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
    assert.ok(loc.length && loc.every(x => /kho|phu-tung|nhien-lieu/.test(x)), 'gõ "kho" phải lọc menu: ' + loc.join(','));
    tim.value = ''; tim.dispatchEvent(new w.Event('input'));
    // Menu người dùng (bánh răng "Cài đặt giao diện" và "Đổi tài khoản") và nút thu gọn thanh bên
    const menu = d.getElementById('nguoiMenu');
    assert.ok(menu.hidden, 'menu người dùng lúc đầu phải đóng');
    d.getElementById('btnNguoi').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.ok(!menu.hidden, 'bấm vào tên người dùng phải mở menu');
    assert.strictEqual(menu.querySelectorAll('[data-mn]').length, 2, 'menu phải có Cài đặt giao diện và Đổi tài khoản');
    d.body.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.ok(menu.hidden, 'bấm ra ngoài phải đóng menu');
    d.getElementById('btnThuGon').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.strictEqual(app.dataset.hep, '1', 'bấm nút thu gọn phải chuyển thanh bên sang chế độ hẹp');
    d.getElementById('btnThuGon').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.strictEqual(app.dataset.hep, '0', 'bấm lần nữa phải mở rộng lại');
    // Nút ngôn ngữ trong ứng dụng là menu thả xuống có cờ, tên, mã và dấu tích ở dòng đang chọn;
    // màn đăng nhập thì CỐ Ý giữ dãy phẳng để người mới thấy ngay là có tiếng Lào.
    {
      const o = d.getElementById('langApp');
      assert.ok(o.querySelector('.ln-nut .ln-co svg'), 'nút ngôn ngữ phải có cờ vẽ bằng SVG (emoji cờ không hiện trên Windows)');
      const muc = [...o.querySelectorAll('.ln-muc')];
      assert.strictEqual(muc.length, w.EPL.NN.danhSach.length, 'menu phải đủ 4 ngôn ngữ');
      assert.ok(muc.every(b => b.querySelector('b').textContent.trim() && b.querySelector('small').textContent.trim() && b.querySelector('.ma').textContent.trim()),
        'dòng ngôn ngữ nào cũng phải có tên gốc, tên phụ và mã');
      assert.strictEqual(o.querySelectorAll('.ln-muc.active').length, 1, 'đúng một dòng được đánh dấu đang chọn');
      const menu = o.querySelector('.ln-menu');
      assert.ok(menu.hidden, 'menu ngôn ngữ lúc đầu phải đóng');
      o.querySelector('.ln-nut').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
      assert.ok(!menu.hidden, 'bấm nút phải mở menu ngôn ngữ');
      o.querySelector('.ln-muc[data-lang="en"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
      assert.strictEqual(w.EPL.NN.lang, 'en', 'chọn English phải đổi ngôn ngữ');
      assert.strictEqual(d.querySelector('#langApp .ln-nut .ma').textContent, 'EN', 'nút phải hiện mã ngôn ngữ đang dùng');
      d.querySelector('#langApp .ln-nut').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
      d.querySelector('#langApp .ln-muc[data-lang="vi"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
      assert.ok(d.querySelectorAll('#login .lang button').length >= 4, 'màn đăng nhập vẫn giữ dãy phẳng bốn nút');
      console.log('✓ nút ngôn ngữ: thả xuống có cờ · tên · mã · dấu tích, đổi được ngôn ngữ');
    }
    console.log('✓ hai kiểu xem: thanh bên ↔ thanh trên, ngôn ngữ và người dùng chuyển chỗ, tìm nhanh lọc được');
  }

  assert.deepStrictEqual(loiJS, [], 'không được có lỗi JS: ' + loiJS.join(' | '));
  console.log(`\nTHỬ GIAO DIỆN: ĐẠT — ${MODULES.length} module · 4 ngôn ngữ · số khớp máy chủ · phân vai đúng (tài xế · thủ kho)`);
  w.close();
}
main().catch(e => { console.error('THỬ GIAO DIỆN: HỎNG —', e.message); process.exit(1); });
