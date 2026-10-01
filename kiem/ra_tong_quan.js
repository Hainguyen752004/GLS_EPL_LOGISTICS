/* Rà riêng màn Tổng quan: từng vai thấy gì, chip dẫn đi đâu, tháng rỗng ra sao, đổi ngôn ngữ có lộ khoá. */
const path = require('path');
const { JSDOM, ResourceLoader } = require(path.join('D:/Demo_Lao/EPL_System/frontend/node_modules/jsdom'));
const GOC = process.argv[2] || 'http://127.0.0.1:8011';
class ChiNoiBo extends ResourceLoader { fetch(u, o) { if (!u.startsWith(GOC)) return Promise.resolve(Buffer.from('')); return super.fetch(u, o); } }
const cho = ms => new Promise(r => setTimeout(r, ms));
async function choDen(dk, mo, td = 25000) { const t0 = Date.now(); while (Date.now() - t0 < td) { if (dk()) return; await cho(60); } throw new Error('Hết giờ: ' + mo); }
const gon = s => String(s).replace(/\s+/g, ' ').trim();
(async () => {
  const html = await (await fetch(GOC + '/')).text();
  const dom = new JSDOM(html, { url: GOC + '/', runScripts: 'dangerously', resources: new ChiNoiBo(), pretendToBeVisual: true });
  const w = dom.window; w.fetch = (u, o) => fetch(new URL(u, GOC).href, o);
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  w.Element.prototype.scrollIntoView = function () {};
  let loi = []; w.addEventListener('error', e => loi.push(gon(e.message || e.error).slice(0, 120)));
  w.console.error = (...a) => loi.push(gon(a.join(' ')).slice(0, 120));
  const d = w.document;
  /** Chờ tới khi khung KHÔNG còn lượt nạp nào nữa. Đổi location.hash chỉ bắn hashchange ở lượt sau,
   *  nên phải để trống một nhịp rồi mới kết luận là đã xong, không thì đo đúng lúc màn còn trắng. */
  async function xongHet() {
    for (let i = 0; i < 60; i++) {
      const pr = w.EPL.sanSang;
      await pr; await cho(70);
      if (pr === w.EPL.sanSang) return;
    }
  }
  const g = () => d.getElementById('noi-dung');
  async function di(hash) {
    const cu = w.EPL.sanSang;
    if (w.location.hash === hash) w.dispatchEvent(new w.HashChangeEvent('hashchange')); else w.location.hash = hash;
    await choDen(() => w.EPL.sanSang && w.EPL.sanSang !== cu, 'nạp ' + hash);
    // Khung nạp nối tiếp nhau: có thể còn lượt nữa đang xếp hàng (đăng nhập với hash của module
    // không có quyền thì khung tự chuyển màn). Chờ tới khi không còn lượt mới nào.
    await xongHet();
    let t = -1, yen = 0; for (let i = 0; i < 50 && yen < 3; i++) { await cho(80); const n = g().textContent.length; yen = n === t ? yen + 1 : 0; t = n; }
  }
  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'đăng nhập');
  const tk = await (await fetch(GOC + '/api/tai-khoan-mau')).json();
  console.log('== AI THẤY MÀN TỔNG QUAN, VÀ THẤY GÌ');
  for (const t of tk) {
    if (!d.getElementById('app').hidden) { w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .acc').length > 0, 'ra'); }
    loi = [];
    await w.EPL.AUTH.dangNhap(t.username, '1234');
    await choDen(() => !d.getElementById('app').hidden, 'vào ' + t.username); await w.EPL.sanSang;
    const co = [...d.querySelectorAll('#nav [data-mod]')].some(b => b.dataset.mod === 'tong-quan');
    if (!co) { console.log(`  ${t.username.padEnd(9)} (${t.role.padEnd(8)}) — không có màn Tổng quan`); continue; }
    await di('#/tong-quan');
    const kpi = [...g().querySelectorAll('.tq-kpi .l')].map(e => gon(e.textContent));
    const chip = [...g().querySelectorAll('.tq-chip')].map(e => gon(e.textContent));
    console.log(`  ${t.username.padEnd(9)} (${t.role.padEnd(8)}) KPI: ${kpi.join(' / ')}`);
    console.log(`  ${''.padEnd(9)} ${''.padEnd(10)} chip: ${chip.join(' / ')}`);
    if (loi.length) console.log('           LỖI JS:', [...new Set(loi)].slice(0, 3).join(' | '));
  }

  // --- bấm thử từng chip: dẫn tới màn nào
  console.log('\n== BẤM THỬ CHIP (vai admin)');
  w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .acc').length > 0, 'ra');
  await w.EPL.AUTH.dangNhap('admin', '1234'); await choDen(() => !d.getElementById('app').hidden, 'vào'); await w.EPL.sanSang;
  await di('#/tong-quan');
  const n = g().querySelectorAll('.tq-chip').length;
  for (let i = 0; i < n; i++) {
    await di('#/tong-quan');
    const b = g().querySelectorAll('.tq-chip')[i], ten = gon(b.textContent);
    b.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await cho(900); await w.EPL.sanSang; await cho(600);
    console.log(`  ${ten.padEnd(24)} → ${w.location.hash}  (màn có ${g().textContent.length} ký tự)`);
  }
  // nút Xuất báo cáo + Xem tất cả + một ô tiến trình
  for (const [ten, sel] of [['Xuất báo cáo', '#tq-xuat'], ['Xem tất cả', '#tq-chu-y-all'], ['ô tiến trình 1', '.tq-step']]) {
    await di('#/tong-quan');
    const b = g().querySelector(sel); if (!b) { console.log('  KHÔNG THẤY ' + ten); continue; }
    b.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await cho(900); await w.EPL.sanSang; await cho(500);
    console.log(`  ${ten.padEnd(24)} → ${w.location.hash}`);
  }

  // --- tháng KHÔNG có chuyến nào
  console.log('\n== THÁNG RỖNG (2026-05)');
  await di('#/tong-quan');
  const o = g().querySelector('#tq-thang'); o.value = '2026-05';
  o.dispatchEvent(new w.Event('change', { bubbles: true }));
  await cho(1500);
  console.log('  chữ trống hiện ra:', [...new Set([...g().querySelectorAll('.tq-empty')].map(e => gon(e.textContent)))].join(' | ') || '(không có)');
  console.log('  KPI:', [...g().querySelectorAll('.tq-kpi .v')].map(e => gon(e.textContent)).join(' / '));
  console.log('  ops:', gon((g().querySelector('#tq-ops') || {}).textContent));

  // --- bốn ngôn ngữ
  console.log('\n== BỐN NGÔN NGỮ');
  o.value = '2026-08'; o.dispatchEvent(new w.Event('change', { bubbles: true })); await cho(1200);
  for (const nn of ['vi', 'lo', 'en', 'both']) {
    w.EPL.NN.dat(nn); await cho(400);
    const chu = g().textContent;
    const tho = (chu.match(/\b(tq|k|s|e|p|attention)_[a-z0-9_]+\b/g) || []);
    console.log(`  ${nn.padEnd(5)} ${chu.replace(/\s+/g,' ').trim().length} ký tự · khoá thô: ${[...new Set(tho)].slice(0,5).join(',') || 'không'} · undefined: ${/\bundefined\b/.test(chu)}`);
  }
  w.EPL.NN.dat('vi');
  w.close();
})().catch(e => { console.error('HỎNG:', e.message); process.exit(1); });
