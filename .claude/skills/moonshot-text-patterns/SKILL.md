---
name: moonshot-text-patterns
description: Caption and on-screen text patterns learned from all 99 public Moonshot (makemoonshot.co) caption templates. Use when planning or reviewing text/captions for a Reel, Short or TikTok, when picking a caption style for a talking-head video, when someone names a Moonshot template (Eclipse, Masala, Headliner, Blue Muse, Floodlight, Kumar, etc.), or when writing a CapCut/Premiere text brief so an editor can recreate a premium caption look.
---

# Moonshot text patterns

This skill is a style library built from Moonshot's caption templates. It covers 99 templates in 13 families. Every template was studied from its official thumbnail plus frames from its preview video.

- Visual index (a thumbnail card for each template): `moonshot-templates/README.md`. The cards live in `moonshot-templates/<NN-Family>/<NN-Name>.jpg`.
- Per-template specs (fonts, hex colours, words per line, motion, when to use, when to skip): `references/catalog.md`. The same data is in `references/templates.json`.

When someone names a template, look it up in the catalog and open its card before you describe it. Don't describe a template from memory.

## The core system: every template is two voices

Almost every Moonshot template is built from the same two layers.

1. **Subtitle voice (small).** These are the words being spoken right now, at most 2–4 on screen at once. It uses a neutral sans (Montserrat Bold/ExtraBold, Inter, Poppins), sentence case or lowercase, in white or off-white. It sits at chest height or in the lower third, and never covers the face.
2. **Hero voice (huge).** One meaning word per sentence: the noun, verb or number that carries the idea (IDEA, DISCIPLINE, PROGRESS, THREE, $600,000). It is 4–8× bigger than the subtitle and uses a display face with the opposite personality. It sits in the top third, usually **behind the speaker's head**. The rest of the time the hero slot stays empty. Frames with no hero word are normal and make the hits land harder.

The spoken word inside the subtitle often flips to the hero's accent colour. That ties the two voices together.

## Rules that hold across the whole library

**Font pairing.** Pair a neutral sentence font with an accent font that contrasts on two axes, size and style. Proven pairs:

| Accent personality | Accent font (seen in) | Sentence font |
|---|---|---|
| Heavy condensed caps | Anton, Bebas Neue, Archivo Black, Black Han Sans, Oswald | Montserrat Bold, Inter, Instrument Sans |
| Brush or calligraphy script | Kaushan Script, Great Vibes, Pinyon Script, Ballet, Dancing Script | Montserrat Bold, Inter Regular |
| Editorial serif or serif italic | Playfair Display (Black/Italic), Instrument Serif, Gloock, DM Serif Display, Unna | Poppins Medium, Instrument Sans, Open Sans |
| Comic or fat rounded | Luckiest Guy, Bagel Fat One, Baloo 2 ExtraBold | Montserrat Bold, Poppins Bold |
| Texture or retro | Press Start 2P (pixel), Special Elite (typewriter), Rubik Spray Paint, Lacquer (painted) | Typewriter or serif |
| Handwritten | Gloria Hallelujah, Caveat Brush, Just Me Again Down Here | Anton or BBH Bartle |

