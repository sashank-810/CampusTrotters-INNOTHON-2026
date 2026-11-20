"""CampusTrotters seven-slide final deck, sourced from verified pipeline outputs."""
from pathlib import Path
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'presentation'/'CampusTrotters_INNOTHON2026_FINAL_v1_3.pptx'
SITE='https://campustrotters-innothon-2026.stormyboot512.chatgpt.site'
S=pd.read_csv(ROOT/'outputs/national_scenarios.csv')
R=pd.read_csv(ROOT/'outputs/regional_summary.csv')
M=pd.read_csv(ROOT/'outputs/regional_allocation.csv')
H=pd.read_csv(ROOT/'data/derived/national_generation_fy.csv')
for key,expected in {'conservative':4434.575,'central':5312.183,'accelerated':5574.683}.items():
 row=S[(S.scenario==key)&(S.fy_end_year==2047)].iloc[0]
 assert abs(row.domestic_generation_twh-expected)<.001
 assert abs(row.domestic_generation_twh+row.bhutan_import_twh-row.total_generation_twh)<1e-6
assert abs(R[(R.scenario=='central')&(R.fy_end_year==2047)].generation_twh.sum()-5312.183196)<.001
def rgb(h):return RGBColor.from_string(h.lstrip('#'))
NAVY='081B2D'; DARK='102B3A'; TEAL='0A8E88'; MINT='74D0C4'; CORAL='F2A37E'; WHITE='FFFFFF'; PALE='EDF5F3'; TEXT='193248'; MUTED='577083'; LINE='D8E5E7'; GOLD='F5B457'
prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
blank=prs.slide_layouts[6]
def rect(sl,x,y,w,h,color,radius=False,line=None):
 sh=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h))
 sh.fill.solid();sh.fill.fore_color.rgb=rgb(color)
 sh.line.fill.background() if not line else None
 if line:sh.line.color.rgb=rgb(line)
 if radius:
  try:sh.adjustments[0]=0.11
  except Exception:pass
 return sh
def txt(sl,text,x,y,w,h,size=16,color=TEXT,bold=False,align=None,fit=False):
 box=sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h));tf=box.text_frame;tf.clear();tf.word_wrap=True
 tf.margin_left=tf.margin_right=Inches(.01);tf.margin_top=tf.margin_bottom=Inches(.01)
 p=tf.paragraphs[0];p.text=text;p.font.name='Aptos';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=rgb(color)
 if align:p.alignment=align
 return box
def title(sl,no,head,sub=None,dark=False):
 bg=NAVY if dark else WHITE
 sl.background.fill.solid();sl.background.fill.fore_color.rgb=rgb(bg)
 rect(sl,.55,.45,.1,.32,TEAL if not dark else MINT)
 txt(sl,'CAMPUS TROTTERS  /  EXXONMOBIL INNOTHON 2026',.82,.45,10,.29,10,MINT if dark else TEAL,True)
 txt(sl,head,.72,.95,11.8,.7,31,WHITE if dark else NAVY,True)
 if sub:txt(sl,sub,.73,1.76,11.8,.47,14,'A9CBD0' if dark else MUTED)
 txt(sl,f'{no:02d} / 07',11.9,7.05,.7,.2,9,'8BAAB2' if dark else MUTED,True,PP_ALIGN.RIGHT)
def note(sl,s,dark=False):
 rect(sl,.72,6.83,11.8,.012,'375468' if dark else LINE)
 txt(sl,s,.73,6.91,11.1,.24,9,'9BBAC0' if dark else MUTED)
def box(sl,x,y,w,h,tag,body,value=None):
 rect(sl,x,y,w,h,PALE,True)
 txt(sl,tag,x+.19,y+.16,w-.38,.25,10,TEAL,True)
 if value:txt(sl,value,x+.19,y+.47,w-.38,.48,24,NAVY,True)
 txt(sl,body,x+.19,y+(1.05 if value else .53),w-.38,h-(1.19 if value else .7),13,TEXT)

# 1 / opening
s=prs.slides.add_slide(blank);title(s,1,'India’s electricity generation to 2047','A generation-first national outlook with transparent regional scenarios',True)
rect(s,.73,2.41,8.0,3.65,'10384A',True)
txt(s,'CENTRAL CASE  ·  FY2046–47',1.08,2.78,6.5,.33,12,MINT,True)
txt(s,'5,312',1.06,3.23,5,.99,56,WHITE,True)
txt(s,'TWh generated domestically',1.10,4.29,6.7,.45,21,WHITE,True)
txt(s,'+ 7.804 TWh assumed Bhutan imports  =  5,319.987 TWh CEA-definition total',1.10,5.12,7.1,.46,13,'BED5DB')
rect(s,9.04,2.41,3.49,1.69,TEAL,True);txt(s,'63%',9.32,2.71,2.9,.8,40,WHITE,True);txt(s,'non-fossil mix assumed',9.33,3.56,3,.3,13,WHITE)
rect(s,9.04,4.37,3.49,1.69,'183D4D',True);txt(s,'48 / 48',9.33,4.7,3,.62,31,WHITE,True);txt(s,'automated tests passed',9.33,5.54,3,.28,12,'C6D8DD')
note(s,'CampusTrotters · IISc Bengaluru  |  National scenario projections; regional allocations are conditional and illustrative.',True)

