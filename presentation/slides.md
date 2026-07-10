---
marp: true
theme: framewise
paginate: true
size: 16:9
---

<style>
/* @theme framewise */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

:root {
  --bg: #0a0e1a;
  --bg-2: #0f1729;
  --fg: #e8ecf6;
  --muted: #8b95ad;
  --blue: #60a5fa;
  --cyan: #22d3ee;
  --purple: #a78bfa;
  --green: #34d399;
  --orange: #fbbf24;
}

section {
  background: radial-gradient(circle at 15% 10%, #132038 0%, var(--bg) 55%), var(--bg);
  color: var(--fg);
  font-family: 'Inter', system-ui, sans-serif;
  padding: 56px 72px;
  font-size: 26px;
}

h1 {
  font-size: 52px;
  font-weight: 800;
  color: var(--cyan);
  margin: 0 0 4px 0;
  letter-spacing: -0.02em;
}

h2 {
  font-size: 32px;
  font-weight: 700;
  color: var(--fg);
  border-bottom: 2px solid #1f2a44;
  padding-bottom: 14px;
  margin-bottom: 26px;
}

h3 { color: var(--blue); font-size: 22px; }

p, li { color: var(--fg); line-height: 1.5; }
strong { color: var(--cyan); font-weight: 700; }
em { color: var(--muted); font-style: normal; }

a { color: var(--blue); }

code {
  background: #14203a;
  color: #7dd3fc;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.85em;
}

pre {
  background: #0d1526;
  border: 1px solid #1f2a44;
  border-radius: 10px;
  padding: 18px 22px;
}
pre code { background: none; color: #cbd5e1; padding: 0; }

.kicker {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--muted);
  font-size: 16px;
  font-weight: 600;
}

.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 18px;
  font-weight: 700;
  font-size: 18px;
  margin: 4px 8px 4px 0;
  border: 1px solid;
}
.b-formal { color: var(--blue); border-color: var(--blue); background: rgba(96,165,250,0.08); }
.b-sarcastic { color: var(--orange); border-color: var(--orange); background: rgba(251,191,36,0.08); }
.b-tech { color: var(--purple); border-color: var(--purple); background: rgba(167,139,250,0.08); }
.b-nontech { color: var(--green); border-color: var(--green); background: rgba(52,211,153,0.08); }

