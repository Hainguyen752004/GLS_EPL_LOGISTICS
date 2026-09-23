/* Thử màn Cấp phát khi MẤT MẠNG — chạy trên jsdom, nối máy chủ thật.
 *
 *   node kiem/thu_ngoai_tuyen.js [http://127.0.0.1:8010]
 *
 * Kịch bản đúng như ngoài kho dầu: thủ kho vào màn lúc còn mạng (máy lưu đệm), rồi mạng rớt, xe
 * vẫn tới, vẫn quét được mã, vẫn cấp được dầu — thao tác xếp hàng đợi; có mạng lại thì tự gửi.
 *
 * Bài TỰ LẬP một phiếu thử (THU-NT-…) có phiếu lĩnh 20 lít ở kho Thà Bốc và chỉ cấp đúng tờ đó — không
 * đụng phiếu lĩnh của dữ liệu mẫu. Xong thì Sếp xoá phiếu thử; phần còn sót chạy tools/don_rac_bo_kiem.py.
 */
const path = require('path');
const assert = require('assert');
const { JSDOM, ResourceLoader } = require(path.join(__dirname, '..', '..', 'EPL_System', 'frontend', 'node_modules', 'jsdom'));

const GOC = process.argv[2] || 'http://127.0.0.1:8010';

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

async function api(duong, than, tk, cach) {
  const r = await fetch(GOC + duong, { method: cach || (than ? 'POST' : 'GET'), headers: { 'Content-Type': 'application/json', ...(tk ? { Authorization: 'Bearer ' + tk } : {}) },
    body: than ? JSON.stringify(than) : undefined });
  const g = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`${cach || (than ? 'POST' : 'GET')} ${duong} → ${r.status} ${JSON.stringify(g).slice(0, 300)}`);
  return g;
}
async function lapPhieuThu() {
  const tk = {};
  for (const u of ['thabok', 'tx01', 'admin']) tk[u] = (await api('/api/dang-nhap', { username: u, password: '1234' })).token;
  const tx = (await api('/api/dang-nhap', { username: 'tx01', password: '1234' })).user;
  const xe = await api('/api/vehicles', null, tk.thabok), kh = await api('/api/customers', null, tk.thabok);
  const tb = (await api('/api/fuel-places', null, tk.thabok)).find(x => x.code === 'KHO-TB');
  const nha = xe.find(x => x.owner_type !== 'joint' && x.active !== false);
  const hom = new Date().toISOString().slice(0, 10), so = 'THU-NT-' + Date.now().toString().slice(-8) + '/EPL';
  const p = await api('/api/trips', { doc_no: so, company: 'EPL', vehicle_id: nha.id, driver_id: tx.driver_id, customer_id: kh[0].id,
    weight_origin: 40, doc_date: hom, out_date: hom, note: 'thử ngoại tuyến',
    expenses: [{ section: 'fuel', item_key: 'diesel', qty: 20, place_id: tb.id, paid_by_epl: true }] }, tk.thabok);
  const v = await api(`/api/trips/${p.id}/vouchers`, { kind: 'fuel' }, tk.thabok);
  return { p, pl: v[0], tkAdmin: tk.admin, tkBai: tk.thabok };
}

