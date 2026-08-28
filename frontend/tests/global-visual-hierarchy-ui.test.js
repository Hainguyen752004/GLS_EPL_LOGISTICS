const assert = require('assert');
const fs = require('fs');
const path = require('path');

const css = fs.readFileSync(path.join(__dirname, '..', 'css', 'styles.css'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

assert.ok(css.includes('--border-color: #cbd6e2;'), 'default borders must remain visible on white surfaces');
assert.ok(css.includes('--border-strong: #aebfd1;'), 'outer panels need a shared strong border');
assert.ok(css.includes('--divider-color: #bdcad8;'), 'section dividers need a shared contrast token');
assert.ok(css.includes('--surface-subtle: #f1f5f9;'), 'lists and toolbars need a distinct secondary surface');
assert.ok(css.includes('--surface-heading: #e6edf5;'), 'section headings need a distinct structural surface');
assert.ok(css.includes('--surface-selected: #dcecff;'), 'selected records need a shared selected surface');

assert.ok(css.includes('.card-panel,'), 'common panels must share the global hierarchy treatment');
assert.ok(css.includes('.fiori-page-header,'), 'page headers must share the global hierarchy treatment');
assert.ok(css.includes('.fiori-table-wrapper'), 'table shells must share the global hierarchy treatment');
assert.ok(css.includes('border-color: var(--border-strong) !important;'), 'common surfaces must use the strong outer border');
assert.ok(css.includes('.data-table th,'), 'table headings must share a stronger heading surface');
assert.ok(css.includes('background: var(--surface-heading) !important;'), 'structural headings need visible contrast');
assert.ok(css.includes('.data-table td,'), 'table rows must share visible separators');
assert.ok(css.includes('border-color: var(--divider-color) !important;'), 'row and section separators must use the divider token');
assert.ok(css.includes('[style*="border: 1px solid #e2e8f0"]'), 'legacy inline panel borders need the hierarchy bridge');
assert.ok(css.includes('[style*="border-bottom:1px solid #e2e8f0"]'), 'legacy inline section dividers need the hierarchy bridge');
assert.ok(css.includes('[style*="border:1px solid #d8e5f2"]'), 'newer inline panel borders need the hierarchy bridge');

assert.ok(html.includes('/static/css/styles.css?v=20260826-visual-hierarchy-v1'), 'stylesheet cache key must expose the hierarchy update');

console.log('GLOBAL_VISUAL_HIERARCHY_UI_OK');
