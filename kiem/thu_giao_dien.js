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
  'phieu-cua-toi', 'cap-phat', 'xe-lien-ket', 'tien-tai-xe', 'tat-toan', 'nha-cung-cap', 'kho-nhien-lieu',
  'diem-do', 'kho-phu-tung', 'khach-hang', 'xe', 'tai-xe', 'tuyen-duong', 'quy-trinh', 'tai-khoan'];

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
  const goc = () => d.getElementById('noi-dung');

  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'màn đăng nhập tải tài khoản mẫu');
  console.log('✓ màn đăng nhập: %d tài khoản mẫu', d.getElementById('acctList').children.length);
  // Màn đăng nhập là TRANG riêng chiếm trọn màn hình (trước đây là thẻ nhỏ, 10 tài khoản xếp dọc
  // nên phải thu nhỏ trình duyệt mới thấy hết) — kiểm đủ khung trái, cột phải và nút hiện mật khẩu.
  assert.ok(d.querySelector('#login .lg-brand') && d.querySelector('#login .lg-cot'), 'màn đăng nhập phải có hai cột');
  assert.ok(d.getElementById('lgMat'), 'màn đăng nhập phải có nút hiện/ẩn mật khẩu');
  assert.strictEqual(d.getElementById('lgP').type, 'password', 'mật khẩu mặc định phải ẩn');
  d.getElementById('lgMat').dispatchEvent(new w.Event('click'));
  assert.strictEqual(d.getElementById('lgP').type, 'text', 'bấm con mắt thì mật khẩu phải hiện');
  d.getElementById('lgMat').dispatchEvent(new w.Event('click'));
  assert.strictEqual(d.getElementById('lgP').type, 'password', 'bấm lần nữa thì mật khẩu phải ẩn lại');
  const goiY = [...d.querySelectorAll('#acctList .acct-btn')];
  assert.ok(goiY.length >= 10, 'phải gợi ý đủ tài khoản demo, đang có ' + goiY.length);
  assert.strictEqual(goiY[0].dataset.u, 'admin', 'gợi ý phải xếp quản trị lên đầu');
  assert.ok(goiY.some(b => b.dataset.u === 'tx01' && b.classList.contains('tx')), 'phải có tài khoản tài xế tx01');
  assert.ok(goiY.every(b => !/<(span|small|b)\b/.test(b.textContent)), 'thẻ tài khoản không được lộ thẻ HTML');
  console.log('✓ màn đăng nhập: hai cột · nút hiện mật khẩu · %d thẻ gợi ý, quản trị đứng đầu', goiY.length);

  // 1. đăng nhập admin, đi hết module
  await w.EPL.AUTH.dangNhap('admin', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào ứng dụng');
  await w.EPL.sanSang;
  const nav = [...d.querySelectorAll('#nav button')].map(b => b.dataset.mod);
  assert.deepStrictEqual(nav, MODULES, 'thanh điều hướng phải đủ ' + MODULES.length + ' module đúng thứ tự');
  console.log('✓ admin: thanh điều hướng đủ %d module', nav.length);

  for (const m of MODULES) {
    await di('#/' + m);
    const chu = goc().textContent;
    assert.ok(!chu.includes(w.EPL.NN.t('err_generic')), 'module ' + m + ' báo lỗi: ' + chu.slice(0, 200));
    assert.ok(!/\bundefined\b|\bNaN\b/.test(chu), 'module ' + m + ' có chữ undefined/NaN');
    assert.ok(goc().querySelector('table, .kpis, .px-phieu, .pct-ds'), 'module ' + m + ' không có bảng/thẻ nào');
    console.log(`  ✓ ${m.padEnd(16)} ${chu.length} ký tự`);
  }
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
  assert.ok(val.startsWith(w.EPL.so(p0.tinh.doanh_thu_usd, 2)), 'thành tiền trên màn (' + val + ') phải khớp máy chủ ' + p0.tinh.doanh_thu_usd);
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
  assert.ok(tt.textContent.includes(w.EPL.so(pj.tinh.tra_chu_xe_usd, 2)), 'tiền trả chủ xe trên màn phải khớp máy chủ ' + pj.tinh.tra_chu_xe_usd);
  console.log('✓ phiếu xe liên kết %s: trả chủ xe %s USD khớp máy chủ', pj.doc_no, w.EPL.so(pj.tinh.tra_chu_xe_usd, 2));

  // Phiếu còn đang chạy (chưa tới nơi) — dùng cho hai bước phân vai bên dưới.
  const pDang = dsPhieu.find(p => p.transport_status !== 'arrived') || dsPhieu[0];
  // 3c. Màn Theo dõi tuyến dựng theo trung tâm điều hành: dải ô số · ba cột · bấm ô là lọc
  await di('#/theo-doi-tuyen');
  const oSo = [...goc().querySelectorAll('#tdt-o-so .tdt-o')];
  assert.strictEqual(oSo.length, 7, 'dải ô số phải có đủ 7 ô, đang có ' + oSo.length);
  assert.ok(oSo.every(o => /^\d/.test(o.querySelector('.v').textContent.trim())), 'mỗi ô phải hiện một con số');
  assert.ok(goc().querySelector('.tdt-ds') && goc().querySelector('.tdt-giua') && goc().querySelector('.tdt-ho-so'),
    'phải đủ ba cột: danh sách · giữa · hồ sơ chuyến');
  const the = [...goc().querySelectorAll('#tdt-the-ds .tdt-the')];
  assert.ok(the.length, 'cột trái phải liệt kê chuyến đang theo dõi');
  assert.ok(goc().querySelector('#tdt-xe').textContent.trim().length > 20, 'hồ sơ chuyến phải có nội dung');
  assert.ok(goc().querySelector('.tdt-muc-hang .tdt-muc-o'), 'hồ sơ chuyến phải hiện trạng thái sáu mục');
  // bấm ô "chưa xuất bến" thì danh sách chỉ còn phiếu chưa xuất bến
  const soTruoc = the.length;
  goc().querySelector('.tdt-o[data-o="chua_xuat_ben"]').dispatchEvent(new w.Event('click'));
  await cho(120);
  const soSau = goc().querySelectorAll('#tdt-the-ds .tdt-the').length;
  assert.ok(soSau <= soTruoc, 'bấm ô số phải lọc bớt danh sách: ' + soTruoc + ' → ' + soSau);
  goc().querySelector('.tdt-o[data-o="chua_xuat_ben"]').dispatchEvent(new w.Event('click'));
  await cho(120);
  assert.strictEqual(goc().querySelectorAll('#tdt-the-ds .tdt-the').length, soTruoc, 'bấm lại chính ô đó phải bỏ lọc');
  console.log('✓ theo dõi tuyến: 7 ô số · 3 cột · %d chuyến · bấm ô lọc được (%d → %d)', soTruoc, soTruoc, soSau);

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
  assert.ok(![...d.querySelectorAll('#nav button')].some(b => b.dataset.mod === 'tai-khoan'), 'vai Bãi không được thấy module Tài khoản');
  await di('#/phieu-xuat-xe?id=' + pDang.id);
  const nut = [...goc().querySelectorAll('[data-muc-act]')].map(b => b.dataset.hd);
  assert.ok(!nut.includes('verify') && !nut.includes('pay') && !nut.includes('book'), 'vai Bãi không được thấy nút kiểm/ghi sổ/chi: ' + nut);
  console.log('✓ vai Bãi: không thấy Tài khoản; nút thấy được: %s', nut.join(',') || '(không có)');

  // 5. vai kho nhiên liệu: chỉ mục III có nút
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('khonl', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai kho NL'); await w.EPL.sanSang;
  await di('#/phieu-xuat-xe?id=' + pDang.id);
  const mucCoNut = [...new Set([...goc().querySelectorAll('[data-muc-act]')].map(b => b.dataset.mucAct))];
  assert.deepStrictEqual(mucCoNut, ['fuel'], 'vai kho nhiên liệu chỉ được có nút ở mục III: ' + mucCoNut);
  console.log('✓ vai kho nhiên liệu: chỉ mục III có nút hành động');

  // 6. vai tài xế: chỉ thấy "Phiếu của tôi", có nút xuất phát / báo hỏng
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('tx01', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai tài xế'); await w.EPL.sanSang;
  const navTx = [...d.querySelectorAll('#nav button')].map(b => b.dataset.mod);
  assert.deepStrictEqual(navTx, ['phieu-cua-toi'], 'tài xế chỉ được thấy Phiếu của tôi: ' + navTx);
  const chuTx = goc().textContent;
  assert.ok(!chuTx.includes(w.EPL.NN.t('err_generic')), 'màn tài xế báo lỗi: ' + chuTx.slice(0, 200));
  assert.ok(!/\bundefined\b|\bNaN\b/.test(chuTx), 'màn tài xế có chữ undefined/NaN');
  console.log('✓ vai tài xế: chỉ thấy Phiếu của tôi · %d ký tự', chuTx.length);

  // 7. vai thủ kho nhiên liệu: chỉ thấy hàng chờ cấp và tồn kho dầu
  w.EPL.AUTH.dangXuat(false); await w.EPL.AUTH.dangNhap('khotb', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào với vai thủ kho'); await w.EPL.sanSang;
  const navKho = [...d.querySelectorAll('#nav button')].map(b => b.dataset.mod);
  assert.deepStrictEqual(navKho, ['cap-phat', 'kho-nhien-lieu'], 'thủ kho chỉ được thấy Cấp phát và Kho nhiên liệu: ' + navKho);
  const chuKho = goc().textContent;
  assert.ok(!chuKho.includes(w.EPL.NN.t('err_generic')), 'màn thủ kho báo lỗi: ' + chuKho.slice(0, 200));
  console.log('✓ vai thủ kho: chỉ thấy %s', navKho.join(', '));

  assert.deepStrictEqual(loiJS, [], 'không được có lỗi JS: ' + loiJS.join(' | '));
  console.log(`\nTHỬ GIAO DIỆN: ĐẠT — ${MODULES.length} module · 4 ngôn ngữ · số khớp máy chủ · phân vai đúng (tài xế · thủ kho)`);
  w.close();
}
main().catch(e => { console.error('THỬ GIAO DIỆN: HỎNG —', e.message); process.exit(1); });
