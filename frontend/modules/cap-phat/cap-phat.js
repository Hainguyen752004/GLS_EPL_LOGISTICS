/* Cấp phát — người cấp đối chiếu rồi cấp dầu / chi tiền theo phiếu lĩnh có mã QR.
 *
 * Hai loại phiếu đi vào đây:
 *   Phiếu lĩnh nhiên liệu  → thủ kho của ĐÚNG kho đó cấp dầu, hệ sinh phiếu xuất kho ngay.
 *   Phiếu tạm ứng đi đường → quỹ chi tiền mặt; mục IV phải "đã ghi sổ" trước, không thì máy chủ chặn.
 *
 * Mở bằng #/cap-phat?ma=<mã QR> — đó chính là địa chỉ nằm trong mã QR in trên tờ phiếu.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], loai = '', P = null;
  const q = (s) => root.querySelector(s);

  function nhan(v) { return v.kind === 'fuel' ? NN.h('v_fuel') : NN.h('v_advance'); }
  function tien(v) {
    return v.kind === 'fuel' ? so(v.qty_l, 1) + ' L' : so(v.amount_lak) + ' LAK';
  }
  function capDuoc(v) {
    if (AUTH.la()) return true;                                   // admin
    return v.kind === 'fuel' ? AUTH.role === 'depot' || AUTH.role === 'fuel'
      : ['cash', 'treasury'].includes(AUTH.role);
  }

  function ve() {
    const ds = DS.filter(v => !loai || v.kind === loai);
    q('#cp-dem').textContent = ds.length ? String(ds.length) : '';
    q('#cp-than').innerHTML = ds.length ? ds.map(v => `<tr data-v="${v.id}" class="${P && P.id === v.id ? 'chon' : ''}">
      <td class="mono">${esc(v.doc_no)}</td><td>${nhan(v)}</td><td>${esc(v.truck_no || '—')}</td>
      <td lang="lo">${esc(v.driver_name || '—')}</td><td lang="lo">${esc(v.place_name || '—')}</td>
      <td class="num">${tien(v)}</td>
      <td class="no-print">${capDuoc(v) ? `<button class="btn sm ok" data-cap="${v.id}">${NN.h('v_issue')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('v_empty')}</td></tr>`;
    q('#cp-than').querySelectorAll('tr[data-v]').forEach(tr => tr.addEventListener('click', e => {
      if (e.target.closest('[data-cap]')) return;
      xem(tr.dataset.v);
    }));
    q('#cp-than').querySelectorAll('[data-cap]').forEach(b => b.addEventListener('click', () => moCap(DS.find(v => v.id === b.dataset.cap))));
  }

  /** Khối đối chiếu: đúng xe, đúng tài xế, đúng chuyến — người cấp nhìn cái này trước khi cấp. */
  function veChiTiet() {
    q('#cp-xem').hidden = !P;
    if (!P) return;
    const p = P.phieu || {};
    q('#cp-tt').innerHTML = tag(P.status === 'cho' ? 'plain' : P.status === 'da_cap' ? 'paid' : 'partial', 'v_' + P.status);
    const o = (k, v, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(v == null || v === '' ? '—' : v)}</span></div>`;
    q('#cp-chi-tiet').innerHTML = `
      <div class="cp-dau"><div><b class="mono">${esc(P.doc_no)}</b><div class="small muted">${nhan(P)} · ${EPL.ngay(P.doc_date)}</div></div>
        <div class="cp-tien">${tien(P)}</div></div>
      <div class="cp-o">
        ${o('truck_no', p.truck_no)}${o('driver', p.driver_name, true)}
        ${o('plate_head', p.plate_head, true)}${o('plate_trailer', p.plate_trailer, true)}
        ${o('doc_no', p.doc_no)}${o('customer', p.customer_name, true)}
        ${o('route', (p.origin || '') + ' → ' + (p.destination || ''), true)}
        ${P.place_name ? o('fp_place', P.place_name, true) : ''}
      </div>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th data-i18n="item"></th><th class="num">${NN.h('qty')}</th>
        <th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th><th>${NN.h('acct_code')}</th></tr></thead>
        <tbody>${(P.dong || []).map(d => `<tr><td lang="lo">${esc(EPL.khoanMuc(d))}</td><td class="num">${so(d.qty, 1)}</td>
          <td class="num">${so(d.unit_price)}${d.currency !== 'LAK' ? ' ' + esc(d.currency) : ''}</td>
          <td class="num">${so(d.tien_lak)}</td><td><span class="acct">${esc(d.acct_code || '')}</span></td></tr>`).join('')
        || `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>
      ${P.status === 'da_cap' ? `<div class="cp-xong">${NN.h('v_granted_by')}: <b lang="lo">${esc(P.granted_by || '')}</b> · ${EPL.ngayGio(P.granted_at)}
        ${P.granted_qty != null ? ' · ' + NN.h('v_qty_real') + ': <b>' + so(P.granted_qty, 1) + ' L</b>' : ''}
        ${P.granted_note ? '<div class="small muted" lang="lo">' + esc(P.granted_note) + '</div>' : ''}</div>` : ''}
      <div class="cp-nut no-print">
        ${P.status === 'cho' && capDuoc(P) ? `<button class="btn primary" id="cp-cap">${NN.h(P.kind === 'fuel' ? 'v_issue_fuel' : 'v_issue_cash')}</button>` : ''}
        <button class="btn" id="cp-mo-phieu">${NN.h('open_slip')}</button>
      </div>`;
    const nut = q('#cp-cap'); if (nut) nut.addEventListener('click', () => moCap(P));
    q('#cp-mo-phieu').addEventListener('click', () => EPL.di('phieu-xuat-xe?id=' + P.trip_id));
  }

  async function xem(id) {
    const v = DS.find(x => x.id === id);
    if (!v) return;
    try { P = await API.get('/api/vouchers/tra-cuu/' + v.token); ve(); veChiTiet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function xemTheoMa(ma) {
    try { P = await API.get('/api/vouchers/tra-cuu/' + encodeURIComponent(ma)); ve(); veChiTiet(); q('#cp-xem').scrollIntoView({ block: 'nearest' }); }
    catch (e) { P = null; veChiTiet(); EPL.toast(e.status === 404 ? NN.t('v_not_found') : e.message, 'loi'); }
  }

  async function moCap(v) {
    if (!v) return;
    if (v.kind !== 'fuel') {
      // Chi tiền: không có gì để đối số lượng, chỉ hỏi cho chắc rồi gọi.
      const ok = await EPL.hoi(NN.t('v_issue_cash'),
        `<b class="mono">${esc(v.doc_no)}</b> · <b>${so(v.amount_lak)} LAK</b><div class="small muted" lang="lo">${esc(v.driver_name || '')}</div>`,
        NN.t('v_issue_cash'));
      if (!ok) return;
      return cap(v, {});
    }
    const dlg = q('#cp-hop');
    q('#cp-hop-tieu-de').textContent = NN.t('v_issue_fuel');
    q('#cp-hop-tom').innerHTML = `<b class="mono">${esc(v.doc_no)}</b> · ${esc(v.truck_no || '')} · <span lang="lo">${esc(v.place_name || '')}</span>`;
    q('#cp-f-duyet').value = v.qty_l == null ? '' : v.qty_l;
    q('#cp-f-that').value = v.qty_l == null ? '' : v.qty_l;
    q('#cp-f-ly-do').value = '';
    q('#cp-hop-ok').textContent = NN.t('v_issue_fuel');
    NN.apDung(dlg); dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const that = EPL.doc(q('#cp-f-that').value), ly = q('#cp-f-ly-do').value.trim();
      if (that <= 0) return EPL.toast(NN.t('v_qty_real') + '?', 'loi');
      if (Math.abs(that - (v.qty_l || 0)) > 0.001 && !ly) return EPL.toast(NN.t('v_reason') + '?', 'loi');
      cap(v, { qty: that, note: ly });
    });
    dlg.showModal();
  }

  async function cap(v, body) {
    try {
      await API.post('/api/vouchers/' + v.id + '/cap', body);
      EPL.toast(NN.t('saved'), 'ok');
      await tai();
      if (P && P.id === v.id) await xemTheoMa(v.token);
    } catch (e) { EPL.baoLoi(e); }
  }

  async function tai() {
    DS = await API.get('/api/vouchers?trang_thai=cho');
    ve();
  }

  EPL.modules['cap-phat'] = {
    async init(r, ctx) {
      root = r;
      r.querySelectorAll('.cp-tab button').forEach(b => b.addEventListener('click', () => {
        r.querySelectorAll('.cp-tab button').forEach(x => x.classList.toggle('active', x === b));
        loai = b.dataset.loai; ve();
      }));
      // Ô mã: quét QR bằng máy quét cầm tay cũng chỉ là gõ chữ rồi Enter.
      const o = r.querySelector('#cp-ma');
      o.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const t = o.value.trim(); if (!t) return;
        xemTheoMa(t.includes('ma=') ? t.split('ma=').pop() : t);
        o.value = '';
      });
      if (AUTH.role === 'depot') q('#cp-kho').textContent = NN.t('fp_keeper');
      await tai();
      const ma = ctx && ctx.tham && ctx.tham.ma;
      if (ma) await xemTheoMa(ma);
    },
    onLang() { if (root) { ve(); veChiTiet(); } },
  };
})();
