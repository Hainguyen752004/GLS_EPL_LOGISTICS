/* Rà màn Tài xế & bằng lái: từng vai thấy gì, cột KẾT LUẬN nói đúng chưa, bấm thử các tab hồ sơ,
   ngăn trượt mở/đóng, 4 ngôn ngữ. BÁO CÁO để người đọc, không phải bộ kiểm đạt/hỏng. */
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
  for (const u of ['admin', 'thabok', 'ketoan', 'khonl', 'doanhthu', 'quyvc', 'tx01']) {
    if (!d.getElementById('app').hidden) { w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .acc').length > 0, 'ra'); }
    loi = [];
    await w.EPL.AUTH.dangNhap(u, '1234'); await choDen(() => !d.getElementById('app').hidden, 'vào'); await xong();
    const co = [...d.querySelectorAll('#nav [data-mod]')].some(b => b.dataset.mod === 'tai-xe');
    if (!co) { console.log(`  ${u.padEnd(9)} — không có màn Tài xế`); continue; }
    await di('#/tai-xe');
    const them = g().querySelector('#tx-them');
    console.log(`  ${u.padEnd(9)} ${g().querySelectorAll('#tx-tbl tbody tr').length} dòng · chip ${g().querySelectorAll('.tx-chip').length} · nút Thêm: ${them && !them.hidden ? 'có' : 'không'} · ${gon(g().textContent).length} ký tự`);
    if (loi.length) console.log('           LỖI:', [...new Set(loi)].slice(0, 3).join(' | '));
  }

  console.log('\n== CỘT KẾT LUẬN (vai admin) — phần mềm tự nói ai được điều xe');
  w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .acc').length > 0, 'ra');
  await w.EPL.AUTH.dangNhap('admin', '1234'); await choDen(() => !d.getElementById('app').hidden, 'vào'); await xong();
  await di('#/tai-xe');
  loi = [];
  [...g().querySelectorAll('#tx-tbl tbody tr')].forEach(tr => {
    const o = [...tr.children].map(td => gon(td.textContent));
    console.log(`  ${o[1].slice(0, 46).padEnd(48)} bằng ${o[2].slice(0, 24).padEnd(26)} → ${o[5]}`);
  });
  console.log('  chân bảng:', gon(g().querySelector('#tx-foot').textContent));
  console.log('  chip:', [...g().querySelectorAll('.tx-chip')].map(b => gon(b.textContent)).join(' · '));

  console.log('\n== NGĂN TRƯỢT + HỒ SƠ');
  const rows = g().querySelectorAll('#tx-tbl tbody tr');
  rows[0].dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(900);
  const detail = g().querySelector('#tx-detail'), scrim = g().querySelector('#tx-scrim');
  console.log('  bấm dòng 1 → ngăn mở:', detail.classList.contains('open'), '· nền mờ:', scrim.classList.contains('open'));
  console.log('  thẻ:', gon(g().querySelector('.tx-head') ? g().querySelector('.tx-head').textContent : '(không có)').slice(0, 96));
  console.log('  cửa chặn:', gon((g().querySelector('.tx-gate') || {}).textContent || '(không có)').slice(0, 96));
  // đóng bằng nút X rồi mở lại
  detail.querySelector('[data-close-detail]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(300);
  console.log('  bấm X → ngăn mở:', detail.classList.contains('open'));
  rows[0].dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(600);
  scrim.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(300);
  console.log('  bấm nền mờ → ngăn mở:', detail.classList.contains('open'));

  rows[0].dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(700);
  g().querySelector('[data-act="open"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(800);
  const modal = g().querySelector('.tx-modal');
  console.log('  mở hồ sơ →', modal ? 'có hộp · tab: ' + [...modal.querySelectorAll('[data-mt]')].map(b => gon(b.textContent)).join(', ') : 'KHÔNG MỞ');
  console.log('  ngăn trượt tự thu:', !g().querySelector('#tx-detail').classList.contains('open'));
  for (const t of ['bang', 'xe', 'lich', 'phieu']) {
    const b = modal.querySelector(`[data-mt="${t}"]`); if (!b) { console.log('   tab', t, 'KHÔNG CÓ'); continue; }
    b.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(t === 'lich' ? 1400 : 350);
    console.log(`   tab ${t.padEnd(6)} ${gon(modal.querySelector('#m-body').textContent).slice(0, 96)}`);
  }
  modal.querySelector('[data-close]').dispatchEvent(new w.MouseEvent('click', { bubbles: true })); await cho(300);
  if (loi.length) console.log('  LỖI:', [...new Set(loi)].slice(0, 5).join(' | '));

  console.log('\n== BỐN NGÔN NGỮ');
  for (const ng of ['vi', 'lo', 'en', 'both']) {
    w.EPL.NN.dat(ng); await cho(500);
    const t = gon(g().textContent);
    console.log(`  ${ng.padEnd(5)} ${t.length} ký tự · khoá thô: ${/\b(tx|xe)_[a-z_]{3,}\b/.test(t) ? 'CÓ — ' + (t.match(/\b(tx|xe)_[a-z_]{3,}\b/g) || []).slice(0, 4).join(',') : 'không'} · undefined: ${t.includes('undefined')}`);
  }
  console.log(loi.length ? '\nLỖI JS: ' + [...new Set(loi)].slice(0, 6).join(' | ') : '\nKhông có lỗi JS.');
  process.exit(0);
})().catch(e => { console.error('HỎNG:', e.message); process.exit(1); });
