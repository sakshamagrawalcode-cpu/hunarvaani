# database: schema and data (PostgreSQL 16 + pgvector)

| Folder | What |
|---|---|
| `schema/` | the tables, applied in order by `scripts/init_db.py` (safe to re-run): calls, answers, consents, stories, events, occupations (`nco`, with a 768-number meaning vector), blocked numbers |
| `seed/nco_seed.csv` | the 59 occupations: NCO code, English / Hindi / Marathi names, words callers use. Loaded by `scripts/seed_nco.py` |
| `sample/` | sample data, **made up for the demo and labelled as sample**: PIN -> district (A7); occupations, courses, centres, demand, sectors, schemes for the recommender (A8). See `sample/README.md` |

Personal data: phone numbers are stored only as a keyed hash plus an encrypted copy; pressing 9
on a call deletes every row of that caller and their recordings.
