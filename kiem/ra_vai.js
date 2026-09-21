/* Rà giao diện TỪNG VAI trên jsdom, nối máy chủ thật: đăng nhập lần lượt mọi tài khoản mẫu, mở
 * từng module vai đó thấy trên thanh điều hướng, và ghi ra một bản báo cáo (không phải bộ kiểm
 * đạt/hỏng — là danh sách việc để sửa):
 *
 *   node kiem/ra_vai.js [http://127.0.0.1:8010]
 *
 * Với mỗi vai × module: lỗi JS · màn trống · khoá chưa dịch (kiểu "nav_dash") · chữ undefined/NaN
 * · nút hành động thấy được · riêng vai Bãi: ô/cột tiền còn hiển thị (Bãi không được thấy tiền).
 * Kiểm cả 4 ngôn ngữ ở một module trọng tâm của vai để bắt câu lai / khoá thô.
 */
const path = require('path');
const { JSDOM, ResourceLoader } = require(path.join(__dirname, '..', '..', 'EPL_System', 'frontend', 'node_modules', 'jsdom'));

const GOC = process.argv[2] || 'http://127.0.0.1:8010';
// Bãi không thấy TIỀN BÁN (cước, doanh thu, giá thuê xe ngoài, lãi) — tiền CHI thì họ vẫn thấy vì
// chính họ chi. Không soi mã tiền tệ suông: chi phí cũng quy ra USD, bắt cả thế thì toàn báo nhầm.
const TU_BAN = /cước|doanh thu|lợi nhuận|\blãi\b|giá thuê|tiền thuê|chưa thu|đã thu|khấu trừ|USD\s*\/\s*(t\b|tấn)|ຄ່າຂົນສົ່ງ|freight|revenue|profit/i;
const gonChu = (s) => String(s).replace(/\s+/g, ' ').trim();

