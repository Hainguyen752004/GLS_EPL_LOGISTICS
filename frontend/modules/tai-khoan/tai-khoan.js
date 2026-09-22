/* Tài khoản — chỉ admin. Tạo người dùng, đổi vai, đặt lại mật khẩu, khoá. */
(function () {
  const { API, NN, esc } = EPL;
  const VAI = ['yard', 'acct', 'expacct', 'fuel', 'parts', 'repair', 'treasury', 'cash', 'rev', 'admin'];
  let root, ds = [];

  function ve() {
    root.querySelector('#tk-than').innerHTML = ds.map((u, i) => `<tr class="${u.active ? '' : 'tk-tat'}">
      <td>${i + 1}</td><td class="mono">${esc(u.username)}</td><td><span class="tk-av">${esc(u.avatar)}</span><b lang="lo">${esc(u.full_name)}</b></td>
      <td>${NN.h('r_' + u.role)}</td><td>${EPL.tag(u.active ? 'ok' : 'plain', u.active ? 'active' : 'inactive')}</td>
      <td><button class="btn sm" data-sua="${u.id}">${NN.h('edit')}</button></td></tr>`).join('');
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
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
  async function tai() { ds = await API.get('/api/users'); ve(); }
  EPL.modules['tai-khoan'] = {
    async init(r) { root = r; r.querySelector('#tk-them').addEventListener('click', () => sua(null)); await tai(); },
    onLang() { if (root) ve(); },
  };
})();
