# Paul Frendach — first prompt for Claude

Paste this entire file as the project’s first message. Build **paulfrendach.com** from it. Do not invent honors, clients, family detail, or a new logo.

Companion files in this pack: `START_HERE.md` · `STING.md` · `ASSETS.md` · `DOCTRINE.md` · `tokens.css` · `marks/` · `flash/` · `fonts/`.

You are helping Paul Frendach ship a personal brand site with **three worlds under one house mark**. The mark, color, type, voice, and sting are locked. Your job is the site: chrome, three rooms, content, motion using the files in this pack.

---

## Who he is

Paul Frendach. Dunkirk / Waldorf, Maryland. Youngest of four. Played soccer all growing up, then college. DeMatha Catholic — central midfielder. Club: Baltimore Celtic. College: Maryland (2018 NCAA championship roster), then Temple (starter, captain).

Favorite player growing up: Ronaldinho. Joy is not the opposite of standards.

He knows what it is to be hungry. He turned to soccer because it offered **order when the rest of life did not**. Family weather. The field as the place things made sense. Say that clean. Do not trauma-dump. Do not invent private detail.

He has been the best on teams and he has been the one watching. That is why the bench and the climb are both in the voice.

He is a little eccentric / unique. The brand should feel human-made, not AI-smooth. Minimal. Radiant. State of the art without looking like a template.

**Honor line — not locked.** Public-safe for now: Gatorade nominee, Celtic national-level run, Maryland State Cup, Maryland 2018 NCAA champions (limited minutes that season), Temple captain. He has also mentioned a USYS national title, a second State Cup, and Gatorade Player of the Year 2018. **Do not print the unlocked items until he confirms.**

---

## The house vs the three worlds

One person. One mark. Three trades.

| Layer | Name | Job |
|---|---|---|
| House | **Paul Frendach** | The person. Persistent chrome, logo, type, ink/bone. |
| Create | **Vision Oasis** | Content / cinema / stills. The lens. |
| Build | Web development | Sites, interfaces, brand pages. |
| Train | **FRENDACH** | Soccer training. The session. |

Rules:
- The house logo **never** changes between tabs.
- Primary wordmark is **ꟼFrendach**: the house mark (mirrored P back-to-back with F) plus **RENDACH**, set as one word. The F in the mark *is* the F in Frendach.
- FRENDACH is the soccer name. Not “Paul Frendach Training.” Not Academy / Elite / FC.
- Vision Oasis is the film house, credited on the work, not the training mark and not the personal name.
- Worlds have unique accent, imagery, and rhythm. They share layout chrome.
- He will take few clients and prioritize content: training, coaching tips, fun moments, cinematic moments, the essence of soccer as an American who played in college.

---

## House logo (LOCKED — do not redesign)

**Do not invent a new logo. Do not use a geometric PF block. Do not put a ball, shield, outline, or gold pip in the letters.**

Construction (source of truth = `marks/pf-house.svg`):

1. Typeface: **Fraunces**, optical size **72**, weight **400 (Regular)**. Axes: `opsz 72, wght 400, SOFT 0, WONK 0`.
2. Capital **P** mirrored (`transform: scaleX(-1)` or `rotateY(180deg)`), back-to-back with capital **F**.
3. Stems share one column. Optical overlap **−0.32em** on the F (or `margin-right: -0.32em` on the mirrored P). One spine. Not fat.
4. **RENDACH** in the same Fraunces Regular, same cap height, same baseline.
5. Gap from the F’s rightmost arm to the **R**: **0.05em**. Tight, not touching.
6. Tracking on RENDACH: **0.02em**.
7. Color default: Bone `#F4F1EA` on Ink `#0B0D0C`. Ink on Bone paper. Gold `#E8C36A` is a rare metal state, not the default.
8. Worlds do **not** recolor the mark. They only change `--accent`.

Live header (copy this):

```html
<a class="sig" href="/">
  <img src="/marks/pf-house.svg" alt="" />
  <span>RENDACH</span>
</a>
```

```css
.sig {
  display: flex;
  align-items: flex-end;
  gap: 0.05em;
  font-family: "Fraunces", ui-serif, Georgia, serif;
  font-weight: 400;
  font-optical-sizing: auto;
  font-variation-settings: "opsz" 72, "wght" 400, "SOFT" 0, "WONK" 0;
  font-size: 28px;
  line-height: 0.9;
  letter-spacing: 0.02em;
  color: #F4F1EA;
  text-decoration: none;
}
.sig img { height: 1.14em; width: auto; display: block; translate: 0 0.02em; }
```

If you set the mark in live type instead of the SVG:

```css
.mark { font-family: Fraunces, serif; font-weight: 400; line-height: 0.9; }
.mark .p { display: inline-block; transform: scaleX(-1); margin-right: -0.32em; }
```

