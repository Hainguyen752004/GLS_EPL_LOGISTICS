/**
 * Test cho phần trình bày "Chất lượng dịch vụ (SLA)".
 *
 * Kiểm cả hành vi (HTML sinh ra đúng chưa) lẫn các quy tắc thiết kế mà phần
 * này cam kết: màu trạng thái luôn kèm icon và chữ, thang độ lớn chỉ dùng một
 * sắc, dữ liệu từ server luôn được escape.
 */
const assert = require('assert');
const path = require('path');
const fs = require('fs');

const view = require(path.join(__dirname, '..', 'js', 'sla-analytics.js'));

// --------------------------------------------------------------------------
// Dữ liệu mẫu theo đúng hợp đồng của TmsCockpit.buildReportingDrilldown
// --------------------------------------------------------------------------

const REPORT = {
  kpis: {
    total_orders: { label: 'Tổng đơn phân tích', count: 9 },
    on_time_rate: { label: 'Tỉ lệ đúng hạn', percent: 78 },
    sla_risks: { label: 'Cảnh báo SLA/KPI', count: 12 },
    critical_risks: { label: 'Cảnh báo nghiêm trọng', count: 12 },
    cost_overrun: { label: 'Vượt chi phí', count: 0 },
  },
  executive_summary: 'SLA có 12 cảnh báo, 12 cảnh báo nghiêm trọng.',
  aging_buckets: [
    { key: 'under_30', label: 'Dưới 30 phút', count: 0, severity: 'info' },
    { key: '30_60', label: '30–60 phút', count: 0, severity: 'info' },
    { key: '60_120', label: '60–120 phút', count: 0, severity: 'warning' },
    { key: 'over_120', label: 'Trên 120 phút', count: 12, severity: 'critical' },
  ],
  trend_by_day: [
    { date: '2026-08-21', issue_count: 2, critical_count: 2, warning_count: 0 },
    { date: '2026-08-22', issue_count: 3, critical_count: 1, warning_count: 2 },
  ],
  risk_heatmap: [
    {
      dimension: 'Khách hàng',
      target: 'customers',
      items: [
        { label: 'Vissan', issue_count: 4, total_orders: 5, risk_level: 'critical', on_time_rate: 20 },
        { label: 'Unilever', issue_count: 0, total_orders: 3, risk_level: 'ok', on_time_rate: 100 },
      ],
    },
    { dimension: 'Tuyến đường', target: 'routes', items: [] },
  ],
  sla_playbook: [
    { code: 'ESCALATE_LATE_DELIVERY', label: 'Xử lý trễ giao hàng', trigger_count: 6, instruction: 'Mở GPS/POD.', navigation: { view: 'tracking' } },
    { code: 'FIX_MISSING_POD', label: 'Bổ sung POD', trigger_count: 0, instruction: 'Upload POD.', navigation: { view: 'tracking' } },
  ],
  drilldown_rows: [
    { order_id: 'DO-001', issue_label: 'Trễ giao hàng', severity: 'warning', metric: '35 phút', owner: 'Điều phối', action_label: 'Mở GPS/POD', navigation: { view: 'tracking' } },
    { order_id: 'DO-002', issue_label: 'Thiếu POD', severity: 'critical', metric: '2 ngày', owner: 'Vận hành', action_label: 'Mở GPS/POD', navigation: { view: 'tracking' } },
  ],
};

// --------------------------------------------------------------------------
// 1. Thang độ lớn phải là MỘT sắc, đơn điệu
// --------------------------------------------------------------------------

assert.strictEqual(view.SEQUENTIAL.length, 5);
assert.deepStrictEqual(
  view.SEQUENTIAL,
  ['#eff6ff', '#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8'],
  'thang độ lớn phải giữ nguyên một sắc xanh, không xen sắc khác'
);

// Giá trị 0 luôn ở bước nhạt nhất; giá trị bằng max ở bước đậm nhất.
assert.strictEqual(view.sequentialStep(0, 10), '#eff6ff');
assert.strictEqual(view.sequentialStep(10, 10), '#1d4ed8');
// Không chia cho 0.
assert.strictEqual(view.sequentialStep(5, 0), '#eff6ff');
// Đơn điệu: giá trị lớn hơn không bao giờ ra bước nhạt hơn.
let previous = -1;
for (let value = 0; value <= 10; value++) {
  const index = view.SEQUENTIAL.indexOf(view.sequentialStep(value, 10));
  assert.ok(index >= previous, `bước thang giảm khi giá trị tăng tại ${value}`);
  previous = index;
}

