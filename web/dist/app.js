/* Static, read-only interactive view of the verified v1.2 outputs.
   Recompute with the Python model in the repository; these controls select precomputed rows. */
const $=s=>document.querySelector(s);
const fmt=(n,d=0)=>Number(n).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const fy=y=>`FY${y-1}–${String(y).slice(-2)}`;
const names={NR:'Northern',WR:'Western',SR:'Southern',ER:'Eastern',NER:'North-Eastern'};
const keys=['coal','gas','nuclear','hydro','solar','wind','other_re'];
const labels={coal:'Coal',gas:'Gas + diesel',nuclear:'Nuclear',hydro:'Hydro',solar:'Solar',wind:'Wind',other_re:'Other RE'};
const colors={coal:'#243c52',gas:'#81909c',nuclear:'#a08dc0',hydro:'#2288b4',solar:'#f5ae50',wind:'#19a89b',other_re:'#80bd79'};
let D,scenario='central',year=2047,region='ALL';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function lineChart(){
 const h=D.history.filter(x=>x.total_twh!=null), f=D.scenario.filter(x=>x.scenario===scenario);
 const points=[...h.map(x=>x.total_twh),...f.map(x=>x.total_generation_twh)], ymax=Math.ceil(Math.max(...points)/1000)*1000;
 const W=660,H=275,l=49,r=17,t=15,b=33;
 const x=y=>l+(y-2010)/(2048-2010)*(W-l-r), y=v=>H-b-v/ymax*(H-t-b);
 const path=rows=>rows.map((p,i)=>(i?'L':'M')+x(p.fy_end_year).toFixed(1)+','+y(p.total_twh??p.total_generation_twh).toFixed(1)).join(' ');
 let g='';for(let v=0;v<=ymax;v+=1000)g+=`<line x1="${l}" x2="${W-r}" y1="${y(v)}" y2="${y(v)}" stroke="#e8eeee"/><text x="0" y="${y(v)+4}" fill="#8a9aa7" font-size="11">${fmt(v)}</text>`;
 for(let v of [2010,2018,2026,2034,2042,2048])g+=`<text x="${x(v)}" y="${H-5}" text-anchor="middle" fill="#8495a1" font-size="11">${v}</text>`;
 const cur=f.find(x=>x.fy_end_year===year);
 $('#trajectory').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Observed generation and modelled scenario to ${fy(year)}">${g}<path d="${path(h)}" fill="none" stroke="#efa582" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="${path([{fy_end_year:2026,total_generation_twh:h.at(-1).total_twh},...f])}" fill="none" stroke="#109b98" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><line x1="${x(year)}" x2="${x(year)}" y1="${t}" y2="${H-b}" stroke="#0d958f" stroke-dasharray="4 5" opacity=".55"/><circle cx="${x(year)}" cy="${y(cur.total_generation_twh)}" r="6" fill="#0d958f" stroke="white" stroke-width="3"/></svg>`;
}
function stack(rows,selector){
 const total=rows.reduce((a,x)=>a+x.twh,0), shown=rows.filter(x=>x.twh>1);
 $(selector).innerHTML=`<div class="stacktrack" style="height:25px;margin:8px 0 20px">${shown.map(x=>`<span title="${esc(labels[x.source])}: ${fmt(x.twh,1)} TWh" style="width:${100*x.twh/total}%;background:${colors[x.source]}"></span>`).join('')}</div><div class="mixlegend">${shown.map(x=>`<div><i style="background:${colors[x.source]}"></i>${esc(labels[x.source])} · ${fmt(100*x.twh/total,1)}%</div>`).join('')}</div>`;
}
function update(){
 $('#yearLabel').textContent=fy(year);
 const s=D.scenario.find(x=>x.scenario===scenario&&x.fy_end_year===year);
 if(!s)return;
 const name={conservative:'Conservative',central:'Central',accelerated:'Accelerated transition'}[scenario];
 $('#overviewTitle').textContent=`${name} case · ${fy(year)}`; $('#regionTitle').textContent=`${region==='ALL'?'Five regions':names[region]} · ${fy(year)}`;
 $('#domestic').textContent=fmt(s.domestic_generation_twh); $('#total').textContent=fmt(s.total_generation_twh); $('#nonfossil').textContent=fmt(100*s.non_fossil_share)+'%';
 lineChart();stack(keys.map(k=>({source:k,twh:s[k+'_twh']})),'#mixChart');
 const stat=D.stat.find(x=>x.model==='rw_drift'&&x.fy_end_year===year);
 $('#statInfo').textContent=stat?`Independent RW-drift median ${fmt(stat.point_twh)} TWh, CEA-total basis. Model-based interval ${fmt(stat.lo95)}–${fmt(stat.hi95)} TWh (95%); tested only at 1–5 year horizons.`:'The 2047 statistical interval is an extrapolation of shorter-horizon validation; it is not calibrated at this horizon.';
 const reg=D.regions.filter(x=>x.scenario===scenario&&x.fy_end_year===year).sort((a,b)=>b.generation_twh-a.generation_twh);
 const max=Math.max(...reg.map(x=>x.generation_twh));
 $('#regionChart').innerHTML=reg.map(x=>`<div class="barrow"><span>${names[x.region]}</span><div class="bartrack"><div class="barfill" style="width:${100*x.generation_twh/max}%"></div></div><b>${fmt(x.generation_twh)}</b></div>`).join('');
 $('#regionalTable').innerHTML=reg.map(x=>`<tr><td>${names[x.region]}</td><td>${fmt(x.generation_twh,1)}</td><td>${fmt(100*x.share_of_national,1)}%</td><td>${fmt(100*x.non_fossil_share,1)}%</td><td>${fmt(100*x.variable_re_share,1)}%</td></tr>`).join('');
 const chosen=region==='ALL'?reg:reg.filter(x=>x.region===region);
 const mix=D.mix.filter(x=>x.scenario===scenario&&x.fy_end_year===year&&chosen.some(r=>r.region===x.region));
 $('#selectedRegionLabel').textContent=region==='ALL'?'DOMESTIC MIX':names[region].toUpperCase();
 stack(keys.map(k=>({source:k,twh:mix.filter(x=>x.source===k).reduce((a,x)=>a+x.twh,0)})),'#regionMix');
 const sum=reg.reduce((a,x)=>a+x.generation_twh,0);
 $('#regionalNote').textContent=`The five illustrative allocations sum to ${fmt(sum,1)} TWh versus ${fmt(s.domestic_generation_twh,1)} TWh in the national scenario. The national mix is an assumption and regional physical feasibility is not established.`;
}
fetch('data.json').then(r=>{if(!r.ok)throw Error('Data request failed');return r.json()}).then(data=>{D=data;update()}).catch(e=>{$('.content').innerHTML='<div class="card"><h2>Dashboard data could not load</h2><p>Refresh the page or check the publication assets.</p></div>';console.error(e)});
$('#scenario').addEventListener('change',e=>{scenario=e.target.value;update()});
$('#year').addEventListener('input',e=>{year=+e.target.value;update()});
$('#region').addEventListener('change',e=>{region=e.target.value;update()});
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.tabpane').forEach(x=>x.classList.toggle('active',x.id===b.dataset.tab))}));
