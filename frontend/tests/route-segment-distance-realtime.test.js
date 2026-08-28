const assert = require('assert');
const path = require('path');

const policy = require(path.join(__dirname, '..', 'js', 'route-segment-policy.js'));

const invalid = policy.validateManualDistance({ km: 0, confirmed: true, source: 'odometer' });
assert.strictEqual(invalid.ok, false);
assert.strictEqual(invalid.code, 'INVALID_DISTANCE');

const unconfirmed = policy.validateManualDistance({ km: 44.7, confirmed: false, source: 'odometer' });
assert.strictEqual(unconfirmed.ok, false);
assert.strictEqual(unconfirmed.code, 'MANUAL_DISTANCE_CONFIRMATION_REQUIRED');

(async () => {
  let persisted;
  const result = await policy.resolveSegment({
    from: 'Kho VSIP',
    to: 'Cảng Cát Lái',
    routingClient: async () => ({ distKm: 44.7, durationMinutes: 55 }),
    persist: (segment) => { persisted = segment; },
  });
  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.segment.distance_km, 44.7);
  assert.strictEqual(result.segment.distance_source, 'routing_service');
  assert.deepStrictEqual(persisted, result.segment);
  console.log('ROUTE_SEGMENT_DISTANCE_REALTIME_OK');
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
