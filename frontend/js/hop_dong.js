/* Hợp đồng — ສັນຍາ (chủ dự án chốt 24/09). Khối dùng chung cho màn Khách hàng (hợp đồng vận chuyển) và màn Xe liên
 * kết · Chủ xe (hợp đồng thuê xe): danh sách hợp đồng của MỘT đối tác, thêm · sửa · ngưng dùng · xoá · đưa bản scan.
 * Điều khoản tính tiền vẫn ở bảng giá / điều khoản chủ xe — ở đây chỉ là giấy khung: số, ngày ký, hiệu lực, bản scan.
 *
 *   EPL.hopDong.mo(khung, { kind: 'khach' | 'thue_xe', doiTacId, ten, suaDuoc, onDoi })   vẽ khối vào `khung`
 *   EPL.hopDong.hienHanh(ds, doiTacId)     hợp đồng đang dùng của đối tác (để hiện ở cột danh sách)
 *   EPL.hopDong.nhan(h)                    "HĐ-… · tag trạng thái" hoặc "—"
 */
(function () {
  const { API, NN, esc } = EPL;
  const THU_TU = { con_han: 0, sap_het: 1, chua_hieu_luc: 2, het_han: 3, ngung: 4 };
  const tag = (st) => EPL.tag('hd_' + st, 'hd_' + st);

  function hienHanh(ds, doiTacId) {
    const cua = (ds || []).filter(h => (h.customer_id || h.owner_id) === doiTacId);
    cua.sort((a, b) => (THU_TU[a.trang_thai] - THU_TU[b.trang_thai]) || String(b.valid_from || b.sign_date || '').localeCompare(String(a.valid_from || a.sign_date || '')));
    return cua[0] || null;
  }
  const nhan = (h) => h ? `<span class="mono">${esc(h.contract_no)}</span> ${tag(h.trang_thai)}` : '<span class="muted">—</span>';

  async function mo(khung, o) {
    const ve = async () => {
      let ds = [];
      try { ds = await API.get(`/api/hop-dong?kind=${o.kind}&${o.kind === 'khach' ? 'customer_id' : 'owner_id'}=${encodeURIComponent(o.doiTacId)}`); }
      catch (e) { return EPL.baoLoi(e); }
      const tk = API.token(), sua = o.suaDuoc;
      khung.hidden = false;
      khung.innerHTML = `<div class="hd-dau">
          <div><h3>${esc(NN.t(o.kind === 'khach' ? 'hd_cua_khach' : 'hd_cua_chu_xe').replace('{n}', o.ten))}</h3>
            <div class="small muted">${NN.h(o.kind === 'khach' ? 'hd_mota_khach' : 'hd_mota_thue')}</div></div>
          <div class="grow"></div>
          ${sua ? `<button class="btn primary sm" data-hd-them><span>+ ${NN.h('add')}</span></button>` : ''}
          <button class="btn sm" data-hd-dong>${NN.h('close')}</button>
        </div>
        <div class="tbl-wrap"><table class="tbl">
          <thead><tr><th data-i18n="hd_so"></th><th data-i18n="hd_ngay_ky"></th><th data-i18n="hd_tu"></th><th data-i18n="hd_den"></th>
            <th data-i18n="status"></th><th class="num" data-i18n="hd_so_phieu"></th><th data-i18n="hd_scan"></th><th data-i18n="note"></th>
            <th class="no-print" data-i18n="actions"></th></tr></thead>
          <tbody>${ds.length ? ds.map(h => `<tr class="${h.active ? '' : 'kh-tat'}">
            <td class="mono"><b>${esc(h.contract_no)}</b></td><td>${EPL.ngay(h.sign_date)}</td><td>${EPL.ngay(h.valid_from)}</td>
            <td>${h.valid_to ? EPL.ngay(h.valid_to) : `<span class="muted">${NN.h('hd_vo_han')}</span>`}</td>
            <td>${tag(h.trang_thai)}${h.ngay_con != null && h.trang_thai === 'sap_het' ? ` <span class="small muted">${NN.h('hd_con_n_ngay', { n: h.ngay_con })}</span>` : ''}</td>
            <td class="num">${h.so_phieu}</td>
            <td>${h.files ? h.files.map(f => `<a class="hd-tep" href="${esc(f.url)}?tk=${encodeURIComponent(tk)}" target="_blank" rel="noopener" title="${esc(f.filename)}">${f.la_anh ? '🖼' : 'PDF'} ${esc(f.filename)}</a>${sua ? ` <button class="x" data-hd-xoa-tep="${f.id}" title="${esc(NN.t('delete'))}">×</button>` : ''}`).join('<br>') : `<span class="muted small">${NN.h('hd_scan_an')}</span>`}
              ${sua ? `<label class="btn sm quiet">+ ${NN.h('attach_add')}<input type="file" accept="image/*,application/pdf" data-hd-tep="${h.id}" hidden></label>` : ''}</td>
            <td class="small muted">${esc(h.note || '')}</td>
            <td class="no-print">${sua ? `<button class="btn sm" data-hd-sua="${h.id}">${NN.h('edit')}</button>${h.so_phieu ? '' : ` <button class="btn sm" data-hd-xoa="${h.id}">${NN.h('delete')}</button>`}` : ''}</td></tr>`).join('')
            : `<tr><td colspan="9" class="empty">${NN.h('hd_trong')}</td></tr>`}</tbody></table></div>`;
      NN.apDung(khung);
      khung.querySelector('[data-hd-dong]').addEventListener('click', () => { khung.hidden = true; khung.innerHTML = ''; if (o.onDoi) o.onDoi(); });
      const them = khung.querySelector('[data-hd-them]'); if (them) them.addEventListener('click', () => sua1(null));
      khung.querySelectorAll('[data-hd-sua]').forEach(b => b.addEventListener('click', () => sua1(ds.find(h => h.id === b.dataset.hdSua))));
      khung.querySelectorAll('[data-hd-xoa]').forEach(b => b.addEventListener('click', async () => {
        const h = ds.find(x => x.id === b.dataset.hdXoa);
        if (!await EPL.hoi(NN.t('delete'), `<p class="mono">${esc(h.contract_no)}</p>`, NN.t('delete'))) return;
        try { await API.goi('/api/hop-dong/' + h.id, { method: 'DELETE' }); EPL.toast(NN.t('saved'), 'ok'); await ve(); if (o.onDoi) o.onDoi(); } catch (e) { EPL.baoLoi(e); }
      }));
      khung.querySelectorAll('[data-hd-tep]').forEach(inp => inp.addEventListener('change', async () => {
        const f = inp.files && inp.files[0]; if (!f) return;
        let nen; try { nen = await EPL.nenTep(f); } catch (e) { return EPL.baoLoi(e); }
        const fd = new FormData(); fd.append('tep', nen, nen.name);
        try { await API.tep(`/api/hop-dong/${inp.dataset.hdTep}/tep`, fd); EPL.toast(NN.t('saved'), 'ok'); await ve(); } catch (e) { EPL.baoLoi(e); }
      }));
      khung.querySelectorAll('[data-hd-xoa-tep]').forEach(b => b.addEventListener('click', async () => {
        if (!await EPL.hoi(NN.t('delete'), `<p>${NN.h('attach_del')}</p>`, NN.t('delete'))) return;
        try { await API.goi('/api/hop-dong-tep/' + b.dataset.hdXoaTep, { method: 'DELETE' }); await ve(); } catch (e) { EPL.baoLoi(e); }
      }));
      if (khung.scrollIntoView) khung.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    };
    const sua1 = async (h) => {
      const v = await EPL.hopNhap(NN.t(h ? 'hd_sua' : 'hd_them'), [
        { id: 'contract_no', label: 'hd_so', value: h ? h.contract_no : '' },
        { id: 'sign_date', label: 'hd_ngay_ky', type: 'date', value: h ? (h.sign_date || '') : EPL.homNay() },
        { id: 'valid_from', label: 'hd_tu', type: 'date', value: h ? (h.valid_from || '') : EPL.homNay() },
        { id: 'valid_to', label: 'hd_den', type: 'date', value: h ? (h.valid_to || '') : '' },
        { id: 'active', label: 'status', type: 'select', value: h && !h.active ? '0' : '1', options: [['1', NN.t('active')], ['0', NN.t('hd_ngung')]] },
        { id: 'note', label: 'note', value: h ? (h.note || '') : '' },
      ], NN.t('save'));
      if (!v) return;
      const body = { ...v, active: v.active === '1', kind: o.kind, [o.kind === 'khach' ? 'customer_id' : 'owner_id']: o.doiTacId };
      try {
        await (h ? API.put('/api/hop-dong/' + h.id, body) : API.post('/api/hop-dong', body));
        EPL.toast(NN.t('saved'), 'ok'); await ve(); if (o.onDoi) o.onDoi();
      } catch (e) { EPL.baoLoi(e); }
    };
    await ve();
  }

  EPL.hopDong = { mo, hienHanh, nhan };
})();