Prefer the SVG master in chrome so the stem never double-draws.

### Lockups (use these, in this order)

1. **Signature** — ꟼFrendach (mark + RENDACH). Header, hero, footer. `pf-signature-*.png`
2. **Paul signature** — small PAUL to the left, then ꟼFrendach. About / formal. `pf-paul-signature-*.png`
3. **Mark alone** — avatar, favicon, app icon. `pf-house.svg` / `pf-house-bone.png`
4. **Spelled lockup** — mark beside PAUL FRENDACH. Secondary.

Subtitle `CREATE · BUILD · TRAIN` is always **below** the name, never on it. Gap under the name ≥ **0.28 of cap height**.

Minimum mark height **24px**. Clearspace: **1/8 of mark height**.

---

## Color tokens

```
INK       #0B0D0C    page, chrome
INK-2     #161816    cards
BONE      #F4F1EA    type on dark, paper on light
BONE-DIM  #C9C3B6    lead text
GOLD      #E8C36A    house metal + Train accent
GLOW      #C6E04A    Create accent only
STEEL     #8FB4C4    Build accent only
MUTED     #8A8578    meta
```

Glow and Steel never enter the logo. They only tint the active world (tab pill, rules, kicker, card edge).

---

## Type

- **House / display / logo / headlines:** Fraunces (display optical size). Regular for the mark. 500–600 only if you spell PAUL FRENDACH in full as a separate line.
- **UI / body / tabs:** Outfit (or another quiet humanist sans). Not Anton in the house chrome.
- **Train world only, inside soccer artifacts / merch:** Anton for a FRENDACH merch word, Oswald for soccer headlines, Montserrat for soccer body. That kit stays inside Train. Never in the site header.

Google Fonts:

```
Fraunces: opsz,wght,SOFT,WONK@72,400..700,0,0
Outfit: wght@300..600
```

A Regular cut also ships in `fonts/Fraunces_72pt-Regular.ttf`.

---

## Train world — FRENDACH doctrine (locked)

**Descriptor:** Soccer Training  
**Tagline:** Love the process.  
**Mission:** Train players who love the game enough to become themselves inside it.  
**Who:** Small roster. High school first. Few clients, full attention. Film is part of the method.

Belief, in his words (compress, do not flatten):

You spend time doing things that you love. Therefore when you apply yourself to training and sports, you must love it. That means having fun, getting frustrated, winning, achieving goals, discovering who you are as a soccer player, playing the athletic mind and body together, learning to enjoy the process and believe in yourself. Accomplishment / identity.

Once you get older and around better players, the margin for technical difference becomes minuscule. The mental area of the game — playing with freedom in tense situations — is what separates one. That, paired with knowing this is just a game and a tool used to develop you in your life. Use it like so. No getting high on the highs. No getting too down on yourself in the lows. This is all part of the process. When you choose to love it, you choose to accept these moments, good or bad, as what makes you better in more facets of life than just health and accomplishment.

### The Seven Laws
1. **Order** — the session is where chaos can be put down.
2. **The Next Team** — Mother’s Law.
3. **Touches** — the hours the team does not see. Touches, touches, touches. They build mental awareness like nothing else.
4. **Body / Ball** — how the ball feels, how to strike it, what direction the spin is. A player has to know how his body and the ball relate.
5. **The Margin** — at the top, technique evens out; freedom under tension does not.
6. **A Tool** — a game used to build a life, not just a body and a trophy.
7. **The Weather** — no high on the highs, no collapse on the lows. Love means you accept both.

### Mother’s Law (her wording)
Once you are the best on the team, it is getting to be time to go — to the next best team in the area. Be the best in the neighborhood first. The country second. You are a player inside a large pool. Know the next step. Rise to the top of this one. Move. Repeat. Continually train in the off hours that you aren’t with your team.

### Voice
Direct. Warm. A little strange. Cinematic. Honest about the bench. Hungry without bitter.  
Not bro-coach. Not corporate academy. Not recruiting spam. Not motivational poster. Not AI-smooth.

Lines that can be said out loud:
- Once you are the best on the team, it is getting to be time to go.
- Touches in the hours nobody scheduled.
- Around better players the technique evens out. The mind does not.
- Do not get high on the highs. Do not get too low on the lows.
- When you choose to love it, you choose the weather.
- This is a game. Use it to build a life.

---

## Create world — Vision Oasis

Cinema first. Useful second. Never stock. Session films, stills, lookbooks, brand film. Same taste as the training films. Credit Vision Oasis in descriptions. Do not put VO on the house mark or the FRENDACH soccer mark.

Accent: GLOW `#C6E04A`. Feel: night, grain, breath, walk-off.

Content he wants to make: soccer training, coaching tips, fun moments, cinematic moments.

---

