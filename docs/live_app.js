/* Live browser UI. Equations and data are in live_model.js / model_inputs.json. */
const $=s=>document.querySelector(s);
const fmt=(n,d=0)=>Number(n).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const fy=y=>`FY${y-1}–${String(y).slice(-2)}`;
const names={NR:'Northern',WR:'Western',SR:'Southern',ER:'Eastern',NER:'North-Eastern'};
const keys=['coal','gas','nuclear','hydro','solar','wind','other_re'];
const labels={coal:'Coal',gas:'Gas + diesel',nuclear:'Nuclear',hydro:'Hydro',solar:'Solar',wind:'Wind',other_re:'Other RE'};
const colors={coal:'#243c52',gas:'#81909c',nuclear:'#a08dc0',hydro:'#2288b4',solar:'#f5ae50',wind:'#19a89b',other_re:'#80bd79'};
const model=window.CampusTrottersModel;
let M,P,scenario='central',year=2047,region='ALL',national=[];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=(id,label,min,max,step,val,help='')=>`<div class="field"><label for="${id}">${label}</label><input id="${id}" type="number" min="${min}" max="${max}" step="${step}" value="${val}"><small>${help}</small></div>`;
const select=(id,label,values)=>`<div class="field"><label for="${id}">${label}</label><select id="${id}">${values.map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></div>`;
const check=(id,label,checked)=>`<div class="field choice"><input id="${id}" type="checkbox" ${checked?'checked':''}><label for="${id}">${label}</label></div>`;
function buildControls(){
 $('#nationalControls').innerHTML=`<div class="two">${number('g0','Initial GDP growth (%)',0,15,.1,100*P.g0)}${number('g1','Final GDP growth (%)',0,15,.1,100*P.g1)}${number('e0','Initial elasticity',0,2,.01,P.e0)}${number('e1','Final elasticity',0,2,.01,P.e1)}</div>${number('addon','Extra electrification by 2047 (TWh)',0,3000,1,P.addon)}${select('variant','Population and urbanization variant',[['central','Central'],['low_pop','Lower population growth'],['high_pop','Higher population growth'],['slow_urban','Slower urbanization'],['fast_urban','Faster urbanization']])}${number('beta','Urbanization effect per percentage point',-.1,.1,.001,P.beta,'Scenario sensitivity assumption.')}<div class="field"><label>FY2046–47 source mix (%)</label><p class="hint">Enter any nonnegative shares; they are normalized to 100%. Coal is editable too.</p>${keys.map(k=>`<div class="mixrow"><label for="mix_${k}">${labels[k]}</label><input type="number" id="mix_${k}" min="0" max="100" step=".1" value="${(100*P.mix[k]).toFixed(2)}"></div>`).join('')}<small id="mixSum"></small></div>`;
 $('#regionalControls').innerHTML=`${select('demand','Demand location basis',[['lgbr_plus_demographic_drift','LGBR + demographic drift'],['lgbr_plus_gsdp_drift','LGBR + GSDP drift'],['lgbr_constant','LGBR constant'],['organizer_proxy','Organizer proxy']])}${number('lam','Demand alignment weight',0,50,.1,P.lam)}${select('geo','Geography bounds',[['observed','Observed geography caps'],['relaxed','Relaxed caps']])}${check('hydro','Apply indicative hydro ceiling',P.hydro)}${check('useReq','Apply demand alignment',P.useReq)}${number('popWeight','Organizer population weight',0,1,.05,P.popWeight,'Used for organizer proxy; remainder is GSDP weight.')}${number('damping','Regional drift damping',0,2,.05,P.damping)}`;
 $('#variant').value=P.variant;$('#demand').value=P.demand;$('#geo').value=P.geo;
 $('#nationalControls').querySelectorAll('input,select').forEach(el=>el.addEventListener('input',readControls));
 $('#regionalControls').querySelectorAll('input,select').forEach(el=>el.addEventListener('input',readControls));
}
function readControls(event){
 if(event?.target?.id?.startsWith('mix_')&&event.target.id!=='mix_coal'){
   const nonCoal=keys.filter(k=>k!=='coal').reduce((sum,k)=>sum+Number($('#mix_'+k).value||0),0);
   $('#mix_coal').value=Math.max(0,100-nonCoal).toFixed(2);
 }
 const val=id=>Number($('#'+id).value), mix={}; keys.forEach(k=>{mix[k]=val('mix_'+k)/100});
 P={...P,g0:val('g0')/100,g1:val('g1')/100,e0:val('e0'),e1:val('e1'),addon:val('addon'),variant:$('#variant').value,beta:val('beta'),mix,
   demand:$('#demand').value,lam:val('lam'),geo:$('#geo').value,hydro:$('#hydro').checked,useReq:$('#useReq').checked,popWeight:val('popWeight'),damping:val('damping')};
 $('#mixSum').textContent=`Entered sum: ${fmt(100*Object.values(mix).reduce((a,b)=>a+b,0),1)}% · model normalizes automatically`;
 try{validate();national=model.nationalPath(M,P);update()}catch(e){status(e.message,'error')}
}
function validate(){
 const fields=['g0','g1','e0','e1','addon','beta','lam','popWeight','damping',...keys.map(k=>'mix_'+k)];
 for(const id of fields){const el=$('#'+id);if(!el.checkValidity()||el.value==='')throw Error(`Check ${el.labels?.[0]?.textContent||id}: out of range.`)}
 if(Object.values(P.mix).reduce((a,b)=>a+b,0)<=0)throw Error('At least one source mix share must be positive.');
}
function status(message,type=''){const el=$('#modelStatus');el.textContent=message;el.className=type}
function lineChart(){
 const h=M.history.filter(x=>x.total_twh!=null),f=national;
 const points=[...h.map(x=>x.total_twh),...f.map(x=>x.total_generation_twh)],ymax=Math.ceil(Math.max(...points)/1000)*1000;
 const W=660,H=275,l=49,r=17,t=15,b=33,x=y=>l+(y-2010)/(2048-2010)*(W-l-r),y=v=>H-b-v/ymax*(H-t-b);
 const path=rows=>rows.map((p,i)=>(i?'L':'M')+x(p.fy_end_year).toFixed(1)+','+y(p.total_twh??p.total_generation_twh).toFixed(1)).join(' ');
 let g='';for(let v=0;v<=ymax;v+=1000)g+=`<line x1="${l}" x2="${W-r}" y1="${y(v)}" y2="${y(v)}" stroke="#e8eeee"/><text x="0" y="${y(v)+4}" fill="#8a9aa7" font-size="11">${fmt(v)}</text>`;
 for(let v of [2010,2018,2026,2034,2042,2048])g+=`<text x="${x(v)}" y="${H-5}" text-anchor="middle" fill="#8495a1" font-size="11">${v}</text>`;
 const cur=f.find(q=>q.fy_end_year===year);
 $('#trajectory').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Observed generation and recalculated scenario to ${fy(year)}">${g}<path d="${path(h)}" fill="none" stroke="#efa582" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="${path([{fy_end_year:2026,total_generation_twh:h.at(-1).total_twh},...f])}" fill="none" stroke="#109b98" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><line x1="${x(year)}" x2="${x(year)}" y1="${t}" y2="${H-b}" stroke="#0d958f" stroke-dasharray="4 5" opacity=".55"/><circle cx="${x(year)}" cy="${y(cur.total_generation_twh)}" r="6" fill="#0d958f" stroke="white" stroke-width="3"/></svg>`;
}
function stack(rows,selector){
 const total=rows.reduce((a,x)=>a+x.twh,0),shown=rows.filter(x=>x.twh>1);
 $(selector).innerHTML=`<div class="stacktrack" style="height:25px;margin:8px 0 20px">${shown.map(x=>`<span title="${esc(labels[x.source])}: ${fmt(x.twh,1)} TWh" style="width:${100*x.twh/total}%;background:${colors[x.source]}"></span>`).join('')}</div><div class="mixlegend">${shown.map(x=>`<div><i style="background:${colors[x.source]}"></i>${esc(labels[x.source])} · ${fmt(100*x.twh/total,1)}%</div>`).join('')}</div>`;
}
function update(){
 const s=national.find(q=>q.fy_end_year===year);if(!s)return;
 $('#yearLabel').textContent=fy(year);
 const name={conservative:'Conservative',central:'Central',accelerated:'Accelerated transition'}[scenario];
 $('#overviewTitle').textContent=`${name} assumptions · ${fy(year)}`;$('#regionTitle').textContent=`${region==='ALL'?'Five regions':names[region]} · ${fy(year)}`;
 $('#domestic').textContent=fmt(s.domestic_generation_twh);$('#total').textContent=fmt(s.total_generation_twh);$('#nonfossil').textContent=fmt(100*s.non_fossil_share)+'%';
 lineChart();stack(keys.map(k=>({source:k,twh:s.bySource[k]})),'#mixChart');
 const stat=M.statistical.find(x=>x.model==='rw_drift'&&x.fy_end_year===year);
 $('#statInfo').textContent=stat?`Independent RW-drift median ${fmt(stat.point_twh)} TWh, CEA-total basis. Model-based interval ${fmt(stat.lo95)}–${fmt(stat.hi95)} TWh (95%); tested only at 1–5 year horizons.`:'The statistical interval is extrapolated from shorter-horizon validation, not calibrated for 2047.';
 let solution=model.allocate(M,P,s);
 if(solution.status!=='solved'){
   status(`Indicative hydro ceiling infeasible: ${fmt(solution.required)} TWh required versus ${fmt(solution.ceiling)} TWh ceiling. Regional chart uses a clearly labelled calculation without that ceiling; the requested constrained allocation has no solution.`,'warning');
   solution=model.allocate(M,P,s,true);
 }else status('Recalculated live · national source totals and regional totals conserved.');
 const reg=solution.rows.sort((a,b)=>b.generation_twh-a.generation_twh),max=Math.max(...reg.map(x=>x.generation_twh));
 $('#regionChart').innerHTML=reg.map(x=>`<div class="barrow"><span>${names[x.region]}</span><div class="bartrack"><div class="barfill" style="width:${100*x.generation_twh/max}%"></div></div><b>${fmt(x.generation_twh)}</b></div>`).join('');
 $('#regionalTable').innerHTML=reg.map(x=>`<tr><td>${names[x.region]}</td><td>${fmt(x.generation_twh,1)}</td><td>${fmt(100*x.share_of_national,1)}%</td><td>${fmt(100*x.non_fossil_share,1)}%</td><td>${fmt(100*x.variable_re_share,1)}%</td></tr>`).join('');
 const chosen=region==='ALL'?reg:reg.filter(x=>x.region===region);
 $('#selectedRegionLabel').textContent=region==='ALL'?'DOMESTIC MIX':names[region].toUpperCase();
 stack(keys.map(k=>({source:k,twh:chosen.reduce((a,x)=>a+x.bySource[k],0)})),'#regionMix');
 const sum=reg.reduce((a,x)=>a+x.generation_twh,0);
 $('#regionalNote').textContent=`${solution.status==='unconstrained_fallback'?'Hydro ceiling removed for illustration. ':''}Five allocations sum to ${fmt(sum,1)} TWh versus ${fmt(s.domestic_generation_twh,1)} TWh nationally. Physical feasibility is not established.`;
}
fetch('model_inputs.json').then(r=>{if(!r.ok)throw Error('Model inputs could not load');return r.json()}).then(m=>{M=m;reset()}).catch(e=>{status('Dashboard could not load model inputs. Refresh the page.','error');console.error(e)});
function reset(){scenario='central';year=2047;region='ALL';$('#scenario').value=scenario;$('#year').value=year;$('#region').value=region;P=model.paramsFromScenario(M,scenario);buildControls();readControls()}
$('#reset').addEventListener('click',reset);
$('#scenario').addEventListener('change',e=>{scenario=e.target.value;P=model.paramsFromScenario(M,scenario);buildControls();readControls()});
$('#year').addEventListener('input',e=>{year=+e.target.value;try{update()}catch(err){status(err.message,'error')}});
$('#region').addEventListener('change',e=>{region=e.target.value;try{update()}catch(err){status(err.message,'error')}});
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.tabpane').forEach(x=>x.classList.toggle('active',x.id===b.dataset.tab))}));
