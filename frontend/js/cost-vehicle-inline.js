(function () {
  let data = null, baseline = '', loading = 0, saving = false;
  const esc = value => escapeHtml(String(value ?? ''));
  const copy = value => JSON.parse(JSON.stringify(value));
  const overrides = () => data.components.filter(r => r.is_overridden).map(r => ({component:r.component,value:r.value,note:r.note || ''}));
  const dirty = () => !!data && JSON.stringify(overrides()) !== baseline;
  const money = value => formatWorkflowCurrencyAmount(value, data.currency);
  function syncSelection() {
    document.querySelectorAll('[data-vehicle-cost-id]').forEach(button => {
      const selected = button.dataset.vehicleCostId === data?.vehicle_id;
      button.classList.toggle('is-selected', selected);
      if (selected) button.setAttribute('aria-current', 'true');
      else button.removeAttribute('aria-current');
    });
  }
  function host() {
    let el = document.getElementById('cfvi');
    if (!el) {
      el = document.createElement('section'); el.id = 'cfvi';
      document.querySelector('#md-tab-formulas .cfv2-workbench').append(el);
    }
    return el;
  }
  function discard() {
    loading++; data = null; baseline = '';
    syncSelection();
    document.getElementById('cfvi')?.remove();
    document.querySelector('.cfv2-workbench')?.classList.remove('vehicle-mode');
    document.querySelector('.cfv2-workbench')?.removeAttribute('aria-busy');
  }
  function close() {
    if (saving) return false;
    if (dirty() && !window.confirm('Bỏ các thay đổi giá riêng chưa lưu?')) return false;
    discard(); return true;
  }
  async function open(id) {
    if (saving || (dirty() && !window.confirm('Bỏ các thay đổi giá riêng chưa lưu?'))) return;
    const generation = ++loading;
    const el = host();
    const workbench = document.querySelector('.cfv2-workbench');
    workbench.setAttribute('aria-busy', 'true');
    el.inert = true;
    try {
      const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(id)}/cost`);
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail?.message || body.detail || `HTTP ${res.status}`);
      if (generation !== loading) return;
      if (!body.data?.vehicle_id || !Array.isArray(body.data.components)) throw new Error('Dữ liệu giá xe không hợp lệ');
      data = copy(body.data); baseline = JSON.stringify(overrides());
      syncSelection();
      workbench.classList.add('vehicle-mode'); render();
    } catch (error) {
      if (generation !== loading) return;
      showToast(`Chưa chuyển được sang xe ${id}: ${error.message}`, 'error');
    } finally {if(generation===loading){workbench.removeAttribute('aria-busy');el.inert=false;}}
  }
  function terms() {
    const source = data.terms?.length ? data.terms : FormulaModel.defaultTerms();
    return source.map(t => ({...t,rate:data.components.find(r => r.component === t.key)?.value ?? t.rate}));
  }
  function preview() {
    const target = document.getElementById('cfvi-results');
    let valid = true;
    try {
      if (data.components.some(row=>!Number.isFinite(row.value) || row.value < 0)) {
        throw new Error('Đơn giá phải là số không âm.');
      }
      const result = FormulaModel.evaluate(terms(), costSampleTrip, data.expressions);
      host().querySelectorAll('[data-amount]').forEach(e=>{
        const row=result.rows.find(r=>r.key===e.dataset.amount);
        e.textContent=row?money(row.amount):'—';
      });
      host().querySelectorAll('[data-multiplier]').forEach(e=>{
        const row=result.rows.find(r=>r.key===e.dataset.multiplier);
        e.textContent=row?`× ${row.multiplier.toLocaleString('vi-VN')}`:'—';
      });
      target.innerHTML = [['cost','Giá thành'],['revenue','Cước thu khách'],['profit','Lợi nhuận'],['perKm','Giá thành mỗi km']]
        .map(([key,label]) => `<div class="cfvi-result ${key}"><span>${label}</span><b>${esc(money(result[key]))}</b></div>`).join('');
    } catch (error) { valid = false; target.textContent = error.message; }
    const count = data.components.filter((row,i) => JSON.stringify(row) !== JSON.stringify(data._original[i])).length;
    document.getElementById('cfvi-change-count').textContent = count ? `${count} khoản mục đã thay đổi` : 'Chưa có thay đổi';
    document.getElementById('cfvi-save').disabled = !valid || !dirty() || saving || !data.has_type_formula;
    window.CostComparison?.render(document.getElementById('cfvi-comparison'), {
      vehicleId:data.vehicle_id, formulaId:data.type_formula_id, currency:data.currency,
      terms:terms(), expressions:data.expressions, trip:costSampleTrip
    });
  }
  function render() {
    if (!data._original) data._original = copy(data.components);
    const unit = key => FormulaModel.FACTORS?.[terms().find(t=>t.key===key)?.factor]?.unit || '';
    host().innerHTML = `<header class="cfvi-header"><button type="button" id="cfvi-back" title="Về công thức chuẩn"><i class="fa-solid fa-arrow-left"></i></button><span>${esc(data.vehicle_type)} <b> / ${esc(data.vehicle_id)}</b></span><span class="cfvi-currency">${esc(data.currency)}</span></header>
      <div class="cfvi-main"><div class="cfvi-inheritance">${data.has_type_formula?'Công thức kế thừa từ loại xe':'Loại xe chưa có công thức chuẩn'}</div>
      <div class="cf-scroll"><table id="cfvi-table" class="cf-table"><colgroup><col style="width:24%"><col style="width:11%"><col style="width:20%"><col style="width:17%"><col style="width:12%"><col style="width:16%"></colgroup><thead><tr><th>Khoản mục</th><th title="Mã phân loại chi phí của EPL — kế thừa từ công thức loại xe, hệ công nợ đọc để lập phiếu">Mã costindex</th><th>Đơn giá</th><th>Chuẩn của loại</th><th>Nhân với</th><th>Thành tiền</th></tr></thead><tbody>${['cost','revenue'].map(kind=>`<tr class="cfv2-group"><td colspan="6">${kind==='cost'?'CHI RA — GIÁ THÀNH':'THU VỀ — CƯỚC KHÁCH'}</td></tr>${data.components.filter(r=>(terms().find(t=>t.key===r.component)?.kind || (r.component==='rate'?'revenue':'cost'))===kind).map(r=>`<tr class="${r.is_overridden?'is-overridden':''}" data-component="${esc(r.component)}"><td><b>${esc(r.label)}</b><input type="text" maxlength="500" data-note="${esc(r.component)}" aria-label="Lý do ${esc(r.label)}" placeholder="Lý do ghi đè" value="${esc(r.note)}"></td><td><code class="cl-ma ${(terms().find(t=>t.key===r.component)?.cost_index)?'':'is-thieu'}" title="Mã costindex kế thừa từ công thức loại xe">${esc(terms().find(t=>t.key===r.component)?.cost_index || 'chưa gán')}</code></td>
        <td><div class="cfvi-price"><input type="number" min="0" step="any" data-rate="${esc(r.component)}" aria-label="Đơn giá ${esc(r.label)}" value="${r.value}" ${data.has_type_formula?'':'disabled'}><small>${esc(data.currency)} ${esc(unit(r.component))}</small></div></td>
        <td><span class="cfvi-standard">${esc(money(r.inherited))}</span><div><span data-source="${esc(r.component)}" class="cfb-source">${r.is_overridden?'Ghi đè':'Kế thừa'}</span><button type="button" data-reset="${esc(r.component)}" title="Trả về giá chuẩn" aria-label="Trả ${esc(r.label)} về giá chuẩn">đặt lại</button></div></td>
        <td data-multiplier="${esc(r.component)}"></td><td><b data-amount="${esc(r.component)}"></b></td></tr>`).join('')}`).join('')}</tbody></table></div>
      <button type="button" id="cfvi-add-type" class="cfb-add">+ Thêm khoản mục vào loại xe</button>
      <section class="cfvi-expressions"><b>Công thức chuẩn của loại</b>${Object.entries(data.expressions || window.CostExpression?.defaults(terms()) || {}).map(([key,expression])=>`<p><b>${esc(key)}</b> = <code>${esc(expression)}</code></p>`).join('')}</section>
      <footer class="cfvi-savebar"><span id="cfvi-change-count" role="status"></span><button type="button" id="cfvi-reset-all">Bỏ toàn bộ ghi đè</button><button type="button" id="cfvi-cancel">Hủy</button><button type="button" id="cfvi-save"><i class="fa-solid fa-floppy-disk"></i> Lưu thay đổi</button></footer></div>
      <aside class="cfvi-side"><h4>Chuyến mẫu</h4><div class="cfvi-sample">${[['km','Quãng đường'],['tonnes','Hàng (tấn)'],['stops','Điểm giao'],['legs','Số chặng']].map(([key,label])=>`<label>${label}<input type="number" min="0" step="any" data-sample="${key}" value="${costSampleTrip[key] ?? 1}"></label>`).join('')}</div><div id="cfvi-results"></div><div id="cfvi-comparison"></div></aside>`;
    const el = host();
    el.querySelector('#cfvi-back').onclick = close;
    el.querySelector('#cfvi-cancel').onclick = () => {data.components=copy(data._original);render();};
    el.querySelector('#cfvi-save').onclick = save;
    el.querySelector('#cfvi-add-type').onclick = async () => {
      const formula=typeof masterFormulaStore==='undefined'?null:masterFormulaStore[data.type_formula_id];
      if(!formula?.vehicleTypeId){showToast('Chưa xác định được công thức chuẩn của loại xe.', 'error');return;}
      const typeId=formula.vehicleTypeId,currency=data.currency;
      if(!close())return;
      await window.requestCostFormulaContextChange(typeId,currency);
      if(masterFormulaStore[activeCostFormulaKey]?.vehicleTypeId===typeId)window.CostFormulaBuilder?.add();
    };
    el.querySelector('#cfvi-reset-all').onclick = () => {data.components.forEach(reset);render();};
    el.querySelectorAll('[data-rate]').forEach(input => input.oninput = () => {
      const row = data.components.find(r=>r.component===input.dataset.rate);
      row.value = input.value === '' ? NaN : Number(input.value);
      row.is_overridden = row.value !== row.inherited;
      input.closest('tr').classList.toggle('is-overridden',row.is_overridden);
      Array.from(el.querySelectorAll('[data-source]')).find(e=>e.dataset.source===row.component).textContent = row.is_overridden?'Ghi đè':'Kế thừa'; preview();
    });
    el.querySelectorAll('[data-note]').forEach(input => input.oninput = () => {data.components.find(r=>r.component===input.dataset.note).note=input.value;preview();});
    el.querySelectorAll('[data-reset]').forEach(button => button.onclick = () => {reset(data.components.find(r=>r.component===button.dataset.reset));render();});
    el.querySelectorAll('[data-sample]').forEach(input => input.oninput = () => {costSampleTrip={...costSampleTrip,[input.dataset.sample]:Number(input.value)};preview();});
    preview();
  }
  function reset(row) {row.value=row.inherited;row.is_overridden=false;row.note='';}
  async function save() {
    if (!data || saving) return false;
    const rows = overrides();
    if (rows.some(r=>!Number.isFinite(r.value) || r.value < 0 || !r.note.trim())) {
      showToast('Đơn giá phải không âm và mỗi ghi đè cần có lý do.', 'error'); return false;
    }
    saving = true; preview();
    try {
      const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(data.vehicle_id)}/cost-overrides`, {
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({overrides:rows})
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail?.message || body.detail || `HTTP ${res.status}`);
      if (!Array.isArray(body.data)) throw new Error('Máy chủ chưa xác nhận danh sách đã lưu');
      baseline=JSON.stringify(overrides());data._original=copy(data.components);
      if (typeof vehicleOverrideCounts !== 'undefined') vehicleOverrideCounts[data.vehicle_id]=rows.length;
      window.renderVehicleTypeFleetCounts?.();
      window.CostComparison?.invalidate();
      showToast('Đã lưu giá riêng của xe.', 'success'); return true;
    } catch(error) {showToast(`Chưa lưu được: ${error.message}`, 'error');return false;}
    finally {saving=false;preview();}
  }
  window.addEventListener('beforeunload', e=>{if(dirty()){e.preventDefault();e.returnValue='';}});
  window.CostVehicleInline={open,close,discard,save,dirty,syncSelection};
})();
