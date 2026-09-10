(function() {
  let open = false, mode = 'COST', draft = '', context = '';
  const labels = {COST:'Giá thành',REV:'Cước',PROFIT:'Lợi nhuận'};
  const contextLabels = {km:'Tổng km tuyến',kg:'Khối lượng (kg)',tonnes:'Khối lượng (tấn)',legs:'Số chặng',stops:'Điểm dừng',value:'Giá trị hàng',COST:'Giá thành',REV:'Cước thu khách'};
  const expressions = () => costFormulaExpressions || CostExpression.defaults(costFormulaTerms);
  const tokens = text => String(text).match(/[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?|[^\s]/g) || [];
  function meta(key) {
    const term = costFormulaTerms.find(t=>t.key===key);
    return {label:term?.label || contextLabels[key] || key, tone:term ? term.kind === 'revenue' ? 'rev' : 'cost' : ['COST','REV'].includes(key) ? 'calc' : 'ctx'};
  }
  const pretty = text => tokens(text).map(t=>meta(t).label).join(' ');
  function insert(text) {
    const input = document.getElementById('cfb-raw');
    const start = input?.selectionStart ?? draft.length, end = input?.selectionEnd ?? start;
    draft = draft.slice(0,start) + text + draft.slice(end);
    if (input) {input.value=draft; input.focus(); input.setSelectionRange(start+text.length,start+text.length);}
    paint();
  }
  function paint() {
    const drop = document.getElementById('cfb-drop');
    if (!drop) return;
    drop.innerHTML = tokens(draft).map((token,i)=> {
      const m=meta(token), variable=/^[A-Za-z_]/.test(token) && !['max','min','abs'].includes(token);
      return variable ? `<span class="tk ${m.tone}">${escapeHtml(m.label)}<button type="button" data-remove="${i}" title="Bỏ biến">×</button></span>` : `<span class="op">${escapeHtml(token)}</span>`;
    }).join(' ');
    drop.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const ts=tokens(draft);ts.splice(Number(b.dataset.remove),1);draft=ts.join(' ');document.getElementById('cfb-raw').value=draft;paint();});
    const message = document.getElementById('cfb-message'), apply = document.getElementById('cfb-apply');
    try {
      const result=CostExpression.evaluate({...expressions(),[mode]:draft},costFormulaTerms,costSampleTrip);
      const value=result[({COST:'cost',REV:'revenue',PROFIT:'profit'})[mode]];
      message.className='fmsg ok';message.textContent='Hợp lệ · Kết quả chuyến mẫu: '+formatWorkflowCurrencyAmount(value,masterCostCurrencyCode());
      apply.disabled=false;
      document.getElementById('cfb-steps').textContent=pretty(draft)+' = '+formatWorkflowCurrencyAmount(value,masterCostCurrencyCode());
    } catch(error) {
      message.className='fmsg bad';message.textContent=error.message;apply.disabled=true;
      document.getElementById('cfb-steps').textContent='';
    }
  }
  function refresh() {
    const lines=document.getElementById('cfb-lines');
    if(!lines)return;
    let result;
    try {result=CostExpression.evaluate(expressions(),costFormulaTerms,costSampleTrip);}catch(error){lines.textContent=error.message;return;}
    lines.innerHTML=Object.keys(labels).map(k=>`<div><b>${labels[k]}</b> = ${escapeHtml(pretty(expressions()[k]))} <strong>= ${escapeHtml(formatWorkflowCurrencyAmount(result[({COST:'cost',REV:'revenue',PROFIT:'profit'})[k]],masterCostCurrencyCode()))}</strong></div>`).join('');
    if(open)paint();
    renderSide();
  }
  function renderSide() {
    const side=document.querySelector('#cost-formula-view .cf-side');
    if(!side)return;
    let extra=document.getElementById('cfb-side-extra');
    if(!extra){extra=document.createElement('div');extra.id='cfb-side-extra';side.append(extra);}
    if(window.CostComparison) {
      extra.innerHTML=`<label class="cfb-route-label">Dùng tuyến thật<select id="cfb-route"><option value="">Chuyến mẫu</option>${(eplRoutes || []).map(r=>`<option value="${escapeHtml(r.id)}" ${costSampleTrip.routeId===r.id?'selected':''}>${escapeHtml(r.name || r.id)}</option>`).join('')}</select></label><div id="cfb-comparison"></div>`;
      extra.querySelector('#cfb-route').onchange=e=>{
        const route=(eplRoutes || []).find(r=>r.id===e.target.value);
        if(!route)return;
        costSampleTrip={...costSampleTrip,routeId:route.id,km:Number(route.distance_km || 0)};
        window.renderCostFormulaEditor();
      };
      window.CostComparison.render(extra.querySelector('#cfb-comparison'),{formulaId:activeCostFormulaKey,currency:masterCostCurrencyCode(),
        terms:costFormulaTerms,expressions:costFormulaExpressions,trip:costSampleTrip});
      return;
    }
    const currency=masterCostCurrencyCode(), money=v=>formatWorkflowCurrencyAmount(v,currency);
    const current=CostExpression.evaluate(expressions(),costFormulaTerms,costSampleTrip);
    const compared=(vehTypes || []).map(type=>{
      const f=masterFormulaStore[costFormulaKeyForVehicleType(type,currency)];
      if(!f?.configured)return '';
      const terms=f.terms?.length?f.terms:FormulaModel.defaultTerms().map(t=>({...t,rate:FormulaModel.toNumber(f[t.key])}));
      try {
        const r=FormulaModel.evaluate(terms,costSampleTrip,f.expressions);
        const difference=current.perKm ? (r.perKm/current.perKm-1)*100 : null;
        return `<tr><td>${escapeHtml(type.name)}</td><td>${money(r.perKm)}</td><td>${difference===null?'—':difference.toFixed(0)+'%'}</td></tr>`;
      }catch{return '';}
    }).join('');
    const history=masterFormulaStore[activeCostFormulaKey]?.history || [];
    extra.innerHTML=`<label class="cfb-route-label">Dùng tuyến thật<select id="cfb-route"><option value="">Chuyến mẫu</option>${(eplRoutes || []).map(r=>`<option value="${escapeHtml(r.id)}">${escapeHtml(r.name || r.id)}</option>`).join('')}</select></label>
      <h5>So với các loại / xe khác</h5><table class="cfb-compare"><thead><tr><th>Loại / xe</th><th>/km</th><th>So với</th></tr></thead><tbody>${compared}</tbody></table>
      <h5>Thay đổi gần đây</h5>${history.length?history.slice(0,5).map(h=>`<div class="cfb-history"><time>${escapeHtml(new Date(h.at).toLocaleString('vi-VN'))}</time><span>Đã lưu ${h.terms.length} khoản mục${h.expressions?' và biểu thức':''} · ${escapeHtml(h.currency)}</span></div>`).join(''):'<p class="cfb-muted">Chưa có lịch sử được ghi nhận.</p>'}`;
    document.getElementById('cfb-route').onchange=e=>{
      const route=(eplRoutes || []).find(r=>r.id===e.target.value);
      if(!route)return;
      costSampleTrip={...costSampleTrip,km:Number(route.distance_km || 0)};
      window.renderCostFormulaEditor();
    };
  }
  function mount() {
    const host=document.querySelector('#cost-formula-view .cf-head');
    if(!host)return;
    if(context!==activeCostFormulaKey){context=activeCostFormulaKey;open=false;}
    host.innerHTML=`<div class="cfb fbox">
      <div class="fhead"><b>Công thức</b><span class="cfb-scope">${escapeHtml(document.getElementById('selected-veh-type-badge')?.textContent || '')}</span>
        <div class="sw">${Object.keys(labels).map(k=>`<button type="button" data-mode="${k}" class="${mode===k?'on':''}">${labels[k]}</button>`).join('')}</div>
        <button type="button" id="cf-trigger" class="edit" aria-expanded="${open}" onclick="toggleCostFormulaPopover()"><i class="fa-solid fa-pen"></i> Sửa công thức</button></div>
      <div class="flines" id="cfb-lines"></div>
      ${open ? `<div class="fbuild">
        <div class="pal">${[...costFormulaTerms.map(t=>t.key),...Object.keys(contextLabels)].filter(k=>k!==mode).map(key=>`<button type="button" draggable="true" class="vchip ${meta(key).tone}" data-var="${escapeHtml(key)}">${escapeHtml(meta(key).label)} <code>${escapeHtml(key)}</code></button>`).join('')}</div>
        <div class="ops">${['+','-','*','/','(',')','max(','min(','abs(',','].map(op=>`<button type="button" data-op="${escapeHtml(op)}">${escapeHtml(op)}</button>`).join('')}</div>
        <div id="cfb-drop" class="drop" tabindex="0" aria-label="Biểu thức kéo thả"></div>
        <textarea class="raw" id="cfb-raw" rows="2" spellcheck="false" aria-label="Nhập biểu thức">${escapeHtml(draft)}</textarea>
        <div id="cfb-message" class="fmsg" role="status"></div>
        <div class="presets"><button type="button" id="cfb-default">Công thức từ các khoản mục</button>${mode==='REV'?'<button type="button" id="cfb-minimum">Cước tối thiểu</button>':''}</div>
        <div class="steps" id="cfb-steps"></div>
        <div class="fsave"><button type="button" class="c" id="cfb-cancel">Hủy</button><button type="button" class="a" id="cfb-apply">Áp dụng công thức</button></div>
      </div>`:''}</div>`;
    host.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;draft=expressions()[mode];mount();});
    if(open) {
      host.querySelectorAll('[data-var]').forEach(b=>{b.onclick=()=>insert(b.dataset.var);b.ondragstart=e=>e.dataTransfer.setData('text/plain',b.dataset.var);});
      host.querySelectorAll('[data-op]').forEach(b=>b.onclick=()=>insert(' '+b.dataset.op+' '));
      const drop=document.getElementById('cfb-drop');
      drop.ondragover=e=>{e.preventDefault();drop.classList.add('over');};drop.ondragleave=()=>drop.classList.remove('over');
      drop.ondrop=e=>{e.preventDefault();drop.classList.remove('over');insert(e.dataTransfer.getData('text/plain'));};
      document.getElementById('cfb-raw').oninput=e=>{draft=e.target.value;paint();};
      document.getElementById('cfb-cancel').onclick=()=>{open=false;mount();};
      document.getElementById('cfb-default').onclick=()=>{draft=CostExpression.defaults(costFormulaTerms)[mode];mount();};
      const minimum=document.getElementById('cfb-minimum');
      if(minimum)minimum.onclick=()=>{draft=`max(${CostExpression.defaults(costFormulaTerms).REV}, 2500000)`;mount();};
      document.getElementById('cfb-apply').onclick=()=>{
        try {CostExpression.evaluate({...expressions(),[mode]:draft},costFormulaTerms,costSampleTrip);}catch(error){paint();return;}
        costFormulaExpressions={...expressions(),[mode]:draft};
        masterFormulaStore[activeCostFormulaKey].expressions={...costFormulaExpressions};
        open=false;window.renderCostFormulaEditor();window.autoCalculateMasterDataCost();
      };
    }
    refresh();
  }
  function add() {
    const host=document.querySelector('#cost-formula-view .cf-main');
    if(document.getElementById('cfb-add-form'))return;
    const form=document.createElement('form');form.id='cfb-add-form';
    form.innerHTML='<input name="label" required placeholder="Tên khoản mục" aria-label="Tên khoản mục"><select name="kind" aria-label="Loại khoản mục"><option value="cost">Chi phí</option><option value="revenue">Cước thu khách</option></select><select name="factor" aria-label="Đơn vị"><option value="per_trip">Mỗi chuyến</option><option value="per_km">Mỗi km</option><option value="per_kg">Mỗi kg</option><option value="per_stop">Mỗi điểm giao</option></select><button type="submit">Thêm</button><button type="button" id="cfb-add-cancel">Hủy</button>';
    host.append(form);form.elements.label.focus();
    form.querySelector('#cfb-add-cancel').onclick=()=>form.remove();
    form.onsubmit=e=>{e.preventDefault();const values=new FormData(form);
      const term={key:'custom_'+Date.now().toString(36),label:String(values.get('label')).trim(),kind:values.get('kind'),factor:values.get('factor'),rate:0,operator:'add'};
      costFormulaTerms.push(term);
      if(costFormulaExpressions){const k=term.kind==='cost'?'COST':'REV';costFormulaExpressions={...costFormulaExpressions,[k]:costFormulaExpressions[k]+' + '+CostExpression.defaults([term])[k]};}
      persistCostFormulaTerms();window.renderCostFormulaEditor();
    };
  }
  function remove(index) {
    const term=costFormulaTerms[index];if(!term)return;
    if(costFormulaExpressions && Object.values(costFormulaExpressions).some(e=>tokens(e).includes(term.key))){showToast('Khoản mục đang có trong biểu thức. Hãy bỏ biến khỏi công thức trước.', 'error');return;}
    costFormulaTerms.splice(index,1);persistCostFormulaTerms();window.renderCostFormulaEditor();
  }
  window.CostFormulaBuilder={mount,refresh,add,remove,toggle(force){open=typeof force==='boolean'?force:!open;draft=expressions()[mode];mount();}};
})();
