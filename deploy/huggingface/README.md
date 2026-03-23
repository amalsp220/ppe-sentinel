---
title: PPE Sentinel
emoji: 🦺
colorFrom: amber
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# PPE Sentinel

Upload construction photos or short videos to detect workers, helmets, vests, masks, and gloves.

## Space secrets

- `OPENAI_API_KEY`

## Notes

- The first run downloads the zero-shot detection model from Hugging Face.
- For production usage, keep videos short and enable persistent storage if you want artifact history.
