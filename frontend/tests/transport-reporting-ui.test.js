const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const source = fs.readFileSync(path.join(root, 'js', 'transport-reporting.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'styles.css'), 'utf8');

assert.match(html, /id="transport-reporting-center"/);
for (const pane of ['overview', 'revenue', 'expenses']) {
  assert.match(html, new RegExp(`data-analysis-pane="${pane}"`));
}
for (const id of ['transport-revenue-chart', 'transport-customer-chart', 'transport-cargo-chart']) {
  assert.match(html, new RegExp(`id="${id}"`));
}
assert.match(source, /\/api\/tms\/reporting\/transport-revenue/);
assert.match(source, /\/api\/tms\/reporting\/expense-vouchers/);
assert.match(source, /\/expense-voucher/);
assert.match(source, /Idempotency-Key/);
assert.match(source, /new Chart\(/);
assert.match(source, /export\.csv/);
assert.match(html, /Biển số rơ-moóc/);
assert.match(css, /\.transport-report-table-wrap\s*\{[^}]*overflow:\s*auto/is);
assert.match(html, /id="analysis-workspace-selector-toggle"/);
assert.match(css, /@media\s*\(max-width:\s*760px\)[\s\S]*\.analysis-workspace-selector-menu\s*\{[^}]*grid-template-columns:\s*1fr/is);

console.log('TRANSPORT_REPORTING_UI_OK');
