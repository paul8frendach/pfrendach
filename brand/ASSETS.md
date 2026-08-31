# Asset inventory

All production files are RGBA PNG (true transparency unless the name says `on-ink` / `on-bone`) or SVG. Do not use the bowl / v2 experiment folders.

## Mark (vector)

| File | Use |
|---|---|
| `marks/pf-house.svg` | Master. Bone fill. Header, favicon source. |
| `marks/pf-house-ink.svg` | Ink fill for light grounds. |
| `marks/pf-house-gold.svg` | Gold metal state only. |

ViewBox ~ 1830×1665. Cropped to the fused ꟼF.

## Mark (raster, 1122×1008)

| File | Ground |
|---|---|
| `pf-house-bone.png` | Transparent, bone ink |
| `pf-house-ink.png` | Transparent, ink |
| `pf-house-gold.png` | Transparent, gold |
| `pf-house-bone-on-ink.png` | Flattened preview |
| `pf-house-ink-on-bone.png` | Flattened preview |
| `pf-house-gold-on-ink.png` | Flattened preview |
| `pf-watermark.png` | Low-opacity mark |

## Signatures (high-res, use scaled down)

| File | Size | What |
|---|---|---|
| `pf-signature-bone.png` | 7886×1206 | ꟼFrendach, transparent |
| `pf-signature-ink.png` | 7886×1206 | Ink on clear |
| `pf-signature-gold.png` | 7886×1206 | Gold on clear |
| `pf-signature-*-on-ink.png` / `*-on-bone.png` | 7886×1206 | Flattened |
| `pf-signature-sub-bone.png` | 7886×1502 | + CREATE · BUILD · TRAIN |
| `pf-signature-sub-on-ink.png` | 7886×1502 | Same, on ink |
| `pf-paul-signature-bone.png` | 9473×1206 | PAUL ꟼFrendach |
| `pf-paul-signature-on-ink.png` | 9473×1206 | On ink |
| `pf-paul-signature-sub-on-ink.png` | 9473×1502 | + subtitle |

## Other lockups

| File | Size | What |
|---|---|---|
| `pf-lockup-bone.png` | 1559×217 | Mark + PAUL FRENDACH |
| `pf-lockup-ink.png` | 1559×217 | Ink |
| `pf-lockup-stacked-bone.png` | 1291×403 | Stacked spelled |
| `pf-wordmark-bone.png` | 1438×218 | Spelled wordmark |

## Chrome / apps

| File | Size |
|---|---|
| `pf-app-icon-1024.png` | 1024² dark |
| `pf-app-icon-light-1024.png` | 1024² light |
| `pf-app-icon-180.png` | 180² |
| `pf-avatar-512.png` / `1024` / `2000` | Square |
| `pf-avatar-circle-1024.png` | Round |
| `pf-banner-1500.png` | 1500×500 |
| `pf-nav-dark.png` / `pf-nav-light.png` | 1600×96 references |
| `pf-header-bar.png` | 1400×120 |
| `pf-colors.png` | 1400×420 palette board |
| `pf-clearspace.png` | Clearspace diagram |
| `pf-size-proof.png` | Size ladder |

## Motion

| File | Spec |
|---|---|
| `flash/intro.mp4` | 10.00s · 1920×1080 · 25fps · H.264 yuv420p · silent · faststart |
| `flash/outro.mp4` | Same. Starts on intro’s last pose. |

## Type

| File | Use |
|---|---|
| `fonts/Fraunces_72pt-Regular.ttf` | Mark, RENDACH, headlines |
| `fonts/Fraunces_72pt-SemiBold.ttf` | Optional spelled name |

Live web: Google Fraunces variable, opsz 72, wght 400.

## Verified

- Every `pf-*.png` in `marks/` is RGBA.
- Intro and outro decode to exactly 250 frames / 10.00s / 1920×1080.
- SVG masters open and render the fused ꟼF in bone / ink / gold.
