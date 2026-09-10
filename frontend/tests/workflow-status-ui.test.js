const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const langSource = fs.readFileSync(path.join(frontendRoot, 'js', 'lang.json'), 'utf8');

function optionValues(selectId) {
  const select = html.match(new RegExp(`<select[^>]+id=["']${selectId}["'][\\s\\S]*?<\\/select>`));
  assert.ok(select, `Missing select #${selectId}`);
  return [...select[0].matchAll(/<option[^>]+value=["']([^"']+)["']/g)].map((match) => match[1]);
}

assert.deepStrictEqual(
  optionValues('do-status'),
  ['Pending', 'In Transit', 'Delivered', 'Cancelled'],
  'Delivery Order UI must match the canonical backend lifecycle.'
);

assert.doesNotMatch(
  appSource,
  /body:\s*\{\s*status:\s*['"]Arrived['"]\s*\}/,
  'Arrived is an operational milestone, not a Delivery Order lifecycle state.'
);

assert.strictEqual(
  (langSource.match(/"status_delivered"\s*:/g) || []).length,
  1,
  'Translation keys must be unique.'
);

console.log('WORKFLOW_STATUS_UI_OK');
