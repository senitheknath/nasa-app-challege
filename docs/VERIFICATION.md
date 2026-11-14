> Historical correction record. The global Crop Finder upgrade is documented in [UPGRADE_VERIFICATION.md](UPGRADE_VERIFICATION.md) and [GLOBAL_SCREENING.md](GLOBAL_SCREENING.md).

# Verification, 8 November 2026

The original working tree passed 61 tests before changes. Three of those tests contained assertions that rewarded synthetic farm scores, globally extrapolated recommendations, or a fixed observation count. Their replacements check the corrected scientific contract. The wizard integration test now supplies explicit pilot confirmation.

**Final run on WSL Ubuntu-26.04, Python 3.14: 71 passed, zero failures in 27.23 seconds.** One Streamlit chart helper issued a pandas deprecation warning. `python -m pip check` reported no broken requirements.

```bash
python -m pytest --tb=short --junitxml=artifacts/scientific-audit-tests.xml
python scripts/collect_global_data.py --offline
```

| Verification area | Executed evidence |
|---|---|
| Synthetic class labels, unsupported farm predictions and yield wording | Checked CSV and model metadata. Direct farm prediction rejected. Checked the workflow export for hybrid, yield and probability fields. |
| Actual NASA provenance, unavailable and cached observations | Checked response point/period versus request, digest, units, fill values, missing days, bounded retries, HTTP errors, invalid coordinates, and exact archive matching under injected timeouts. |
| Explicit simulation boundary | Created a labelled artificial series and attempted crop screening, rotation assessment and a farm report. All three rejected it. |
| Unknown pH, irrigation and references | Exercised blank wizard inputs and a qualitative reliable-irrigation profile without net mm. Unknowns propagated to scores and JSON. |
| Seasonal water and paddy limits | Altered rainfall and actual net irrigation. Checked changes in the maize water component and continuing uncertainty for rice and pulses. |
| Eligibility and temperature | Tested persistent waterlogging, short cowpea windows, MI 6 versus unknown cultivar, missing maize temperature and known cowpea preferences. |
| Shared ranking and sensitivity | Compared sequence results from the crop view and regional/legacy entry points. Tested normalized weights, changes to priority order, zero weights and overlapping intervals. |
| Unsupported geography | Parsed real records for Nairobi and Ames. Loaded the exact 25-year Nairobi archive during a simulated outage. Climate analysis worked and regional screening declined. |
| Assistant | Tested local explanations and references. Mocked Gemini returned a permitted topic, then an invented agricultural claim. The latter was rejected. A live Gemini account was not exercised. |
| End to end | Streamlit AppTest traversed the wizard, location change, climate charts, rotations, scenarios, educational studio, assistant and reports. Compared the displayed rotation intervals with the JSON passed to the report download. |

## Live application and data checks

The application ran locally on port 8510. The health endpoint returned HTTP 200 with `ok`. In the browser the recorded demo showed the bundled NASA source, Level 2 scope, adjustable weights and unresolved ordering. The reports page exposed all three export controls. The embedded browser did not emit a native download-completion notification. An independent session against the running Streamlit server activated the demo and fetched all three actual download URLs. Each returned HTTP 200. The JSON held 25 rotations and two seasonal summaries, all 25 names appeared in the HTML, and the CSV contained 9,131 data rows. The saved files are under `artifacts/verified-exports/` in the working copy.

The station collector persisted 33 compressed raw responses plus the existing Anuradhapura snapshot. A second, entirely offline pass read and verified all 34 named locations. Each manifest row names the exact archived file and payload digest. The country selector's custom coordinate option is excluded from this count.

The live demo values are recorded in the [walkthrough](../DEMONSTRATION_AND_SUBMISSION.md). The [desktop preview](rotation-preview.jpg) shows the interval comparison. Software checks establish reproducibility under these inputs. Agronomic outcome validation, commercial deployment and competition eligibility are separate outstanding matters.

The official competition terms and challenge pages returned HTTP 502 during the 8 November recheck. Existing implementation and audit commits predate the advertised event. No competition submission was made.
