/* Khoản mục chi phí — ລາຍການຄ່າໃຊ້ຈ່າຍ (08/10, anh Khampla: "chi phí khác cho gõ tay → thêm trang cấu hình chi phí để dùng lại";
 * chủ dự án chốt: cách trả mặc định theo khoản mục, KT Chi phí VC đổi từng dòng khi kiểm mục).
 *
 * Khoản có sẵn (dầu, tiền nước, phí cao tốc…) giữ tên theo từ điển; khoản thêm mới mang tên ba thứ tiếng. Thêm ở mục IV · V · VI (mục
 * III chỉ có dầu — mã hàng kho). Đổi cách trả mặc định: dòng trên phiếu cũ giữ cách trả đang có (máy chủ ghi rõ trước khi đổi). Không xoá
 * khoản — ngưng dùng (dòng cũ vẫn hiện tên). Luật, quyền: máy chủ (services/khoan_muc.py, routes/khoan_muc.py).
 */
(function () {
  const { API, NN, esc, tag } = EPL;
  let root, DS = [], Q = { sua: false }, L = { sections: [], sections_them: [], sections_cach_tra: [], pay_channels: [] };

  const g = (id) => root.querySelector('#' + id);
  const SO_MUC = { fuel: 3, travel: 4, repair: 5, other: 6 };
  const LA_MA = { 3: 'III', 4: 'IV', 5: 'V', 6: 'VI' };
  const tenMuc = (m) => `${LA_MA[SO_MUC[m]]} · ${NN.t('sec' + SO_MUC[m])}`;
  const CA = { tien_mat: 'pm_on_dispatch', luong: 'pm_trip_salary', ncc: 'pm_supplier' };
  // tên hiện: khoản có sẵn theo từ điển, khoản thêm mới theo ngôn ngữ đang xem (cũng đã nạp vào từ điển — EPL.themTu)
  const ten = (x) => x.built_in ? NN.t(x.key) : (NN.lang === 'lo' ? (x.name_lo || x.name_vi) : NN.lang === 'en' ? (x.name_en || x.name_vi) : x.name_vi) || x.key;
  const coCachTra = (m) => L.sections_cach_tra.includes(m);

  function ve() {
    const q = g('km-q').value.trim().toLowerCase(), muc = g('km-loc-muc').value;
    const rows = DS.filter(x => (!muc || x.section === muc) && (!q || [ten(x), x.name_vi, x.name_lo, x.name_en, x.key].join(' ').toLowerCase().includes(q)));
    let nhom = '';
    g('km-than').innerHTML = rows.length ? rows.map(x => {
      const dau = x.section !== nhom ? `<tr class="km-nhom"><td colspan="6">${esc(tenMuc(x.section))}</td></tr>` : '';
      nhom = x.section;
      return dau + `<tr class="${x.active ? '' : 'km-tat'}">
        <td><b lang="lo">${esc(ten(x))}</b>${x.built_in ? `<span class="km-san">${NN.h('km_co_san')}</span>` : ''}<span class="km-ma">${esc(x.key)}</span></td>
        <td>${coCachTra(x.section) ? NN.h(CA[x.pay_default || 'tien_mat']) : '<span class="muted">—</span>'}</td>
        <td class="num">${x.so_dong || 0}</td>
        <td class="num">${x.sort || 0}</td>
        <td>${tag(x.active ? 'ok' : 'plain', x.active ? 'active' : 'inactive')}</td>
        <td class="no-print">${Q.sua ? `<button class="btn sm" data-sua="${esc(x.id)}">${NN.h('edit')}</button>` : ''}</td></tr>`;
    }).join('') : `<tr><td colspan="6" class="empty">${NN.h('no_data')}</td></tr>`;
    g('km-dem').textContent = rows.length ? `${rows.length} ${NN.t('rows')}` : '';
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(DS.find(x => x.id === b.dataset.sua))));
  }

  const oCachTra = (v) => ({ id: 'pay_default', label: 'km_cach_tra', type: 'select', value: v || 'tien_mat',
    options: L.pay_channels.map(c => [c, NN.t(CA[c] || c)]) });

  async function them() {
    const v = await EPL.hopNhap(NN.t('km_them'), [
      { id: 'section', label: 'km_muc', type: 'select', value: 'travel', options: L.sections_them.map(m => [m, tenMuc(m)]) },
      { id: 'name_vi', label: 'km_ten_vi', value: '' },
      { id: 'name_lo', label: 'km_ten_lo', value: '', lo: true },
      { id: 'name_en', label: 'km_ten_en', value: '' },
      oCachTra('tien_mat'),
    ], NN.t('save'));
    if (!v) return;
    if (!String(v.name_vi || v.name_lo || '').trim()) return EPL.toast(NN.t('km_ten_vi') + '?', 'loi');
    const than = { section: v.section, name_vi: v.name_vi, name_lo: v.name_lo, name_en: v.name_en };
    if (coCachTra(v.section)) than.pay_default = v.pay_default;        // mục V không có cách trả
    await luu(() => API.post('/api/khoan-muc', than));
  }

  async function sua(x) {
    if (!x) return;
    const v = await EPL.hopNhap(NN.t('edit') + ' · ' + ten(x), [
      ...(x.built_in ? [] : [
        { id: 'name_vi', label: 'km_ten_vi', value: x.name_vi || '' },
        { id: 'name_lo', label: 'km_ten_lo', value: x.name_lo || '', lo: true },
        { id: 'name_en', label: 'km_ten_en', value: x.name_en || '' }]),
      ...(coCachTra(x.section) ? [oCachTra(x.pay_default)] : []),
      { id: 'sort', label: 'km_thu_tu', type: 'number', value: String(x.sort || 0) },
      ...(x.khong_tat ? [] : [{ id: 'active', label: 'status', type: 'select', value: x.active ? '1' : '0',
        options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }]),
    ], NN.t('save'));
    if (!v) return;
    const than = { sort: v.sort };
    if (!x.built_in) Object.assign(than, { name_vi: v.name_vi, name_lo: v.name_lo, name_en: v.name_en });
    if (!x.khong_tat) than.active = v.active === '1';
    if (coCachTra(x.section)) {
      than.pay_default = v.pay_default;
      // đổi mặc định của khoản đang dùng: nói rõ phiếu cũ giữ cách trả đang có
      if (v.pay_default !== (x.pay_default || 'tien_mat') && (x.so_dong || 0) > 0
        && !await EPL.hoi(NN.t('km_cach_tra'), `<p>${NN.h('km_doi_mac_dinh_hoi', { ten: ten(x), n: x.so_dong })}</p>`, NN.t('save'))) return;
    }
    await luu(() => API.put('/api/khoan-muc/' + x.id, than));
  }

  async function luu(goi) {
    try {
      await goi();
      EPL.toast(NN.t('saved'), 'ok');
      await EPL.napTenKhoanMuc();          // tên khoản mới vào từ điển — phiếu mở sau đó thấy ngay, không phải đăng nhập lại
      await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function tai() {
    const r = await API.get('/api/khoan-muc/danh-sach');
    DS = r.items || []; Q = r.quyen || { sua: false }; L = r.lookups || L;
    DS.sort((a, b) => (SO_MUC[a.section] - SO_MUC[b.section]) || ((a.sort || 0) - (b.sort || 0)) || String(a.key).localeCompare(String(b.key)));   // III → VI
    const loc = g('km-loc-muc'), cu = loc.value;
    loc.innerHTML = `<option value="">${esc(NN.t('all'))}</option>` + L.sections.map(m => `<option value="${m}">${esc(tenMuc(m))}</option>`).join('');
    loc.value = cu;
    g('km-them').hidden = !Q.sua;
    ve();
  }

  EPL.modules['khoan-muc'] = {
    async init(r) {
      root = r;
      g('km-q').addEventListener('input', ve);
      g('km-loc-muc').addEventListener('change', ve);
      g('km-them').addEventListener('click', them);
      await tai();
    },
    onLang() { if (root) tai().catch(EPL.baoLoi); },
  };
})();
