/* Cấp phát — người cấp đối chiếu rồi cấp dầu / chi tiền theo phiếu lĩnh có mã QR.
 *
 * Hai loại phiếu đi vào đây:
 *   Phiếu lĩnh nhiên liệu  → thủ kho của ĐÚNG kho đó cấp dầu, hệ sinh phiếu xuất kho ngay.
 *   Phiếu tạm ứng đi đường → quỹ chi tiền mặt; mục IV phải "đã ghi sổ" trước, không thì máy chủ chặn.
 *
 * Mở bằng #/cap-phat?ma=<mã QR> — đó chính là địa chỉ nằm trong mã QR in trên tờ phiếu.
 *
 * ======================== CHẠY ĐƯỢC KHI MẤT MẠNG ========================
 * Kho dầu ngoài hiện trường không phải lúc nào cũng có mạng, nhưng xe thì vẫn tới. Nên màn này:
 *
 *   1. Còn mạng  → tải danh sách phiếu chờ VÀ chi tiết từng phiếu, lưu đệm vào máy (localStorage).
 *   2. Mất mạng  → quét mã vẫn tra ra được từ bản đệm, có ghi rõ "bản lưu lúc …".
 *   3. Bấm Cấp khi mất mạng → xếp vào HÀNG ĐỢI trong máy, dòng đó hiện "chờ gửi".
 *   4. Có mạng lại → tự gửi hàng đợi lên máy chủ, việc nào máy chủ từ chối thì báo rõ để xem lại.
 *
 * Cố ý KHÔNG nhồi số liệu vào mã QR để giải bài toán này: số liệu còn đổi sau lúc in, nhồi vào là
 * tờ giấy nói một đằng hệ thống nói một nẻo. Bản đệm trong máy luôn mới hơn tờ giấy.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], loai = '', P = null, demLuc = null, dangGui = false;
  const q = (s) => root.querySelector(s);

  /* ----------------------------------------------------------------- bộ nhớ trong máy */
  const KHOA = () => 'epl_lao_cap_phat_' + (AUTH.user ? AUTH.user.id : 'x');
  const KHOA_HANG = () => 'epl_lao_cap_phat_hang_' + (AUTH.user ? AUTH.user.id : 'x');
  function docKho(k, macDinh) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : macDinh; } catch (e) { return macDinh; }
  }
  function ghiKho(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* hết chỗ thì thôi */ } }
  const hangDoi = () => docKho(KHOA_HANG(), []);
  const datHang = (h) => ghiKho(KHOA_HANG(), h);

  /** Lỗi do MẤT MẠNG chứ không phải máy chủ từ chối. Máy chủ từ chối thì có mã lỗi nghiệp vụ. */
  const laMatMang = (e) => !(e instanceof EPL.LoiAPI) || !e.status;

  /* ----------------------------------------------------------------- vẽ */
  function nhan(v) { return v.kind === 'fuel' ? NN.h('v_fuel') : NN.h('v_advance'); }
  function tien(v) { return v.kind === 'fuel' ? so(v.qty_l, 1) + ' L' : so(v.amount_lak) + ' LAK'; }
  function capDuoc(v) {
    if (AUTH.la()) return true;                                   // admin
    return v.kind === 'fuel' ? AUTH.role === 'depot' || AUTH.role === 'fuel'
      : ['cash', 'treasury'].includes(AUTH.role);
  }
  const dangCho = (id) => hangDoi().some(x => x.id === id);

  function veTrangThaiMang() {
    const h = hangDoi(), o = q('#cp-mang');
    const ngoai = !!demLuc;
    o.hidden = !ngoai && !h.length;
    if (o.hidden) return;
    o.className = 'cp-mang ' + (ngoai ? 'ngoai' : 'cho');
    o.innerHTML = `<div><b>${NN.h(ngoai ? 'off_title' : 'off_online')}</b>
        <div class="small">${ngoai ? NN.h('off_hint') : ''}${demLuc ? ' · ' + NN.h('off_cached', { luc: EPL.ngayGio(demLuc) }) : ''}</div></div>
      <div class="grow"></div>
      ${h.length ? `<span class="cp-dem-hang">${NN.h('off_queued', { n: h.length })}</span>
        <button class="btn sm" id="cp-gui">${NN.h('off_sync')}</button>` : ''}`;
    const b = q('#cp-gui'); if (b) b.addEventListener('click', () => guiHangDoi(true));
  }

  function ve() {
    const ds = DS.filter(v => !loai || v.kind === loai);
    q('#cp-dem').textContent = ds.length ? String(ds.length) : '';
    q('#cp-than').innerHTML = ds.length ? ds.map(v => {
      const cho = dangCho(v.id);
      return `<tr data-v="${v.id}" class="${P && P.id === v.id ? 'chon' : ''} ${cho ? 'cho-gui' : ''}">
      <td class="mono">${esc(v.doc_no)}</td><td>${nhan(v)}</td><td>${esc(v.truck_no || '—')}</td>
      <td lang="lo">${esc(v.driver_name || '—')}</td><td lang="lo">${esc(v.place_name || '—')}</td>
      <td class="num">${tien(v)}</td>
      <td class="no-print">${cho ? `<span class="cp-cho">${NN.h('off_wait')}</span>`
        : capDuoc(v) ? `<button class="btn sm ok" data-cap="${v.id}">${NN.h('v_issue')}</button>` : ''}</td></tr>`;
    }).join('') : `<tr><td colspan="7" class="empty">${NN.h(demLuc && !DS.length ? 'off_none' : 'v_empty')}</td></tr>`;
    q('#cp-than').querySelectorAll('tr[data-v]').forEach(tr => tr.addEventListener('click', e => {
      if (e.target.closest('[data-cap]')) return;
      xem(tr.dataset.v);
    }));
    q('#cp-than').querySelectorAll('[data-cap]').forEach(b => b.addEventListener('click', () => moCap(DS.find(v => v.id === b.dataset.cap))));
    veTrangThaiMang();
  }

  /** Khối đối chiếu: đúng xe, đúng tài xế, đúng chuyến — người cấp nhìn cái này trước khi cấp. */
  function veChiTiet() {
    q('#cp-xem').hidden = !P;
    if (!P) return;
    const p = P.phieu || {};
    const cho = dangCho(P.id);
    q('#cp-tt').innerHTML = cho ? tag('partial', 'off_wait')
      : tag(P.status === 'cho' ? 'plain' : P.status === 'da_cap' ? 'paid' : 'partial', 'v_' + P.status);
    const o = (k, v, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(v == null || v === '' ? '—' : v)}</span></div>`;
    q('#cp-chi-tiet').innerHTML = `
      <div class="cp-dau"><div><b class="mono">${esc(P.doc_no)}</b><div class="small muted">${nhan(P)} · ${EPL.ngay(P.doc_date)}</div></div>
        <div class="cp-tien">${tien(P)}</div></div>
      <div class="cp-o">
        ${o('truck_no', p.truck_no)}${o('driver', p.driver_name || P.driver_name, true)}
        ${o('plate_head', p.plate_head, true)}${o('plate_trailer', p.plate_trailer, true)}
        ${o('doc_no', p.doc_no)}${o('customer', p.customer_name, true)}
        ${o('route', (p.origin || '') + ' → ' + (p.destination || ''), true)}
        ${P.place_name ? o('fp_place', P.place_name, true) : ''}
      </div>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('item')}</th><th class="num">${NN.h('qty')}</th>
        <th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th><th>${NN.h('acct_code')}</th></tr></thead>
        <tbody>${(P.dong || []).map(d => `<tr><td lang="lo">${esc(EPL.khoanMuc(d))}</td><td class="num">${so(d.qty, 1)}</td>
          <td class="num">${so(d.unit_price)}${d.currency !== 'LAK' ? ' ' + esc(d.currency) : ''}</td>
          <td class="num">${so(d.tien_lak)}</td><td><span class="acct">${esc(d.acct_code || '')}</span></td></tr>`).join('')
        || `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>
      ${P.status === 'da_cap' ? `<div class="cp-xong">${NN.h('v_granted_by')}: <b lang="lo">${esc(P.granted_by || '')}</b> · ${EPL.ngayGio(P.granted_at)}
        ${P.granted_qty != null ? ' · ' + NN.h('v_qty_real') + ': <b>' + so(P.granted_qty, 1) + ' L</b>' : ''}
        ${P.granted_note ? '<div class="small muted" lang="lo">' + esc(P.granted_note) + '</div>' : ''}</div>` : ''}
      <div class="cp-nut no-print">
        ${P.status === 'cho' && !cho && capDuoc(P) ? `<button class="btn primary" id="cp-cap">${NN.h(P.kind === 'fuel' ? 'v_issue_fuel' : 'v_issue_cash')}</button>` : ''}
        <button class="btn" id="cp-mo-phieu">${NN.h('open_slip')}</button>
      </div>`;
    const nut = q('#cp-cap'); if (nut) nut.addEventListener('click', () => moCap(P));
    q('#cp-mo-phieu').addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: P.trip_id }));
  }

  /* ----------------------------------------------------------------- tra cứu */
  function tuDem(dieuKien) {
    const d = docKho(KHOA(), null);
    if (!d || !d.chi_tiet) return null;
    return d.chi_tiet.find(dieuKien) || null;
  }
  async function xem(id) {
    const v = DS.find(x => x.id === id);
    if (!v) return;
    await xemTheoMa(v.token);
  }
  async function xemTheoMa(ma) {
    try {
      P = await API.get('/api/vouchers/tra-cuu/' + encodeURIComponent(ma));
    } catch (e) {
      if (!laMatMang(e)) { P = null; veChiTiet(); return EPL.toast(e.status === 404 ? NN.t('v_not_found') : e.message, 'loi'); }
      P = tuDem(x => x.token === ma || x.id === ma);
      if (!P) { veChiTiet(); return EPL.toast(NN.t('v_not_found'), 'loi'); }
      EPL.toast(NN.t('off_cached', { luc: EPL.ngayGio(demLuc) }));
    }
    ve(); veChiTiet();
    const o = q('#cp-xem'); if (o.scrollIntoView) o.scrollIntoView({ block: 'nearest' });
  }

  /* ----------------------------------------------------------------- cấp */
  async function moCap(v) {
    if (!v) return;
    if (v.kind !== 'fuel') {
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
    } catch (e) {
      if (!laMatMang(e)) return EPL.baoLoi(e);
      // Mất mạng: cất vào hàng đợi, xe cứ lấy dầu, số liệu gửi sau.
      const h = hangDoi();
      if (!h.some(x => x.id === v.id)) h.push({ id: v.id, doc_no: v.doc_no, body, luc: new Date().toISOString() });
      datHang(h);
      EPL.toast(NN.t('off_queued', { n: h.length }));
      ve(); veChiTiet();
    }
  }

  /** Gửi hàng đợi lên máy chủ. `bangTay` = người dùng tự bấm, cần báo kết quả rõ. */
  async function guiHangDoi(bangTay) {
    if (dangGui) return;
    let h = hangDoi();
    if (!h.length) return;
    dangGui = true;
    let xong = 0; const hong = [];
    for (const viec of h.slice()) {
      try {
        await API.post('/api/vouchers/' + viec.id + '/cap', viec.body);
        xong += 1;
        h = h.filter(x => x.id !== viec.id); datHang(h);
      } catch (e) {
        if (laMatMang(e)) break;                 // vẫn chưa có mạng, để nguyên hàng đợi
        h = h.filter(x => x.id !== viec.id); datHang(h);
        hong.push(viec.doc_no + ': ' + e.message);
      }
    }
    dangGui = false;
    if (xong) EPL.toast(NN.t('off_synced', { n: xong }), 'ok');
    if (hong.length) {
      await EPL.hoi(NN.t('off_conflict', { n: hong.length }),
        '<ul style="margin:0;padding-left:18px">' + hong.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>', NN.t('ok'));
    }
    if (xong || hong.length || bangTay) await tai();
  }

  /* ----------------------------------------------------------------- tải */
  async function tai() {
    try {
      const ds = await API.get('/api/vouchers?trang_thai=cho');
      // Tải luôn chi tiết từng phiếu để lúc mất mạng vẫn đối chiếu được đúng xe, đúng biển số.
      const chi_tiet = [];
      for (const v of ds) {
        try { chi_tiet.push(await API.get('/api/vouchers/tra-cuu/' + v.token)); } catch (e) { /* bỏ qua tờ lỗi */ }
      }
      DS = ds; demLuc = null;
      ghiKho(KHOA(), { luc: new Date().toISOString(), ds, chi_tiet });
    } catch (e) {
      if (!laMatMang(e)) throw e;
      const d = docKho(KHOA(), null);
      DS = d ? d.ds : [];
      demLuc = d ? d.luc : new Date().toISOString();
    }
    ve();
  }

  let boNghe = null;
  EPL.modules['cap-phat'] = {
    async init(r, ctx) {
      root = r;
      r.querySelectorAll('.cp-tab button').forEach(b => b.addEventListener('click', () => {
        r.querySelectorAll('.cp-tab button').forEach(x => x.classList.toggle('active', x === b));
        loai = b.dataset.loai; ve();
      }));
      // Ô mã: máy quét QR cầm tay cũng chỉ là gõ chữ rồi Enter.
      const o = r.querySelector('#cp-ma');
      o.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const t = o.value.trim(); if (!t) return;
        xemTheoMa(t.includes('ma=') ? t.split('ma=').pop() : t);
        o.value = '';
      });
      if (AUTH.role === 'depot') q('#cp-kho').textContent = NN.t('fp_keeper');
      await tai();
      await guiHangDoi(false);                    // vào màn là gửi nốt việc còn kẹt từ lần trước
      boNghe = () => { tai().then(() => guiHangDoi(false)).catch(() => {}); };
      window.addEventListener('online', boNghe);
      const ma = ctx && ctx.tham && ctx.tham.ma;
      if (ma) await xemTheoMa(ma);
    },
    destroy() { if (boNghe) window.removeEventListener('online', boNghe); boNghe = null; },
    onLang() { if (root) { ve(); veChiTiet(); } },
  };
})();