// Chữ trên bước đậm phải là màu sáng để còn đọc được.
assert.strictEqual(view.inkOnStep('#1d4ed8'), '#ffffff');
assert.strictEqual(view.inkOnStep('#eff6ff'), '#0f172a');

// --------------------------------------------------------------------------
// 2. Màu trạng thái không bao giờ là tín hiệu DUY NHẤT
// --------------------------------------------------------------------------

// Mỗi trạng thái phải có icon riêng, không chỉ khác màu.
const icons = Object.values(view.STATUS).map(entry => entry.icon);
assert.strictEqual(new Set(icons).size, icons.length, 'mỗi trạng thái phải có icon riêng');

// Bảng chi tiết: mỗi chip mức độ đều có icon và chữ.
{
  const html = view.drilldownRows(REPORT.drilldown_rows, 'vi');
  const chips = html.match(/<span class="svc-chip"[\s\S]*?<\/span>/g) || [];
  assert.strictEqual(chips.length, 2);
  for (const chip of chips) {
    assert.ok(/fa-solid fa-/.test(chip), 'chip mức độ thiếu icon');
    assert.ok(/(Nghiêm trọng|Cảnh báo|Đạt|Thông tin)/.test(chip), 'chip mức độ thiếu chữ');
  }
}

// Chú giải biểu đồ cột cũng phải có icon kèm chữ, không chỉ ô màu.
{
  const html = view.trendByDay(REPORT.trend_by_day, 'vi');
  assert.ok(html.includes('svc-legend'), 'hai chuỗi thì phải có chú giải');
  assert.ok(/svc-swatch[\s\S]*?fa-solid[\s\S]*?Nghiêm trọng/.test(html));
  assert.ok(/svc-swatch[\s\S]*?fa-solid[\s\S]*?Cảnh báo/.test(html));
}

// --------------------------------------------------------------------------
// 3. Số dẫn dắt: ngưỡng và thanh đo
// --------------------------------------------------------------------------

// 78% → nghiêm trọng (dưới 85).
{
  const html = view.onTimeHero(REPORT.kpis, REPORT.executive_summary, 'vi');
  assert.ok(html.includes('#b91c1c'), '78% phải là mức nghiêm trọng');
  assert.ok(html.includes('width:78%'), 'thanh đo phải khớp giá trị');
  assert.ok(html.includes('aria-label='), 'thanh đo phải có nhãn cho trình đọc màn hình');
}
// 96% → đạt.
assert.ok(
  view.onTimeHero({ on_time_rate: { percent: 96 }, total_orders: { count: 4 } }, '', 'vi').includes('#059669')
);
// 90% → cảnh báo.
assert.ok(
  view.onTimeHero({ on_time_rate: { percent: 90 }, total_orders: { count: 4 } }, '', 'vi').includes('#d97706')
);
// Giá trị ngoài khoảng bị kẹp lại, không tràn thanh đo.
assert.ok(view.onTimeHero({ on_time_rate: { percent: 140 } }, '', 'vi').includes('width:100%'));
assert.ok(view.onTimeHero({ on_time_rate: { percent: -5 } }, '', 'vi').includes('width:0%'));
// Thiếu dữ liệu thì không được vỡ.
assert.ok(view.onTimeHero(undefined, undefined, 'vi').includes('svc-hero'));

// --------------------------------------------------------------------------
// 4. Ô chỉ số: 0 việc cần làm là tin TỐT, không phải trung tính
// --------------------------------------------------------------------------

{
  const html = view.kpiTiles(REPORT.kpis, 'vi');
  // cost_overrun = 0 → đạt (xanh); sla_risks = 12 → cảnh báo; critical = 12 → nghiêm trọng.
  assert.ok(html.includes('#059669'), 'chỉ số bằng 0 phải hiện là đạt');
  assert.ok(html.includes('#d97706'));
  assert.ok(html.includes('#b91c1c'));
  // Tổng đơn phân tích chỉ là số nền, không mang màu trạng thái.
  const tiles = html.match(/<article class="svc-tile"[\s\S]*?<\/article>/g) || [];
  assert.strictEqual(tiles.length, 4);
  const neutral = tiles.find(tile => tile.includes('Tổng đơn phân tích'));
  assert.ok(neutral && !neutral.includes('svc-tile-state'),
    'số nền không được gắn nhãn trạng thái');
}

