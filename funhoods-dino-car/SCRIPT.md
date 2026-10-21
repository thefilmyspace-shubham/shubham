# Funhoods — Dino Car (MT-03) · VO script

Reel: 30 s · 9:16 · white background motion graphics · B2B (distributors & wholesalers only).
No phone number on screen. The car is push-and-go (friction / inertial power): no pull-back needed.

## Final VO (client's ElevenLabs file, `audio/vo_elevenlabs.mp3`, voice "Ishaan")

```
The Dino Monster Truck!                                   [roar SFX]
No batteries needed, just push and go.                    [zoom SFX + the toy's real friction sound]
It flips 360 degree and its dino mouth opens wide.
Four fun colours. Blue, pink, green and yellow.
BIS approved, made of virgin polymer, safe for little hands.
12 per display box, it sells itself on the counter.
192 pieces per carton with pan India delivery.
Distributors and wholesalers, place your bulk order today.
Funhoods, childhood full of fun.
```

The file is 30.7 s long. `tools/vo_retime.py` speeds it up 4.7 % (pitch kept) and cuts it into its phrases.
That opens a 0.75 s gap for the ElevenLabs roar after line 1 and a 0.8 s gap for the zoom after line 2.
The result is `audio/vo_timed.wav` and `audio/vo_timing.json`, with word times on the reel clock that the cuts follow.

## Approved draft (for reference)

```
[cheerful] Funhoods presents... the Dino Monster Truck! [playful] Rawr!
No batteries needed — just push and go... zoom!
It flips 360, climbs like a champ, and its dino mouth opens wide!
Four fun colours — blue, pink, green and yellow!
BIS approved, made of virgin polymer — safe for little hands.
Twelve per display box — it sells itself on the counter!
One ninety-two pieces per carton, with pan India delivery.
Distributors and wholesalers — place your bulk order today!
[excited] Funhoods — Childhood Full of Fun!
```

`vo_samples/` holds three free Kokoro TTS drafts made while ElevenLabs was rate-limited. They are not used in the reel.
