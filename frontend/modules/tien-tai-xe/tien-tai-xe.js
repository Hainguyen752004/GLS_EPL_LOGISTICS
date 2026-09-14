/* Tiền chuyến & tiền nước tài xế — tổng hợp theo tháng từ mục IV các phiếu. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, d;
  function ve() {
    const rows = d.rows; let t = { x_trip: 0, x_water: 0, x_phone: 0, x_vn: 0, x_food: 0, tong: 0, phieu: 0 };
    root.querySelector('#ttx-ky').textContent = `${EPL.ngay(d.tu)} – ${EPL.ngay(d.den)}`;
    root.querySelector('#ttx-than').innerHTML = rows.length ? rows.map(r => {
      const k = r.khoan; ['x_trip', 'x_water', 'x_phone', 'x_vn', 'x_food'].forEach(x => { t[x] += k[x] || 0; }); t.tong += r.tong_lak; t.phieu += r.so_phieu;
      return `<tr><td lang="lo"><b>${esc(r.driver)}</b></td><td class="num">${r.so_phieu}</td><td class="num">${so(k.x_trip || 0)}</td><td class="num">${so(k.x_water || 0)}</td><td class="num">${so(k.x_phone || 0)}</td><td class="num">${so(k.x_vn || 0)}</td><td class="num">${so(k.x_food || 0)}</td><td class="num"><b>${so(r.tong_lak)}</b></td><td>${NN.h('pm_trip_salary')}</td><td>${tag(r.trang_thai)}</td></tr>`;
    }).join('') : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#ttx-chan').innerHTML = `<tr class="ttx-tong"><td>${NN.h('total')}</td><td class="num">${t.phieu}</td><td class="num">${so(t.x_trip)}</td><td class="num">${so(t.x_water)}</td><td class="num">${so(t.x_phone)}</td><td class="num">${so(t.x_vn)}</td><td class="num">${so(t.x_food)}</td><td class="num">${so(t.tong)}</td><td colspan="2"></td></tr>`;
  }
  async function tai() { const th = root.querySelector('#ttx-thang').value || EPL.thangNay(); d = await API.get('/api/bao-cao/tien-tai-xe?thang=' + th); ve(); }
  EPL.modules['tien-tai-xe'] = {
    async init(r) {
      root = r;
      // Mặc định tháng có phiếu gần nhất — cùng lý do với màn Tổng quan.
      let thang = EPL.thangNay();
      try { const ds = await API.get('/api/trips'); if (ds.length && ds[0].doc_date) thang = ds[0].doc_date.slice(0, 7); } catch (e) { /* giữ tháng nay */ }
      r.querySelector('#ttx-thang').value = thang;
      r.querySelector('#ttx-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      await tai();
    },
    onLang() { if (d) ve(); },
  };
})();