async function main() {
  const thu = await lapPhieuThu();
  console.log('✓ lập phiếu thử %s · phiếu lĩnh %s lít ở kho Thà Bốc', thu.p.doc_no, thu.pl.qty_l);
  const tonTB = async () => (await api('/api/fuel-moves', null, thu.tkAdmin)).kho.find(k => k.code === 'KHO-TB').ton_lit;
  const tonTruoc = await tonTB();
  let daChay = false;
  try { await chay(thu); daChay = true; } finally {
    if (daChay) {
      // phiếu lĩnh đã cấp: Bãi xoá phiếu phải bị chặn rõ ràng; Sếp xoá được (trước đây Sếp xoá thì máy chủ trả 500 vì khoá ngoại)
      const r = await fetch(GOC + '/api/trips/' + thu.p.id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + thu.tkBai } });
      const g = await r.json().catch(() => ({}));
      assert.strictEqual(r.status, 409, 'Bãi xoá phiếu có phiếu lĩnh đã cấp phải bị chặn 409, không phải ' + r.status);
      assert.ok(['DA_XUAT_KHO', 'DA_CAP_PHAT'].includes((g.detail || {}).ma), 'mã chặn lạ: ' + JSON.stringify(g));
      console.log('✓ Bãi xoá phiếu đã cấp dầu → bị chặn 409 %s', g.detail.ma);
    }
    await api('/api/trips/' + thu.p.id, null, thu.tkAdmin, 'DELETE');
    const tonSau = await tonTB();
    assert.ok(Math.abs(tonSau - tonTruoc) < 0.01, `Sếp xoá phiếu thì dầu đã cấp phải trả về kho: ${tonTruoc} → ${tonSau}`);
    console.log('✓ Sếp xoá phiếu thử %s (dọn) · tồn kho Thà Bốc %s → %s L', thu.p.doc_no, tonTruoc, tonSau);
  }
}

