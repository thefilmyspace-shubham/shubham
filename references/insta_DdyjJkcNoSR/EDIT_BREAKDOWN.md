# Edit breakdown — Instagram reel DdyjJkcNoSR (talking-head tech explainer, "Meta's Muse")

Source: https://www.instagram.com/reel/DdyjJkcNoSR/ — studied for its editing only (the clip itself is not kept in the repo).
Frames: `sheet0-2.jpg` = one frame per shot (shot no. + time); `motion0-3.jpg` = 7 frames across each graphic shot.

## Numbers
- 1:59 · 720x1280 · 23.976 fps · English VO with Hinglish meme captions.
- **55 cuts → a new shot every ~2 s** (median shot 1.9 s). The first 20 s alone have 11 cuts.
- Screen time:

  | Kind | Shots | Time | Share | Avg. shot |
  |---|---|---|---|---|
  | Talking head (A-roll) | 21 | 44 s | 37 % | 2.1 s |
  | White-background graphics / UI / articles | 21 | 50 s | 42 % | 2.4 s |
  | Black & white meme / film inserts | 13 | 22 s | 19 % | 1.7 s |

  So more than 60 % of the reel is cutaways, and the face never stays on screen for long.

## Structure (story)
1. **0–20 s, the hook before the intro.** A bold claim: "Mark Zuckerberg is back... wants access to your emails... money". It is shown with collage graphics, app icons and a meme ("BACHAO AUCH AUCH"). There is a self-aware aside too: the A-roll goes black & white and a glowing orange handwritten "Ha Ha.. Good Hook" appears.
2. **20.6 s, "Hi, I'm Asma."** The intro comes only after the hook has landed.
3. **Explain, then the twist, then the question.**
   - Explain: what Muse does (feature carousel), why it's scary (access, money).
   - Twist: the PR angle (daughters, baking), a Wall-E analogy (B&W film clips).
   - Ending: an open question to the viewer, back on the face.

## The 8 techniques
1. **Minimal captions on the A-roll, not full subtitles.**
   - Only 1–3 words of the current phrase ("new tool", "very scary.", "super helpful"), small white sans, centred, about 18 % from the top.
   - They change with every phrase, and never appear on graphics shots.
2. **Punch-in zoom on emphasis words.** Medium-wide by default, cut to a tight close-up (~1.5x) on the punch word ("very scary", "super helpful").
3. **White-background explainer graphics with "build-up" typography.**
   - Small thin grey words appear one by one, with a fade and blur-to-sharp. They lead into one big bold keyword in **blue** (or heavy black): "is back in the market with a → **New AI Tool**", "AI with access to → **Accounts & Money**", "→ **Daughters**", "→ **Towards that Direction.**"
   - A soft gold/beige highlighter bar sits behind header lines ("Very Interesting", "Floating on a Device").
4. **Collage / cutout humour.**
   - A real B&W head cutout sits on a drawn body, with a floor shadow and a yellow floor plane.
   - Pixel "deal-with-it" sunglasses drop in, a heart sticker pops, and the 3D mascot pops in with a little bounce.
   - The creator also has her own flat cartoon avatar (glasses, red hair), used as a recurring character.
5. **UI mock-ups that act out the sentence.**
   - An app dock with a **cursor that clicks each icon** (each click has its own click sound).
   - Phone mock-ups with a chat bubble and an order list.
   - A bank-balance card, with a money stack sliding in.
   - A retro computer with a feature carousel: FILL FORMS → BOOK TRIPS → PURCHASE.
   - The camera slowly **pushes in** on the phone or computer, then cuts closer.
6. **Black & white for everything borrowed.** Meme clips, film clips (Wall-E, SpongeBob), the phone video and article screenshots are all desaturated. That keeps the palette tight: colour = her face + clean white graphics with one blue accent.
   - Meme captions are **big bold white CAPS** in Hinglish, centred or left-aligned: "CHAT GPT BE LIKE:", "MUSE BE LIKE:", "KASAY BATAO SARA PAISA KA CHAKAR HAI."
7. **Proof shots.** A news-article screenshot gets a slow push-in plus a scroll. The key sentence is highlighted in **blue**, and the shot blurs out into the next cut.
8. **Transitions are mostly hard cuts, with a few seasonings:**
   - a quick blur-in or zoom on the first frames of an A-roll shot;
   - a **pixelate / mosaic** transition into a film clip;
   - a push-in "through" a screen;
   - objects that fly or drop in with motion blur.

## Sound
- The voice is dry and upfront. Under it there is only a very quiet bed (floor about −31 dB), with no loud music.
- **SFX are synced to the graphics:** a click on every cursor click (8.76 / 9.12 / 9.63 / 10.12 / 10.69 s), plus pops and whooshes on the reveals.
- Meme and film inserts **keep their own audio** at full level for the joke.

## Why it works
- A new visual about every 2 s, and every visual *illustrates the exact words being said* (literal and funny).
- One consistent design system: white background, thin + bold type, blue accent, B&W for borrowed footage.
- The hook comes before the intro. The question ending invites comments.

## Using it for TFS / Funhoods (what our code pipeline can already do or easily add)
- **Build-up typography with a blue keyword:** our `text_img` plus a word-by-word fade/blur reveal, with a highlighter bar.
- **Cursor-click UI sequences:** for example, ordering on a distributor app, or "Add to cart → 240 pcs".
- **Collage cutouts:** our product cut-outs and dealer illustrations, with pixel sunglasses, stickers, drop-in bounce and floor shadows.
- **B&W meme inserts with bold Hinglish captions:** we use the client's own clips or our renders; we don't use copyrighted memes in client ads.
- **Minimal 1–3 word captions** over talking-head footage (for clients who shoot A-roll), plus punch-in zooms on emphasis words.
- **Pixelate transition, push-in through screens, blur-in on cuts.**
- **SFX on every motion** (click, pop, whoosh), a quiet bed under the voice, the voice upfront.
