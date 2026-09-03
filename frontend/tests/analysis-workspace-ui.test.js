const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');
const reportSource = fs.readFileSync(path.join(root, 'js', 'transport-reporting.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'styles.css'), 'utf8');

function viewMarkup(id, nextId) {
  const start = html.indexOf(`<section id="${id}"`);
  const end = nextId ? html.indexOf(`<section id="${nextId}"`, start) : html.length;
  assert.ok(start >= 0, `Missing ${id}`);
  assert.ok(end > start, `Cannot find boundary after ${id}`);
  return html.slice(start, end);
}

const analysisView = viewMarkup('view-lab-summary', 'view-lab-summary-placeholder');

assert.match(analysisView, /id="analysis-workspace"/);
assert.match(analysisView, /id="transport-reporting-center"/);

// Man "Dau thau & Nha thau" (view-reporting) da duoc do: nghiep vu dau thau
// khong con dung. Khoi SLA/KPI truoc do da chuyen sang workspace Phan tich.
// Phan NHA THAU van giu: Carrier Master trong Master Data.
assert.doesNotMatch(html, /<section id="view-reporting"/);
assert.doesNotMatch(html, /id="tender-cockpit-panel"/);
assert.doesNotMatch(html, /data-view="reporting"/);
assert.match(html, /id="md-tab-carriers"|md-tab-carriers/);

// Khoi SLA/KPI gio nam trong workspace Phan tich.
assert.match(analysisView, /id="reporting-kpi-cards"/);
assert.match(analysisView, /data-analysis-pane="sla"/);
assert.match(analysisView, /id="reporting-drilldown-table"/);

for (const pane of ['overview', 'panorama', 'revenue', 'expenses', 'sla']) {
  assert.match(analysisView, new RegExp(`data-analysis-nav="${pane}"`));
  assert.match(analysisView, new RegExp(`data-analysis-pane="${pane}"`));
}

assert.match(analysisView, /id="analysis-workspace-selector"/);
assert.match(analysisView, /id="analysis-workspace-selector-toggle"/);
assert.match(analysisView, /id="analysis-workspace-selector-label"/);
assert.match(analysisView, /class="analysis-workspace-selector-menu"/);
assert.doesNotMatch(analysisView, /analysis-workspace-sidebar/);
assert.doesNotMatch(analysisView, /id="analysis-workspace-mobile-nav"/);
assert.match(reportSource, /function selectWorkspacePane\(name\)/);
assert.match(reportSource, /function toggleWorkspaceMenu\(force\)/);
assert.match(reportSource, /analysis-workspace-selector-label/);
assert.match(reportSource, /toggleWorkspaceMenu\(false\)/);
assert.match(reportSource, /document\.activeElement[\s\S]*\.blur\(\)/);
assert.match(reportSource, /data-analysis-nav/);
assert.match(appSource, /targetView === 'lab-summary'[\s\S]*TransportReporting\.load\(\)/);
assert.match(css, /\.analysis-workspace-layout\s*\{[^}]*display:\s*block/is);
assert.match(css, /\.analysis-workspace-selector-menu\s*\{[^}]*display:\s*none/is);
assert.match(css, /\.analysis-workspace-selector:hover\s+\.analysis-workspace-selector-menu[\s\S]*display:\s*grid/is);
assert.match(css, /\.analysis-workspace-selector\.open\s+\.analysis-workspace-selector-menu[\s\S]*display:\s*grid/is);
assert.match(analysisView, /id="transport-report-load-state"/);
assert.match(reportSource, /function setLoadState\(status,/);
assert.match(reportSource, /setLoadState\('error',\s*error\.message\)/);
assert.doesNotMatch(reportSource, /setLoadState\('error',\s*error\.message\);\s*showMessage\(error\.message,\s*'error'\)/);
assert.match(css, /\.transport-report-center\.has-load-error\s+\.transport-report-chart-grid\s*\{[^}]*display:\s*none/is);
assert.match(css, /\.transport-chart-canvas\s*\{[^}]*height:\s*220px/is);
assert.match(css, /@media\s*\(max-width:\s*760px\)[\s\S]*\.analysis-workspace-selector-menu\s*\{[^}]*grid-template-columns:\s*1fr/is);

console.log('ANALYSIS_WORKSPACE_UI_OK');
