const assert = require('assert');
const path = require('path');

const utils = require(path.join(__dirname, '..', 'js', 'route-map-utils.js'));
const route = {
  id: 'RT-TEST',
  segments_json: JSON.stringify([
    { from: 'Kho A', to: 'Trạm B' },
    { from: 'Trạm B', to: 'Cảng C' },
  ]),
};

assert.deepStrictEqual(utils.buildOrderedRouteLocations(route), ['Kho A', 'Trạm B', 'Cảng C']);
assert.deepStrictEqual(
  utils.buildOrderedRouteLocations([{ from: 'Kho A', to: '' }]),
  [],
  'Chặng thiếu điểm đến không được dùng để vẽ tuyến.'
);

(async () => {
  const geocoded = await utils.resolveRouteWaypoints(route, async (label) => ({
    lat: label.length,
    lng: label.length + 100,
    label,
  }));
  assert.strictEqual(geocoded.length, 3);
  assert.strictEqual(geocoded[2].label, 'Cảng C');
  console.log('ROUTE_MAP_UTILS_OK');
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
