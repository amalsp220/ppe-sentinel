# Publish checklist

## GitHub repository

1. Create an empty GitHub repository.
2. Run:
```powershell
.\scripts\publish_github.ps1 -RepoUrl https://github.com/<your-user>/<your-repo>.git
```
3. Push with:
```powershell
git push -u origin main
```

## Hugging Face Space

1. Create a new Docker Space on Hugging Face.
2. Add `OPENAI_API_KEY` as a secret if you want AI summaries.
3. Export a Space-ready bundle:
```powershell
.\scripts\export_hf_space.ps1
```
4. Publish the exported bundle:
```powershell
.\scripts\publish_hf_space.ps1 -SpaceRepoUrl https://huggingface.co/spaces/<your-user>/<space-name>
```

## Notes

- The Space bundle is generated into `dist/huggingface-space`.
- The first model load downloads Grounding DINO, so the initial boot can be slower than later runs.
