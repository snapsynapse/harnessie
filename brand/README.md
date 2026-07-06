# Brand source assets

High-resolution originals for the Harnessie mascot. This folder is at the repo root, not under `docs/`, so GitHub Pages never serves it: these are working sources, and the web-optimized derivatives that ship live under `docs/imgs/`.

| Source | What it is | Derived, served asset |
|---|---|---|
| `harnessie2.png` | Chosen mascot badge, 1567x1536. Selective color: a green harnessed Nessie on a black line-art loch scene. | `docs/imgs/harnessie-mark.png` (512px, circular-cropped, 361KB) used by the nav avatar, the 404 mark, and as the video poster/fallback. |
| `harnessie_og.mp4` | Source hero animation, 1280x720, 10s, with an audio track. | `docs/imgs/harnessie-hero.mp4` (audio stripped, `+faststart`, re-encoded 2.66MB to 890KB) used as the homepage hero. |

`docs/imgs/og.png` (the 1200x630 social card) was generated with Gemini from the prompt in `working/og-image-prompt.md`, then quantized to a 256-color palette (1.03MB to 433KB).

A flat fully-colored badge variant was considered and dropped in favor of `harnessie2.png`.

## Regenerating a derivative

```bash
# circular web mark from the badge source
sips -Z 512 brand/harnessie2.png --out docs/imgs/harnessie-mark.png

# web-optimized hero clip from the source video (strip audio, faststart)
ffmpeg -y -i brand/harnessie_og.mp4 -an -c:v libx264 -crf 27 -preset veryslow \
  -pix_fmt yuv420p -movflags +faststart docs/imgs/harnessie-hero.mp4
```
