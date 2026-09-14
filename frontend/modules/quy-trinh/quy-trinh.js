/* Quy trình & trách nhiệm — đọc từ /api/quy-trinh, là bộ luật thật đang chạy. */
(function () {
  const { API, NN, esc } = EPL;
  const AV = { yard: 'TB', acct: 'KT', fuel: 'KN', treasury: 'QV', cash: 'CE', rev: 'DT', admin: 'AD' };
  let root, d;
  const vai = (ds, cls) => ds.length ? ds.map(v => `<span class="qt-vai ${cls}"><span class="av">${AV[v] || v.slice(0, 2).toUpperCase()}</span><span>${NN.h('r_' + v)}</span></span>`).join('') : '<span class="muted">—</span>';
  const tk = (s) => s ? s.split(' · ').map(a => `<span class="acct">${esc(a)}</span>`).join(' ') : '<span class="muted">—</span>';
  function ve() {
    root.querySelector('#qt-than').innerHTML = d.phieu_xuat_xe.map(r => `<tr><td>${NN.h(r.khoa)}</td><td>${vai(r.nhap, '')}</td><td>${vai(r.kiem, 'kiem')}</td><td>${vai(r.ghi_so, 'kiem')}</td><td>${vai(r.chi, 'chi')}</td><td>${tk(r.acct)}</td></tr>`).join('');
    root.querySelector('#qt-hd').innerHTML = d.hoa_don.map(r => `<tr><td>${NN.h('wf_invoice')}</td><td>${vai(r.nhap, '')}</td><td>${vai(r.kiem, 'kiem')}</td><td>${tk(r.acct)}</td></tr>`).join('');
  }
  EPL.modules['quy-trinh'] = { async init(r) { root = r; d = await API.get('/api/quy-trinh'); ve(); }, onLang() { if (d) ve(); } };
})();
