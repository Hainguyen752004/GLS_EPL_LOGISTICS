const assert = require('node:assert/strict');
const E = require('../js/cost-expression');
const terms = [{key:'fuel',rate:4800,kind:'cost',factor:'per_km'}, {key:'rate',rate:1200,kind:'revenue',factor:'per_kg'}];
const expressions = {COST:'fuel * km + max(100, 50)',REV:'max(rate * kg, 2500000)',PROFIT:'(REV - COST) * 0.97'};
const r = E.evaluate(expressions, terms, {km:200,tonnes:15});
assert.equal(r.cost,960100);
assert.equal(r.revenue,18000000);
assert.equal(r.profit,(18000000-960100)*.97);
for(const expr of ['fuel / 0','globalThis.x','max.constructor(1)','unknown + 1','REV','true','2 ** 100000']) {
  assert.throws(()=>E.evaluate({...expressions,COST:expr,REV:'COST'},terms,{km:200,tonnes:15}));
}
console.log('cost-expression: precedence, functions, cycles, invalid syntax OK');
