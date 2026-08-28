const assert = require('assert');
const fs = require('fs');
const path = require('path');

const mainPath = path.join(__dirname, '..', '..', 'backend', 'app', 'main.py');
const source = fs.readFileSync(mainPath, 'utf8');

assert.match(source, /@app\.get\("\/test-runner"/);
assert.match(source, /@app\.get\("\/kich-ban-test"/);
assert.match(source, /Kiểm thử API, không thay thế kiểm thử giao diện/);
assert.match(source, /(?:5,000|5000)/);

console.log('STRESS_RUNNER_CONFIG_OK');
