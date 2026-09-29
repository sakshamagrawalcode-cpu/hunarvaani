# Sample data (made up for the demonstration; labelled "sample" everywhere)

Real PM-AJAY beneficiary, centre and course data is not public, so these files stand in for it.
Course ids are ours (`U7531`, `R7531`, …), **not** real NSQF qualification pack codes; centre
names, distances, demand and wages are invented. Scheme names and benefits describe real schemes
in simple words and **must be checked against the official sources** before any real use.
Region: Maharashtra (fits Marathi) plus a few Hindi-belt cities, the districts in
`pin_districts.csv`.

| File | Rows | What |
|---|---|---|
| `pin_districts.csv` | 35 | first 3 PIN digits → main district of that postal area (approximate); used by `core/geo.py` (A7) |
| `sectors.csv` | 16 | sectors with names in 3 languages and a typical monthly wage range |
| `occupations.csv` | 59 | one per NCO occupation: sector, skills people in it usually have (for the skill gap), near trades, the loan scheme for own work, whether an RPL certificate exists |
| `courses.csv` | 115 | `upskill` course per occupation (NSQF level, hours, minimum education, age range, fee, placement, heavy work, skills taught, scheme); `certificate` = RPL for the trade; `startup` = PM Vishwakarma training + toolkit (its 9 trades here) and "Start your own work" (RSETI, any trade) |
| `centres.csv` | 124 | 4 per district: block skill centre (3–8 km), Kaushal Kendra (12–28 km), RSETI (15–35 km, hostel), Government ITI (25–45 km, hostel); the sectors each teaches; women-only batches |
| `demand.csv` | 141 | sectors with **high** or **low** demand per district (anything else is medium) |
| `schemes.csv` | 9 | PMKVY, PMKVY-RPL, DDU-GKY, PM-AJAY GIA, RSETI, PM Vishwakarma, PMEGP, Mudra, PM SVANidhi |

`core/sample_data.py` loads them; `core/recommend.py` (A9) picks the options;
`python scripts/recommend.py --occupation 7531 --age 26_35 --pin 411001 …` shows them.
`backend/tests/test_recommend.py` checks that every row points at things that exist.

To change the data, edit the CSVs directly (they are the source of truth) and run the tests.
