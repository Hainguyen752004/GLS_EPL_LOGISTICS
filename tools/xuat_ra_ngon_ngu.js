/* Xuất chữ giao diện (frontend/js/ngon_ngu.js) để người bản ngữ rà tiếng Lào — 10/10 (anh Cello, bạn anh Khampla, xin "localization
 * review"). Ghi JSON cho tools/xuat_ra_ngon_ngu.py dựng tệp Excel ba cột Việt · Anh · Lào.
 *
 *    node tools/xuat_ra_ngon_ngu.js <ra.json>
 *
 * Mỗi khoá được gắn MÀN nơi nó hiện, tìm trong mã: chữ khoá có trong frontend/modules/<màn>/ → màn đó; có trong js/*.js hoặc
 * index.html → "mọi màn"; chỉ có ở backend → tên trạng thái máy chủ gửi. Khoá ghép động ('qt_b' + i + '_ten', `s_${ma}`) tính theo
 * tiền tố chữ đứng ngay trước dấu + / ${. Khoá không thấy ở đâu → nhóm "có thể không còn dùng" (vẫn xuất, để rà sau cùng).
 * Các khoá cùng đủ ba câu Việt · Anh · Lào gộp thành một dòng (mọi khoá ghi ở cột mã). */
const fs = require('fs'), path = require('path');
const GOC = path.resolve(__dirname, '..');
global.window = {};
require(path.join(GOC, 'frontend/js/ngon_ngu.js'));
const D = window.EPL_TU_DIEN, KHOA = Object.keys(D);

const doc = (f) => fs.readFileSync(f, 'utf8');
const tep = (thu, loc) => fs.readdirSync(thu).filter(loc).map(f => path.join(thu, f));
const nhom = [];                                  // [{ten, noi dung}]
const mod = path.join(GOC, 'frontend/modules');
for (const m of fs.readdirSync(mod).filter(f => fs.statSync(path.join(mod, f)).isDirectory())) {
  const ds = tep(path.join(mod, m), f => /\.(js|html)$/.test(f));
  if (ds.length) nhom.push({ ten: m, src: ds.map(doc).join('\n') });
}
nhom.push({ ten: '*chung', src: [...tep(path.join(GOC, 'frontend/js'), f => /\.js$/.test(f) && f !== 'ngon_ngu.js'),
  path.join(GOC, 'frontend/index.html')].map(doc).join('\n') });
const py = [];
const di = (p) => { for (const f of fs.readdirSync(p)) { const q = path.join(p, f); if (fs.statSync(q).isDirectory()) { if (f !== '__pycache__') di(q); } else if (f.endsWith('.py')) py.push(q); } };
di(path.join(GOC, 'backend/app'));
nhom.push({ ten: '*may_chu', src: py.map(doc).join('\n') });

// thứ tự màn + tên tiếng Anh theo menu (MODULES trong chung.js)
const chung = doc(path.join(GOC, 'frontend/js/chung.js'));
const THU_TU = [...chung.matchAll(/\{ id: '([a-z-]+)',\s*nhom: '[a-z_]+',\s*nav: '([a-z_]+)'/g)].map(m => ({ id: m[1], nav: m[2] }));
const tenMan = (id) => {
  if (id === '*chung') return 'All screens (menu, buttons, common words)';
  if (id === '*may_chu') return 'Status names sent by the server';
  const x = THU_TU.find(t => t.id === id);
  return x && D[x.nav] ? D[x.nav].en.replace(/<[^>]+>.*$/, '') : id;
};
const thuTu = (id) => id === '*chung' ? -1 : id === '*may_chu' ? 999 : (THU_TU.findIndex(t => t.id === id) + 1 || 500);

const noi = new Map();                            // khoá → Set(màn)
for (const n of nhom) {
  const tu = new Set(n.src.match(/[A-Za-z0-9_]+/g));
  const dong = new Set();
  for (const m of n.src.matchAll(/['"`]([a-z0-9_]{2,})['"`]\s*\+/gi)) dong.add(m[1]);
  for (const m of n.src.matchAll(/`([a-z0-9_]{2,})\$\{/gi)) dong.add(m[1]);
  for (const k of KHOA) {
    if (tu.has(k) || [...dong].some(p => p.includes('_') && k.startsWith(p))) {
      if (!noi.has(k)) noi.set(k, new Set());
      noi.get(k).add(n.ten);
    }
  }
}

const gop = new Map();
for (const k of KHOA) {
  const x = D[k], o = noi.get(k);
  let man = null, them = [];
  if (o) {
    const ds = [...o].sort((a, b) => thuTu(a) - thuTu(b));
    const chi = ds.filter(t => !t.startsWith('*'));
    man = o.has('*chung') || chi.length >= 3 ? '*chung' : chi[0] || ds[0];
    them = chi.filter(t => t !== man);
  }
  const khoa = [x.vi, x.en, x.lo, man || '-'].join('\u0001');
  if (!gop.has(khoa)) gop.set(khoa, { vi: x.vi, en: x.en, lo: x.lo, keys: [], man, them: new Set(), thu: KHOA.indexOf(k), nhom: new Set() });
  const g = gop.get(khoa);
  g.keys.push(k); them.forEach(t => g.them.add(t)); (o || []).forEach(t => g.nhom.add(t));
}
const dong = [...gop.values()].map(g => ({
  vi: g.vi, en: g.en, lo: g.lo, keys: g.keys, dung: !!g.man, man: g.man ? tenMan(g.man) : '', thu_man: g.man ? thuTu(g.man) : 1000,
  cung: [...g.them].map(tenMan), thu: g.thu, nhom: [...g.nhom],      // nhom: mọi màn / tệp có dùng (id thư mục, *chung, *may_chu)
})).sort((a, b) => a.thu_man - b.thu_man || a.thu - b.thu);
fs.writeFileSync(process.argv[2], JSON.stringify(dong, null, 1));
console.log('khoá', KHOA.length, '· dòng', dong.length, '· đang dùng', dong.filter(d => d.dung).length, '· có thể không dùng', dong.filter(d => !d.dung).length);