# 2 / data and provenance
s=prs.slides.add_slide(blank);title(s,2,'Preserve the base data. Add generation evidence.','The organizer CSV is preserved byte-for-byte; every added series has a source and a unit.')
box(s,.73,2.38,3.6,3.9,'01  ORGANIZER BASE TRUTH','State-year population, GSDP and geography. Electricity generated is not present in the supplied fields.','635 rows')
box(s,4.53,2.38,3.9,3.9,'02  OBSERVED GENERATION','CEA/MoP national and region/source generation; Ember calendar-year series supplies an independent comparison.','17 FY + 26 CY')
box(s,8.63,2.38,3.9,3.9,'03  ASSUMPTION LAYER','Technical Group population and urbanization to 2036; later demographic paths, GDP growth and 2047 fuel shares are scenarios.','2047 paths')
note(s,'Organizer SHA-256: f8f98adf…c692b35450d7bd4f  |  185/186 source validation checks pass; PSAG-GR-2011 is documented.')

# 3 / model method and backtest
s=prs.slides.add_slide(blank);title(s,3,'Forecast nationally. Allocate conditionally. Test both.','Generation (TWh) is the outcome throughout; installed capacity and consumption are not forecast targets.')
steps=[('1','RECONCILE','CEA financial years, Ember calendar years; tag observed vs estimated values.'),('2','FORECAST','Compare CAGR, log-linear, Holt and random-walk drift on rolling origins.'),('3','SCENARIOS','Apply generation–GDP elasticity and assumed growth, electrification and fuel shares.'),('4','ALLOCATE','Constrain illustrative region × fuel quantities to sum to national domestic generation.')]
for i,(n,h,b) in enumerate(steps):
 x=.73+i*3.05;rect(s,x,2.42,2.85,2.05,PALE,True);txt(s,n,x+.2,2.58,.48,.55,29,TEAL,True);txt(s,h,x+.2,3.16,2.47,.3,12,NAVY,True);txt(s,b,x+.2,3.58,2.48,.67,12,TEXT)
rect(s,.73,4.86,11.8,1.37,NAVY,True)
for x,v,label in [(1.05,'5.37%','CEA FY WAPE · 40 tests'),(5.12,'4.25%','Ember CY WAPE · 70 tests'),(9.18,'1–5 years','validated horizons')]:
 txt(s,v,x,5.03,3.35,.48,25,MINT,True);txt(s,label,x,5.56,3.35,.3,12,WHITE)
note(s,'Selected interval model: random walk with drift. The 2047 interval extends beyond tested horizons and is not calibrated at 21 years.')

# 4 / 2047 scenario results
s=prs.slides.add_slide(blank);title(s,4,'A scenario range, not a single promise.','FY2046–47 domestic generation, modelled; target fuel shares are assumptions.')
cases=[('Conservative',4434.575,.46,'52% coal + 2% gas'),('Central',5312.183,.63,'35% coal + 2% gas'),('Accelerated transition',5574.683,.80,'18% coal + 2% gas')]
for i,(label,value,nonfossil,fossil) in enumerate(cases):
 y=2.45+i*1.13;txt(s,label,.83,y,.31 if False else 2.65,.36,17,NAVY,True)
 rect(s,3.47,y+.05,6.75,.36,'E8F0F0',True)
 rect(s,3.47,y+.05,6.75*value/6000,.36,TEAL if i==1 else ('83B6B1' if i==0 else CORAL),True)
 txt(s,f'{value:,.0f} TWh',10.38,y-.06,1.93,.5,21,NAVY,True)
 txt(s,f'{nonfossil:.0%} assumed non-fossil  ·  {fossil}',3.49,y+.51,8.5,.28,12,MUTED)
rect(s,.73,6.06,11.8,.52,PALE,True)
txt(s,'INDEPENDENT CHECK   RW-drift 2047 median: 5,469 TWh (CEA-total basis)  ·  indicative 95%: 3,640–8,215 TWh',.94,6.2,11.35,.25,12,TEAL,True)
note(s,'Scenario range reflects chosen economic/mix assumptions, not a statistical prediction interval. Bhutan imports assumed flat at 7.804 TWh.')

