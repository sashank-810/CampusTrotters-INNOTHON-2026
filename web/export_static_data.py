"""Export the checked Python model's CSV products for the read-only public dashboard."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
FILES={
 'scenario':'outputs/national_scenarios.csv',
 'regions':'outputs/regional_summary.csv',
 'mix':'outputs/regional_allocation.csv',
 'history':'data/derived/national_generation_fy.csv',
 'stat':'outputs/national_forecast_statistical.csv',
 'demo':'outputs/demography_sensitivity.csv',
 'checks':'outputs/validation_checks.csv',
 'sensitivity':'outputs/allocation_sensitivity.csv',
}
data={key:(lambda df:df.astype(object).where(pd.notna(df),None).to_dict('records'))(pd.read_csv(ROOT/path)) for key,path in FILES.items()}
for case in ('conservative','central','accelerated'):
 for year in range(2027,2049):
  national=next(x['domestic_generation_twh'] for x in data['scenario'] if x['scenario']==case and x['fy_end_year']==year)
  regional=sum(x['generation_twh'] for x in data['regions'] if x['scenario']==case and x['fy_end_year']==year)
  assert abs(national-regional)<1e-6,(case,year,national,regional)
dest=ROOT/'web/dist/data.json'
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(data,separators=(',',':'),allow_nan=False),encoding='utf-8')
print(f'Wrote {dest}; 66/66 national-regional accounting comparisons passed.')
