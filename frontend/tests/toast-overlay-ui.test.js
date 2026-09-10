const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const toast = appSource.match(/window\.showToast\s*=\s*function\s*\(msg\)\s*\{[\s\S]*?\n\};/);

assert.ok(toast, 'Missing global showToast().');
assert.match(toast[0], /data-app-toast['"],\s*['"]top-right['"]/, 'Toast must use the non-blocking top-right layout.');
assert.match(toast[0], /calc\(var\(--header-height, 72px\) \+ 12px\)/, 'Desktop toast must sit below the application header.');
assert.match(toast[0], /toast\.style\.right\s*=\s*['"]20px['"]/, 'Desktop toast must align with the right content edge.');
assert.doesNotMatch(toast[0], /toast\.style\.left\s*=\s*['"]50%['"]/, 'Toast must not cover the center of the active form.');
assert.doesNotMatch(toast[0], /translate\(-50%,\s*-50%\)/, 'Toast must not use centered overlay transforms.');
assert.match(toast[0], /translateY\(-10px\)/, 'Toast should enter with a compact vertical motion.');
assert.match(toast[0], /toast\.style\.zIndex\s*=\s*['"]2147483647['"]/, 'Toast must sit above modals/forms.');
assert.doesNotMatch(toast[0], /toast\.style\.bottom\s*=/, 'Toast must not be anchored to the bottom of the screen.');
assert.match(toast[0], /min\(390px, calc\(100vw - 24px\)\)/, 'Toast width must remain compact on desktop and safe on mobile.');
assert.match(toast[0], /@media \(max-width: 600px\)/, 'Toast needs an explicit mobile layout.');
assert.match(toast[0], /toast\.setAttribute\(['"]role['"],\s*['"]status['"]\)/, 'Toast should announce operation feedback.');
assert.match(toast[0], /data-toast-title/, 'Toast must render a dedicated title line.');
assert.match(toast[0], /data-toast-body/, 'Toast must render message body separately from title.');
assert.match(toast[0], /data-toast-copy/, 'Compact toast must align its title and message in one status row.');
assert.match(toast[0], /data-toast-icon-badge/, 'Toast must use a polished icon badge.');
assert.match(toast[0], /data-toast-progress/, 'Toast must include a subtle progress/accent bar.');
assert.match(toast[0], /data-toast-close/, 'Toast must expose a compact dismiss button.');
assert.match(toast[0], /backdropFilter/, 'Toast should use a refined translucent surface.');
assert.match(toast[0], /linear-gradient\(90deg/, 'Toast should use a horizontal accent treatment.');
assert.match(toast[0], /toast\.style\.borderLeft\s*=\s*`3px solid \$\{tone\.progress\}`/, 'Toast should use a restrained status accent instead of a full colored outline.');

[
  ['quotation save', /window\.saveOracleQT\s*=\s*async function[\s\S]*?executeWorkflowCommand[\s\S]*?showToast/],
  ['quotation approve', /window\.approveQuotation\s*=\s*async function[\s\S]*?executeWorkflowCommand[\s\S]*?showToast/],
  ['delivery completion', /window\.submitDeliveryCompletion\s*=\s*async function[\s\S]*?showToast\(`Đang lưu POD[\s\S]*?\/complete-delivery[\s\S]*?showToast\(`Đã hoàn tất/],
].forEach(([name, pattern]) => {
  assert.match(appSource, pattern, `${name} must show visible backend operation feedback.`);
});

console.log('TOAST_OVERLAY_UI_OK');