## Build world — Web

Quiet pages. Sharp objects. Personal brands and small companies. Design-to-build in one hand. No template sludge. The house mark sits in the chrome of every property he ships.

Accent: STEEL `#8FB4C4`. Feel: precise, cooler, still elegant. Fraunces stays.

---

## Sting (intro / outro)

Two 10-second 1920×1080 H.264 files. Silent. They join on the same pose.

Files: `flash/intro.mp4`, `flash/outro.mp4`.

| File | Starts | Ends |
|---|---|---|
| intro.mp4 | REST — centered PAUL | HOLD — centered ꟼFrendach + subtitle |
| outro.mp4 | HOLD | REST |

Motion (intro):
1. **PAUL** drops in from above, centered. One P. Natural tracking.
2. Hold so it can be read.
3. **AUL** leaves as a group.
4. That same **P** throws (`rotateY` 0→180), crank-driven. Nothing else moves.
5. Slot for FRENDACH opens; the P slides left so the finished word stays page-centered.
6. **F** seats into the mirrored P (overlap −0.32em — the house mark). No ghosting, no second P.
7. **RENDACH** ticks in left-to-right, small vertical travel, like type seating.
8. Subtitle `CREATE · BUILD · TRAIN` fades. Gold glow on the lockup.

Clockwork under the type: balance wheel, escapement, gear train, slider-crank. Gold hairline on ink. Vignette. Do not put gears on the letters.

Outro is the reverse. Loop = intro then outro.

Live implementation (this repo): `src/components/logo-flash.tsx`. Routes: `/` (loop in the hero), `/flash?v=intro`, `/flash?v=outro`.

Rules learned the hard way:
- **One P.** Never draw a second P for the lockup.
- Center **PAUL**. Center **ꟼFrendach**. The P is allowed to travel between those two seats.
- Do not fade F through P. Open the slot, then seat F already in the locked overlap.
- Do not leave ꟼFrendach right-aligned.
- Reduced motion: skip to HOLD (locked ꟼFrendach).

---

## Site architecture

Persistent on every tab (do not restyle the structure per world):

1. Sticky chrome: ꟼFrendach signature left, world pills right, contact. Padding ≥ 16px. Mark ≥ 24px.
2. Hero: sting or still of the locked signature, kicker, Fraunces headline, gold/accent rule, lead.
3. Three house cards that switch the world (Create / Build / Train).
4. Footer: name, place, one quiet line.

What *does* change per world: `--accent`, kicker, headline, lead, panel copy, photography/texture.

One house CSS file. World skins are `data-world` + tokens, not three templates.

### What to build

1. Multi-section or multi-route site from this brief.
2. **Train:** doctrine, Seven Laws, offer, how a session works, honor line (locked facts only), contact.
3. **Create:** selected film/stills grid, Vision Oasis credit.
4. **Build:** selected sites / process.
5. Use the sting as the home hero or as intro/outro overlays on film.
6. Mobile: chrome wraps, pills stay usable, mark stays Fraunces / SVG.

---

## Files in this pack

See `ASSETS.md`. Masters to actually use:

| Use | File |
|---|---|
| Vector mark | `marks/pf-house.svg` (also `-ink`, `-gold`) |
| Transparent mark PNG | `marks/pf-house-bone.png` / `-ink.png` / `-gold.png` |
| Header wordmark | `marks/pf-signature-bone.png` (+ on-ink, ink, gold) |
| PAUL ꟼFrendach | `marks/pf-paul-signature-bone.png` |
| With subtitle | `marks/pf-signature-sub-on-ink.png` |
| Favicon / app | `marks/pf-app-icon-1024.png`, `pf-app-icon-180.png` |
| Avatar | `marks/pf-avatar-1024.png`, `pf-avatar-circle-1024.png` |
| Banner | `marks/pf-banner-1500.png` |
| Palette board | `marks/pf-colors.png` |
| Sting | `flash/intro.mp4`, `flash/outro.mp4` |
| Font | `fonts/Fraunces_72pt-Regular.ttf` |

On-ink / on-bone files are flattened previews. Prefer the transparent PNG or SVG on live backgrounds.

---

## Do not

- Do not redesign the logo.
- Do not revive a blocky PF, a gold square, a soccer ball, a shield, or an outline.
- Do not set PAUL FRENDACH or the header in Anton.
- Do not mix Glow into Train or Steel into the logo.
- Do not write fake testimonials or unlocked honors.
- Do not make three unrelated websites. One house. Three rooms.
- Do not overlap the subtitle on the wordmark.
- Do not swap the house mark per tab.
- Do not crowd the F-arm into the R.
- Do not draw two P’s.
- Do not trauma-dump family detail.
- Do not make it look AI-generated: keep it spare, one strong object, real Fraunces, real overlap.
