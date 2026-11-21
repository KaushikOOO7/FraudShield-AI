# Implementation roadmap

Updated 2026-11-21. Status below means implemented and tested locally, with
external verification recorded separately. The full platform remains in progress.

| Phase | Deliverable | Status |
| --- | --- | --- |
| Inspection | Repository, environment, configuration, models/data/contracts | Completed; visible workspace initially empty |
| 1 | FastAPI, Pydantic, JWT verification, configuration, errors and limits | Implemented and tested |
| 1 storage | All 25 required entities plus internal counters, ordered migrations | Implemented; SQLite migrations and constraints executed/tested |
| 1 Supabase | PostgreSQL TLS/role handling, Auth foreign key and RLS migration | Implemented; real Supabase/PostgreSQL verification pending |
| 2 SMS | Real corpus, provenance, cleaning, group/stratified splits, TF-IDF/Logistic Regression, artifact and inference | Completed and tested with genuine data |
| 2 URL | Original PhiUSIIL acquisition, reproducible URL-text features, conservative domain-group splitting and RF/XGBoost comparison | Code and feature/unavailable guards tested; corpus download failed; actual training/evaluation pending |
| 3 adapters | Safe Browsing, VirusTotal, URLhaus, PhishTank, AbuseIPDB, fixed-registry RDAP and crt.sh | Implemented and fixture-tested; live verification remains pending |
| 4 services | SMS/model/rules/URL/risk/storage/history/deletion | Completed end to end and tested |
| 4 interpretation | Optional Gemini selection of existing finding/action references | Implemented and fixture-tested; no live communication verified; no factual generation or critical scoring |
| 4 agents | LangGraph multi-agent coordination | Planned |
| 5 correlation | NetworkX, persisted evidence graph, direct owner-scoped SMS/URL/QR/parsed-APK URL identifier matches | Implemented; API, access isolation, rollback and deletion/retention tested locally |
| 5 user records | Owner-scoped unreviewed reports, watchlists and opt-in alert history | Implemented; validation, storage, isolation, empty results and actual warning creation tested locally |
| 5 QR/caller formats | Bounded OpenCV/Pillow QR decoding, UPI syntax, URL routing and masked caller-format storage | Implemented/tested; fraud models, payee identity and caller reputation unavailable |
| 5 APK adapter/guards | Bounded archive/upload guards and optional isolated Androguard parser | Guards/unavailable status tested; successful genuine APK parsing pending dependency and fixture |
| 5 remaining | Caller reputation, verified brands, advanced campaigns, moderation and push delivery | Planned; no unverified success claimed |
| 6 initial | Android JSON/auth/error contracts, OpenAPI and Postman | Implemented for current HTTP operations; independent Android verification pending |
| 6 uploads | QR uploads, APK guards and independent Android integration | QR/guards tested in backend; genuine APK parsing and independent Android checks pending |

First target achieved locally: real SMS inference runs through FastAPI, signed
JWT verification, actual SQL persistence, explanations, ownership filters and
deletion. Optional-provider absence stays explicit.

Next: install the optional PostgreSQL driver and verify a dedicated Supabase
project's migrations, safe role, Auth/JWKS and RLS. Then acquire and inspect
the licensed PhiUSIIL raw-URL dataset before training the prepared baseline.
Do not infer arbitrary URLs with unreproducible benchmark features.

Continue one complete, tested feature at a time. Real provider smoke tests need
actual keys and permitted inputs. Add LangGraph after reliable services, verify
the isolated APK parser with a genuine fixture, and expand evidence-supported
correlation. Never create
relationships from placeholders, similarity alone or redacted-value collisions.
