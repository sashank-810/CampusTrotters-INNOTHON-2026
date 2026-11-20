/* Browser port of src/scenarios.py, src/demography.py and the convex objective
   in src/allocation.py. All generation figures are TWh, never capacity.
   Node import is supported for independent comparisons against Python. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CampusTrottersModel = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const lin = (a,b,t,t0,t1) => t<=t0?a:t>=t1?b:a+(b-a)*(t-t0)/(t1-t0);
  const clip = (v,l,u) => Math.min(u,Math.max(l,v));
  const normalized = values => {const sum=values.reduce((a,b)=>a+b,0);return values.map(v=>v/sum)};
  const variants = {
    central:{pop:0,urban:1}, low_pop:{pop:-.2,urban:1},
    high_pop:{pop:.2,urban:1}, slow_urban:{pop:0,urban:.5},
    fast_urban:{pop:0,urban:2}
  };
  function paramsFromScenario(m,key){
    const s=m.scenarios[key], mix={...s.mix_2047};
    return {scenario:key,g0:s.gdp_growth_start,g1:s.gdp_growth_end,e0:m.eps0,
      e1:s.elasticity_end,addon:s.addon_twh_2047,mix,variant:'central',beta:.005,
      lam:1,demand:'lgbr_plus_demographic_drift',useReq:true,geo:'observed',
      hydro:true,popWeight:.5,damping:.5};
  }
  function nationalPath(m,p) {
    const ks=m.sources, base=m.base, baseDom=Object.values(base.mix_twh).reduce((a,b)=>a+b,0);
    const baseShares=Object.fromEntries(ks.map(k=>[k,base.mix_twh[k]/baseDom]));
    const targetTotal=ks.reduce((a,k)=>a+Math.max(0,p.mix[k]),0);
    if(!(targetTotal>0)) throw Error('Mix shares must contain positive generation.');
    const target=Object.fromEntries(ks.map(k=>[k,Math.max(0,p.mix[k])/targetTotal]));
    const demos=Object.fromEntries(m.national_demography.map(r=>[r.fy_end_year,r]));
    const variant=variants[p.variant]||variants.central;
    const b=m.base_fy_end, basePop=demos[b].population_m, baseUrban=demos[b].urban_pct;
    let pop=basePop,core=base.total_twh;
    const rows=[];
    for(let t=b+1;t<=m.horizon_end;t++){
      const g=p.g0+(p.g1-p.g0)*Math.min(1,(t-b-1)/(m.headline_fy_end-b-1));
      const e=lin(p.e0,p.e1,t,b+1,m.headline_fy_end);
      core*=Math.pow(1+g,e);
      const addon=t>=m.addon_ramp_start?lin(0,p.addon,t,m.addon_ramp_start,m.headline_fy_end):0;
      const central=demos[t],prev=demos[t-1];
      pop*=1+(central.population_m/prev.population_m-1)+variant.pop/100;
      const urb=Math.min(100,baseUrban+variant.urban*(central.urban_pct-baseUrban));
      const factor=(pop/central.population_m)*(1+p.beta*(urb-central.urban_pct));
      const domestic=(core+addon-m.bhutan_import_twh)*factor;
      const shares={},bySource={};
      for(const k of ks){
        shares[k]=lin(baseShares[k],target[k],t,b,m.headline_fy_end);
        bySource[k]=domestic*shares[k];
      }
      rows.push({fy_end_year:t,gdp_growth:g,elasticity:e,addon_twh:addon,
        domestic_generation_twh:domestic,total_generation_twh:domestic+m.bhutan_import_twh,
        population_m:pop,urban_pct:urb,demographic_factor:factor,
        non_fossil_share:ks.filter(k=>k!=='coal'&&k!=='gas').reduce((a,k)=>a+shares[k],0),
        variable_re_share:shares.solar+shares.wind,shares,bySource});
    }
    return rows;
  }
  function demandShares(m,p,year){
    const rs=m.regions;
    if(!p.useReq || p.demand==='organizer_proxy')
      return normalized(rs.map(r=>p.popWeight*m.demand_proxy_2024[r].pop_share+
        (1-p.popWeight)*m.demand_proxy_2024[r].gsdp_share));
    const base=rs.map(r=>m.demand_lgbr[r]);
    if(year<=2025 || p.demand==='lgbr_constant') return normalized(base);
    if(p.demand==='lgbr_plus_gsdp_drift')
      return normalized(rs.map((r,i)=>base[i]*Math.exp(m.gsdp_slopes[r]*(year-2025)*p.damping)));
    const byYear=Object.fromEntries(m.regional_demography.map(row=>[row.fy_end_year+'-'+row.region,row]));
    return normalized(rs.map((r,i)=>{
      const a=byYear['2025-'+r],b=byYear[year+'-'+r];
      return base[i]*(b.pop_share/a.pop_share)*
        (1+p.beta*(b.urban_pct-a.urban_pct))*
        Math.exp(p.damping*m.pc_slopes[r]*(year-2025));
    }));
  }
  // Exact one-column minimizer for the convex QP, with source conservation
  // and the original hard box bounds. Bisection finds its Lagrange multiplier.
  function boundedColumn(v,lo,hi,sum){
    if(lo.reduce((a,b)=>a+b,0)>sum+1e-9||hi.reduce((a,b)=>a+b,0)<sum-1e-9)
      throw Error('Infeasible regional source bounds.');
    let left=Math.min(...v.map((x,i)=>x-hi[i]))-1;
    let right=Math.max(...v.map((x,i)=>x-lo[i]))+1;
    for(let q=0;q<85;q++){
      const mid=(left+right)/2;
      const actual=v.reduce((a,x,i)=>a+clip(x-mid,lo[i],hi[i]),0);
      if(actual>sum)left=mid;else right=mid;
    }
    return v.map((x,i)=>clip(x-(left+right)/2,lo[i],hi[i]));
  }
  function allocate(m,p,nat,ignoreHydro=false){
    const rs=m.regions,ks=m.sources,G=nat.domestic_generation_twh;
    const n=ks.map(k=>Math.max(nat.bySource[k],0)/G);
    const jh=ks.indexOf('hydro'),capacity=rs.reduce((s,r)=>s+m.hydro_ceiling[r],0);
    if(p.hydro&&!ignoreHydro&&nat.bySource.hydro>capacity*(1+1e-9))
      return {status:'infeasible_under_indicative_hydro_ceiling',
        required:nat.bySource.hydro,ceiling:capacity,rows:[]};
    const delta=demandShares(m,p,nat.fy_end_year),lam=p.useReq?p.lam:0;
    const target=rs.map(r=>ks.map((k,j)=>m.rho[r][k]*n[j]));
    const lo=rs.map(()=>ks.map(()=>0)),hi=rs.map(r=>ks.map((k,j)=>{
      if(p.geo==='relaxed')return n[j];
      return Math.min(n[j],m.caps[k]*m.rho[r][k]*n[j]);
    }));
    if(p.hydro&&!ignoreHydro)
      rs.forEach((r,i)=>{hi[i][jh]=Math.min(n[jh],m.hydro_ceiling[r]/G)});
    rs.forEach((r,i)=>ks.forEach((k,j)=>{
      if(k==='hydro'||k==='nuclear') lo[i][j]=Math.min(m.observed_base[r][k]/G,hi[i][j]);
      hi[i][j]=Math.max(hi[i][j],lo[i][j]);
    }));
    let x=rs.map((_,i)=>ks.map((_,j)=>clip(target[i][j],lo[i][j],hi[i][j])));
    for(let j=0;j<ks.length;j++){
      const col=boundedColumn(rs.map((_,i)=>x[i][j]),rs.map((_,i)=>lo[i][j]),rs.map((_,i)=>hi[i][j]),n[j]);
      col.forEach((v,i)=>{x[i][j]=v});
    }
    let iterations=0;
    for(let iter=0;iter<3000;iter++){
      let diff=0;
      for(let j=0;j<ks.length;j++){
        const k=ks[j],a=m.weights[k]/Math.max(n[j],1e-9);
        const v=rs.map((_,i)=>{
          const others=x[i].reduce((s,z)=>s+z,0)-x[i][j];
          return (a*target[i][j]+lam*(delta[i]-others))/(a+lam);
        });
        const col=boundedColumn(v,rs.map((_,i)=>lo[i][j]),rs.map((_,i)=>hi[i][j]),n[j]);
        col.forEach((value,i)=>{diff=Math.max(diff,Math.abs(value-x[i][j]));x[i][j]=value});
      }
      iterations=iter+1;
      if(diff<2e-12)break;
    }
    const rows=rs.map((r,i)=>{
      const bySource=Object.fromEntries(ks.map((k,j)=>[k,x[i][j]*G]));
      const total=Object.values(bySource).reduce((a,b)=>a+b,0);
      return {region:r,generation_twh:total,share_of_national:total/G,
        demand_proxy_share:delta[i],indicative_net_export_twh:total-delta[i]*G,
        non_fossil_share:(total-bySource.coal-bySource.gas)/total,
        variable_re_share:(bySource.solar+bySource.wind)/total,bySource};
    });
    const sourceResidual=Math.max(...ks.map(k=>Math.abs(rows.reduce((a,r)=>a+r.bySource[k],0)-nat.bySource[k])));
    if(sourceResidual>1e-5)throw Error('Source conservation failed: '+sourceResidual);
    return {status:ignoreHydro?'unconstrained_fallback':'solved',rows,iterations,
      sourceResidual,required:nat.bySource.hydro,ceiling:capacity};
  }
  return {paramsFromScenario,nationalPath,demandShares,allocate};
});
