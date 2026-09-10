const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const d=new JSDOM('<section id="comparison"></section>',{runScripts:'outside-only'}), w=d.window;
const terms=[{key:'fuel',label:'Fuel',rate:4800,kind:'cost',factor:'per_km',operator:'add'}];
w.API_BASE='';w.escapeHtml=s=>String(s).replaceAll('<','&lt;');w.formatWorkflowCurrencyAmount=String;
w.FormulaModel=require('../js/formula-model');
w.masterFormulaStore={T:{name:'Type',currency:'VND',vehicleTypeId:'T',configured:true,terms,history:[]}};
w.fetch=async()=>({ok:true,json:async()=>({data:{vehicles:[
  {vehicle_id:'V1',has_type_formula:true,type_formula_id:'T',currency:'VND',terms},
  {vehicle_id:'V2',has_type_formula:true,type_formula_id:'T',currency:'VND',terms:[{...terms[0],rate:5200}]}
],history:[{at:'2026-09-08T00:00:00Z',vehicle_id:'V2',actor:'Planner',message:'4800 → 5200'}]}})});
w.eval(fs.readFileSync(require('node:path').join(__dirname,'../js/cost-comparison.js'),'utf8'));
w.CostComparison.render(w.document.querySelector('#comparison'),{vehicleId:'V1',formulaId:'T',currency:'VND',terms,trip:{km:200,tonnes:15}});
setTimeout(()=>{
 try {
  const content=w.document.body.textContent;
  assert.match(content,/V1/);assert.match(content,/V2/);assert.match(content,/5200/);
  assert.match(content,/\+8%/);assert.match(content,/Planner/);
  w.document.querySelector('.cfcompare-expand').click();
  assert.match(w.document.body.textContent,/Thu gọn/);
  console.log('PASS real comparison math, current vehicle and persisted history');
 }catch(e){console.error(e);process.exitCode=1;}finally{d.window.close();}
},30);
