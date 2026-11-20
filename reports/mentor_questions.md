# Unresolved assumptions and questions for mentors / organizers

1. **Year definition.** Should "2047" be FY2046-47, FY2047-48 or calendar 2047? (We headline FY2046-47 and also report FY2047-48.)
2. **Scope of "generation".** Utility generation (CEA) only, or including captive plants (Ember totals exceed CEA by ~150–210 TWh/yr since FY2016-17)? Should Bhutan/Nepal imports be excluded from the target?
3. **Organizer dataset.** Is the `Year` field calendar or financial year? Which cells were XGBoost-imputed? Is Ladakh included in J&K after 2019?
4. **Rule scope (capacity and consumption) — NOT yet clarified.** The organizer's installed-capacity columns are not used at all, and neither capacity nor consumption is ever a forecasting target or predictor of national generation. Two *secondary* inputs may still fall under the rule: (a) CEA hydro resource potential (MW), used only as a dimensionless potential/developed ratio to cap regional hydro generation; (b) CEA electricity-requirement shares, used only to locate demand for the transfer term of the regional allocation. Both are optional, labelled exploratory, and can be switched off (a sensitivity case runs without either). May we keep them? May NIWE/NISE solar and wind potentials be used the same way?
5. **Regions.** Is the 5-region CEA grid classification acceptable, or must results also be shown on the organizer's 6-zone `Zone` scheme (which places Rajasthan in West, MP/Chhattisgarh in Central, A&N in South, Sikkim in North-East)?
6. **State-level output.** Is a state-level generation strategy expected at the final stage? (Data exist for state-level RE; conventional state-level generation would require DGR Sub-report-2 extraction.)
7. **Policy anchors.** Which official targets should scenarios honour (net-zero 2070, nuclear and green-hydrogen missions), given that most are stated in capacity terms?
8. **Resource potentials.** May we import CEA hydro basin potential, NIWE wind and NISE solar potentials and land-use data to replace the observed-geography caps?
9. **Transmission.** Is an indicative inter-regional transfer (generation minus demand share) sufficient, or is a corridor-capacity analysis expected?
10. **External forecasts.** Is using NEP/EPS requirement projections as a plausibility cross-check acceptable, given they are consumption-side?
11. **Reliability.** What reliability metric would judges prefer at this stage (dispatchable share, firm-energy share, LOLP proxy)?
12. **FY2025-26 base year.** Generation grew only ~1% while GDP grew ~7.8% (reported); we have not established the cause. Should the base year be normalised?
13. **Demography.** Are TG (2020) projections acceptable, or should UN WPP 2024 / Census 2027 provisional figures be used? Is a demand-side urbanization semi-elasticity sensible, and is there an official value to use?
14. **Regional strategy expectation.** Do judges expect an optimised national mix (cost/emissions/reliability), or is a transparent policy-scenario mix with an illustrative regional allocation acceptable at this stage?
