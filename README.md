# Measuring what the AI hiring market actually asks for

A measured pipeline over the monthly *"Ask HN: Who is hiring?"* threads. It
answers one question I could not answer about my own field: **what do companies
hiring for AI and data roles actually ask for, and has it changed?**

Not scraped opinions. Not a survey. The raw text of what companies wrote when
they were spending money to hire.

> **Status: stages 1–6 of 7 complete. Total cost: USD 0.00.**
>
> **Live panel:** [`docs/panel/`](docs/panel/) — rebuilt automatically on the
> 2nd of every month by [`.github/workflows/mensual.yml`](.github/workflows/mensual.yml).
>
> **Headline result:** the published count of 3,909 hiring posts reproduces —
> 3,907 by hand-labelled stratified sample, 3,903 by a rules classifier — and
> nobody had verified it before. But it counts *posts*, not *companies*:
> **17% of the corpus is republished text**, so the number of distinct
> companies is about **3,048**, roughly 22% lower.
>
> Full write-up: [`docs/INFORME.md`](docs/INFORME.md) (Spanish).
> Every prediction, hit or miss: [`docs/PREDICCIONES.md`](docs/PREDICCIONES.md).

---

## Why this project exists

My previous three projects measure AI systems: an evaluation harness
(`eval-extraccion-licitaciones`), a reconciliation agent that cross-checks two
public sources (`conciliador-contrataciones`), and an adversarial audit of that
agent (`auditoria-adversarial-agente`). Together they answer *"can this model be
trusted with this task, and how do you know?"*

They share a gap: in all three, **somebody else chose the problem.** A public
procurement portal was the subject because it was there.

This project starts from the other end. The problem is picked, defined and
defended by me, from a corpus nobody handed me, and the first thing it measures
is **whether its own measurements can be believed.**

## The honest framing of the comparison

A public analysis of this same corpus was published in October 2026. It reports
**3,909 company posts and 9,194 roles across 13 threads**, structured with an
LLM. Asked in the comments whether the extraction had been validated against a
hand-checked sample, the author said it had not.

That analysis is a **reference point, not a validation target.** If my counts
differ, the default hypothesis is *not* that I am wrong — it is that the
difference has to be explained, and the explanation is a finding either way.
It also did not break out AI/ML demand as a category, which is the part I
actually need.

So the contribution is not "redo it." It is: **the same corpus, with the
extraction measured against a human ceiling, and the AI/data segment analysed.**

## Predictions are registered before each run

`docs/PREDICCIONES.md` records, before every stage: the expected number and
where the range comes from, the **failure signature** that would mean the code
is lying (as opposed to a number I simply dislike), and which decision the
result changes. If no decision changes, the run is not worth making.

Each script prints its own verdict against those ranges, so the comparison does
not depend on my memory or my convenience after seeing the data.

This is pre-registration, borrowed from experimental methodology. A result you
have already seen can be explained convincingly in hindsight; that is the thing
the file prevents.

## Why Hacker News and not LinkedIn

The threads are posted monthly by the `whoishiring` account and each top-level
comment is one company hiring. Startups, heavily remote, heavily AI — the exact
population I am targeting.

It is fetched through **Hacker News's official public Firebase API**: no key, no
rate limit, no scraping. That is a decision, not a convenience. LinkedIn
prohibits scraping in its terms and the usual sanction is suspending the
account — the same account you apply for jobs with. A corpus obtained by
breaking terms of service cannot be published or defended in an interview.

---

## The seven stages