class ChiNoiBo extends ResourceLoader {
  fetch(url, options) { if (!url.startsWith(GOC)) return Promise.resolve(Buffer.from('')); return super.fetch(url, options); }
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
  w.fetch = (u, o) => fetch(new URL(u, GOC).href, o);
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function (v) { this.returnValue = v || this.returnValue; this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); };
  w.Element.prototype.scrollIntoView = w.Element.prototype.scrollIntoView || function () {};
  let loiJS = []; w.addEventListener('error', e => loiJS.push(String(e.message || e.error)));
  w.console.error = (...a) => loiJS.push(a.join(' ').slice(0, 200));
  const d = w.document;
  /** Đợi tới khi màn VẼ XONG, không đợi một khoảng cố định: nhiều module còn gọi API trong init nên
   *  đo ngay sau sanSang là đo lúc màn còn trống (đã có lần báo nhầm "Tổng quan 139 ký tự"). */
  async function di(hash) {
    const cu = w.EPL.sanSang;
    if (w.location.hash === hash) w.dispatchEvent(new w.HashChangeEvent('hashchange')); else w.location.hash = hash;
    await choDen(() => w.EPL.sanSang && w.EPL.sanSang !== cu, 'bắt đầu nạp ' + hash); await w.EPL.sanSang;
    let truoc = -1, yen = 0;
    for (let i = 0; i < 60 && yen < 3; i++) {          // ba lượt liền chữ không đổi thì coi là xong
      await cho(80);
      const n = goc().textContent.length;
      yen = n === truoc ? yen + 1 : 0; truoc = n;
    }
  }
  const goc = () => d.getElementById('noi-dung');
  const hienThi = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { if (e.hidden || w.getComputedStyle(e).display === 'none') return false; } return true; };

  /** Khối cha nhỏ nhất còn đọc được như một cụm (dưới 120 ký tự): "Doanh thu vận chuyển 8,501.36 USD"
   *  là một cụm, còn cả thanh công cụ thì không. Con số chỉ có nghĩa khi đi cùng nhãn của nó. */
  function khoiNho(el) {
    let t = gonChu(el.textContent);
    for (let e = el.parentElement, i = 0; e && i < 4; e = e.parentElement, i++) {
      const s = gonChu(e.textContent);
      if (s.length > 120) break;
      t = s;
    }
    return t;
  }
  /** Nhãn các cột ĐANG HIỆN của bảng chứa ô này. Cột bị ẩn với vai đó thì nhãn của nó cũng không tính —
   *  nhờ vậy một bảng đã giấu cột "Cước" thì các ô số còn lại không bị báo nhầm. */
  function nhanBang(el) {
    const b = el.closest && el.closest('table');
    if (!b) return '';
    return [...b.querySelectorAll('thead th')].filter(hienThi).map(th => th.textContent).join(' ');
  }
  function laTienBan(el) {
    if (!/\d/.test(el.textContent)) return false;
    return TU_BAN.test(khoiNho(el) + ' ' + gonChu(nhanBang(el)));
  }

  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'màn đăng nhập');
  const tk = await (await fetch(GOC + '/api/tai-khoan-mau')).json();
  const baoCao = [];
  let doDuocTienBan = 0;                 // đếm cho phép tự kiểm ở vai kế toán
  const ghi = (vai, u, mod, loai, chi_tiet) => baoCao.push({ vai, u, mod, loai, chi_tiet });

  for (const t of tk) {
    const u = t.username, vai = t.role;
    if (!d.getElementById('app').hidden) { w.EPL.AUTH.dangXuat(false); await choDen(() => d.querySelectorAll('#acctList .person').length > 0, 'về màn đăng nhập'); }
    loiJS = [];
    await w.EPL.AUTH.dangNhap(u, '1234');
    await choDen(() => !d.getElementById('app').hidden, 'vào với ' + u, 15000); await w.EPL.sanSang;
    const mods = [...d.querySelectorAll('#nav [data-mod]')].map(b => b.dataset.mod);
    console.log(`\n== ${u} (${vai}) · ${mods.length} module: ${mods.join(', ')}`);
    if (!mods.length) ghi(vai, u, '-', 'KHONG_CO_MODULE', 'thanh điều hướng trống');
    for (const m of mods) {
      loiJS = [];
      try { await di('#/' + m); } catch (e) { ghi(vai, u, m, 'KHONG_NAP', e.message); continue; }
      const chu = goc().textContent.replace(/\s+/g, ' ').trim();
      if (loiJS.length) ghi(vai, u, m, 'LOI_JS', loiJS.slice(0, 3).join(' | '));
      if (chu.includes(w.EPL.NN.t('err_generic'))) ghi(vai, u, m, 'BAO_LOI', chu.slice(0, 160));
      if (chu.length < 40) ghi(vai, u, m, 'MAN_TRONG', chu.length + ' ký tự');
      const xau = chu.match(/\b(undefined|NaN|null)\b/g); if (xau) ghi(vai, u, m, 'CHU_LA', [...new Set(xau)].join(','));
      const khoaTho = chu.match(/\b(nav|mod|title|hint|stt|sec|td|px|kh|ct|bh|s)_[a-z0-9_]+\b/g);
      if (khoaTho) ghi(vai, u, m, 'KHOA_CHUA_DICH', [...new Set(khoaTho)].slice(0, 6).join(','));
      if (!goc().querySelector('table, .kpis, .px-phieu, .pct-ds, .card, .tdt2')) ghi(vai, u, m, 'KHONG_BANG', 'không có bảng/thẻ');
      const nut = [...goc().querySelectorAll('button')].filter(hienThi).map(b => b.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean);
      const nutKhac = [...new Set(nut)];
      if (vai === 'acct' && m === 'theo-doi') {
        // Tự kiểm phép dò: vai kế toán ĐƯỢC thấy tiền bán, nên ở đây nó phải bắt ra khối. Không bắt
        // được gì tức là phép dò đã hỏng và mọi báo cáo "sạch" ở trên đều vô nghĩa.
        const la = [...goc().querySelectorAll('*')].filter(e => !e.children.length && e.textContent.trim() && hienThi(e));
        doDuocTienBan += la.filter(laTienBan).length;
      }
      // Bỏ qua 'quy-trinh': đó là sơ đồ giải thích quy trình (ai làm bước nào, sinh chứng từ gì),
      // không có số liệu chuyến nào — Bãi nên đọc được cả sơ đồ.
      if (vai === 'yard' && m !== 'quy-trinh') {
        // Bãi không thấy tiền bán: soi mọi phần tử lá đang hiện, không chỉ nhãn cột
        const la = [...goc().querySelectorAll('*')].filter(e => !e.children.length && e.textContent.trim() && hienThi(e));
        const lo = [...new Set(la.filter(laTienBan).map(e => e.textContent.replace(/\s+/g, ' ').trim()))];
        if (lo.length) ghi(vai, u, m, 'BAI_THAY_TIEN_BAN', lo.slice(0, 8).join(' · '));
      }
      console.log(`  ${m.padEnd(16)} ${String(chu.length).padStart(5)} ký tự · nút: ${nutKhac.slice(0, 8).join(' | ') || '(không)'}${nutKhac.length > 8 ? ' …' : ''}`);
    }
    // 4 ngôn ngữ ở module đầu của vai
    if (mods.length) {
      const m0 = mods[0]; await di('#/' + m0);
      for (const nn of ['vi', 'lo', 'en', 'both']) {
        w.EPL.NN.dat(nn); await cho(150);
        const chu = goc().textContent.replace(/\s+/g, ' ');
        const khoaTho = chu.match(/\b(nav|mod|title|hint|stt|sec|td|px|kh|ct|bh|s)_[a-z0-9_]+\b/g);
        if (khoaTho) ghi(vai, u, m0 + '@' + nn, 'KHOA_CHUA_DICH', [...new Set(khoaTho)].slice(0, 6).join(','));
        if (/\bundefined\b/.test(chu)) ghi(vai, u, m0 + '@' + nn, 'CHU_LA', 'undefined');
      }
      w.EPL.NN.dat('vi');
    }
  }

  console.log('\n================ BÁO CÁO RÀ VAI ================');
  if (!baoCao.length) console.log('Không thấy gì bất thường.');
  for (const r of baoCao) console.log(`[${r.loai}] ${r.u} (${r.vai}) · ${r.mod}: ${r.chi_tiet}`);
  console.log(`\nTổng: ${baoCao.length} ghi nhận · ${tk.length} tài khoản`);
  console.log(doDuocTienBan
    ? `Phép dò tiền bán còn tốt: bắt được ${doDuocTienBan} chỗ ở màn Theo dõi của kế toán (vai này ĐƯỢC thấy).`
    : 'CẢNH BÁO: phép dò tiền bán không bắt được gì ngay cả ở vai kế toán — nó đã hỏng, sửa rồi rà lại.');
  try { w.close(); } catch (e) { /* bỏ */ }
}

main().catch(e => { console.error('RÀ VAI: HỎNG —', e.message); process.exit(1); });
