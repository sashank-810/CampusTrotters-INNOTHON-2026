/* Regression checks against independently produced v1.2 Python output. */
const assert=require('node:assert/strict');
const m=require('./dist/model_inputs.json'),live=require('./dist/live_model.js');
const expected={
  conservative:{national:4434.574830685146,regional:{NR:1235.73197,WR:1453.90274,SR:1153.61391,ER:528.43111,NER:62.89510}},
  central:{national:5312.183196449455,regional:{NR:1535.18269,WR:1686.47860,SR:1496.99698,ER:484.16948,NER:109.35545}},
  accelerated:{national:5574.683196449455,regional:{NR:1660.74354,WR:1720.02801,SR:1685.10507,ER:340.13425,NER:168.67232}}
};
for(const [key,ref] of Object.entries(expected)){
  const p=live.paramsFromScenario(m,key),nat=live.nationalPath(m,p).find(x=>x.fy_end_year===2047),res=live.allocate(m,p,nat);
  assert.ok(Math.abs(nat.domestic_generation_twh-ref.national)<1e-5,key+' national');
  assert.equal(res.status,'solved');
  for(const row of res.rows)assert.ok(Math.abs(row.generation_twh-ref.regional[row.region])<.002,key+' '+row.region);
  assert.ok(res.sourceResidual<1e-6,key+' conservation');
}
let p=live.paramsFromScenario(m,'central');
const base=live.nationalPath(m,p).find(x=>x.fy_end_year===2047);
p={...p,g0:.08};
assert.ok(live.nationalPath(m,p).find(x=>x.fy_end_year===2047).domestic_generation_twh>base.domestic_generation_twh);
p={...live.paramsFromScenario(m,'central'),mix:{...live.paramsFromScenario(m,'central').mix,hydro:.2,coal:.22}};
const hydro=live.nationalPath(m,p).find(x=>x.fy_end_year===2047),constraint=live.allocate(m,p,hydro);
assert.equal(constraint.status,'infeasible_under_indicative_hydro_ceiling');
assert.ok(Math.abs(constraint.required-1062.43663929)<.003);
assert.ok(Math.abs(constraint.ceiling-480.363)<.01);
assert.equal(live.allocate(m,p,hydro,true).status,'unconstrained_fallback');
p={...live.paramsFromScenario(m,'central'),variant:'high_pop'};
assert.ok(live.nationalPath(m,p).find(x=>x.fy_end_year===2047).domestic_generation_twh>base.domestic_generation_twh+200);
console.log('Live browser model: three reference scenarios, 15 regional totals, source conservation, GDP, demography and hydro stress verified.');