async function chay(thu) {
  const html = await (await fetch(GOC + '/')).text();
  const dom = new JSDOM(html, { url: GOC + '/', runScripts: 'dangerously', resources: new ChiNoiBo(), pretendToBeVisual: true });
  const w = dom.window, d = w.document;
  const thatFetch = (u, o) => fetch(new URL(u, GOC).href, o);
  let matMang = false;
  w.fetch = (u, o) => (matMang ? Promise.reject(new TypeError('Failed to fetch')) : thatFetch(u, o));
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function (v) { this.returnValue = v || this.returnValue; this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); };
  const loiJS = []; w.console.error = (...a) => loiJS.push(a.join(' '));

  async function di(hash) {
    const cu = w.EPL.sanSang;
    if (w.location.hash === hash) w.dispatchEvent(new w.HashChangeEvent('hashchange'));
    else w.location.hash = hash;
    await choDen(() => w.EPL.sanSang && w.EPL.sanSang !== cu, 'bắt đầu nạp ' + hash);
    await w.EPL.sanSang; await cho(120);
  }
  const goc = () => d.getElementById('noi-dung');
  const dong = () => [...goc().querySelectorAll('#cp-than tr[data-v]')];

  await choDen(() => w.EPL && d.getElementById('acctList').children.length > 0, 'màn đăng nhập sẵn sàng');

  // ---- 1. Thủ kho vào màn lúc CÒN MẠNG: máy lưu đệm danh sách và chi tiết
  await w.EPL.AUTH.dangNhap('khotb', '1234');
  await choDen(() => !d.getElementById('app').hidden, 'vào ứng dụng');
  await di('#/cap-phat');
  const soDong = dong().length;
  assert.ok(dong().some(tr => tr.dataset.v === thu.pl.id), 'phiếu lĩnh thử phải hiện trong danh sách chờ của kho Thà Bốc');
  const maPhieu = thu.pl.id;
  const khoaDem = 'epl_lao_cap_phat_' + w.EPL.AUTH.user.id;
  const dem = JSON.parse(w.localStorage.getItem(khoaDem));
  assert.ok(dem && dem.ds.length === soDong, 'phải lưu đệm đủ danh sách phiếu chờ');
  assert.ok(dem.chi_tiet.length === soDong, 'phải lưu đệm cả chi tiết từng phiếu để đối chiếu khi mất mạng');
  assert.ok(dem.chi_tiet[0].phieu && dem.chi_tiet[0].phieu.plate_head !== undefined, 'chi tiết lưu đệm phải có biển số để đối chiếu');
  assert.ok(goc().querySelector('#cp-mang').hidden, 'còn mạng thì không hiện dải ngoại tuyến');
  console.log('✓ còn mạng: %d phiếu chờ, đã lưu đệm cả chi tiết', soDong);

  // ---- 2. MẤT MẠNG: vào lại màn, vẫn thấy việc, có dải báo ngoại tuyến
  matMang = true;
  await di('#/tong-quan');
  await di('#/cap-phat');
  assert.strictEqual(dong().length, soDong, 'mất mạng vẫn phải thấy đủ phiếu chờ từ bản lưu');
  const dai = goc().querySelector('#cp-mang');
  assert.ok(!dai.hidden, 'mất mạng phải hiện dải ngoại tuyến');
  assert.ok(/[A-Za-zÀ-ỹ]/.test(dai.textContent) && !/off_/.test(dai.textContent), 'dải ngoại tuyến không được lộ khoá thô');
  console.log('✓ mất mạng: vẫn thấy %d phiếu từ bản lưu, có dải báo ngoại tuyến', soDong);

  // ---- 3. Quét mã khi mất mạng: vẫn tra ra, vẫn đối chiếu được biển số
  const oMa = goc().querySelector('#cp-ma');
  const cuaMinh = dem.ds.find(x => x.id === maPhieu);
  assert.ok(cuaMinh, 'bản lưu đệm phải có phiếu lĩnh thử');
  oMa.value = cuaMinh.token;
  oMa.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter' }));
  await choDen(() => !goc().querySelector('#cp-xem').hidden, 'tra cứu từ bản lưu');
  const xem = goc().querySelector('#cp-chi-tiet').textContent;
  assert.ok(xem.includes(cuaMinh.doc_no), 'khối đối chiếu phải hiện đúng số phiếu');
  console.log('✓ mất mạng: quét mã vẫn tra ra phiếu %s', cuaMinh.doc_no);

  // ---- 4. Cấp dầu khi mất mạng → xếp hàng đợi, KHÔNG mất việc
  const nutCap = goc().querySelector(`tr[data-v="${maPhieu}"] [data-cap]`);
  assert.ok(nutCap, 'phải còn nút Cấp khi mất mạng');
  nutCap.dispatchEvent(new w.Event('click'));
  const hop = goc().querySelector('#cp-hop');
  await choDen(() => hop.hasAttribute('open'), 'mở hộp cấp dầu');
  hop.close('ok');
  const khoaHang = 'epl_lao_cap_phat_hang_' + w.EPL.AUTH.user.id;
  await choDen(() => (JSON.parse(w.localStorage.getItem(khoaHang) || '[]')).length === 1, 'thao tác phải vào hàng đợi');
  await cho(150);
  assert.ok(goc().querySelector(`tr[data-v="${maPhieu}"]`).className.includes('cho-gui'), 'dòng đã cấp phải được đánh dấu chờ gửi');
  console.log('✓ mất mạng: bấm Cấp thì vào hàng đợi, dòng hiện "chờ gửi"');

  // ---- 5. CÓ MẠNG LẠI: hàng đợi tự gửi, phiếu thành đã cấp trên máy chủ
  matMang = false;
  w.dispatchEvent(new w.Event('online'));
  await choDen(() => (JSON.parse(w.localStorage.getItem(khoaHang) || '[]')).length === 0, 'hàng đợi phải tự gửi hết', 25000);
  const tk = w.EPL.API.token();
  const sau = await (await fetch(GOC + '/api/vouchers/tra-cuu/' + cuaMinh.token, { headers: { Authorization: 'Bearer ' + tk } })).json();
  assert.strictEqual(sau.status, 'da_cap', 'máy chủ phải ghi nhận phiếu đã cấp sau khi gửi hàng đợi');
  assert.ok(sau.granted_by, 'phải ghi tên người cấp');
  console.log('✓ có mạng lại: hàng đợi tự gửi, máy chủ ghi nhận đã cấp (người cấp: %s)', sau.granted_by);

  assert.deepStrictEqual(loiJS, [], 'không được có lỗi JS: ' + loiJS.join(' | '));
  console.log('\nTHỬ NGOẠI TUYẾN: ĐẠT — lưu đệm · tra cứu offline · hàng đợi · tự gửi khi có mạng lại');
  w.close();
}
main().catch(e => { console.error('THỬ NGOẠI TUYẾN: HỎNG —', e.message); process.exit(1); });