// --------------------------------------------------------------------------
// 5. Thanh ngang: đậm theo THỨ TỰ nhóm, kể cả khi nhóm đang bằng 0
// --------------------------------------------------------------------------

{
  const html = view.agingBuckets(REPORT.aging_buckets, 'vi');
  // Nhóm trễ nặng nhất phải dùng bước đậm nhất dù các nhóm nhẹ đang bằng 0.
  assert.ok(html.includes('#1d4ed8'), 'nhóm trễ nặng nhất phải đậm nhất');
  // Giá trị ghi trực tiếp nên không cần trục số.
  assert.ok(html.includes('svc-bar-value'));
  // Nhóm bằng 0 vẫn hiện dòng, không bị ẩn.
  assert.strictEqual((html.match(/svc-bar-row/g) || []).length, 4);
}
// Không có dữ liệu thì hiện trạng thái rỗng, không vỡ.
assert.ok(view.agingBuckets([], 'vi').includes('svc-empty'));
assert.ok(view.agingBuckets(undefined, 'vi').includes('svc-empty'));

// --------------------------------------------------------------------------
// 6. Cột xếp chồng: hai phần cộng lại đúng 100%
// --------------------------------------------------------------------------

{
  const html = view.trendByDay(REPORT.trend_by_day, 'vi');
  const columns = html.match(/<li class="svc-col"[\s\S]*?<\/li>/g) || [];
  assert.strictEqual(columns.length, 2);
  for (const column of columns) {
    const heights = [...column.matchAll(/svc-col-seg--\w+" style="height:(\d+)%/g)]
      .map(match => Number(match[1]));
    assert.strictEqual(heights.length, 2, 'mỗi cột phải có đúng hai phần');
    assert.strictEqual(heights[0] + heights[1], 100, 'hai phần phải cộng đủ 100%');
  }
  // Ngày 2026-08-21 có 2/2 là nghiêm trọng → phần nghiêm trọng chiếm 100%.
  assert.ok(columns[0].includes('svc-col-seg--critical" style="height:100%'));
}

// --------------------------------------------------------------------------
// 7. Việc cần làm: chỉ hiện việc thực sự có
// --------------------------------------------------------------------------

{
  const html = view.slaPlaybook(REPORT.sla_playbook, 'vi');
  assert.ok(html.includes('Xử lý trễ giao hàng'), 'việc có 6 lần phải hiện');
  assert.ok(!html.includes('Bổ sung POD'), 'việc có 0 lần không được chiếm chỗ');
}
assert.ok(view.slaPlaybook([], 'vi').includes('svc-empty'));

// --------------------------------------------------------------------------
// 8. Bản đồ rủi ro
// --------------------------------------------------------------------------

{
  const html = view.riskHeatmap(REPORT.risk_heatmap, 'vi');
  assert.ok(html.includes('Khách hàng') && html.includes('Tuyến đường'));
  // Chiều không có dữ liệu vẫn hiện thẻ, kèm trạng thái rỗng.
  assert.ok(html.includes('svc-empty'));
  // Có thang màu để người đọc biết ô đậm nghĩa là gì.
  assert.ok(html.includes('svc-scale-step'));
  // Tỉ lệ đúng hạn là đại lượng KHÁC nên không dùng chung cách mã hóa với ô số.
  assert.ok(html.includes('svc-heat-rate'));
}
assert.strictEqual(view.riskHeatmap([], 'vi'), '');

// --------------------------------------------------------------------------
// 9. Dữ liệu từ server phải được escape ở mọi hàm
// --------------------------------------------------------------------------

