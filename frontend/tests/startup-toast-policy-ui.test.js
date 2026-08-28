const assert = require('assert');
const fs = require('fs');
const path = require('path');

const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

assert.match(
  app,
  /window\.loadSelectedFormulaPreset\s*=\s*function\s*\(key,\s*options\s*=\s*\{\}\)/,
  'Formula loading must accept an explicit notification policy.'
);
assert.match(
  app,
  /if\s*\(options\.notify\s*!==\s*false\)\s*\{[\s\S]*?showToast\(toastMsg\);[\s\S]*?\}/,
  'A user-triggered formula selection should still be allowed to show feedback.'
);
assert.match(
  app,
  /loadSelectedFormulaPreset\([\s\S]*?\{\s*notify:\s*false\s*\}\s*\);[\s\S]*?catch\s*\(error\)/,
  'Formula hydration during application startup must be silent.'
);

console.log('STARTUP_TOAST_POLICY_OK');
