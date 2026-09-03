/**
 * Trình bày phần "Chất lượng dịch vụ (SLA)" trong workspace Phân tích.
 *
 * Đây là các hàm THUẦN: nhận dữ liệu từ TmsCockpit.buildReportingDrilldown và
 * trả về chuỗi HTML. Tách ra khỏi app.js để phần trình bày kiểm chứng được
 * bằng Node, đúng như cách workflow-ui-utils.js đang làm.
 *
 * Quy ước màu — dùng token sẵn có của ứng dụng, không áp bảng màu mới:
 *
 *   Trạng thái (dành riêng, không bao giờ dùng cho mục đích khác):
 *     tốt        #059669  (--accent-emerald)
 *     cảnh báo   #d97706  (--accent-amber)
 *     nghiêm trọng #b91c1c (--lao-red-hover)
 *   Bộ ba này đã qua kiểm tra bằng máy: nằm trong dải độ sáng, đủ sắc độ, và
 *   ΔE người nhìn bình thường 18.8 giữa cặp gần nhất. Riêng ΔE cho người mù
 *   màu đỏ-lục là 7.9 — mức chỉ được phép khi có mã hóa phụ, nên MỌI chỗ dùng
 *   màu trạng thái ở đây đều kèm icon và chữ, không bao giờ chỉ có màu.
 *
 *   Thang độ lớn (một sắc, nhạt → đậm), suy từ --lao-blue:
 *     #eff6ff → #dbeafe → #93c5fd → #3b82f6 → #1d4ed8
 *   Dùng cho aging bucket và heatmap, nơi màu biểu thị ĐỘ LỚN chứ không phải
 *   danh tính. Không dùng cầu vồng, không đổi sắc giữa dải.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SlaAnalytics = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STATUS = {
    ok: { color: '#059669', soft: '#ecfdf5', icon: 'fa-circle-check' },
    warning: { color: '#d97706', soft: '#fffbeb', icon: 'fa-triangle-exclamation' },
    critical: { color: '#b91c1c', soft: '#fef2f2', icon: 'fa-circle-exclamation' },
    info: { color: '#475569', soft: '#f1f5f9', icon: 'fa-circle-info' },
  };

  /**
   * Chữ của riêng phần trình bày này.
   *
   * Các nhãn đến TỪ DỮ LIỆU (tên nhóm trễ, tên việc cần làm, tên chiều phân
   * tích, mức độ, chỉ số) đã được app.js dịch trước khi truyền vào, vì các bản
   * đồ dịch đó vốn nằm ở app.js. Ở đây chỉ dịch phần khung.
   */
  const T = {
    status_ok: { vi: 'Đạt', en: 'On target', la: 'ບັນລຸ' },
    status_warning: { vi: 'Cảnh báo', en: 'Warning', la: 'ແຈ້ງເຕືອນ' },
    status_critical: { vi: 'Nghiêm trọng', en: 'Critical', la: 'ຮ້າຍແຮງ' },
    status_info: { vi: 'Thông tin', en: 'Info', la: 'ຂໍ້ມູນ' },
    on_time_eyebrow: { vi: 'Tỉ lệ giao đúng hạn', en: 'On-time delivery rate', la: 'ອັດຕາການສົ່ງຕົງເວລາ' },
    analyzed_orders: { vi: 'đơn được phân tích', en: 'orders analyzed', la: 'ໃບສັ່ງທີ່ວິເຄາະ' },
    tile_sla_risks: { vi: 'Cảnh báo SLA/KPI', en: 'SLA/KPI alerts', la: 'ແຈ້ງເຕືອນ SLA/KPI' },
    tile_critical: { vi: 'Cảnh báo nghiêm trọng', en: 'Critical alerts', la: 'ແຈ້ງເຕືອນຮ້າຍແຮງ' },
    tile_cost_overrun: { vi: 'Đơn vượt chi phí', en: 'Cost overrun orders', la: 'ໃບສັ່ງເກີນຕົ້ນທຶນ' },
    tile_total_orders: { vi: 'Tổng đơn phân tích', en: 'Total orders analyzed', la: 'ໃບສັ່ງທັງໝົດ' },
    panel_aging: { vi: 'Nhóm thời gian trễ', en: 'Delay buckets', la: 'ກຸ່ມເວລາຊັກຊ້າ' },
    panel_trend: { vi: 'Diễn biến cảnh báo', en: 'Alert trend', la: 'ແນວໂນ້ມການແຈ້ງເຕືອນ' },
    panel_actions: { vi: 'Việc cần làm', en: 'Actions to take', la: 'ວຽກທີ່ຕ້ອງເຮັດ' },
    heat_title: {
      vi: 'Rủi ro theo khách hàng, tuyến và tài xế',
      en: 'Risk by customer, route and driver',
      la: 'ຄວາມສ່ຽງຕາມລູກຄ້າ, ເສັ້ນທາງ ແລະ ຄົນຂັບ',
    },
    scale_low: { vi: 'Ít cảnh báo', en: 'Fewer alerts', la: 'ແຈ້ງເຕືອນນ້ອຍ' },
    scale_high: { vi: 'Nhiều', en: 'More', la: 'ຫຼາຍ' },
    empty_aging: { vi: 'Chưa có cảnh báo trễ nào.', en: 'No delay alerts yet.', la: 'ຍັງບໍ່ມີການແຈ້ງເຕືອນຊັກຊ້າ.' },
    empty_trend: { vi: 'Chưa có cảnh báo để dựng diễn biến.', en: 'Not enough alerts to plot a trend.', la: 'ຍັງບໍ່ພຽງພໍເພື່ອສ້າງແນວໂນ້ມ.' },
    empty_actions: { vi: 'Không có việc nào cần xử lý.', en: 'Nothing to action.', la: 'ບໍ່ມີວຽກທີ່ຕ້ອງແກ້ໄຂ.' },
    empty_data: { vi: 'Chưa có dữ liệu.', en: 'No data yet.', la: 'ຍັງບໍ່ມີຂໍ້ມູນ.' },
    empty_table: {
      vi: 'Không có cảnh báo SLA/KPI trong dữ liệu hiện tại.',
      en: 'No SLA/KPI alerts in current data.',
      la: 'ບໍ່ມີການແຈ້ງເຕືອນ SLA/KPI ໃນຂໍ້ມູນປະຈຸບັນ.',
    },
    open: { vi: 'Mở', en: 'Open', la: 'ເປີດ' },
  };

  function t(key, lang) {
    const entry = T[key];
    if (!entry) return '';
    return entry[lang] || entry.vi;
  }

  // Thang một sắc, nhạt → đậm. Chỉ số càng cao = độ lớn càng lớn.
  const SEQUENTIAL = ['#eff6ff', '#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8'];

  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function statusOf(key, lang) {
    const known = STATUS[key] ? key : 'info';
    return Object.assign({}, STATUS[known], { label: t(`status_${known}`, lang) });
  }

  /** Chọn bước trên thang một sắc theo tỉ lệ value/max. */
  function sequentialStep(value, max) {
    const total = Number(max) || 0;
    const amount = Number(value) || 0;
    if (!total || amount <= 0) return SEQUENTIAL[0];
    const ratio = Math.min(1, amount / total);
    const index = Math.min(
      SEQUENTIAL.length - 1,
      Math.max(1, Math.ceil(ratio * (SEQUENTIAL.length - 1)))
    );
    return SEQUENTIAL[index];
  }

  /** Màu chữ đọc được trên một bước của thang. */
  function inkOnStep(step) {
    return step === '#1d4ed8' || step === '#3b82f6' ? '#ffffff' : '#0f172a';
  }

  // ------------------------------------------------------------------
  // Dải mở đầu: một con số dẫn dắt + các ô chỉ số
  // ------------------------------------------------------------------

  /**
   * Tỉ lệ đúng hạn là con số duy nhất đáng đặt lên đầu, nên nó được trình bày
   * dưới dạng số dẫn dắt kèm thanh đo — không phải một ô nhỏ ngang hàng với
   * các ô khác. Ngưỡng: >=95% đạt, >=85% cảnh báo, dưới đó là nghiêm trọng.
   */
  function onTimeHero(kpis, executiveSummary, lang) {
    const percent = Math.max(0, Math.min(100, Number(kpis?.on_time_rate?.percent) || 0));
    const total = Number(kpis?.total_orders?.count) || 0;
    const level = percent >= 95 ? 'ok' : percent >= 85 ? 'warning' : 'critical';
    const tone = statusOf(level, lang);
    const summary = executiveSummary
      ? `<p class="svc-hero-note"><i class="fa-solid fa-circle-info" aria-hidden="true"></i> ${esc(executiveSummary)}</p>`
      : '';
    return `
      <section class="svc-hero" style="--svc-tone:${tone.color}; --svc-tone-soft:${tone.soft};">
        <div class="svc-hero-main">
          <p class="svc-eyebrow">${esc(t('on_time_eyebrow', lang))}</p>
          <p class="svc-hero-value">${percent}<span class="svc-hero-unit">%</span></p>
          <p class="svc-hero-status">
            <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}
          </p>
        </div>
        <div class="svc-hero-meter">
          <div class="svc-meter" role="img"
               aria-label="Tỉ lệ giao đúng hạn ${percent} phần trăm trên ${total} đơn"
               title="${percent}% đúng hạn · ${total} đơn được phân tích">
            <div class="svc-meter-fill" style="width:${percent}%;"></div>
          </div>
          <p class="svc-hero-base">${total.toLocaleString('vi-VN')} ${esc(t('analyzed_orders', lang))}</p>
        </div>
        ${summary}
      </section>
    `;
  }

  /**
   * Các ô chỉ số. Ô nào là số cần hành động thì mang màu trạng thái, và luôn
   * kèm icon với chữ — màu không bao giờ là tín hiệu duy nhất.
   */
  function kpiTiles(kpis, lang) {
    const tiles = [
      { key: 'sla_risks', label: t('tile_sla_risks', lang), value: kpis?.sla_risks?.count, actionable: true },
      { key: 'critical_risks', label: t('tile_critical', lang), value: kpis?.critical_risks?.count, actionable: true, escalate: true },
      { key: 'cost_overrun', label: t('tile_cost_overrun', lang), value: kpis?.cost_overrun?.count, actionable: true },
      { key: 'total_orders', label: t('tile_total_orders', lang), value: kpis?.total_orders?.count, actionable: false },
    ];
    return `
      <div class="svc-tiles">
        ${tiles.map(tile => {
          const count = Number(tile.value) || 0;
          let level = 'info';
          if (tile.actionable) {
            level = count === 0 ? 'ok' : tile.escalate ? 'critical' : 'warning';
          }
          const tone = statusOf(level, lang);
          const badge = tile.actionable
            ? `<span class="svc-tile-state"><i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}</span>`
            : '';
          return `
            <article class="svc-tile" style="--svc-tone:${tone.color}; --svc-tone-soft:${tone.soft};">
              <p class="svc-tile-label">${esc(tile.label)}</p>
              <p class="svc-tile-value">${count.toLocaleString('vi-VN')}</p>
              ${badge}
            </article>
          `;
        }).join('')}
      </div>
    `;
  }

  // ------------------------------------------------------------------
  // Aging bucket — độ lớn trên các nhóm CÓ THỨ TỰ
  // ------------------------------------------------------------------

  /**
   * Các nhóm thời gian trễ có thứ tự tự nhiên, nên đây là độ lớn chứ không
   * phải danh tính: thanh ngang, một sắc, càng trễ càng đậm. Giá trị ghi trực
   * tiếp ở đầu thanh nên không cần trục số.
   */
  function agingBuckets(buckets, lang) {
    const rows = Array.isArray(buckets) ? buckets : [];
    const max = rows.reduce((peak, row) => Math.max(peak, Number(row.count) || 0), 0);
    if (!rows.length) {
      return panel(t('panel_aging', lang), 'fa-hourglass-half', emptyState(t('empty_aging', lang)));
    }
    const body = `
      <ul class="svc-bars">
        ${rows.map((row, index) => {
          const count = Number(row.count) || 0;
          const width = max ? Math.max(count ? 4 : 0, Math.round(count * 100 / max)) : 0;
          // Đậm dần theo THỨ TỰ nhóm, không theo giá trị: người đọc thấy ngay
          // nhóm nào là nhóm trễ nặng, kể cả khi nhóm đó đang bằng 0.
          const step = SEQUENTIAL[Math.min(SEQUENTIAL.length - 1, index + 1)];
          return `
            <li class="svc-bar-row" title="${esc(row.label)}: ${count} cảnh báo">
              <span class="svc-bar-label">${esc(row.label)}</span>
              <span class="svc-bar-track">
                <span class="svc-bar-fill" style="width:${width}%; background:${step};"></span>
              </span>
              <span class="svc-bar-value">${count.toLocaleString('vi-VN')}</span>
            </li>
          `;
        }).join('')}
      </ul>
    `;
    return panel(t('panel_aging', lang), 'fa-hourglass-half', body);
  }

  // ------------------------------------------------------------------
  // Diễn biến theo ngày — thay đổi theo thời gian, hai thành phần
  // ------------------------------------------------------------------

  /**
   * Cột xếp chồng theo ngày: nghiêm trọng dưới, cảnh báo trên, cách nhau 2px
   * để hai phần không dính thành một khối. Có hai chuỗi nên phải có chú giải.
   * Chỉ ghi nhãn tổng trên đỉnh cột, không ghi số lên từng phần.
   */
  function trendByDay(trend, lang) {
    const rows = (Array.isArray(trend) ? trend : []).slice(-14);
    if (!rows.length) {
      return panel(t('panel_trend', lang), 'fa-chart-column', emptyState(t('empty_trend', lang)));
    }
    const max = rows.reduce((peak, row) => Math.max(peak, Number(row.issue_count) || 0), 0) || 1;
    const columns = rows.map(row => {
      const total = Number(row.issue_count) || 0;
      const critical = Number(row.critical_count) || 0;
      const warning = Math.max(0, Number(row.warning_count) || (total - critical));
      const height = Math.round(total * 100 / max);
      const criticalShare = total ? Math.round(critical * 100 / total) : 0;
      const day = String(row.date || '').slice(5);
      return `
        <li class="svc-col" title="${esc(row.date)}: ${total} cảnh báo (${critical} nghiêm trọng, ${warning} cảnh báo)">
          <span class="svc-col-total">${total}</span>
          <span class="svc-col-stack" style="height:${Math.max(height, 3)}%;">
            <span class="svc-col-seg svc-col-seg--warning" style="height:${100 - criticalShare}%;"></span>
            <span class="svc-col-seg svc-col-seg--critical" style="height:${criticalShare}%;"></span>
          </span>
          <span class="svc-col-day">${esc(day)}</span>
        </li>
      `;
    }).join('');
    const legend = `
      <ul class="svc-legend">
        <li><span class="svc-swatch" style="background:${STATUS.critical.color};"></span>
          <i class="fa-solid ${STATUS.critical.icon}" aria-hidden="true"></i> ${esc(t('status_critical', lang))}</li>
        <li><span class="svc-swatch" style="background:${STATUS.warning.color};"></span>
          <i class="fa-solid ${STATUS.warning.icon}" aria-hidden="true"></i> ${esc(t('status_warning', lang))}</li>
      </ul>
    `;
    return panel(
      t('panel_trend', lang),
      'fa-chart-column',
      `<ol class="svc-cols">${columns}</ol>${legend}`
    );
  }

  // ------------------------------------------------------------------
  // Playbook — danh sách hành động, không phải biểu đồ
  // ------------------------------------------------------------------

  function slaPlaybook(playbook, lang) {
    const rows = (Array.isArray(playbook) ? playbook : []).filter(row => Number(row.trigger_count) > 0);
    if (!rows.length) {
      return panel(t('panel_actions', lang), 'fa-list-check', emptyState(t('empty_actions', lang)));
    }
    const body = `
      <ul class="svc-actions">
        ${rows.map(row => {
          const count = Number(row.trigger_count) || 0;
          const view = row.navigation && row.navigation.view;
          const target = view
            ? ` onclick="switchView('${esc(String(view))}')" role="button" tabindex="0"`
            : '';
          return `
            <li class="svc-action${view ? ' svc-action--clickable' : ''}"${target}>
              <span class="svc-action-count">${count.toLocaleString('vi-VN')}</span>
              <span class="svc-action-body">
                <strong>${esc(row.label)}</strong>
                <small>${esc(row.instruction)}</small>
              </span>
              ${view ? '<i class="fa-solid fa-arrow-right svc-action-go" aria-hidden="true"></i>' : ''}
            </li>
          `;
        }).join('')}
      </ul>
    `;
    return panel(t('panel_actions', lang), 'fa-list-check', body);
  }

  // ------------------------------------------------------------------
  // Bản đồ rủi ro — độ lớn theo từng ô
  // ------------------------------------------------------------------

  /**
   * Mỗi chiều (khách hàng / tuyến / tài xế) là một bảng nhỏ. Ô số cảnh báo tô
   * theo thang một sắc; tỉ lệ đúng hạn để nguyên dạng chữ với màu ink, vì đó
   * là hai đại lượng khác nhau và không được dùng chung một cách mã hóa.
   */
  function riskHeatmap(groups, lang) {
    const dimensions = Array.isArray(groups) ? groups : [];
    if (!dimensions.length) return '';
    const max = dimensions.reduce((peak, group) => (
      (group.items || []).reduce((inner, item) => Math.max(inner, Number(item.issue_count) || 0), peak)
    ), 0);

    const cards = dimensions.map(group => {
      const items = group.items || [];
      const body = items.length
        ? `<ul class="svc-heat-list">
            ${items.map(item => {
              const count = Number(item.issue_count) || 0;
              const step = sequentialStep(count, max);
              const rate = Number(item.on_time_rate);
              const tone = statusOf(item.risk_level === 'ok' ? 'ok' : item.risk_level, lang);
              return `
                <li class="svc-heat-row">
                  <span class="svc-heat-label" title="${esc(item.label)}">${esc(item.label)}</span>
                  <span class="svc-heat-cell" style="background:${step}; color:${inkOnStep(step)};"
                        title="${esc(item.label)}: ${count} cảnh báo trên ${Number(item.total_orders) || 0} đơn">
                    ${count.toLocaleString('vi-VN')}
                  </span>
                  <span class="svc-heat-rate">
                    <i class="fa-solid ${tone.icon}" aria-hidden="true" style="color:${tone.color};"></i>
                    ${Number.isFinite(rate) ? `${rate}%` : '—'}
                  </span>
                </li>
              `;
            }).join('')}
          </ul>`
        : emptyState(t('empty_data', lang));
      return `
        <article class="svc-heat-card">
          <h4 class="svc-heat-title">${esc(group.dimension)}</h4>
          ${body}
        </article>
      `;
    }).join('');

    const scale = `
      <div class="svc-scale" aria-hidden="true">
        <span>${esc(t('scale_low', lang))}</span>
        ${SEQUENTIAL.map(step => `<span class="svc-scale-step" style="background:${step};"></span>`).join('')}
        <span>${esc(t('scale_high', lang))}</span>
      </div>
    `;
    return `
      <section class="svc-heat">
        <header class="svc-section-head">
          <h3><i class="fa-solid fa-table-cells" aria-hidden="true"></i> ${esc(t('heat_title', lang))}</h3>
          ${scale}
        </header>
        <div class="svc-heat-grid">${cards}</div>
      </section>
    `;
  }

  // ------------------------------------------------------------------
  // Bảng chi tiết — cũng là "table view" cho mọi biểu đồ ở trên
  // ------------------------------------------------------------------

  function drilldownRows(rows, lang) {
    const items = Array.isArray(rows) ? rows : [];
    if (!items.length) {
      return `<tr><td colspan="6" class="svc-table-empty">${esc(t('empty_table', lang))}</td></tr>`;
    }
    const rank = { critical: 0, warning: 1, info: 2 };
    return items
      .slice()
      .sort((a, b) => (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3))
      .map(row => {
        const tone = statusOf(row.severity, lang);
        const view = row.navigation && row.navigation.view;
        const action = view
          ? `<button type="button" class="svc-table-go" onclick="switchView('${esc(String(view))}')">
               ${esc(row.action_label || t('open', lang))} <i class="fa-solid fa-arrow-right" aria-hidden="true"></i>
             </button>`
          : '—';
        return `
          <tr>
            <td class="svc-mono">${esc(row.order_id)}</td>
            <td>${esc(row.issue_label)}</td>
            <td>
              <span class="svc-chip" style="--svc-tone:${tone.color}; --svc-tone-soft:${tone.soft};">
                <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}
              </span>
            </td>
            <td class="svc-mono">${esc(row.metric)}</td>
            <td>${esc(row.owner)}</td>
            <td>${action}</td>
          </tr>
        `;
      }).join('');
  }

  // ------------------------------------------------------------------
  // Khung dùng chung
  // ------------------------------------------------------------------

  function panel(title, icon, body) {
    return `
      <article class="svc-panel">
        <h4 class="svc-panel-title"><i class="fa-solid ${icon}" aria-hidden="true"></i> ${esc(title)}</h4>
        ${body}
      </article>
    `;
  }

  function emptyState(message) {
    return `<p class="svc-empty">${esc(message)}</p>`;
  }

  return {
    STATUS,
    SEQUENTIAL,
    sequentialStep,
    inkOnStep,
    onTimeHero,
    kpiTiles,
    agingBuckets,
    trendByDay,
    slaPlaybook,
    riskHeatmap,
    drilldownRows,
  };
});
