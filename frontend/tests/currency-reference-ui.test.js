const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');

assert.match(html, /id=["']currency-reference-refresh["'][^>]*onclick=["']refreshCurrencyReferenceRates\(\)["']/, 'Currency screen needs a manual reference refresh command.');
assert.match(html, /id=["']currency-reference-status["']/, 'Currency screen needs a visible source and freshness status.');
assert.match(html, /12\s*giờ/i, 'Currency screen must disclose the 12-hour refresh interval.');
assert.match(appSource, /window\.refreshCurrencyReferenceRates\s*=\s*async/, 'App must expose the manual refresh flow.');
assert.match(appSource, /\/api\/currencies\/reference-rates\/refresh/, 'Manual refresh must call the backend reference endpoint.');
assert.match(appSource, /Tham chiếu chưa áp dụng/i, 'Reference values must be identified as not yet applied.');
assert.match(appSource, /window\.loadCurrencyReferenceStatus\s*=\s*async/, 'App must load the cached provider status without making a provider request.');
assert.match(html, /id=["']currency-rate-history["']/, 'Currency screen needs a database-backed history view.');
assert.match(html, /data-rate-role=["']current["']/, 'Currency cards must identify the approved current rate.');
assert.match(html, /data-rate-role=["']previous["']/, 'Currency cards must identify the previous rate.');
assert.match(html, /data-rate-role=["']reference["']/, 'Currency cards must identify the provider proposal.');
assert.match(appSource, /\/api\/currencies\/history/, 'App must load approved rate history from the backend.');
assert.match(appSource, /CurrencyRateUtils\.parseCurrencyRateNumber/, 'Currency calculations must use the locale-safe parser.');

const refreshStart = appSource.indexOf('window.refreshCurrencyReferenceRates');
const refreshEnd = appSource.indexOf('window.saveCurrencyRates', refreshStart);
const refreshFlow = appSource.slice(refreshStart, refreshEnd);
assert.doesNotMatch(refreshFlow, /method:\s*['"]POST['"][\s\S]*body:\s*JSON\.stringify\(\{\s*USD/, 'Reference refresh must not automatically save approved operational rates.');

console.log('CURRENCY_REFERENCE_UI_OK');
