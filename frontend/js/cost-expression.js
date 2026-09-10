(function(root, factory) {
  const api = factory(typeof module === 'object' && module.exports ? require('jsep') : root.jsep);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.CostExpression = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function(parse) {
  const names = ['COST', 'REV', 'PROFIT'];
  function defaults(terms) {
    const build = kind => terms.filter(t => (t.kind || 'cost') === kind).map((t,i) =>
      `${t.operator === 'sub' ? '-' : i ? '+' : ''}${t.key}${({per_km:' * km',per_kg:' * kg',per_tonne:' * tonnes',per_stop:' * stops'})[t.factor] || ''}`).join(' ') || '0';
    return {COST:build('cost'),REV:build('revenue'),PROFIT:'REV - COST'};
  }
  function evaluate(expressions, terms, trip = {}) {
    const formulas = {...defaults(terms), ...expressions};
    const scope = Object.create(null);
    terms.forEach(t => {scope[t.key] = Number(t.rate || 0);});
    Object.assign(scope, {km:Number(trip.km ?? 200), kg:Number(trip.tonnes ?? 15)*1000,
      tonnes:Number(trip.tonnes ?? 15), stops:Number(trip.stops ?? 1), legs:Number(trip.legs ?? 1), value:Number(trip.value ?? 0)});
    const visiting = new Set(), values = {};
    const calc = key => {
      if (Object.hasOwn(values,key)) return values[key];
      if (visiting.has(key)) throw Error('Công thức tham chiếu vòng tròn');
      visiting.add(key);
      const source = String(formulas[key] || '').trim();
      if (!source || source.length > 2000) throw Error('Công thức trống hoặc quá dài');
      let count = 0;
      const visit = node => {
        if (++count > 256) throw Error('Công thức quá phức tạp');
        let value;
        if (node.type === 'Literal' && typeof node.value === 'number') value = node.value;
        else if (node.type === 'Identifier') {
          if (names.includes(node.name)) value = calc(node.name);
          else if (Object.hasOwn(scope,node.name)) value = scope[node.name];
          else throw Error('Không nhận ra biến: ' + node.name);
        } else if (node.type === 'UnaryExpression' && ['+','-'].includes(node.operator)) {
          value = visit(node.argument) * (node.operator === '-' ? -1 : 1);
        } else if (node.type === 'BinaryExpression' && ['+','-','*','/'].includes(node.operator)) {
          const a = visit(node.left), b = visit(node.right);
          if (node.operator === '/' && b === 0) throw Error('Không thể chia cho 0');
          value = node.operator === '+' ? a+b : node.operator === '-' ? a-b : node.operator === '*' ? a*b : a/b;
        } else if (node.type === 'CallExpression' && node.callee.type === 'Identifier'
          && ['min','max','abs'].includes(node.callee.name) && node.arguments.length > 0 && node.arguments.length <= 20) {
          if (node.callee.name === 'abs' && node.arguments.length !== 1) throw Error('abs cần một tham số');
          value = Math[node.callee.name](...node.arguments.map(visit));
        } else throw Error('Chỉ hỗ trợ số, biến, + − × ÷, ngoặc, min/max/abs');
        if (!Number.isFinite(value) || Math.abs(value) > 1e18) throw Error('Kết quả vượt giới hạn');
        return value;
      };
      values[key] = visit(parse(source));
      visiting.delete(key);
      return values[key];
    };
    const cost=calc('COST'), revenue=calc('REV'), profit=calc('PROFIT');
    return {cost,revenue,profit,total:profit,perKm:scope.km > 0 ? cost/scope.km : 0,marginPct:revenue ? profit/revenue*100 : null};
  }
  return {defaults,evaluate};
});
