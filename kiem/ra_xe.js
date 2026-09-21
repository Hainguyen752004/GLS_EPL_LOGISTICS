/* Rà màn Xe: từng vai thấy gì, bấm thử các nút, đổi tab hồ sơ, 4 ngôn ngữ. */
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
  let loi = []; w.addEventListener('error', e => loi.push(gon(e.message || e.error).slice(0, 140)));
  w.console.error = (...a) => loi.push(gon(a.join(' ')).slice(0, 140));
  const d = w.document, g = () => d.getElementById('noi-dung');
  async function xong() { for (let i = 0; i < 60; i++) { const pr = w.EPL.sanSang; await pr; await cho(70); if (pr === w.EPL.sanSang) return; } }
  async function di(hash) { const cu = w.EPL.sanSang; if (w.location.hash === hash) w.dispatchEvent(new w.HashChangeEvent('hashchange')); else w.location.hash = hash; await choDen(() => w.EPL.sanSang !== cu, 'nạp'); await xong(); await cho(500); }
  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'đăng nhập');

  console.log('== TỪNG VAI');
  for (const u of ['admin', 'thabok', 'ketoan', 'khonl', 'doanhthu', 'quyvc']) {
    if (!d.getElementById('app').hidden) { w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .person').length > 0, 'ra'); }
    loi = [];
    await w.EPL.AUTH.dangNhap(u, '1234'); await choDen(() => !d.getElementById('app').hidden, 'vào'); await xong();
    const co = [...d.querySelectorAll('#nav [data-mod]')].some(b => b.dataset.mod === 'xe');
    if (!co) { console.log(`  ${u.padEnd(9)} — không có màn Xe`); continue; }
    await di('#/xe');
    const them = g().querySelector('#xe-them');
    console.log(`  ${u.padEnd(9)} ${g().querySelectorAll('#xe-tbl tbody tr').length} dòng · chip ${g().querySelectorAll('.xe-chip').length} · nút Thêm: ${them && !them.hidden ? 'có' : 'không'} · ${gon(g().textContent).length} ký tự`);
    const kv = [...g().querySelectorAll('.xe-kv div')].map(e => gon(e.textContent)).slice(0, 4).join(' | ');
    console.log(`  ${''.padEnd(9)} thẻ phải: ${kv}`);
    if (loi.length) console.log('           LỖI:', [...new Set(loi)].slice(0, 3).join(' | '));
  }

  console.log('\n== BẤM THỬ (vai admin)');
  w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .person').length > 0, 'ra');
  await w.EPL.AUTH.dangNhap('admin', '1234'); await choDen(() => !d.getElementById('app').hidden, 'vào'); await xong();
  await di('#/xe');
  loi = [];
  // chọn dòng 2
  const rows = g().querySelectorAll('#xe-tbl tbody tr');
  rows[1].dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(800);
  console.log('  chọn dòng 2 →', gon(g().querySelector('.xe-head') ? g().querySelector('.xe-head').textContent : '(không có thẻ)').slice(0, 80));
  // mở hồ sơ
  g().querySelector('[data-act="open"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(600);
  const modal = g().querySelector('.xe-modal');
  console.log('  mở hồ sơ →', modal ? 'có hộp · tab: ' + [...modal.querySelectorAll('[data-mt]')].map(b => gon(b.textContent)).join(', ') : 'KHÔNG MỞ');
  for (const t of ['phaply', 'kythuat', 'romooc', 'lich', 'sua', 'phieu']) {
    const b = modal.querySelector(`[data-mt="${t}"]`); if (!b) { console.log('   tab', t, 'KHÔNG CÓ'); continue; }
    b.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(t === 'lich' ? 1200 : 300);
    console.log(`   tab ${t.padEnd(7)} ${gon(modal.querySelector('#m-body').textContent).slice(0, 90)}`);
  }
  // đóng
  modal.querySelector('[data-close]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(300);
  // sang tab rơ-moóc
  g().querySelector('#xe-loai button[data-v="ro-mooc"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(900);
  console.log('  tab Rơ-moóc:', g().querySelectorAll('#xe-tbl tbody tr').length, 'dòng ·', gon((g().querySelector('.xe-head') || {}).textContent || '').slice(0, 70));
  if (loi.length) console.log('  LỖI:', [...new Set(loi)].slice(0, 4).join(' | '));

  console.log('\n== BỐN NGÔN NGỮ');
  g().querySelector('#xe-loai button[data-v="dau-keo"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(600);
  for (const nn of ['vi', 'lo', 'en', 'both']) {
    w.EPL.NN.dat(nn); await cho(400);
    const chu = g().textContent;
    const tho = (chu.match(/\b(xe|tq|k|s|e|p)_[a-z0-9_]+\b/g) || []);
    console.log(`  ${nn.padEnd(5)} ${gon(chu).length} ký tự · khoá thô: ${[...new Set(tho)].slice(0,5).join(',') || 'không'} · undefined: ${/\bundefined\b/.test(chu)}`);
  }
  w.EPL.NN.dat('vi');
  w.close();
})().catch(e => { console.error('HỎNG:', e.message); process.exit(1); });
