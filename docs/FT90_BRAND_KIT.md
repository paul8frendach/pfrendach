# Find the 90 — Brand Kit
*For AI content creation tools: captions, graphics, overlays, social posts.*

---

## Identity

| Field         | Value                                 |
|---------------|---------------------------------------|
| Brand name    | Find the 90 / FindThe90               |
| Tagline       | "Find Your 90"                        |
| Coach         | Alex Hood                             |
| Platform site | findthe90.com                         |
| Audience      | Youth soccer players, parents, clubs  |

---

## Colors

| Token name   | Hex       | Usage                                      |
|--------------|-----------|--------------------------------------------|
| Black (BK)   | `#0A0A0A` | Backgrounds, dark fills, base canvas       |
| Red (RED)    | `#C41010` | Primary accent, CTAs, highlights, badges   |
| Warm Gray (GRY) | `#908070` | Secondary text, muted labels, borders   |
| Light Gray (LGY) | `#F5F3F0` | Headings on dark, card text, light text |

**Usage rule:** RED is the signal — use it for one focal point per graphic (button, stat callout, or accent line). Never use it on a white or light background without sufficient contrast testing.

---

## Typography

Fonts loaded in the project:

| Role       | Font            | Weight(s)      | Notes                            |
|------------|-----------------|----------------|----------------------------------|
| Display    | Fraunces        | 400, 600       | Serif — headlines, pull quotes   |
| Sans body  | Outfit          | 300, 400, 500  | UI, body copy, captions          |
| Impact/All-caps | Montserrat | 300, 400, 500 | Training callouts, overlays      |
| Bold accent | Anton          | 400 (display)  | Short stat overlays, scoreboard-style |

**For graphics and overlays:** Montserrat Bold (or Anton) for short all-caps callouts; Outfit 400/500 for supporting text. Never use Fraunces for small sizes.

---

## Logo / Mark

Logo files live at: `static/marks/` in the project.

Key files:
- `pf-house.svg` — house mark (Paul Frendach's site mark; **not** for FindThe90 use)
- FindThe90 does not yet have a separate logo file in the project. Use the wordmark **"FIND THE 90"** in Montserrat Bold, all caps, white on black, with the "90" in RED (#C41010).

**Placeholder until a logo file is created:** Text lockup: `FIND THE 90` — white / RED "90" / black background.

---

## Voice & Tone

- **Direct.** No fluff. Every word earns its place.
- **Performance-driven.** Players are here to get better. Everything points at improvement.
- **Youth soccer-focused.** Speak to the player (and their parents) at club/HS level.
- **Aspirational without hype.** Confident, not pushy. Show don't tell.
- **Alex's voice:** Knowledgeable coach, not a hype man. Real talk, real results.

**Avoid:** Vague motivational clichés ("unlock your potential", "level up your game"). Use specific, concrete language instead ("one-on-one finishing sessions", "12-week development plan").

---

## Content Pillars

1. **Training tips** — technique breakdowns, drill clips, coaching cues
2. **Camp announcements** — upcoming sessions, registration opens, early-bird spots
3. **Player spotlights** — player progress, testimonials (with parent permission)
4. **Shop drops** — new gear, limited runs, "just restocked" posts
5. **Session recaps** — what we worked on, key takeaways, behind-the-scenes

---

## Caption Formula

```
[Hook — 1 punchy line, max 10 words]
[Value / proof — 1–3 sentences showing why this matters]
[CTA — one clear action]
[Hashtags]
```

**Example (training tip):**
> Most players miss this finishing detail. ↓
> When you're 1v1 with the keeper, keep your plant foot pointed at the far post — it opens your hip angle and gives you the whole net. Alex covers this in every session.
> Book your spot at findthe90.com/train
> #findthe90 #youthsoccer #soccertraining #soccercoach #finishingdrills #1v1 #goalkeeper #soccertips #usyouthsoccer #marylandsoccer

---

## Standard Hashtag Set

```
#findthe90
#youthsoccer
#soccertraining
#soccercoach
#soccertips
#usyouthsoccer
#marylandsoccer
#soccerdrills
#soccerplayer
#soccerlife
#goalkeeper  (use on finishing / GK content)
#1v1
#finishingdrills
#soccerdad #soccermom  (use on camp/registration posts)
```

Use 8–12 hashtags per post. Lead with the 3–4 most relevant; trail with the broader ones.

---

## Social Handles

*(Not yet set in codebase — confirm with Alex and add to SiteConfig via /admin/)*

| Platform  | Handle (placeholder)  |
|-----------|-----------------------|
| Instagram | @findthe90            |
| TikTok    | @findthe90            |
| X/Twitter | @findthe90            |

Set final handles in the Django admin under **House → Site config → Instagram URL** (and add TikTok/X fields as needed).

---

## Post Templates by Type

### Camp announcement
```
[City / region] — spots are open.
[Session name] with Alex Hood.
[Date range] · [Location]
Link in bio → findthe90.com/train
#findthe90 #youthsoccer #soccercamp #marylandsoccer
```

### Shop drop
```
New [product name] just dropped.
[One-line description of what makes it worth wearing]
Shop at findthe90.com/shop
#findthe90 #soccergear #youthsoccer
```

### Player spotlight
```
[Player first name] put in the work.
[One specific thing they improved]
This is what Find the 90 is for.
#findthe90 #playerspotlight #youthsoccer
```

---

## File Checklist for Designers

- [ ] Official FindThe90 logo (SVG + PNG, white and black versions)
- [ ] Alex Hood headshot (hi-res, at least 2000px wide)
- [ ] Action shots from sessions (for Stories and Reels covers)
- [ ] Product photos from Printful (auto-populated once shop is live)

---

*Last updated: 2026-09-22 — Paul Frendach build session.*
