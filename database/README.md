# database: schema and data (PostgreSQL 16 + pgvector)

| Folder | What |
|---|---|
| `schema/` | the tables, applied in order by `scripts/init_db.py` (safe to re-run): calls, answers, consents, stories, events, occupations (`nco`, with a 768-number meaning vector), blocked numbers |
| `seed/nco_seed.csv` | the 59 occupations: NCO code, English / Hindi / Marathi names, words callers use. Loaded by `scripts/seed_nco.py` |
| `sample/` | sample data, **made up for the demo and labelled as sample**: `pin_districts.csv` (first 3 PIN digits -> district, approximate; used by `core/geo.py`, step A7). Step A8 adds NSQF courses, training centres, local demand, schemes |

Personal data: phone numbers are stored only as a keyed hash plus an encrypted copy; pressing 9
on a call deletes every row of that caller and their recordings.
