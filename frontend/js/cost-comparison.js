(function () {
  let overview = null, pending = null, failure = '', generation = 0;
  const contexts = new WeakMap(), expanded = new WeakSet();
  const esc = value => escapeHtml(String(value ?? ''));
  const termsFor = item => {
    if(item.terms?.length)return item.terms;
    return FormulaModel.defaultTerms().map(t=>({...t,rate:item.components?.find?.(r=>r.component===t.key)?.value ?? FormulaModel.toNumber(item[t.key])}));
  };
  function load() {
    if(!pending) {
      const requestGeneration=generation;
      pending=fetch(`${API_BASE}/api/cost-formulas/fleet-overview`).then(async r=>{
        if(!r.ok)throw new Error(`HTTP ${r.status}`);
        const body=await r.json();
        if(!Array.isArray(body.data?.vehicles))throw new Error('Dữ liệu so sánh chưa hợp lệ');
        if(requestGeneration===generation){overview=body.data;failure='';}
      }).catch(e=>{if(requestGeneration===generation)failure=e.message;}).finally(()=>{if(requestGeneration===generation)pending=null;});
    }
    return pending;
  }
  function render(host, context) {
    if(!host)return;
    contexts.set(host,context);
    if(!overview && !failure) {
      host.innerHTML='<p class="cfb-muted" role="status">Đang tải so sánh và lịch sử...</p>';
      load().then(()=>{if(host.isConnected)paint(host,contexts.get(host));});return;
    }
    paint(host,context);
  }
  function paint(host,c) {
    if(!c)return;
    const money=n=>formatWorkflowCurrencyAmount(n,c.currency);
    let current;
    try {current=FormulaModel.evaluate(c.terms,c.trip,c.expressions);}catch{host.textContent='Chưa thể so sánh khi công thức đang lỗi.';return;}
    const formulas=typeof masterFormulaStore==='undefined'?[]:Object.entries(masterFormulaStore)
      .filter(([,f])=>f.configured && f.currency===c.currency && f.vehicleTypeId);
    const rows=[];
    for(const [id,f] of formulas)rows.push({id,label:`${f.vehicleTypeName || f.name} · chuẩn`,type:true,
      current:!c.vehicleId && id===c.formulaId,related:id===c.formulaId,
      terms:termsFor(f),expressions:f.expressions,vehicleTypeId:f.vehicleTypeId});
    for(const v of overview?.vehicles || []) {
      if(v.currency!==c.currency || !v.has_type_formula)continue;
      rows.push({id:v.vehicle_id,label:v.vehicle_id,current:v.vehicle_id===c.vehicleId,
        related:v.type_formula_id===c.formulaId,terms:termsFor(v),expressions:v.expressions});
    }
    rows.sort((a,b)=>Number(b.related)-Number(a.related) || Number(b.type || false)-Number(a.type || false) || a.label.localeCompare(b.label));
    const visible=expanded.has(host)?rows:rows.slice(0,8);
    const body=visible.map(row=>{
      let result;
      try {result=row.current?current:FormulaModel.evaluate(row.terms,c.trip,row.expressions);}catch{return '';}
      const difference=current.perKm ? (result.perKm/current.perKm-1)*100 : null;
      return `<tr class="${row.current?'is-current':''}"><td>${esc(row.label)}</td><td>${esc(money(result.perKm))}</td><td>${row.current?'đang xem':difference===null?'—':`${difference>0?'+':''}${difference.toFixed(0)}%`}</td></tr>`;
    }).join('');
    const formulaHistory=formulas.flatMap(([id,f])=>(f.history || []).map((h,index,all)=>{
      const before=all[index+1]?.terms || [];
      const changes=(h.terms || []).filter(t=>!before.some(p=>p.key===t.key && p.rate===t.rate)).map(t=>{
        const old=before.find(p=>p.key===t.key);
        return `${t.label || t.key}: ${old?`${old.rate} → `:''}${t.rate}`;
      });
      return {at:h.at,actor:h.actor,message:`${f.vehicleTypeName || f.name} · ${changes.join('; ') || 'Lưu công thức'}`};
    }));
    const history=[...formulaHistory,...(overview?.history || []).map(h=>({...h,message:`${h.vehicle_id} · ${h.message}`}))]
      .sort((a,b)=>String(b.at).localeCompare(String(a.at))).slice(0,8);
    host.innerHTML=`<div class="cfcompare-heading"><h5>So với các loại / xe khác</h5><button type="button" class="cfcompare-expand">${expanded.has(host)?'Thu gọn':'Bảng đầy đủ'}</button></div>
      ${failure?`<p role="alert">Chưa tải được giá xe: ${esc(failure)} <button type="button" class="cfcompare-retry">Thử lại</button></p>`:''}
      <div class="cfcompare-scroll"><table class="cfb-compare"><thead><tr><th>Loại / xe</th><th>${esc(c.currency)}/km</th><th>so với</th></tr></thead><tbody>${body || '<tr><td colspan="3">Chưa có dữ liệu giá để so sánh.</td></tr>'}</tbody></table></div>
      <h5>Thay đổi gần đây</h5>${history.length?history.map(h=>`<div class="cfb-history"><time>${esc(h.at?new Date(h.at).toLocaleString('vi-VN'):'')}</time><span>${esc(h.message)}${h.actor?` · ${esc(h.actor)}`:''}</span></div>`).join(''):'<p class="cfb-muted">Chưa có lịch sử được ghi nhận.</p>'}`;
    host.querySelector('.cfcompare-expand').onclick=()=>{if(expanded.has(host))expanded.delete(host);else expanded.add(host);paint(host,contexts.get(host));};
    host.querySelector('.cfcompare-retry')?.addEventListener('click',()=>{invalidate();render(host,contexts.get(host));});
  }
  function invalidate(){generation++;overview=null;pending=null;failure='';}
  window.CostComparison={render,invalidate};
})();
