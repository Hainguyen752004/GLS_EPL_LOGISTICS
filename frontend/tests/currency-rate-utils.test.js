const assert = require('assert');
const { parseCurrencyRateNumber, convertVndByRate } = require('../js/currency-rate-utils.js');

assert.strictEqual(parseCurrencyRateNumber('26.173,50'), 26173.5);
assert.strictEqual(parseCurrencyRateNumber('26,173.50'), 26173.5);
assert.strictEqual(parseCurrencyRateNumber('25,450'), 25450);
assert.strictEqual(parseCurrencyRateNumber('1.000'), 1000);
assert.strictEqual(parseCurrencyRateNumber('1.18'), 1.18);
assert.strictEqual(parseCurrencyRateNumber('710'), 710);
assert.ok(Number.isNaN(parseCurrencyRateNumber('không hợp lệ')));
assert.strictEqual(convertVndByRate('1.000', '26.173,50'), 0.04);

console.log('CURRENCY_RATE_UTILS_OK');