const ATTACK = '<img src=x onerror=alert(1)>';
const cases = [
  ['onTimeHero', () => view.onTimeHero(REPORT.kpis, ATTACK, 'vi')],
  ['agingBuckets', () => view.agingBuckets([{ label: ATTACK, count: 1 }], 'vi')],
  ['slaPlaybook', () => view.slaPlaybook([{ label: ATTACK, trigger_count: 1, instruction: ATTACK }], 'vi')],
  ['riskHeatmap', () => view.riskHeatmap([{ dimension: ATTACK, items: [{ label: ATTACK, issue_count: 1, on_time_rate: 50, risk_level: 'ok' }] }], 'vi')],
  ['drilldownRows', () => view.drilldownRows([{ order_id: ATTACK, issue_label: ATTACK, severity: 'warning', metric: ATTACK, owner: ATTACK }], 'vi')],
  ['trendByDay', () => view.trendByDay([{ date: ATTACK, issue_count: 1, critical_count: 1 }], 'vi')],
];
for (const [name, run] of cases) {
  const html = run();
  assert.ok(!html.includes('<img src=x'), `${name} chưa escape dữ liệu`);
  assert.ok(html.includes('&lt;img src=x'), `${name} phải escape thành thực thể HTML`);
}

// Tên view trong onclick cũng phải được escape (nó đi vào chuỗi JavaScript).
{
  const html = view.drilldownRows(
    [{ order_id: 'DO-1', issue_label: 'x', severity: 'warning', metric: '1', owner: 'y', navigation: { view: "');alert(1);('" } }],
    'vi'
  );
  assert.ok(!/switchView\('\);alert/.test(html), 'tên view chưa được escape');
}

// --------------------------------------------------------------------------
// 10. Đa ngôn ngữ
// --------------------------------------------------------------------------

assert.ok(view.onTimeHero(REPORT.kpis, '', 'en').includes('On-time delivery rate'));
assert.ok(view.onTimeHero(REPORT.kpis, '', 'la').includes('ອັດຕາການສົ່ງຕົງເວລາ'));
// Ngôn ngữ lạ thì lùi về tiếng Việt, không để trống.
assert.ok(view.onTimeHero(REPORT.kpis, '', 'zz').includes('Tỉ lệ giao đúng hạn'));

// --------------------------------------------------------------------------
// 11. Nối vào ứng dụng
// --------------------------------------------------------------------------

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

// CSS và module phải được nạp, module trước app.js.
assert.ok(html.includes('css/sla-analytics.css'), 'phải nạp sla-analytics.css');
assert.ok(html.includes('js/sla-analytics.js'), 'phải nạp sla-analytics.js');
assert.ok(
  html.indexOf('js/sla-analytics.js') < html.indexOf('js/app.js'),
  'sla-analytics.js phải nạp trước app.js'
);

// Pane SLA nằm trong workspace Phân tích, và mỗi container chỉ có MỘT chỗ.
assert.ok(html.includes('data-analysis-pane="sla"'), 'phải có pane sla trong workspace Phân tích');
assert.ok(html.includes('data-analysis-nav="sla"'), 'phải có nút chọn pane sla');
for (const id of ['reporting-hero', 'reporting-kpi-cards', 'reporting-panels', 'reporting-drilldown-table']) {
  const count = (html.match(new RegExp(`id="${id}"`, 'g')) || []).length;
  assert.strictEqual(count, 1, `id ${id} phải tồn tại đúng một chỗ, đang có ${count}`);
}

// Khối SLA cũ đã rời khỏi màn Đấu thầu.
assert.ok(!html.includes('id="reporting-drilldown-panel"'), 'khối SLA cũ phải được dỡ khỏi màn Báo cáo');

// Màn "Đấu thầu & Nhà thầu" đã được dỡ hẳn: nghiệp vụ đấu thầu không còn dùng.
// Phần nhà thầu vẫn giữ ở Carrier Master trong Master Data.
assert.ok(!html.includes('id="tender-cockpit-panel"'), 'Tender Cockpit phải được dỡ');
assert.ok(!html.includes('<section id="view-reporting"'), 'section view-reporting phải được dỡ');
// Màn Phân tích phải còn đường đi tới từ khung điều hướng. Trước đây phép
// kiểm neo vào đúng chuỗi "Phân tích Doanh thu &amp; Chi phí" của "mega menu"
// cũ; khung ba tầng đặt nhãn qua khóa dịch `khung_mi_analysis`, nên neo vào
// chuỗi cứng là neo vào một thứ không còn tồn tại. Kiểm cái THẬT SỰ quan
// trọng: có một mục nào trong khung trỏ tới màn này hay không.
assert.ok(/data-i18n="khung_mi_analysis"/.test(html),
  'khung điều hướng phải có mục dẫn tới màn Phân tích');
assert.ok(/data-view="lab-summary"/.test(html),
  'mục dẫn tới màn Phân tích phải trỏ đúng #view-lab-summary');

// renderReportingDrilldown giờ chỉ điều phối, không tự dựng HTML kèm style inline.
// Cắt đúng thân hàm: từ khai báo tới dấu "}" đầu tiên ở cột 0. Cắt theo số ký
// tự sẽ lấn sang hàm kế tiếp và làm phép kiểm tra vô nghĩa.
const renderStart = app.indexOf('function renderReportingDrilldown()');
const renderFn = app.slice(renderStart, app.indexOf('\n}', renderStart) + 2);
assert.ok(renderFn.includes('window.SlaAnalytics'), 'phải dùng module trình bày');
assert.ok(!/style="background:#ffffff; border:1px solid/.test(renderFn),
  'không được quay lại dựng HTML kèm style inline');

console.log('sla-analytics: tất cả kiểm tra đã qua');

// --------------------------------------------------------------------------
// 12. Dọn nợ kỹ thuật ở màn Báo cáo / Bảng điều khiển
// --------------------------------------------------------------------------

// switchView('transportation') từng chỉ hiện "không tìm thấy màn hình", nên
// hệ thống bảo người dùng đi mở Trip rồi không đưa họ tới được.
assert.ok(
  /transportation:\s*'delivery-shipment'/.test(app),
  "phải có alias transportation -> delivery-shipment"
);
assert.ok(
  !html.includes('id="view-transportation"'),
  'không có màn hình transportation nên phải đi qua alias'
);

// Các thẻ minh họa trong Bảng điều khiển chứa số cố định trong HTML
// (2.587.500, 2.846.250...) nên phải nói rõ để không bị hiểu là dữ liệu thật.
{
  const cards = (html.match(/class="master-form-card"/g) || []).length;
  const flags = (html.match(/class="svc-sample-flag"/g) || []).length;
  assert.ok(cards > 0, 'không tìm thấy thẻ minh họa nào');
  assert.strictEqual(flags, cards,
    `mọi thẻ minh họa phải có nhãn: ${cards} thẻ nhưng chỉ ${flags} nhãn`);
  assert.ok(html.includes('2,587,500'), 'số minh họa vẫn còn (không xóa, chỉ gắn nhãn)');
}

// Khối P&L luôn hidden với canvas không có id đã được dỡ, cùng dữ liệu nuôi nó.
assert.ok(
  !/<div hidden>[\s\S]{0,400}Lợi Nhuận Hàng Tháng/.test(html),
  'khối P&L hidden phải được dỡ'
);

// Hàm render SLA cũ ghi vào container không tồn tại đã được dỡ.
assert.ok(
  !/^function renderSlaKpiDrilldown\(\)/m.test(app),
  'renderSlaKpiDrilldown phải được dỡ'
);
// Nhưng builder thì vẫn dùng qua buildReportingDrilldown, không được xóa.
{
  const utils = fs.readFileSync(path.join(__dirname, '..', 'js', 'tms-cockpit-utils.js'), 'utf8');
  assert.ok(/function buildSlaKpiDrilldown/.test(utils),
    'buildSlaKpiDrilldown vẫn được buildReportingDrilldown dùng');
}

console.log('don no ky thuat: tất cả kiểm tra đã qua');

// --------------------------------------------------------------------------
// 13. Chống cache cũ
// --------------------------------------------------------------------------

// Sửa app.js mà không nâng ?v= thì trình duyệt vẫn nạp bản cũ từ cache, nên
// người dùng không thấy bản sửa và tưởng là chưa sửa.
{
  const version = /js\/app\.js\?v=([^"]+)/.exec(html);
  assert.ok(version, 'app.js phải có tham số ?v= chống cache');
  assert.ok(
    version[1] !== '20260827-dispatch-day-workbench-v1',
    'phải nâng phiên bản app.js sau khi sửa, nếu không trình duyệt nạp bản cũ'
  );
  const reporting = /js\/transport-reporting\.js\?v=([^"]+)/.exec(html);
  assert.ok(
    reporting && reporting[1] !== '20260824-analysis-top-selector-v3',
    'phải nâng phiên bản transport-reporting.js sau khi sửa'
  );
}

console.log('chong cache: tất cả kiểm tra đã qua');
