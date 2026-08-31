# Sting spec — 10s intro / 10s outro

Clockwork logo flash. Elegant, mechanical, not a kinetic-type circus.

## Files

- `flash/intro.mp4` — REST → HOLD
- `flash/outro.mp4` — HOLD → REST

Play intro then outro. They share the HOLD pose (mirrored P locked to F, RENDACH in, subtitle up, gold glow).

## HOLD (locked)

Centered **ꟼFrendach**. One mirrored P. F overlapped −0.32em (house mark). RENDACH on the same baseline. Subtitle `CREATE · BUILD · TRAIN` under, ≥ 0.28 cap. Gold drop-shadow ~18px at 32% on the word.

## REST

Centered **PAUL**. P unflipped. AUL in. No F. No subtitle.

## Intro timeline (seconds)

| t | What |
|---|---|
| 0.00 | REST |
| 0.38–1.0 | P, then A, U, L seat from above (tiny travel, damped). PAUL centered. |
| 1.0–2.9 | Hold PAUL. Clockwork running. |
| 2.88–3.55 | AUL leaves as a group. Width collapses. P stays. |
| 3.35–5.20 | P `rotateY` 0→180, driven by slider-crank travel. Nothing else moves. |
| 5.25–5.85 | FRENDACH slot opens. Group recenters: P slides left, word stays on the page center. F still invisible. |
| 5.92 | F seats into the P (overlap already in the layout). No x-slide through the P. |
| 6.04–6.46 | R, E, N, D, A, C, H tick in L→R, small rise. |
| 5.7–6.5 | Gold glow on the lockup. |
| 7.0–7.8 | Subtitle in. |
| 9.95 | HOLD |

## Outro

Reverse: RENDACH out, F out, slot closes, P unflips, AUL returns, all rest. P does not get redrawn.

## Clockwork (always on, under type)

- Balance wheel ~1 Hz, pallet, 15-tooth escape, 16/10 gear train, slider-crank (r=26, rod=70).
- Gold hairlines, opacity 0.16–0.7, on ink.
- Chapter ring, 60 ticks. Pulse the current tick 90ms.
- Gears in the corners / vignette. Never across the word.

## Implementation notes

Live component: `src/components/logo-flash.tsx`  
Styles: `.flash-*` in `src/styles.css`  
Routes: `/flash?v=intro` · `/flash?v=outro` · `/` loops both.

CSS variables on `.flash-word`:
- `--aul` 1→0 as AUL width
- `--mark` 0→1 as FRENDACH width
- F overlap: `margin-left: calc(var(--mark) * -0.32em)`
- PAUL optical tighten: `margin-right: calc(var(--aul) * -0.06em)` on the P

One DOM P. AUL row and mark row are width-animated flex children. The lockup is shrink-wrapped and flex-centered, so PAUL and ꟼFrendach are both page-centered.

`prefers-reduced-motion`: snap to HOLD.

## Do not

- Two P’s
- F fading through P
- Right-aligned ꟼFrendach
- Letters from opposite verticals at once (too noisy — rejected)
- Horizontal type slide as the main move