table { font-size: 21px; border-collapse: collapse; width: 100%; background: transparent !important; }
tr, tr:nth-child(2n), tr:nth-child(odd), tr:nth-child(even) {
  background-color: transparent !important;
  border-top: 1px solid #1a2338 !important;
}
th { color: var(--cyan); text-align: left; border-bottom: 2px solid #1f2a44; padding: 8px 14px; background: transparent !important; }
td { padding: 8px 14px; color: var(--fg); background: transparent !important; }

.cols { display: flex; gap: 36px; }
.col { flex: 1; }

.card {
  background: #101a30;
  border: 1px solid #1f2a44;
  border-radius: 12px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.card h3 { margin: 0 0 6px 0; }
.card p { margin: 0; color: var(--muted); font-size: 21px; }

.pipe {
  display: flex; align-items: center; justify-content: space-between;
  margin: 30px 0;
}
.pipe .step {
  background: #101a30; border: 1px solid #1f2a44; border-radius: 10px;
  padding: 14px 18px; text-align: center; flex: 1; font-weight: 600; font-size: 20px;
}
.pipe .arrow { color: var(--muted); font-size: 26px; padding: 0 10px; }

.footline { color: var(--muted); font-size: 19px; margin-top: 18px; }

section.title { justify-content: center; }
section.title .kicker { font-size: 18px; }
section.title h1 { font-size: 68px; margin-top: 10px; }
section.title h2 { border: none; font-size: 30px; font-weight: 600; color: var(--muted); }

.quote {
  border-left: 3px solid var(--blue);
  padding-left: 20px;
  color: var(--muted);
  font-size: 22px;
  font-style: italic;
}

.small { font-size: 20px; color: var(--muted); }
.center { text-align: center; }
</style>

<!-- _class: title -->

<span class="kicker">AMD Developer Hackathon &middot; ACT II &middot; Track 2</span>

# FrameWise

## Multi-Style Video Captioning Agent

<br>

<span class="badge b-formal">&#9679; formal</span><span class="badge b-sarcastic">&#9679; sarcastic</span><span class="badge b-tech">&#9679; humorous_tech</span><span class="badge b-nontech">&#9679; humorous_non_tech</span>

<p class="footline">One clip in. Four voices out — every caption grounded in what's actually on screen.</p>

---

## The Brief

Track 2 hands the agent a list of video clips and asks it to caption each one — in **multiple distinct tones** — without inventing anything that isn't visible.

<div class="cols">
<div class="col">

**Input** — `/input/tasks.json`
```json
{
  "task_id": "v2",
  "video_url": "https://.../kitten.mp4",
  "styles": ["formal", "sarcastic",
    "humorous_tech", "humorous_non_tech"]
}
```

</div>
<div class="col">

**Output** — `/output/results.json`
```json
{
  "task_id": "v2",
  "captions": {
    "formal": "...",
    "sarcastic": "...",
    "humorous_tech": "...",
    "humorous_non_tech": "..."
  }
}
```

</div>
</div>

---

## What We Built

A small, provider-agnostic agent that turns a clip URL into four grounded, on-tone captions — packaged as a container that runs anywhere.

<div class="pipe">
  <div class="step">download<br><span class="small">clip via URL</span></div>
  <div class="arrow">&#8594;</div>
  <div class="step">observe<br><span class="small">native video or sampled frames</span></div>
  <div class="arrow">&#8594;</div>
  <div class="step">caption<br><span class="small">1 call &rarr; all 4 styles as JSON</span></div>
  <div class="arrow">&#8594;</div>
  <div class="step">validate<br><span class="small">contract self-check</span></div>
</div>

<p class="footline">main.py orchestrates · providers.py adapts the model · media.py handles download/frames · validation.py enforces the contract</p>

---

## The Pivot: External &gt; Local

The original design baked **Qwen2.5-VL-3B + a ROCm/torch stack** into the image for on-device inference. We ripped it out.

<div class="quote">
"The judge VM's hardware is unknown, so betting the whole entry on a local GPU model is a single point of failure — a missing or incompatible GPU means every caption is empty and the score is zero."
</div>

<br>

| | Local model (v1 design) | Hosted vision API (shipped) |
|---|---|---|
| Hardware bet | Needs a compatible AMD GPU | None — runs on any host |
| Image size | GBs of ROCm/torch/weights | Slim Python + ffmpeg |
| Cold start | Model load | Seconds |
| Caption quality | Bounded by 3B model | Frontier hosted models |

---

## Provider Abstraction

`CAPTION_PROVIDER` env var swaps the backend — **no code change**, same output contract.

| Provider | Input | SDK | Default model |
|---|---|---|---|
| **gemini** *(default)* | native video (Files API) | `google-genai` | `gemini-2.5-flash` |
| **openai** | sampled frames | `openai` | `gpt-4o` |
| **anthropic** | sampled frames | `anthropic` | `claude-sonnet-5` |

- One `CaptionProvider` protocol, one method: `caption_clip(path, duration, styles)`
- Gemini gets the whole clip natively — best temporal grounding
- OpenAI/Anthropic reuse the same ffmpeg frame sampler: rate-based (one frame every 4s, capped at 30), downscaled to 512px — a single ffmpeg pass, not one process per frame

---

## One Call, Four Styles

Every clip costs **exactly one model call** — the prompt asks for all requested styles at once as strict JSON, so every caption is grounded in the same observation.

<div class="cols">
<div class="col">

```text
You are shown a short video clip.

First, silently observe: setting,
subjects, actions, objects, motion.

Then write ONE caption per style —
faithful to what's visible, no
invented details.

Respond with ONLY a JSON object
mapping each style to its caption.
```

</div>
<div class="col">

<span class="badge b-formal">formal</span><br>Professional, objective, factual.

<span class="badge b-sarcastic">sarcastic</span><br>Dry, ironic, lightly mocking.

<span class="badge b-tech">humorous_tech</span><br>Funny, code/IT-culture references.

<span class="badge b-nontech">humorous_non_tech</span><br>Funny, everyday analogies, zero jargon.

</div>
</div>

---

## Reliability by Design

The agent never guesses. It either produces a real, grounded caption — or it fails loudly.

<div class="card">
<h3>Fail fast on setup</h3>
<p>Unknown provider or missing API key raises before a single task is touched.</p>
</div>

<div class="card">
<h3>No fabrication</h3>
<p>A failed clip gets empty captions, not made-up ones — the run exits non-zero so the failure is visible, never silent.</p>
</div>

<div class="card">
<h3>Bounded retries</h3>
<p>2 retries with backoff per request, 25s timeout — under the 30s per-request budget.</p>
</div>

<div class="card">
<h3>Contract self-check</h3>
<p><code>validation.py</code> verifies <code>results.json</code> is a well-formed array, one entry per task, non-empty string per requested style — enforced by both the runtime and the tests.</p>
</div>

---

## Ship It: Docker &amp; CI

<div class="cols">
<div class="col">

**Image**
- `python:3.11-slim` + `ffmpeg`
- No ROCm, no GPU libs, no baked weights
- Well under the 10 GB compressed cap
- Optional `BAKE_PROVIDER_KEY` build-arg for judges who can't inject env vars *(runtime `-e` always wins)*

</div>
<div class="col">

**CI/CD**
- GitHub Actions builds + publishes on every push to `main` and every `v*` tag
- Target: `ghcr.io/akay7/framewise`
- Tags: `latest`, branch name, `sha-<commit>`, semver

```bash
docker run --rm \
  -e CAPTION_PROVIDER=gemini \
  -e GEMINI_API_KEY=... \
  -v tasks.json:/input/tasks.json:ro \
  -v ./out:/output \
  ghcr.io/.../framewise
```

</div>
</div>

---

## Tested at Two Speeds

<div class="cols">
<div class="col">

**Fast** — no Docker, no network, no keys
- `test_contract.py` — validates good/bad `results.json` fixtures against the output contract
- `test_providers.py` — stubs the SDKs to check provider selection, missing-key / unknown-provider errors, style parsing

```bash
python -m pytest tests/test_contract.py \
  tests/test_providers.py
```

</div>
<div class="col">

**End-to-end** — real container, real provider
- Runs the built image against a fixture task
- Asserts exit 0 and a contract-satisfying `results.json`
- Opt-in via `RUN_E2E=1` (needs Docker + network + a valid key)

```bash
RUN_E2E=1 CAPTION_PROVIDER=gemini \
  GEMINI_API_KEY=... \
  python tests/run_e2e.py
```

</div>
</div>

<p class="footline">Test code lives in <code>tests/</code>, excluded from the Docker build context — never counts against the image size cap.</p>

---

## Bonus: Still Runs Fully Local

Dropping the *baked-in* model didn't mean dropping local inference as an option — it means it's no longer the load-bearing bet.

The `openai` adapter targets **any OpenAI-compatible server** via `OPENAI_BASE_URL` — including [Lemonade](https://lemonade-server.ai/) serving a vision model (e.g. Qwen2.5-VL) on your own machine.

```bash
lemonade-server serve
CAPTION_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:13305/api/v1 \
OPENAI_MODEL=<vision-model> \
python3 main.py
```

<p class="footline">Same code path as vLLM, LM Studio, or Ollama — swap the URL and model, nothing else changes.</p>

---

## See It In Action

Same three clips, four voices each — one model call per clip.

<div class="card">
<h3>v2 &middot; kitten walking through a garden</h3>
<p><strong>formal:</strong> "A small orange tabby kitten emerges from behind green foliage and walks forward through the branches toward the camera."</p>
<p><strong>humorous_tech:</strong> "The kitten.init() process finally completed boot-up and is now slowly walking toward the user."</p>
</div>

<div class="card">
<h3>v3 &middot; woman working at a desk</h3>
<p><strong>sarcastic:</strong> "Ah yes, nothing says 'productive work environment' quite like a bowl of charging-cable spaghetti."</p>
<p><strong>humorous_non_tech:</strong> "The charging cords are doing their best impression of an unmade bed — tangled, sprawling, unbothered."</p>
</div>

---

## Try It Yourself: Live Demo

The same pipeline, behind a URL — no Docker, no CLI, nothing to install.

<div class="cols">
<div class="col">

**Two tabs, one pipeline**
- **Single video** — upload a file or paste a URL, pick styles, caption it
- **Batch** — upload a `tasks.json` shaped like `sample_tasks.json`, get a downloadable `results.json`
- Built on `app.py`, a thin Gradio UI over the exact same `providers.py` / `main.run_tasks` the container uses

</div>
<div class="col">

**Bring your own key**
- Pick a provider, paste your own API key — used only in-memory for that request, never stored or logged
- No shared demo key to exhaust or leak
- `openai` also accepts a custom Base URL/Model, so you can point the demo at your own local server (Lemonade, vLLM, ...)

</div>
</div>

<p class="footline center">Live now: framewise-demo.onrender.com — Render free tier, Docker</p>

---

<!-- _class: title -->

<span class="kicker">Status</span>

# v3.0 &middot; Ready for Judging

<p class="small">Provider-agnostic &middot; hardware-independent &middot; contract-enforced &middot; CI-published</p>

<br>

<div class="pipe">
  <div class="step">🎯 no GPU bet</div>
  <div class="step">🔌 3 swappable providers</div>
  <div class="step">✅ self-validating output</div>
  <div class="step">📦 &lt;&lt; 10GB image</div>
</div>

<p class="footline center">github.com/Akay7/FrameWise</p>
