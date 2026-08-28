const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('driver role badge has no-wrap styling', () => {
  assert.match(html, /master-driver-table/, 'Driver table should expose a stable styling hook.');
  assert.match(html, /driver-role-badge/, 'Driver role badge class is required.');
  assert.match(html, /\.driver-role-badge\s*\{[\s\S]*?white-space:\s*nowrap/i, 'Driver role badge must not wrap to multiple lines.');
  assert.match(html, /\.driver-name-cell\s*\{[\s\S]*?grid-template-columns/i, 'Driver name cell should keep avatar/name alignment stable.');
});

check('reporting view does not duplicate overview P&L monthly chart', () => {
  assert.doesNotMatch(html, /id=["']plChartCanvas["']/, 'Reporting must not render the monthly P&L canvas duplicated from overview.');
  assert.doesNotMatch(html, /title_monthly_pl/, 'Reporting must not show the monthly P&L chart block.');
  assert.doesNotMatch(appSource, /renderPLChartJS\s*\(/, 'Dashboard loading must not render the removed reporting P&L chart.');
  assert.doesNotMatch(appSource, /function\s+renderPLChartJS\b/, 'Removed reporting chart renderer must not remain active.');
});

if (failures.length) {
  throw new Error(`Master/reporting UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('MASTER_REPORTING_UI_OK');
