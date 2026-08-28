(function () {
  const state = { report: null, vouchers: [], charts: {}, activeTab: 'overview' };

  function apiBase() {
    return typeof API_BASE !== 'undefined' ? API_BASE : '';
  }

  function authHeaders(extra) {
    const token = window.EPL_TMS_API_TOKEN || localStorage.getItem('EPL_TMS_API_TOKEN') || '';
    return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(extra || {}) };
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function money(value, currency) {
    if (value == null) return '-';
    return `${Number(value || 0).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} ${currency || ''}`.trim();
  }

  function dateText(value) {
    if (!value) return '-';
    const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('vi-VN');
  }

  function queryString() {
    const params = new URLSearchParams();
    const fields = {
      date_from: document.getElementById('transport-report-from')?.value,
      date_to: document.getElementById('transport-report-to')?.value,
      customer_id: document.getElementById('transport-report-customer')?.value.trim(),
      vehicle_id: document.getElementById('transport-report-vehicle')?.value.trim()
    };
    Object.entries(fields).forEach(([key, value]) => { if (value) params.set(key, value); });
    return params.toString();
  }

  async function api(path, options) {
    const response = await fetch(`${apiBase()}${path}`, {
      ...(options || {}),
      headers: authHeaders(options?.headers)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = payload?.error?.message || payload?.detail?.message || payload?.message || 'Máy chủ chưa xử lý được yêu cầu.';
      throw new Error(message);
    }
    return payload.data;
  }

  function showMessage(message, kind) {
    if (typeof showToast === 'function') showToast(`${kind === 'error' ? 'Không thể thực hiện: ' : ''}${message}`);
  }

  function setLoadState(status, message) {
    const center = document.getElementById('transport-reporting-center');
    const element = document.getElementById('transport-report-load-state');
    if (!center || !element) return;
    center.classList.toggle('is-loading', status === 'loading');
    center.classList.toggle('has-load-error', status === 'error');
    element.hidden = status === 'ready';
    element.className = `transport-report-load-state ${status}`;
    const icon = status === 'error' ? 'fa-triangle-exclamation' : 'fa-spinner fa-spin';
    element.innerHTML = `<i class="fa-solid ${icon}"></i><div><strong>${status === 'error' ? 'Chưa tải được dữ liệu' : 'Đang tải dữ liệu'}</strong><span>${escapeHtml(message || '')}</span></div>`;
  }

  function summary(report) {
    const element = document.getElementById('transport-report-summary');
    if (!element) return;
    const item = report.summary;
    element.innerHTML = [
      ['Doanh thu đã ghi sổ', money(item.recognized_revenue, item.currency_code)],
      ['Chi phí đã duyệt', money(item.approved_cost, item.currency_code)],
      ['Lợi nhuận gộp', money(item.gross_profit, item.currency_code)],
      ['Biên lợi nhuận', `${Number(item.margin_percent || 0).toLocaleString('vi-VN')}% · ${item.trip_count} chuyến`]
    ].map(([label, value]) => `<div class="transport-report-kpi"><span>${label}</span><strong>${value}</strong></div>`).join('');
  }

  function destroyChart(name) {
    if (state.charts[name]) state.charts[name].destroy();
    state.charts[name] = null;
  }

  function charts(report) {
    if (typeof Chart === 'undefined') return;
    ['trend', 'customer', 'cargo'].forEach(destroyChart);
    const trend = report.charts.trend || [];
    state.charts.trend = new Chart(document.getElementById('transport-revenue-chart'), {
      type: 'line',
      data: { labels: trend.map(item => item.label), datasets: [
        { label: 'Doanh thu', data: trend.map(item => item.revenue), borderColor: '#0875d1', backgroundColor: 'rgba(8,117,209,.08)', tension: .25, fill: true },
        { label: 'Chi phí', data: trend.map(item => item.cost), borderColor: '#df8a14', backgroundColor: 'transparent', tension: .25 },
        { label: 'Lợi nhuận', data: trend.map(item => item.gross_profit), borderColor: '#0a9b70', backgroundColor: 'transparent', tension: .25 }
      ] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { position: 'bottom' } } }
    });
    const customers = (report.charts.by_customer || []).slice(0, 8);
    state.charts.customer = new Chart(document.getElementById('transport-customer-chart'), {
      type: 'bar',
      data: { labels: customers.map(item => item.label), datasets: [{ label: 'Doanh thu', data: customers.map(item => item.revenue), backgroundColor: '#0875d1' }] },
      options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
    });
    const cargo = report.charts.by_cargo || [];
    state.charts.cargo = new Chart(document.getElementById('transport-cargo-chart'), {
      type: 'doughnut',
      data: { labels: cargo.map(item => item.label), datasets: [{ data: cargo.map(item => item.value), backgroundColor: ['#0875d1', '#0a9b70', '#df8a14', '#6554c0', '#d64545', '#52718f'] }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });
  }

  function exceptions(report) {
    const element = document.getElementById('transport-report-exceptions');
    if (!element) return;
    element.innerHTML = (report.exceptions || []).map(item => `
      <div class="transport-report-exception"><i class="fa-solid fa-triangle-exclamation"></i><span><strong>${escapeHtml(item.do_id)}</strong> · ${escapeHtml(item.message)}</span></div>
    `).join('');
  }

  function revenueTable(report) {
    const body = document.getElementById('transport-report-revenue-body');
    if (!body) return;
    if (!(report.rows || []).length) {
      body.innerHTML = '<tr><td class="transport-report-empty" colspan="23">Chưa có chuyến có hóa đơn AR đã ghi sổ trong kỳ đã chọn.</td></tr>';
      return;
    }
    body.innerHTML = report.rows.map((row, index) => {
      const total = row.totals || {};
      return `<tr>
        <td>${index + 1}</td><td>${dateText(row.departure_date)}</td><td title="${escapeHtml(row.dispatch_order_no)}">${escapeHtml(row.dispatch_order_no)}</td>
        <td>${dateText(row.recognition_date)}</td><td>${escapeHtml(row.invoice_no)}</td><td title="${escapeHtml(row.origin)}">${escapeHtml(row.origin)}</td>
        <td title="${escapeHtml(row.destination)}">${escapeHtml(row.destination)}</td><td>${escapeHtml(row.agency_company || '-')}</td><td>${escapeHtml(row.driver_name || '-')}</td>
        <td>${escapeHtml(row.tractor_plate || '-')}</td><td>${escapeHtml(row.trailer_plate || '-')}</td><td>${escapeHtml(row.vehicle_code || '-')}</td>
        <td>${escapeHtml(row.customer_name || '-')}</td><td>${escapeHtml(row.cargo_type || '-')}</td><td>${row.trip_count}</td><td>${escapeHtml(row.uom || '-')}</td>
        <td>${Number(row.weight_tons || 0).toLocaleString('vi-VN')}</td><td>${money(total.LAK)}</td><td>${money(total.THB)}</td><td>${money(total.USD)}</td>
        <td>${money(total.CNY)}</td><td>${money(total.VND)}</td><td>${escapeHtml(row.note || '-')}</td>
      </tr>`;
    }).join('');
  }

  function voucherList(vouchers) {
    const element = document.getElementById('transport-expense-list');
    if (!element) return;
    if (!vouchers.length) {
      element.innerHTML = '<div class="transport-report-empty">Chưa có phiếu chi phí EPL. Bấm “Lập phiếu chi phí” để tạo hồ sơ từ chuyến đã hoàn thành.</div>';
      return;
    }
    element.innerHTML = vouchers.map(item => `<article class="transport-expense-row">
      <div><span>Số phiếu</span><strong>${escapeHtml(item.voucher_no)}</strong><small>${escapeHtml(item.trip_id)}</small></div>
      <div><span>Ngày lập</span><strong>${dateText(item.voucher_date)}</strong></div>
      <div><span>Xe / tài xế</span><strong>${escapeHtml(item.vehicle?.plate || '-')}</strong><small>${escapeHtml(item.driver?.name || '-')}</small></div>
      <div><span>Tổng chi thực tế</span><strong>${money(item.cost?.total_amount, item.cost?.currency_code)}</strong></div>
      <button type="button" class="fiori-btn fiori-btn-secondary" onclick="TransportReporting.openVoucher('${escapeHtml(item.trip_id)}')"><i class="fa-solid fa-eye"></i> Xem phiếu</button>
    </article>`).join('');
  }

  async function load() {
    if (!document.getElementById('transport-reporting-center')) return;
    mountPanorama();
    setLoadState('loading', 'Đang đối chiếu doanh thu và chi phí từ hệ thống.');
    try {
      const suffix = queryString();
      const [report, vouchers] = await Promise.all([
        api(`/api/tms/reporting/transport-revenue${suffix ? `?${suffix}` : ''}`),
        api('/api/tms/reporting/expense-vouchers')
      ]);
      state.report = report;
      state.vouchers = vouchers || [];
      summary(report); charts(report); exceptions(report); revenueTable(report); voucherList(state.vouchers);
      setLoadState('ready');
    } catch (error) {
      setLoadState('error', error.message);
    }
  }

  function mountPanorama() {
    const source = document.querySelector('#view-lab-panorama-source .card-panel');
    const target = document.getElementById('analysis-panorama-pane');
    if (source && target && !target.contains(source)) target.appendChild(source);
  }

  function toggleWorkspaceMenu(force) {
    const selector = document.getElementById('analysis-workspace-selector');
    const toggle = document.getElementById('analysis-workspace-selector-toggle');
    if (!selector || !toggle) return;
    const open = typeof force === 'boolean' ? force : !selector.classList.contains('open');
    selector.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open && selector.contains(document.activeElement)) document.activeElement.blur();
  }

  function selectWorkspacePane(name) {
    const validNames = ['overview', 'panorama', 'revenue', 'expenses'];
    const labels = {
      overview: 'Tổng quan P&L',
      panorama: 'Bức tranh toàn cảnh',
      revenue: 'Doanh thu theo chuyến',
      expenses: 'Phiếu chi phí'
    };
    if (!validNames.includes(name)) name = 'overview';
    state.activeTab = name;
    mountPanorama();
    document.querySelectorAll('[data-analysis-nav]').forEach(button => {
      const active = button.dataset.analysisNav === name;
      button.classList.toggle('active', active);
      button.setAttribute('aria-current', active ? 'page' : 'false');
    });
    document.querySelectorAll('[data-analysis-pane]').forEach(pane => pane.classList.toggle('active', pane.dataset.analysisPane === name));
    const selectorLabel = document.getElementById('analysis-workspace-selector-label');
    if (selectorLabel) selectorLabel.textContent = labels[name];
    toggleWorkspaceMenu(false);
    document.getElementById('transport-reporting-center')?.classList.toggle('show-panorama', name === 'panorama');
    if (name === 'overview') setTimeout(() => Object.values(state.charts).forEach(chart => chart?.resize()), 0);
    if (name === 'panorama' && typeof loadDashboard === 'function') setTimeout(loadDashboard, 0);
  }

  function selectTab(name) {
    selectWorkspacePane(name);
  }

  async function exportCsv() {
    try {
      const suffix = queryString();
      const response = await fetch(`${apiBase()}/api/tms/reporting/transport-revenue/export.csv${suffix ? `?${suffix}` : ''}`, {
        headers: authHeaders()
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.error?.message || payload?.detail?.message || 'Không thể xuất báo cáo.');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'bao-cao-doanh-thu-van-tai.csv';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      showMessage(error.message, 'error');
    }
  }

  function lineTemplate(line) {
    return `<div class="transport-voucher-line">
      <input data-field="name" required placeholder="Nội dung chi phí" value="${escapeHtml(line?.name || '')}">
      <input data-field="original_amount" required type="number" min="0" step="0.01" placeholder="Giá ban đầu" value="${escapeHtml(line?.original_amount ?? '0')}">
      <input data-field="actual_amount" required type="number" min="0" step="0.01" placeholder="Giá thực tế" value="${escapeHtml(line?.actual_amount ?? '0')}">
      <input data-field="note" placeholder="Số lượng / ghi chú" value="${escapeHtml(line?.note || '')}">
      <button type="button" onclick="this.closest('.transport-voucher-line').remove()" title="Xóa khoản phí"><i class="fa-solid fa-trash"></i></button>
    </div>`;
  }

  function addVoucherLine(line) {
    document.getElementById('transport-voucher-lines')?.insertAdjacentHTML('beforeend', lineTemplate(line));
  }

  async function openVoucher(tripId) {
    const modal = document.getElementById('transport-voucher-modal');
    const form = document.getElementById('transport-voucher-form');
    if (!modal || !form) return;
    form.reset();
    form.elements.voucher_date.value = new Date().toISOString().slice(0, 10);
    document.getElementById('transport-voucher-lines').innerHTML = '';
    if (tripId) {
      try {
        const item = await api(`/api/tms/reporting/expense-vouchers/${encodeURIComponent(tripId)}`);
        ['trip_id', 'do_id', 'voucher_no', 'voucher_date', 'vehicle_manager', 'payment_method', 'contract_no', 'machine_numbers', 'checked_by', 'note'].forEach(key => {
          if (form.elements[key]) form.elements[key].value = item[key] || '';
        });
        form.elements.currency_code.value = item.cost?.currency_code || 'VND';
        (item.cost?.lines || []).forEach(addVoucherLine);
      } catch (error) {
        showMessage(error.message, 'error');
        return;
      }
    } else {
      addVoucherLine();
    }
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeVoucher() {
    const modal = document.getElementById('transport-voucher-modal');
    if (modal) modal.hidden = true;
    document.body.style.overflow = '';
  }

  async function saveVoucher(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const lines = Array.from(document.querySelectorAll('#transport-voucher-lines .transport-voucher-line')).map(row => ({
      name: row.querySelector('[data-field="name"]').value.trim(),
      original_amount: row.querySelector('[data-field="original_amount"]').value,
      actual_amount: row.querySelector('[data-field="actual_amount"]').value,
      note: row.querySelector('[data-field="note"]').value.trim() || null
    }));
    if (!lines.length) { showMessage('Phiếu phải có ít nhất một khoản chi phí.', 'error'); return; }
    const values = Object.fromEntries(new FormData(form).entries());
    const tripId = values.trip_id.trim();
    delete values.trip_id;
    Object.keys(values).forEach(key => { if (values[key] === '') values[key] = null; });
    values.lines = lines;
    try {
      await api(`/api/tms/reporting/trips/${encodeURIComponent(tripId)}/expense-voucher`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': `expense-voucher-${tripId}-${Date.now()}` },
        body: JSON.stringify(values)
      });
      closeVoucher();
      showMessage('Đã lưu phiếu chi phí EPL vào cơ sở dữ liệu.');
      await load();
      selectWorkspacePane('expenses');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  }

  function initializeDates() {
    const from = document.getElementById('transport-report-from');
    const to = document.getElementById('transport-report-to');
    if (!from || from.value) return;
    const now = new Date();
    from.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    to.value = now.toISOString().slice(0, 10);
  }

  window.TransportReporting = { load, selectWorkspacePane, toggleWorkspaceMenu, selectTab, exportCsv, openVoucher, closeVoucher, addVoucherLine, saveVoucher, initializeDates };
})();
