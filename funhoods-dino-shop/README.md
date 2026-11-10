# Funhoods — Dino Car (MT-03) · "The Shop Story" · B2B reel (9:16, 2160x3840, 60 fps, 37.5 s)

Master: `exports/Funhoods_Dino_Shop_Story_4K60.mp4` · share copy: `exports/Funhoods_Dino_Shop_Story_1080p.mp4`
Script: `SCRIPT.md` · storyboard: `exports/Dino_Shop_Story_Storyboard.png` · caption: `CAPTION.md`

A story reel animated entirely in code:
1. A quiet toy shop gets the Funhoods Dino Car display box.
2. Kids stop, push it, see the 360° flip and the chomping mouth, and crowd in.
3. By evening the box is empty and the dealer reorders.
4. Then the B2B facts, and the message to distributors: put it in every shop on your route.

- **Audience:** distributors & wholesalers only. Bulk orders only, pan India delivery.
- **Left out:** no phone number, no price.
- **Wording:** "sells itself" is not used.

**Drawn in code (`render.py`):** a flat illustration of the shop:
- the street front with its rolling shutter and signboard, and the inside with shelves of generic toys, the wall clock, the window and the lamp;
- the counter, the dealer (moods and poses), the kids (front view walking and cheering, back view at the counter);
- a row of shops on a road.

**From the Dino Car reel (`../funhoods-dino-car/assets`):**
- the toy rig (cut-outs of the client's mockup): rims spin, the head chomps on its hinge;
- the 12-pc display box, the 4 colours, and the carton and truck props.

`tools/make_box_empty.py` paints the display box's tray empty (`assets/box_empty.png`), so the box can empty one colour column at a time as the kids take the dinos.

| Time | VO | Scene |
|---|---|---|
| 0–5.3 | Morning at the toy shop. Full shelves... but nobody stops. | Street: the shutter rolls up, dull shelves, the dealer yawns; kids walk past without looking in. No music yet, only street sounds and birds. |
| 5.3–8.2 | Then the Funhoods Dino Car arrives! | The yellow Funhoods truck pulls up (the music starts); a carton hops to the shop door with a burst; the dealer is surprised · FUNHOODS DINO CAR |
| 8.2–11.6 | 12 dinos in a bright display box, right on the counter. | Inside: the real 12-pc box lands on the counter, the lamp turns into a spotlight, the shelves light up, the dealer presents it · 12 PCS DISPLAY BOX · RIGHT ON THE COUNTER |
| 11.6–18.1 | One push and off it goes! A full 360 flip... and that dino mouth opens wide! | On the counter: a kid's hand pushes the dino (real friction ratchet), it rolls up a book ramp (flywheel whirr), flips 360 and lands (kids cheer). It chomps on landing, on "mouth" and wide on "wide" (roar) · PUSH & GO · 360° FLIP! · MOUTH OPENS WIDE! · DINOSAUR MOUTH CAN BE OPENED UP AND DOWN |
| 18.1–22.7 | Kids crowd in... and by evening the box is empty. Time to reorder! | Three kids at the counter (from behind), the 12 dinos hop out of the box to them one by one, the clock runs to evening, the window turns orange · KIDS LOVE IT · SOLD OUT! stamp · the dealer gives a thumbs-up with a Funhoods reorder slip (register bell) · TIME TO REORDER! |
| 22.7–26.1 | Four colours, BIS approved, safe for little hands. | The 4 colours on the shop shelf · AVAILABLE IN 4 COLORS · BIS APPROVED · SAFE FOR LITTLE HANDS · 3+ AGES |
| 26.1–29.2 | 192 pieces per carton, pan India delivery. | Cartons stack · 192 PCS PER CARTON · the truck drives in · PAN INDIA DELIVERY |
| 29.2–33.5 | Distributors and wholesalers, put the Dino Car in every shop on your route! | A row of shops on a road; the Funhoods truck drives past and each window lights up with the Dino display · FOR DISTRIBUTORS & WHOLESALERS · BULK ORDERS ONLY · EVERY SHOP ON YOUR ROUTE! |
| 33.5–37.5 | Funhoods... Childhood Full of Fun! | End card: logo, display box, colours, DINO CAR • MT-03 • 3+ AGES, BULK ORDERS ONLY, 192 PCS / CARTON, PAN INDIA DELIVERY, packaging disclaimer |

## Sound
- **VO:** Magnific (ElevenLabs v4), voice "Gavin" (client pick, sample 1). `tools/vo_retime.py` makes it 8 % faster (pitch kept) and cuts it into its 9 lines with story pauses. The VO never speaks a sound effect.
- **Music:** **"Playful" — Ahjay Stelino (Mixkit Stock Music Free License)**, 130 BPM. It is a new track, and it starts when the truck arrives (the quiet morning has none). It is ducked under the VO and dips under the toy's sounds.
- **Toy:** the Dino Car's REAL friction sound and the roar, both from the Dino Car reel.
- **Generated (Magnific SFX):** kids cheering and the shop shutter.
- **Synthesized:** street ambience and birds, the truck engine (no horn), thocks, the stamp, the register bell, clock ticks, whooshes, pops and chimes.

## Render
```sh
python3 tools/make_box_empty.py && python3 tools/storyboard.py
python3 tools/vo_retime.py && sh music/get_music.sh && python3 audio.py     # mix.wav (-14 LUFS)
python3 render.py --start 0 --end 9.4 --out c0.mp4                           # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af aresample=192000,alimiter=limit=0.8:level=false:attack=2:release=60,aresample=48000 -c:a aac -b:a 256k Funhoods_Dino_Shop_Story_4K60.mp4
```
