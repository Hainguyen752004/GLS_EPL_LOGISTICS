/* Tài khoản — chỉ admin. Người dùng (tạo, đổi vai, đặt lại mật khẩu, khoá) và Vai trò & trách nhiệm (mỗi vai làm
 * công đoạn nào, vào màn nào, quyền trên phiếu, thấy tiền không, sinh chứng từ nào). */
(function () {
  const { API, NN, esc } = EPL;
  const VAI = ['yard', 'acct', 'expacct', 'fuel', 'parts', 'repair', 'treasury', 'cash', 'rev', 'admin'];
  // Tóm tắt bằng lời theo bảng Nhiệm Vụ của khách — một câu cho mỗi vai
  const LAM = {
    yard: 'Lập phiếu xuất xe tại bãi: xe, tài xế, khách, tuyến, cân, số lít, khoản đi đường. Không thấy và không nhập tiền.',
    acct: 'Kiểm mục I, II; nhập số phiếu quặng, giá cước, giá thuê xe liên kết; khoá phiếu; điều khoản chủ xe; đẩy chứng từ.',
    expacct: 'Nhập đơn giá rồi kiểm và ghi sổ mục IV, V, VI; lệnh sửa chữa; nhà cung cấp; tất toán tài xế.',
    fuel: 'Nhập đơn giá dầu mua ngoài; kiểm và ghi sổ mục III; duyệt khai đổ dầu. Nhập, xuất, chuyển kho dầu — ở trang kế toán (Kho → Kho nhiên liệu).',
    depot: 'Quét QR phiếu đề nghị xuất nguyên liệu, cấp dầu tại một kho — làm ở trang kế toán (Kho → Cấp phát).',
    parts: 'Nhập, xuất kho phụ tùng Thà Bốc — làm ở trang kế toán (Kho → Kho phụ tùng).',
    repair: 'Duyệt báo hỏng của tài xế, lập lệnh sửa chữa; quyết lấy phụ tùng kho hay mua ngoài.',
    treasury: 'Thủ quỹ Viêng Chăn: chi mục III, trả chủ xe, trả nhà cung cấp, thu bán hàng.',
    cash: 'Quỹ tiền mặt cảng cạn Thà Bốc: chi tạm ứng, chi mục V, VI, trả chủ xe.',
    rev: 'Lập hoá đơn (lẻ, gộp tháng), ghi thu tiền khách, cấn trừ cuối tháng; lập phiếu bán hàng.',
    driver: 'Xem phiếu của mình, nhận tạm ứng, xuất phát, báo hỏng, khai số lít dầu đổ dọc đường.',
    admin: 'Sếp: xem và làm được mọi việc, mở khoá mục đã duyệt, cấu hình kế toán.',
  };
  let root, ds = [], D = null;
  const q = (s) => root.querySelector(s);

  function ve() {
    q('#tk-than').innerHTML = ds.map((u, i) => `<tr class="${u.active ? '' : 'tk-tat'}">
      <td>${i + 1}</td><td class="mono">${esc(u.username)}</td><td><span class="tk-av">${esc(u.avatar)}</span><b lang="lo">${esc(u.full_name)}</b></td>
      <td><button class="tk-vai-nut" data-den-vai="${u.role}">${NN.h('r_' + u.role)}</button></td>
      <td class="small muted tk-lam">${esc(LAM[u.role] || '')}</td>
      <td>${EPL.tag(u.active ? 'ok' : 'plain', u.active ? 'active' : 'inactive')}</td>
      <td><button class="btn sm" data-sua="${u.id}">${NN.h('edit')}</button></td></tr>`).join('');
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
    root.querySelectorAll('[data-den-vai]').forEach(b => b.addEventListener('click', () => { doiTab('vai'); const o = q('#tk-v-' + b.dataset.denVai); if (o) { o.scrollIntoView({ block: 'start' }); o.classList.add('soi'); setTimeout(() => o.classList.remove('soi'), 1600); } }));
  }

  /* ---------------------------------------------------------------- vai trò */
  async function napQuyTrinh() {
    // công đoạn nằm ở màn Quy trình — nạp tệp của màn đó một lần nếu chưa mở
    if (!EPL.QUY_TRINH) await new Promise(ok => { const s = document.createElement('script'); s.src = 'modules/quy-trinh/quy-trinh.js'; s.onload = ok; s.onerror = ok; document.head.appendChild(s); });
    if (!D) D = await API.get('/api/quy-trinh');
  }
  function veVai() {
    if (!D) return;
    const QT = EPL.QUY_TRINH || { CHUYEN: [], NGOAI: [], VIEC: [] };
    const buoc = [...QT.CHUYEN, ...QT.NGOAI].flatMap(g => g.buoc);
    const MUC = [['info', 'I'], ['trans', 'II'], ['fuel', 'III'], ['travel', 'IV'], ['repair', 'V'], ['other', 'VI']];
    const ctTen = (ma) => (D.chung_tu.find(c => c.ma === ma) || {}).ten || ma;
    const vaiDs = [...D.vai.filter(v => v !== 'admin'), 'admin'];
    q('#tk-vai-ds').innerHTML = vaiDs.map(v => {
      const nguoi = ds.filter(u => u.role === v);
      const cua = buoc.filter(b => b.vai.includes(v));
      const ct = [...new Set(cua.flatMap(b => b.ct || []))];
      const man = (EPL.manCuaVai ? EPL.manCuaVai(v) : []).map(m => NN.h(m.nav));
      const p = D.quyen[v] || {}, t = { ...(D.tien[v] || {}) };
      // nhập đơn giá THẬT: được phép và có nhập / kiểm một mục chi III–VI (giống ma trận ở màn Quy trình)
      t.nhap_gia = t.nhap_gia && ['fuel', 'travel', 'repair', 'other'].some(m => (p.edit || []).includes(m) || (p.verify || []).includes(m));
      const o = (k) => MUC.filter(([m]) => (p[k] || []).includes(m)).map(x => x[1]).join(' · ') || '—';
      const viec = (QT.VIEC || []).filter(([, ai]) => ai.includes(v)).map(([ten]) => ten);
      return `<article class="card tk-the" id="tk-v-${v}">
        <div class="hd"><h3>${NN.h('r_' + v)}</h3><div class="grow"></div><span class="small muted">${nguoi.length} người</span></div>
        <div class="bd">
          <p class="tk-mo">${esc(LAM[v] || '')}</p>
          <div class="tk-nguoi">${nguoi.length ? nguoi.map(u => `<span class="tk-chip ${u.active ? '' : 'tat'}"><b class="mono">${esc(u.username)}</b> <span lang="lo">${esc(u.full_name)}</span></span>`).join('') : '<span class="muted small">chưa có tài khoản</span>'}</div>
          <div class="tk-hai">
            <div><div class="l">Trên phiếu xuất xe</div>
              <table class="tk-q"><tr><td>Nhập</td><td>${o('edit')}</td></tr><tr><td>Kiểm</td><td>${o('verify')}</td></tr><tr><td>Ghi sổ</td><td>${o('book')}</td></tr><tr><td>Chi tiền</td><td>${o('pay')}</td></tr></table>
              <div class="l">Tiền</div>
              <div class="tk-tien">${[['thay_tien_ban', 'thấy tiền bán'], ['thay_tien_chi', 'thấy tiền chi'], ['nhap_gia', 'nhập đơn giá']].map(([k, ten]) => `<span class="${t[k] ? 'co' : 'khong'}">${t[k] ? '✓' : '✗'} ${ten}</span>`).join('')}</div>
            </div>
            <div><div class="l">Màn vào được (${man.length})</div><div class="tk-man">${man.join(' · ') || '—'}</div>
              ${viec.length ? `<div class="l">Việc ngoài phiếu</div><ul>${viec.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</div>
          </div>
          <div class="l">Công đoạn làm (${cua.length})</div>
          <ol class="tk-buoc">${cua.map(b => `<li><b>${esc(String(b.so))}.</b> ${esc(b.ten)}</li>`).join('') || '<li class="muted">—</li>'}</ol>
          <div class="l">Chứng từ sinh ra ở các công đoạn đó</div>
          <div class="tk-ct">${ct.map(ma => `<button class="tk-ctb" data-mo-ct="${ma}"><b>${ma}</b> ${esc(ctTen(ma))}</button>`).join(' ') || '<span class="muted small">không sinh chứng từ</span>'}</div>
        </div></article>`;
    }).join('');
    root.querySelectorAll('[data-mo-ct]').forEach(b => b.addEventListener('click', () => EPL.di('quy-trinh')));
  }
  function doiTab(t) {
    root.querySelectorAll('.tk-tab button').forEach(b => b.classList.toggle('active', b.dataset.tk === t));
    q('#tk-nguoi').hidden = t !== 'nguoi'; q('#tk-vai').hidden = t !== 'vai'; q('#tk-them').hidden = t !== 'nguoi';
    q('#tk-lt').hidden = t !== 'lt';
    if (t === 'lt') napLienThong().catch(EPL.baoLoi);
  }

  /* ---------------------------------------------------------------- liên thông trang kế toán (28/09) */
  async function napLienThong() {
    const c = await API.get('/api/ke-toan/cau-hinh');
    q('#tk-lt-api').value = c.ke_toan_api || '';
    q('#tk-lt-web').value = c.ke_toan_web || '';
    q('#tk-lt-day').placeholder = NN.t(c.co_token ? 'tk_lt_co' : 'tk_lt_chua');
    q('#tk-lt-nhan').innerHTML = EPL.tag(c.co_token_nhan_ke_toan ? 'ok' : 'plain', c.co_token_nhan_ke_toan ? 'tk_lt_co' : 'tk_lt_chua');
  }
  function ganLienThong() {
    q('#tk-lt-luu').addEventListener('click', async () => {
      const body = { ke_toan_api: q('#tk-lt-api').value.trim(), ke_toan_web: q('#tk-lt-web').value.trim() };
      const k = q('#tk-lt-day').value.trim(); if (k) body.ke_toan_token = k;
      try { await API.put('/api/ke-toan/cau-hinh', body); q('#tk-lt-day').value = ''; EPL.toast(NN.t('saved'), 'ok'); await napLienThong(); }
      catch (e) { EPL.baoLoi(e); }
    });
    q('#tk-lt-tao').addEventListener('click', async () => {
      if (!await EPL.hoi(NN.t('tk_lt_tao'), esc(NN.t('tk_lt_tao_hint')), NN.t('tk_lt_tao'))) return;
      try { const g = await API.post('/api/lien-thong/tao-khoa', {}); const o = q('#tk-lt-khoa'); o.textContent = g.token_nhan_ke_toan; o.hidden = false; await napLienThong(); }
      catch (e) { EPL.baoLoi(e); }
    });
    q('#tk-lt-thu').addEventListener('click', async () => {
      const o = q('#tk-lt-kq'); o.textContent = '…';
      try { const g = await API.get('/api/lien-thong/thu');
        o.innerHTML = g.ok ? `<span class="tag ok">${esc(NN.t('tk_lt_ok').replace('{ms}', g.ms).replace('{u}', (g.ben_kia || {}).nguoi || '?'))}</span>`
          : `<span class="tag loi">${esc(NN.t('tk_lt_hong').replace('{loi}', g.loi || g.ma || ''))}</span>`;
      } catch (e) { o.textContent = NN.t('tk_lt_hong').replace('{loi}', e.message || ''); }
    });
  }

  async function sua(u) {
    const v = await EPL.hopNhap(u ? NN.t('edit') : NN.t('add'), [
      ...(u ? [] : [{ id: 'username', label: 'username', value: '' }]),
      { id: 'full_name', label: 'full_name', value: u ? u.full_name : '', lo: true },
      { id: 'avatar', label: 'avatar', value: u ? u.avatar : '' },
      { id: 'role', label: 'role', type: 'select', value: u ? u.role : 'yard', options: VAI.map(r => [r, NN.t('r_' + r)]) },
      { id: 'password', label: u ? 'new_password' : 'password', type: 'password', value: '' },
      ...(u ? [{ id: 'active', label: 'status', type: 'select', value: u.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    try {
      const body = { full_name: v.full_name, avatar: v.avatar, role: v.role };
      if (v.password) body.password = v.password;
      if (u) body.active = v.active === '1'; else body.username = v.username;
      if (!u && (!v.username.trim() || !v.password)) return EPL.toast(NN.t('username') + ' / ' + NN.t('password') + '?', 'loi');
      await (u ? API.put('/api/users/' + u.id, body) : API.post('/api/users', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/users'); ve(); veVai(); }
  EPL.modules['tai-khoan'] = {
    async init(r) {
      root = r;
      q('#tk-them').addEventListener('click', () => sua(null));
      ganLienThong();
      root.querySelectorAll('.tk-tab button').forEach(b => b.addEventListener('click', () => doiTab(b.dataset.tk)));
      await napQuyTrinh().catch(() => {});
      await tai(); doiTab('nguoi');
    },
    onLang() { if (root) { ve(); veVai(); } },
  };
})();
