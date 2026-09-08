(function () {
  'use strict';

  const state = {
    rows: [],
    filtered: [],
    selectedId: '',
    selected: null,
    deliveryOrders: [],
    detailTab: 'items',
    loading: false
  };

  // `draft` ĐÃ BỎ khỏi máy trạng thái ở máy chủ: `generate_from_do` tạo phiếu
  // thẳng ở `ready`, nên không đường nào dẫn tới `draft` cả. Giữ nhãn cho một
  // trạng thái không bao giờ xảy ra là để lại một chỗ cho người sau tưởng nó
  // còn — và họ sẽ viết nhánh xử lý cho một tình huống không tồn tại.
  const statusMeta = {
    ready: ['Sẵn sàng in tem', 'ready'],
    parked: ['Đã vào bãi chờ', 'parked'],
    gate_in: ['Đã qua cổng', 'gate_in'],
    loaded: ['Đã bốc hàng', 'loaded'],
    dispatched: ['Đã xuất bãi', 'dispatched'],
    delivered: ['Đã giao', 'delivered'],
    cancelled: ['Đã hủy', 'cancelled'],
    generated: ['Đã tạo Parking List', 'generated'],
    labels_printed: ['Đã in tem kiện', 'labels_printed'],
    packing_list_printed: ['Đã in Packing List', 'packing_list_printed'],
    // BA loại sự kiện quét, không phải một.
    //
    // Máy chủ trước đây chỉ ghi `package_loaded`, vì hai bước đầu chuyển cả
    // phiếu ngay khi quét MỘT kiện nên không có sự kiện theo từng kiện. Giờ cả
    // ba bước đều đánh dấu từng kiện, nên có `package_parked` và
    // `package_gate_in`. Thiếu nhãn ở đây thì lịch sử phiếu hiện ra mấy dòng
    // trống — người đọc thấy có sự kiện mà không biết là sự kiện gì.
    package_parked: ['Đã quét một kiện vào bãi', 'package_parked'],
    package_gate_in: ['Đã quét một kiện qua cổng', 'package_gate_in'],
    package_loaded: ['Đã bốc một kiện', 'package_loaded']
  };
  const progress = ['ready', 'parked', 'gate_in', 'loaded', 'dispatched', 'delivered'];
  const scanActions = {
    ready: ['yard_arrival', 'Quét QR vào bãi chờ'],
    parked: ['gate_entry', 'Quét QR qua cổng'],
    gate_in: ['load_package', 'Quét tem kiện đã bốc']
  };

  function api(path) {
    const base = typeof API_BASE !== 'undefined' ? API_BASE : '';
    return `${base}${path}`;
  }

  function authHeaders(extra) {
    const base = typeof financeAuthHeaders === 'function' ? financeAuthHeaders() : {};
    return Object.assign({}, base, extra || {});
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function number(value, digits) {
    const parsed = Number(value || 0);
    return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: digits == null ? 2 : digits }).format(parsed);
  }

  function dateTime(value) {
    if (!value) return '-';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? escapeHtml(value) : parsed.toLocaleString('vi-VN');
  }

  function notify(message, severity) {
    if (typeof showToast === 'function') showToast(message, severity || 'info');
  }

  async function request(path, options) {
    const response = await fetch(api(path), Object.assign({}, options || {}, {
      headers: authHeaders(Object.assign({ 'Content-Type': 'application/json' }, options && options.headers))
    }));
    let body = {};
    try { body = await response.json(); } catch (_) { body = {}; }
    if (!response.ok) {
      const detail = body.error && (body.error.message || body.error.code);
      throw new Error(detail || body.detail || body.message || `Máy chủ trả lỗi ${response.status}`);
    }
    return body.data == null ? body : body.data;
  }

  async function loadAllPages() {
    const first = await request('/api/parking-lists?page=1&page_size=100');
    const rows = Array.isArray(first.items) ? first.items.slice() : [];
    const pages = Math.ceil(Number(first.total || rows.length) / 100);
    for (let page = 2; page <= pages; page += 1) {
      const data = await request(`/api/parking-lists?page=${page}&page_size=100`);
      rows.push(...(Array.isArray(data.items) ? data.items : []));
    }
    return rows;
  }

  async function loadDeliveryOrders() {
    const first = await request('/api/delivery-orders?page=1&page_size=200');
    const rows = Array.isArray(first) ? first.slice() : (first.items || first.data || []).slice();
    const pages = Array.isArray(first) ? 1 : Math.ceil(Number(first.total || rows.length) / 200);
    for (let page = 2; page <= pages; page += 1) {
      const payload = await request(`/api/delivery-orders?page=${page}&page_size=200`);
      rows.push(...(Array.isArray(payload) ? payload : (payload.items || payload.data || [])));
    }
    state.deliveryOrders = rows.filter(row => !['cancelled', 'canceled'].includes(String(row.status || '').toLowerCase()));
    renderDeliveryOrderOptions();
  }

  async function load(options) {
    if (state.loading) return;
    state.loading = true;
    const list = document.getElementById('parking-list');
    if (list) list.innerHTML = '<div class="parking-empty"><div><i class="fa-solid fa-spinner fa-spin"></i>Đang tải dữ liệu...</div></div>';
    try {
      state.rows = await loadAllPages();
      filter();
      if (state.selectedId && state.rows.some(row => row.id === state.selectedId)) {
        await select(state.selectedId);
      } else if (state.filtered.length) {
        await select(state.filtered[0].id);
      } else {
        state.selected = null;
        renderDetail();
      }
      if (!(options && options.silent)) notify('Đã tải Parking List từ cơ sở dữ liệu.', 'success');
    } catch (error) {
      if (list) list.innerHTML = `<div class="parking-empty"><div><i class="fa-solid fa-triangle-exclamation"></i>${escapeHtml(error.message)}</div></div>`;
      notify(error.message, 'error');
    } finally {
      state.loading = false;
    }
  }

  function filter() {
    const query = String(document.getElementById('parking-search')?.value || '').trim().toLowerCase();
    const status = String(document.getElementById('parking-status-filter')?.value || '');
    state.filtered = state.rows.filter(row => {
      const text = [row.id, row.do_id, row.store_id, row.store_name, row.route_code, row.route_name].join(' ').toLowerCase();
      return (!query || text.includes(query)) && (!status || row.status === status);
    });
    renderKpis();
    renderList();
  }

  function renderKpis() {
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    set('parking-kpi-total', state.rows.length);
    set('parking-kpi-waiting', state.rows.filter(row => ['ready', 'parked'].includes(row.status)).length);
    set('parking-kpi-loading', state.rows.filter(row => ['gate_in', 'loaded'].includes(row.status)).length);
    set('parking-kpi-dispatched', state.rows.filter(row => ['dispatched', 'delivered'].includes(row.status)).length);
  }

  function statusChip(status) {
    const meta = statusMeta[status] || [status || 'Chưa rõ', ''];
    return `<span class="parking-status ${escapeHtml(meta[1])}">${escapeHtml(meta[0])}</span>`;
  }

  function renderList() {
    const target = document.getElementById('parking-list');
    const count = document.getElementById('parking-list-count');
    if (count) count.textContent = state.filtered.length;
    if (!target) return;
    target.innerHTML = state.filtered.map(row => `
      <button type="button" class="parking-list-row ${row.id === state.selectedId ? 'active' : ''}" onclick="selectParkingList('${escapeHtml(row.id)}')">
        <strong>${escapeHtml(row.id)}</strong>
        <small>DO: ${escapeHtml(row.do_id)} · ${escapeHtml(row.store_name || row.store_id || 'Chưa có điểm nhận')}</small>
        <div class="parking-row-meta">${statusChip(row.status)}<small>${number(row.box_count, 0)} kiện</small></div>
      </button>`).join('') || '<div class="parking-empty"><div><i class="fa-solid fa-box-open"></i>Không có hồ sơ phù hợp bộ lọc.</div></div>';
  }

  async function select(id) {
    state.selectedId = id;
    renderList();
    const target = document.getElementById('parking-detail');
    if (target) target.innerHTML = '<div class="parking-empty"><div><i class="fa-solid fa-spinner fa-spin"></i>Đang mở hồ sơ...</div></div>';
    try {
      state.selected = await request(`/api/parking-lists/${encodeURIComponent(id)}`);
      renderDetail();
    } catch (error) {
      notify(error.message, 'error');
      if (target) target.innerHTML = `<div class="parking-empty"><div>${escapeHtml(error.message)}</div></div>`;
    }
  }

  function renderProgress(item) {
    const current = progress.indexOf(item.status);
    return `<div class="parking-progress">${progress.map((status, index) => `<div class="parking-progress-step ${index <= current ? 'done' : ''}">${escapeHtml(statusMeta[status][0])}</div>`).join('')}</div>`;
  }

  function renderItems(item) {
    const rows = item.items || [];
    return `<div class="parking-table-wrap"><table class="parking-table"><thead><tr><th>STT</th><th>Barcode</th><th>Item ID Laos</th><th>Item ID Thai</th><th>SKU</th><th>Mô tả hàng</th><th>Case</th><th>Piece</th><th>Khối lượng</th></tr></thead><tbody>${rows.map((row, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(row.barcode || '-')}</td><td>${escapeHtml(row.item_id_laos || '-')}</td><td>${escapeHtml(row.item_id_thai || '-')}</td><td>${escapeHtml(row.sku || '-')}</td><td>${escapeHtml(row.description || '-')}</td><td>${number(row.case_qty, 0)}</td><td>${number(row.piece_qty, 0)}</td><td>${number(row.weight_kg)} kg</td></tr>`).join('') || '<tr><td colspan="9">SO/DO chưa có dòng hàng chi tiết.</td></tr>'}</tbody></table></div>`;
  }

  function renderLabels(item) {
    return `<div class="parking-labels-grid">${(item.labels || []).map(label => `<div class="parking-label-tile"><img src="${escapeHtml(api(label.qr_path))}" alt="QR kiện ${label.package_no}"><div><b>Kiện ${label.package_no}/${label.package_total}</b><span>${escapeHtml(label.id)}</span><span>${escapeHtml(statusMeta[label.status]?.[0] || label.status)}</span></div></div>`).join('') || 'Chưa có tem QR.'}</div>`;
  }

  function renderEvents(item) {
    return (item.events || []).slice().reverse().map(event => `<div class="parking-event"><strong>${dateTime(event.occurred_at)}</strong><span>${escapeHtml(statusMeta[event.event_type]?.[0] || event.event_type)}</span><span>${escapeHtml(event.note || event.actor || '-')}</span></div>`).join('') || '<div>Chưa có lịch sử thao tác.</div>';
  }

  function renderTabPane(item) {
    if (state.detailTab === 'labels') return renderLabels(item);
    if (state.detailTab === 'events') return renderEvents(item);
    return renderItems(item);
  }

  function renderDetail() {
    const target = document.getElementById('parking-detail');
    const item = state.selected;
    if (!target) return;
    if (!item) {
      target.innerHTML = '<div class="parking-empty"><div><i class="fa-solid fa-arrow-left"></i>Chọn một hồ sơ để xem hàng hóa, tem QR và lịch sử.</div></div>';
      return;
    }
    const scanAction = scanActions[item.status];
    const labels = item.labels || [];
    const loadedCount = labels.filter(label => ['loaded', 'dispatched', 'delivered'].includes(label.status)).length;
    const systemNote = item.status === 'loaded'
      ? '<div class="parking-auto-note"><i class="fa-solid fa-truck-fast"></i><div><strong>Đã bốc đủ kiện</strong><span>Trạng thái Xuất bãi sẽ tự cập nhật khi chốt điều phối.</span></div></div>'
      : item.status === 'dispatched'
        ? '<div class="parking-auto-note"><i class="fa-solid fa-file-signature"></i><div><strong>Đã xuất bãi</strong><span>Trạng thái Đã giao sẽ tự cập nhật khi hoàn tất POD.</span></div></div>'
        : item.status === 'gate_in'
          ? `<div class="parking-auto-note"><i class="fa-solid fa-boxes-stacked"></i><div><strong>Đã bốc ${loadedCount}/${labels.length} kiện</strong><span>Quét từng tem kiện; hệ thống chỉ hoàn tất khi đủ 100%.</span></div></div>`
          : '';
    target.innerHTML = `
      <div class="parking-detail-header"><div><h3>${escapeHtml(item.id)}</h3><p>DO ${escapeHtml(item.do_id)} · SO ${escapeHtml(item.so_id || '-')} · Version ${number(item.version, 0)}</p></div><div class="parking-detail-actions"><button type="button" class="fiori-btn fiori-btn-secondary" onclick="printParkingLabels()"><i class="fa-solid fa-tags"></i> In tem kiện</button><button type="button" class="fiori-btn fiori-btn-secondary" onclick="printParkingPackingList()"><i class="fa-solid fa-file-lines"></i> In Packing List</button>${scanAction ? `<button type="button" class="fiori-btn fiori-btn-primary" onclick="openParkingScanModal('${scanAction[0]}')"><i class="fa-solid fa-qrcode"></i> ${scanAction[1]}</button>` : ''}</div></div>
      <div class="parking-summary-grid">
        <div class="parking-summary-item"><span>Trạng thái</span><strong>${statusChip(item.status)}</strong></div><div class="parking-summary-item"><span>Cửa hàng</span><strong>${escapeHtml(item.store_name || item.store_id || '-')}</strong></div><div class="parking-summary-item"><span>Tuyến</span><strong>${escapeHtml(item.route_name || item.route_code || '-')}</strong></div><div class="parking-summary-item"><span>Wave / Gate</span><strong>${escapeHtml(item.wave || '-')} / ${escapeHtml(item.gate || '-')}</strong></div>
        <div class="parking-summary-item"><span>Số kiện</span><strong>${number(item.box_count, 0)}</strong></div><div class="parking-summary-item"><span>Tổng pieces</span><strong>${number(item.total_pieces, 0)}</strong></div><div class="parking-summary-item"><span>Khối lượng</span><strong>${number(item.total_weight_kg)} kg</strong></div><div class="parking-summary-item"><span>Thể tích</span><strong>${number(item.total_cube_m3, 4)} m³</strong></div>
      </div>${renderProgress(item)}${systemNote}
      <div class="parking-tabs"><button type="button" class="parking-tab ${state.detailTab === 'items' ? 'active' : ''}" onclick="setParkingDetailTab('items')"><i class="fa-solid fa-table-list"></i> Hàng hóa</button><button type="button" class="parking-tab ${state.detailTab === 'labels' ? 'active' : ''}" onclick="setParkingDetailTab('labels')"><i class="fa-solid fa-qrcode"></i> Tem QR (${(item.labels || []).length})</button><button type="button" class="parking-tab ${state.detailTab === 'events' ? 'active' : ''}" onclick="setParkingDetailTab('events')"><i class="fa-solid fa-clock-rotate-left"></i> Lịch sử</button></div>
      <div class="parking-tab-pane">${renderTabPane(item)}</div>`;
  }

  function renderDeliveryOrderOptions() {
    const select = document.getElementById('parking-do-select');
    if (!select) return;
    const existingCounts = state.rows.reduce((counts, row) => {
      if (row.status !== 'cancelled') counts[row.do_id] = (counts[row.do_id] || 0) + 1;
      return counts;
    }, {});
    const options = state.deliveryOrders.map(row => {
      const existingCount = existingCounts[row.id] || 0;
      const label = `${row.id} · ${row.customer_id || 'Chưa có khách'} · ${row.route_id || 'Chưa có tuyến'}${existingCount ? ` · Đã có ${existingCount} Packing List` : ''}`;
      return `<option value="${escapeHtml(row.id)}">${escapeHtml(label)}</option>`;
    }).join('');
    select.innerHTML = `<option value="">Chọn DO để lấy hàng hóa...</option>${options}`;
  }

  function previewDO() {
    const id = document.getElementById('parking-do-select')?.value || '';
    const row = state.deliveryOrders.find(item => String(item.id) === String(id));
    const preview = document.getElementById('parking-do-preview');
    if (!preview) return;
    if (!row) { preview.textContent = 'Chọn DO để xem khách hàng, tuyến, trọng lượng và số pallet.'; return; }
    preview.innerHTML = `<strong>${escapeHtml(row.id)}</strong><br>Khách hàng: ${escapeHtml(row.customer_id || '-')} · Tuyến: ${escapeHtml(row.route_id || '-')} · ${number(row.weight_kg)} kg · ${number(row.pallet_count, 0)} pallet · ${number(row.volume_m3)} m³`;
    const countInput = document.getElementById('parking-list-count-input');
    if (countInput) {
      const packageCount = Math.max(Number(row.pallet_count || 0), 1);
      countInput.max = String(packageCount);
      countInput.value = String(Math.min(Math.max(Number(countInput.value || 1), 1), packageCount));
    }
  }

  async function openCreateModal() {
    const modal = document.getElementById('parking-create-modal');
    if (!modal) return;
    modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    try { await loadDeliveryOrders(); } catch (error) { notify(error.message, 'error'); }
  }

  function closeCreateModal() {
    const modal = document.getElementById('parking-create-modal');
    if (modal) { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
    document.body.style.overflow = '';
  }

  async function submit(event) {
    event.preventDefault();
    const doId = document.getElementById('parking-do-select')?.value;
    if (!doId) return notify('Vui lòng chọn DO.', 'warning');
    const listCount = Number(document.getElementById('parking-list-count-input')?.value || 1);
    if (!Number.isInteger(listCount) || listCount < 1) return notify('Số Packing List phải là số nguyên lớn hơn 0.', 'warning');
    const button = document.getElementById('parking-create-submit');
    if (button) button.disabled = true;
    try {
      const batch = await request(`/api/parking-lists/auto-from-do/${encodeURIComponent(doId)}`, {
        method: 'POST',
        body: JSON.stringify({ list_count: listCount })
      });
      const created = Array.isArray(batch.items) ? batch.items : [];
      closeCreateModal();
      document.getElementById('parking-create-form')?.reset();
      state.selectedId = created[0]?.id || '';
      notify(`Đã tự động tạo ${created.length} Packing List và QR thật từ DO.`, 'success');
      await load({ silent: true });
    } catch (error) { notify(error.message, 'error'); }
    finally { if (button) button.disabled = false; }
  }

  function extractQrToken(value) {
    const raw = String(value || '').trim();
    const match = raw.match(/\/api\/parking-qr\/([^/?#]+)/i);
    return decodeURIComponent(match ? match[1] : raw);
  }

  function openScanModal(action) {
    const modal = document.getElementById('parking-scan-modal');
    if (!modal || !state.selected || !scanActions[state.selected.status]) return;
    document.getElementById('parking-scan-action').value = action;
    document.getElementById('parking-scan-title').textContent = scanActions[state.selected.status][1];
    document.getElementById('parking-scan-progress').textContent = action === 'load_package'
      ? `Quét tem kiện của ${state.selected.id}. Hệ thống tự đếm đến khi đủ kiện.`
      : `Quét một tem bất kỳ thuộc ${state.selected.id}.`;
    document.getElementById('parking-scan-token').value = '';
    document.getElementById('parking-scan-note').value = '';
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(() => document.getElementById('parking-scan-token')?.focus(), 50);
  }

  function closeScanModal() {
    const modal = document.getElementById('parking-scan-modal');
    if (modal) { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
    document.body.style.overflow = '';
  }

  async function submitParkingQrScan(event) {
    event.preventDefault();
    const action = document.getElementById('parking-scan-action')?.value;
    const token = extractQrToken(document.getElementById('parking-scan-token')?.value);
    if (!token || !action) return notify('Vui lòng quét QR hợp lệ.', 'warning');
    try {
      const updated = await request(`/api/parking-qr/${encodeURIComponent(token)}/scan`, {
        method: 'POST',
        body: JSON.stringify({ action, note: document.getElementById('parking-scan-note')?.value || null })
      });
      state.selected = updated;
      state.selectedId = updated.id;
      const index = state.rows.findIndex(row => row.id === updated.id);
      if (index >= 0) state.rows[index] = updated;
      filter(); renderDetail();
      const loadedCount = (updated.labels || []).filter(label => ['loaded', 'dispatched', 'delivered'].includes(label.status)).length;
      if (action === 'load_package' && updated.status === 'gate_in') {
        document.getElementById('parking-scan-progress').textContent = `Đã bốc ${loadedCount}/${(updated.labels || []).length} kiện. Quét kiện tiếp theo.`;
        document.getElementById('parking-scan-token').value = '';
        document.getElementById('parking-scan-token').focus();
      } else {
        closeScanModal();
      }
      notify(action === 'load_package' ? `Đã ghi nhận kiện ${loadedCount}/${(updated.labels || []).length}.` : 'Đã ghi nhận QR vào hệ thống.', 'success');
    } catch (error) { notify(error.message, 'error'); }
  }

  function openPrintWindow(title, html, landscape) {
    const popup = window.open('', '_blank', 'width=1100,height=850');
    if (!popup) { notify('Trình duyệt đang chặn cửa sổ in. Hãy cho phép popup.', 'warning'); return false; }
    popup.opener = null;
    popup.document.open();
    popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title><style>@page{size:${landscape ? 'A4 landscape' : 'A4 portrait'};margin:8mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#111;margin:0}table{width:100%;border-collapse:collapse}th,td{border:1px solid #222;padding:5px;font-size:11px;text-align:left}.print-actions{position:sticky;top:0;display:flex;justify-content:flex-end;padding:8px;background:#fff;border-bottom:1px solid #ccc}.print-actions button{padding:8px 14px;font-weight:700}.sheet{page-break-after:always}.sheet:last-child{page-break-after:auto}.label{width:100%;border:2px solid #111;padding:12px}.label-head{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;border:1px solid #111}.label-head div{padding:8px;border-right:1px solid #111;text-align:center}.label-head div:last-child{border-right:0}.label-grid{display:grid;grid-template-columns:130px 1fr;gap:12px;align-items:center;margin-top:10px}.label img{width:120px;height:120px}.big{font-size:26px;font-weight:800}.packing-title{text-align:center;font-size:24px;font-weight:800;margin:8px}.meta{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #222;margin-bottom:8px}.meta div{padding:7px;border-right:1px solid #222}.meta div:last-child{border-right:0}.qr{width:105px;height:105px}@media print{.print-actions{display:none}}</style></head><body><div class="print-actions"><button onclick="window.print()">In tài liệu</button></div>${html}</body></html>`);
    popup.document.close();
    return true;
  }

  async function recordPrint(documentType) {
    if (!state.selected) return;
    try {
      state.selected = await request(`/api/parking-lists/${encodeURIComponent(state.selected.id)}/print`, {
        method: 'POST', body: JSON.stringify({ document_type: documentType })
      });
      const index = state.rows.findIndex(row => row.id === state.selected.id);
      if (index >= 0) state.rows[index] = state.selected;
      renderDetail();
    } catch (error) {
      notify(`Đã mở bản in nhưng chưa ghi được lịch sử: ${error.message}`, 'warning');
    }
  }

  function printLabels() {
    const item = state.selected; if (!item) return;
    const labels = (item.labels || []).map(label => `<section class="sheet"><div class="label"><div style="font-size:20px;font-weight:900;margin-bottom:8px">RDC LAOS</div><div class="label-head"><div><span>STORE</span><div class="big">${escapeHtml(item.store_id || '-')}</div></div><div><span>ROUTE</span><div class="big">${escapeHtml(item.route_code || '-')}</div></div><div><span>WAVE</span><div class="big">${escapeHtml(item.wave || '-')}</div></div><div><span>GATE</span><div class="big">${escapeHtml(item.gate || '-')}</div></div></div><div style="margin-top:8px"><b>TO:</b> ${escapeHtml(item.store_name || item.customer_id || '-')}</div><div class="label-grid"><img src="${escapeHtml(api(label.qr_path))}" alt="QR"><div><div>DO: <b>${escapeHtml(item.do_id)}</b></div><div>ITEM: <b>${number((item.items || []).length, 0)}</b> &nbsp; PACK: <b>${number(item.total_pieces, 0)}</b></div><div>Weight: <b>${number(item.total_weight_kg)} kg</b></div><div>Cube: <b>${number(item.total_cube_m3, 4)} m³</b></div><div class="big" style="text-align:right">${label.package_no}/${label.package_total}</div></div></div></div></section>`).join('');
    if (openPrintWindow(`Tem kiện ${item.do_id}`, labels, false)) void recordPrint('labels');
  }

  function printPackingList() {
    const item = state.selected; if (!item) return;
    const qrPath = item.labels && item.labels[0] ? api(item.labels[0].qr_path) : '';
    const rows = (item.items || []).map((row, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(row.barcode || '-')}</td><td>${escapeHtml(row.item_id_laos || '-')}</td><td>${escapeHtml(row.item_id_thai || '-')}</td><td>${escapeHtml(row.description || row.sku || '-')}</td><td>${number(row.case_qty, 0)}</td><td>${number(row.piece_qty, 0)}</td><td>${number(row.weight_kg)}</td></tr>`).join('');
    if (openPrintWindow(`Packing List ${item.do_id}`, `<section><div style="display:flex;justify-content:space-between;align-items:flex-start"><div><b>RDC: ${escapeHtml(item.route_code || '-')}</b><br>Parking List: ${escapeHtml(item.id)}<br>DO: ${escapeHtml(item.do_id)}</div>${qrPath ? `<img class="qr" src="${escapeHtml(qrPath)}" alt="QR">` : ''}</div><div class="packing-title">Packing List</div><div class="meta"><div><b>Date</b><br>${new Date().toLocaleDateString('vi-VN')}</div><div><b>Store</b><br>${escapeHtml(item.store_name || '-')}</div><div><b>Store ID</b><br>${escapeHtml(item.store_id || '-')}</div><div><b>Box</b><br>${number(item.box_count, 0)}</div></div><table><thead><tr><th>No</th><th>Barcode</th><th>Item ID Laos</th><th>Item ID Thai</th><th>Item Description</th><th>Case</th><th>Piece</th><th>Total weight (kg)</th></tr></thead><tbody>${rows || '<tr><td colspan="8">Chưa có dòng hàng chi tiết</td></tr>'}</tbody><tfoot><tr><th colspan="6">TỔNG</th><th>${number(item.total_pieces, 0)}</th><th>${number(item.total_weight_kg)}</th></tr></tfoot></table></section>`, true)) void recordPrint('packing_list');
  }

  window.ParkingListUI = { load, filter, select, openCreateModal, closeCreateModal, submit, previewDO, openScanModal, closeScanModal, submitParkingQrScan, printLabels, printPackingList };
  window.reloadParkingLists = () => load();
  window.filterParkingLists = filter;
  window.selectParkingList = select;
  window.openParkingCreateModal = openCreateModal;
  window.closeParkingCreateModal = closeCreateModal;
  window.submitParkingList = submit;
  window.previewParkingDO = previewDO;
  window.openParkingScanModal = openScanModal;
  window.closeParkingScanModal = closeScanModal;
  window.submitParkingQrScan = submitParkingQrScan;
  window.setParkingDetailTab = tab => { state.detailTab = tab; renderDetail(); };
  window.printParkingLabels = printLabels;
  window.printParkingPackingList = printPackingList;
})();
