const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

assert.match(
  html,
  /onclick=["']appendFormulaToken\('\*',\s*['"]\*['"],\s*['"]op['"]\)[^>]*>\s*\*\s*</,
  'Multiplication formula control must have a visible label.'
);
assert.match(
  html,
  /onclick=["']appendFormulaToken\('\/',\s*['"]\/['"],\s*['"]op['"]\)[^>]*>\s*\/\s*</,
  'Division formula control must have a visible label.'
);
assert.match(html, /Thêm Khách Hàng Mới/, 'Customer create button must keep the full Vietnamese label.');

console.log('VISIBLE_FORM_CONTROLS_UI_OK');
