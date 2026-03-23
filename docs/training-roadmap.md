# PPE model roadmap

This app ships with a zero-shot PPE detector so you can launch without collecting private data first.

## Recommended production hardening path

1. Start with public construction-safety images and validate the zero-shot output on your target camera angles.
2. Build a labeled dataset with your exact PPE policy, site uniforms, and camera positions.
3. Fine-tune a dedicated detector once you have at least a few thousand labeled examples.
4. Keep this FastAPI app as the product layer while swapping the detector behind `app/services/detection.py`.

## What to collect before training

- Daylight and low-light shots
- High-angle CCTV and gate cameras
- Occlusions, crowding, and partial bodies
- Region-specific PPE variants like hard hats, reflective jackets, masks, and gloves

## Quality checklist

- Measure precision and recall separately for each PPE class.
- Validate on footage from sites that were not used during labeling.
- Review failure cases involving small distant workers and strong backlighting.