| # | stage | what it produces | status |
|---|---|---|---|
| 1 | **Raw corpus** | every top-level post from 13 threads, stored verbatim, resumable, counted | **built** |
| 2 | **Human ceiling** | a hand-labelled sample, double-labelled blind, to measure how well *I* can do this task | **built** — `es_empresa` kappa **0.89**; `pide_ia`, `n_puestos` and `visa` fail their ceiling and are dropped |
| 3 | **Measured extraction** | structured fields per post, with per-field precision and recall against the labelled set | **built** — rules only, no LLM: kappa **0.870** on held-out, census **3,903** |
| 4 | **Unattended monthly run** | GitHub Actions cron: new thread each month, extracted, with the run log as the audit trail | **built** — `src/mensual.py`, monthly cron, commits the data and fails red on a broken run |
| 5 | **The AI/data segment** | what those companies ask for, and how it moved across 13 months | **built, and the answer is "cannot be determined"** — the +0.92 pts/month trend does not survive the measured survivorship confound |
| 6 | **Published panel** | the numbers, with the measurement error shown next to each one | **built** — `docs/panel/` |
| 7 | **Self-drift detection** | the pipeline flagging when its own accuracy degrades on new months | **partial** — health checks catch breakage; with 12 months of history the 3σ band only fires above 7.1% meta-comments, and the panel says so instead of hiding it |

Stage 2 comes before stage 3 on purpose. **You cannot report extraction accuracy
without a ceiling to measure it against**, and in the first project that ceiling
turned out not to be a single number — it split by document format, 98.7% versus
72.7%. The global figure was a comfortable lie.

## What the measurement found

| | |
|---|---|
| hiring posts, hand-labelled sample | **3,907** [3,804, 3,977] |
| hiring posts, rules classifier | **3,903** |
| distinct companies | **~3,048** |
| published analysis reports | 3,909 |
| registered predictions hit | **2 of 19** |
| cost | **USD 0.00** |

Three findings that were not in the plan:

1. **A blind double pass measures whether a labeller repeats himself, not
   whether he is right.** One company was mislabelled four times, identically —
   perfect agreement, perfect error. 9 of 266 reference labels (3.4%) were
   wrong, all in the same direction, and the double pass found only 2 of them.
2. **17% of the corpus is republished text.** That turns the corpus into a
   free consistency instrument the design never planned for: identical text
   with opposite labels is a guaranteed error, no second annotator required.
3. **A significant trend that cannot be claimed.** AI vocabulary in hiring
   posts rises +0.92 points/month (t=3.49) — a headline most dashboards would
   publish. Newer threads lose more posts to deletion, and a deleted post has
   no text to check. Assume *no* deleted post mentioned AI and the slope falls
   to +0.34 (t=1.23, not significant). The panel draws both lines.
4. **No LLM was needed.** A 180-line deterministic classifier lands inside the
   human interval. The decision rule for that was registered in advance.

## What is built

```
src/bajar.py        fetch the corpus (stdlib only, no key, no LLM)
docs/PREDICCIONES.md   predictions registered before each run
data/hilos.json     the threads found, with their post counts
data/posts.jsonl    one line per company post, append-only, resumable
```

```bash
python src/bajar.py --listar     # find the threads only (~120 calls, seconds)
python src/bajar.py              # fetch everything, resumable
```

No dependencies: stage 1 is Python standard library only. There is nothing to
install and nothing to pay for.

The fetcher is resumable because it makes roughly 4,000 requests, and
append-only because of a bug I shipped in the previous project: a results file
opened in `"w"` mode destroyed two completed rounds of attack data. Audit logs
are append-only, which that project's own README explains — and which I then
violated in its code.

## What it does not do yet

- Nothing is extracted. No structured fields, no counts by technology, no trend.
- No accuracy claim exists, because the labelled set does not exist yet.
- One corpus, one source. Hacker News startups are not the whole market, and
  any finding here is a finding about **this population**, not about hiring.
- The monthly run is designed, not running.

---

## Repository conventions

Organised by function, not by stage — `src/`, `data/`, `docs/`, `reports/` —
matching the other three repositories. Stage folders duplicate code and age
badly; the stage lives in the filename and in `docs/PREDICCIONES.md`.

Code comments and working notes are in Spanish, as in the other repositories.
The README is in English.