**Two colours, one accent.**
- Base: white or a warm off-white (#FFFFFF, #F6EFE2, #FBF4E4, #FFF1DC).
- Accent: one saturated colour, used only on hero words and the active word. Seen: yellow #FFE500 / #FFD700 / #F5D300, lime #A8FF1A / #96FF1A / #C6FF3D, red #E50914 / #E2382A / #B90000, cobalt #2B53D4 / #2742C4, ice blue #7FD3FF, orange #FF6A2B, magenta #EC00B5.
- Pull the accent from the set or wardrobe. Examples: a lime notebook gives a lime hero (Signal), an olive room gives an olive hero (Soundwave), a mustard wall gives gold (Masala).

**Density.**
- Most templates show **2–4 words** at a time; the maximum is 8. The only exception is Real Estate (up to 16), where small spoken captions run under big numbers.
- One hero per sentence, never two at once.
- Short and punchy beats long and readable.

**Placement.**
- Hero: top third, full width, often clipped by or tucked behind the head.
- Subtitle: chest or lower third.
- Playful styles put small asides in the top-left and big words around the body, never on the face.
- Keep everything inside the Reels safe zone. Don't place text in the bottom ~20% or in the right-side button column.

**Case.**
- Caps belong to the hero (condensed/impact).
- Sentence case or lowercase belongs to the subtitle.
- An editorial look uses sentence case, with the key word set in *italic serif*.

## Pattern families (which look does what)

1. **Behind the person** (Eclipse, Gatekeep, Signal, Kumar, Masala, Sunburst, Crimson, Golden Hour, Chrome, Ghostline, Sprayline, Retro Cut, Sticker, Calligraph, Soundwave, Aura, Desi Bold, Monument, Lime Swipe)
   - The hero word is masked behind the head; white subtitles sit in front.
   - Use it for hooks, founder takes and personal-brand content.
   - Needs a clean silhouette and empty wall above the head.
   - Skip it on wide shots or busy backgrounds.
2. **Multiline lockups** (Supernova, Gold Centre, Blue Muse, Red Shift, Diagonal, Headliner, Margin Note, Moonbeam, Fireline, Focusline)
   - 2–3 stacked rows in the lower third: a tiny tracked-caps context row, one giant hero row, and sometimes a tiny trailing word ("now", "today", "them").
   - Headliner lays white script over red condensed caps.
   - Blue Muse stacks a caps word, a bold word and a Playfair italic word.
   - Use it for cinematic or premium talking heads with no masking.
3. **Editorial serif** (Delhi, Soft Script, Serif Quote, Crimson, Storyline, Pastel Fisheye)
   - Clean sans sentence, with the key word in italic serif, sometimes amber-tinted or glowing.
   - Use it for luxury, fashion, lifestyle, quotes and calm storytelling.
4. **Active-word / karaoke** (Floodlight, Filmstrip, Karaoke, Lime Swipe, Liquid Glass, Beast Mode, Pink Neon, Searchlight)
   - ALL CAPS Montserrat ExtraBold, 3–5 words, centred low.
   - The active word gets a yellow box (Floodlight), a yellow word in a black box (Filmstrip), a colour wipe (Karaoke), a neon glow (Beast Mode) or a frosted pill (Liquid Glass).
   - Use it for high-retention, sound-off viewing, podcasts and tutorials.
5. **Playful scatter** (Pop Off, Butter, Cursive, Blush Lab, Ribbon, Cutout)
   - Tiny white asides plus big chartreuse/butter words placed around the speaker, some tucked behind them.
   - Use it for lifestyle, food, comedy and casual chat.
6. **Spatial 3D** (Spatial Red/Yellow/White, Deep Focus)
   - Words are pinned in 3D around the room, tracked to camera movement, mixing tiny and huge sizes.
   - "They slip BEHIND your head."
7. **Dynamic motion** (Inception, Linen, Quill, Glide, Wiggle, Dolly)
   - The motion itself is the style: an impact word that inverts the footage and fills the frame, typing behind a cursor, a flickering script opener, a script word gliding through, a painted word tracing a path, or a keyword springing forward.
8. **Real estate / numbers** (Agent Story, Number Story, Gradient Estate, Dimension Story)
   - Huge outlined amounts (`$600,000`, `25,000 a month`), counters that roll up, and a bold magenta or green keyword over small spoken captions.
   - Use it whenever a number is the hook.
9. **Desi / Hinglish** (Desi Bold, Tabahi)
   - Baloo 2 ExtraBold handles Devanagari and Roman in one face.
   - Tabahi = comic caps (Anton) over a rounded Hinglish line, for full hype.
10. **AI Edits** (35 templates: Blackboard, Kraft, Matinee, Boldface, Notes, Riso, B-Side, Afterglow, Podcast Cutout, Explainer, Moodboard…)
    - These are full edit treatments, not just captions. The recurring scene grammar:
      - **Hook title card**: a giant word or stacked repeated word (`DISCIPLINE DISCIPLINE…`, `STORY` wallpaper with one filled glowing line, `RECORD` bands top and bottom).
      - **Talking head** with the family's caption style.
      - **B-roll cutaway** that keeps the caption running over it.
      - **A graphic "board" moment** for lists, numbers and contrasts: a note card with ticking checkboxes, a receipt, polaroids or instant prints, blueprint grid with selection boxes, torn paper strips and tape labels, an envelope with a wax seal, a TV frame, or the speaker as a white-outlined sticker cut-out.
      - **Return to the speaker**, often as a rounded picture-in-picture card or a split screen.
    - Graphic devices that recur:
      - highlighter swipe behind a word
      - hand-drawn circle around a keyword
      - strike-through on the "wrong" word
      - red-pen marks
      - number counters
      - a pill caption that fills as you speak
      - zoom-blur cuts
      - film-frame borders and light leaks

## How to use this skill

**Pick a style for a video.**
1. Look at the footage: framing (close or wide), how clean the background is above the head, and the set and wardrobe colours.
2. Consider the tone and the niche.
3. Shortlist 2–3 templates from the families above. Confirm each one's "When to use / Skip when" in `references/catalog.md`.
4. Name the thumbnail card path so the person can see it.

**Write a caption plan.** For each sentence, output a row like this:

| Time | Subtitle (small) | Hero word (big) | Hero placement | Accent / motion |
|---|---|---|---|---|
| 0:00–0:02 | "The clearest" | IDEA | behind head, top third | #FFE500 Anton, pop-in |

Mark exactly one hero per sentence, or none. Prefer nouns, verbs and numbers over filler.

**Write an editor brief (CapCut / Premiere).**
- **Behind-the-person:** duplicate the clip, run background removal / auto cutout on the top copy, and put the hero text layer between the two copies.
- **Two text styles:** create two text presets. A subtitle preset (sentence font, white, 2–4 words) and a hero preset (accent font, accent colour, top third).
- **Active word:** colour the word being spoken with the accent colour, or put a box or highlight behind it.
- **Animation:** keep it simple. Pop or scale-in for the hero, fade or typewriter for subtitles. Use one motion idea per template.
- **AI Edit look:** plan the cutaways and the board moments (lists, numbers, contrasts) in the script before editing.

**Review someone else's captions.** Check these against the rules above:
- too many words on screen
- two competing heroes
- accent used on non-key words
- text over the face or outside the safe zone
- a hero font with no contrast against the subtitle font

## Notes

- Moonshot templates are a product of Kaizynn/Moonshot. This library is for learning patterns and briefing editors. Recreate the *style*; don't claim it as Moonshot output.
- The data is a snapshot of the public template page. Moonshot's editor has ~158 more styles that aren't on the public page.
