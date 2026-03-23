# PPE Sentinel

PPE Sentinel is a polished PPE detection web app built for construction and industrial safety teams. It runs zero-shot object detection for people, helmets, vests, masks, and gloves, scores worker-level compliance, and can generate an executive incident summary with OpenAI.

## What you get

- Responsive desktop and mobile web experience
- Image and short-video upload flow
- Worker-level PPE compliance scoring
- Annotated evidence output
- Optional AI-generated manager summary
- Docker and Hugging Face Spaces deployment assets
- GitHub Actions test workflow

## Stack

- FastAPI for the product backend
- Grounding DINO from Hugging Face Transformers for zero-shot detection
- OpenAI Responses API for executive summaries
- Custom HTML, CSS, and JavaScript frontend

## Run locally

1. Create a Python 3.11 virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and add `OPENAI_API_KEY` if you want AI summaries. The default OpenAI report model is `gpt-5.2`.
4. Start the app with `uvicorn app.main:app --reload --host 0.0.0.0 --port 7860`.
5. Open `http://localhost:7860`.

## Deploy

### Hugging Face Spaces

1. Create a Docker Space.
2. Export the ready-to-publish Space bundle with `.\scripts\export_hf_space.ps1`.
3. Push the contents of `dist/huggingface-space` to your Space repo and set `OPENAI_API_KEY` as a Space secret.

### GitHub

- The workflow at `.github/workflows/ci.yml` runs `pytest` on push and pull request.
- Use `.\scripts\publish_github.ps1 -RepoUrl https://github.com/<your-user>/<your-repo>.git` to attach a remote and prepare the first push.

## Production notes

- This repo starts with zero-shot detection so you can launch without custom training data.
- For site-specific accuracy, use the roadmap in `docs/training-roadmap.md`.
- The publishing checklist lives in `docs/publish-checklist.md`.
