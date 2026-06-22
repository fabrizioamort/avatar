# Knowledge Base Interview — Progress Log

This file tracks an ongoing "interview" with Fabrizio (via voice-memo transcripts) used to
enrich `knowledge/` with first-person career history. It lives outside `knowledge/` on purpose:
files under `knowledge/` are loaded into the system prompt and embedded for RAG, and this log
is process notes, not owner knowledge for the Avatar to draw on.

To resume: read the "Next question pending" section below, get Fabrizio's answer, update the
relevant file(s) under `knowledge/background/` (or elsewhere if the topic doesn't fit there),
commit, and push to `claude/audio-transcript-kb-edqag9`. Re-run
`cd backend && uv run python scripts/ingest_knowledge.py` once GCP credentials are available, to
re-embed changed chunks into Firestore.

## Covered so far

| Topic | File(s) changed | Commit |
|---|---|---|
| Early self-taught path (HP/RPN calculators, Sharp PC-1211, BASIC, Sinclair ZX Spectrum) and university thesis (genetic algorithms optimizing an expert system on a transputer-based parallel architecture, 110 e lode) | `knowledge/background/education-and-certifications.md` | `268ad47` |
| Telesoft start date (May 1991) and the NetKit project (expert system normalizing multi-vendor telephone-exchange alarms) | `knowledge/background/career-journey.md` | `e032e5d` |
| Shared Service Center (2003-2007): SAP Portal intranet for ~100k TIM/SIP + Pirelli employees, the per-machine Java-class memory problem, the fix (partition the server fleet by tenant), and the LoadRunner performance-testing experience | `knowledge/background/career-journey.md` | `e33783b` |
| TIM Drupal era origin story: scope (all TIM Group sites except commercial), the first site (custom French-vendor platform), why Drupal was chosen, the Multiblog shared-base architecture, the LAMP stack | `knowledge/background/career-journey.md` | `5292244` |
| TIM Drupal era security discipline: daily automated attack attempts (WordPress/Drupal CVE scans) that never succeeded, patching disclosed vulnerabilities within hours rather than on a normal change cycle, verifying SOC-flagged attempts | `knowledge/background/career-journey.md` | `14b2b91` |

## Open clarifications (asked, not yet answered)

These were left out of the knowledge base rather than guessed, because they're proper nouns or
specific facts a wrong guess would misrepresent:

1. **The serious Drupal vulnerability mentioned in the security story** — does it match
   Drupalgeddon (SA-CORE-2014-005, October 2014), the SQL injection where the Drupal Security
   Team warned that an unpatched site should be assumed compromised within 7 hours of
   disclosure? Or was it a different advisory?
2. **The first corporate blog's name and the French vendor** — the transcript renders the name
   as something like "per comunicare"; was that the actual site name? What was the French
   vendor's custom platform called?
3. **The long-lived subsidiary site/company** — transcribed unintelligibly as "nipotino" /
   "ti inventos"; what was the actual name of the group-subsidiary site that survived for years?

## Next question pending

Asked, awaiting Fabrizio's voice/text answer:

> Nel ruolo di GenAI Architect (dal 2024), oltre a FAT2 quali altri PoC o pilot hai sviluppato o
> supervisionato, e qual è stato il più significativo dal punto di vista architetturale o di
> impatto business?

## Suggested future topics

Chronological gaps and thin spots noticed while reviewing the knowledge base, beyond what's
already been asked:

- GenAI Architect role (2024-present): other PoCs/pilots besides FAT2 (in progress above).
- Specific stories behind the other current/past projects in `knowledge/projects/` (e.g.
  `agent-starter-pack.md`, `rag-evaluator.md`, `rlm-rag.md`, `veritasloop.md`,
  `projects/past/finally-trading.md`) — most have generic descriptions and would benefit from a
  concrete origin story or technical anecdote the way NetKit and Multiblog now do.
- Any standout moment from the ~30 Drupal-era websites (a launch, a migration, a notable
  client) beyond the security angle already covered.