# 5 / regional
s=prs.slides.add_slide(blank);title(s,5,'What the central case allocates across five regions.','FY2046–47, conditional illustration; five regional totals equal 5,312.183 TWh domestic.')
reg=R[(R.scenario=='central')&(R.fy_end_year==2047)].set_index('region')
order=[('WR','Western'),('NR','Northern'),('SR','Southern'),('ER','Eastern'),('NER','North-Eastern')]
for i,(code,label) in enumerate(order):
 y=2.39+i*.72;v=reg.loc[code];txt(s,label,.8,y,2.45,.34,15,NAVY,True)
 rect(s,3.38,y+.08,5.55,.25,'E8F0F0',True);rect(s,3.38,y+.08,5.55*v.generation_twh/1800,.25,TEAL if code!='NER' else CORAL,True)
 txt(s,f'{v.generation_twh:,.0f}',9.06,y-.01,1.0,.33,17,NAVY,True);txt(s,f'{v.non_fossil_share:.0%} non-fossil',10.17,y+.01,2.2,.3,12,MUTED)
rect(s,.75,6.13,11.8,.48,PALE,True)
txt(s,'Solar concentrates in North / South / West; North-Eastern hydro ~86 TWh in the central allocation, against an indicative ~195 TWh ceiling.',.95,6.25,11.35,.24,11,TEAL,True)
note(s,'No independently fitted regional model or validated land, site, transmission, storage or dispatch constraints; regional mix is exploratory.')

# 6 / guardrails & honest limitations
s=prs.slides.add_slide(blank);title(s,6,'Make constraints fail visibly. Keep claims bounded.','A hydro stress test and accounting checks prevent a visually plausible but invalid regional story.')
rect(s,.74,2.34,6.02,3.98,NAVY,True)
txt(s,'HYDRO STRESS TEST',1.05,2.66,4.8,.32,12,MINT,True)
txt(s,'1,062',1.02,3.11,2.9,.7,38,WHITE,True);txt(s,'TWh required',1.06,3.91,2.55,.31,15,WHITE)
txt(s,'vs',3.85,3.51,.48,.32,19,MINT,True)
txt(s,'480',4.54,3.11,1.85,.7,38,CORAL,True);txt(s,'TWh indicative ceiling',4.56,3.91,2.0,.53,14,WHITE)
txt(s,'Result: infeasible under the ceiling; no constrained allocation is falsely marked compliant.',1.07,4.71,5.18,1.11,15,'C8DBDF')
box(s,7.02,2.34,5.52,1.83,'ACCOUNTING GATE','66/66 default region-year allocations solved; national / regional totals conserve generation.','66 / 66')
box(s,7.02,4.39,5.52,1.93,'RULE & FEASIBILITY LIMIT','Capacity-derived hydro ceiling and demand proxy are optional exploratory inputs; physical feasibility and regional calibration remain open.')
note(s,'20% central hydro stress: FY2046–47 requirement 1,062.437 TWh; original indicative ceiling 480.363 TWh.')

# 7 / impact and delivery
s=prs.slides.add_slide(blank);title(s,7,'A working decision tool with a reproducible audit trail.','Use the dashboard to examine scenario and region choices; inspect the repository to rerun the full model.',True)
shot=ROOT/'presentation/dashboard_screenshot_final.jpg'
if shot.exists():
 s.shapes.add_picture(str(shot), Inches(.73), Inches(2.34), width=Inches(5.78),height=Inches(3.65))
 rect(s,.73,2.34,5.78,3.65,NAVY,False,'416475').fill.background()
rect(s,6.86,2.35,5.66,1.13,'123E4D',True)
txt(s,'LIVE PUBLIC DASHBOARD',7.16,2.55,5.04,.28,11,MINT,True)
link=txt(s,'Open interactive dashboard  ↗',7.16,2.95,5.02,.32,17,WHITE,True);link.click_action.hyperlink.address=SITE
rect(s,6.86,3.74,5.66,2.23,'123E4D',True)
txt(s,'WHAT IT ENABLES',7.16,3.99,5.0,.25,11,MINT,True)
txt(s,'Compare 3 national scenarios; inspect 5 regional generation allocations; view source mix, data status and validation limits.',7.16,4.44,4.97,1.18,17,WHITE)
note(s,'Public site selects precomputed, independently checked v1.2 results; the Python Streamlit app recomputes custom controls. 48 tests passed.',True)

assert len(prs.slides)==7
OUT.parent.mkdir(parents=True,exist_ok=True)
prs.save(OUT)
print(OUT)
