---
title: Template Final Assignment
emoji: 🕵🏻‍♂️
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.25.2
app_file: app.py
pinned: false
hf_oauth: true
# optional, default duration is 8 hours/480 minutes. Max duration is 30 days/43200 minutes.
hf_oauth_expiration_minutes: 480
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

## GAIA Agent

An OpenAI function-calling agent for the GAIA Unit 4 leaderboard.

### Setup
In your Space, add a **Secret** (Settings → Variables and secrets):
- `OPENAI_API_KEY` — required.
- `OPENAI_MODEL` — optional, defaults to `gpt-4o` (needs vision for image tasks).

Then log in with the HF button and click **Run Evaluation & Submit All Answers**.

### ZeroGPU
The Space runs on ZeroGPU hardware. Inference is done via the OpenAI API (remote),
so no local GPU is used and the submit function is intentionally **not** wrapped in
`@spaces.GPU` — that decorator caps a call at ~60s, and evaluating all 20 questions
takes minutes. The `spaces` package is included only for ZeroGPU runtime compatibility.

### Structure
```
app.py                 # Gradio UI + fetch/run/submit loop (template, minimally edited)
agent/
  gaia_agent.py        # GaiaAgent: the OpenAI tool-calling loop + answer extraction
  prompts.py           # GAIA system prompt (exact-match formatting rules)
agent_tools/
  __init__.py          # tool registry + dispatch
  web.py               # web_search, visit_webpage
  files.py             # read_file (text/CSV/Excel) for attached task files
  media.py             # transcribe_audio (Whisper), analyze_image (vision)
  python_exec.py       # run_python (calculations)
```