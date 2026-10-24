# Paimal: Nagar Nigam speech (Magnates-style reel, 1080×1920)

**Edit rules**
- A-roll gets no graphics. It only has jump cuts (pauses tightened) and punch-in zooms.
- Every B-roll is a real source: the client's two newspaper cuttings, or a news article captured with `article_shot.py`.
  That tool checks that each highlighted line is actually on the page; if a line isn't there, it exits with an error.
- Ads on the source pages are never shown. Pages behind a login ("पढ़िए पूरा") are used only up to the part that is
  publicly visible.
- Subtitles are minimal Hindi, matched to what is actually spoken.
- Music is original (Magnific / Lyria 3 Pro): `music/paimal_intense_170s.mp3`.

## B-roll sources (in order)
| # | Line in the speech | Source | Highlight |
|---|---|---|---|
| 1 | लकड़पीठा, 9 महीने, चक्का जाम | Patrika, 22 Oct 2026, "लक्कड़पीठा में आक्रोशित व्यापारियों ने महापौर को घेरा" https://www.patrika.com/ratlam-news/angry-traders-protest-21000576 | "व्यापारियों ने चक्काजाम कर अपना गुस्सा जाहिर किया।" |
| 2 | मकान तोड़ने की जल्दी थी | Dainik Bhaskar, 9 Mar 2026, bulldozer story https://www.bhaskar.com/local/mp/ratlam/news/ratlam-fourlane-encroachment-removal-lakkarpeetha-137389751.html | "27 मकान-दुकानों के हिस्से हटाए गए" |
| 3 | कमिश्नर साहब गए, महापौर जी आए | ETV Bharat, 21 Oct 2026 https://www.etvbharat.com/hi/state/ratlam-bussinessmen-protest-against-pending-four-lane-road-work-since-1-year-mps26102104145 | "चक्काजाम की सूचना पर महापौर प्रहलाद पटेल एवं निगम आयुक्त अनिल भाना मौके पर पहुंचे." |
| 4a | सिस्टम लाचार है | VandeMatram News, 22 Oct 2026 https://www.vandematramnews.com/the-helplessness-of-the-mayor-and-the-commissioner-in-ratlam/ | "नगर निगम का सिस्टम लाचार है, नपुंसक हो गए सभी।" |
| 4b | इंजीनियरों को चिंता नहीं | Dainik Bhaskar, 21 Oct 2026 https://www.bhaskar.com/local/mp/ratlam/news/ratlam-mayor-protest-municipal-corporation-commissioner-controversy-139443562.html | "सब नपुंसक हो गए" (headline); "महापौर ने नगर निगम के सिस्टम और इंजीनियरों की कार्यप्रणाली पर सवाल उठाए।" |
| 5 | ऊपर से नीचे तक कमीशनखोरी | VandeMatram News, 15 Sep 2023 (contractors' complaint) https://www.vandematramnews.com/contractors-complain-against-sub-engineer-with-serious-allegations-of-bribery/ | "रतलाम निगम में कमीशन का खेल"; "...तय कमीशन से अधिक कमीशन एवं एडवांस कमीशन मांगा जा रहा है" |
| 6 | कुत्तों का बधियाकरण, 32,000, करोड़ों | Dainik Bhaskar online, 6 Feb 2026 https://www.bhaskar.com/local/mp/ratlam/news/ratlam-dog-sterilization-scam-commissioner-137135437.html, and the client's Dainik Bhaskar cutting of 27 Dec 2025 | "33 हजार की नसबंदी का दावा, सर्वे में 2204 मिले"; circles on "33 हजार" and "2.58 करोड़" |
| 7 | 700 का एलईडी 2,900 में; एक फर्म को टेंडर | The client's Naidunia cutting of 29 Apr 2023 | Circles on "700" and "2966"; highlight on "सिंगल फर्म का टेंडर आने के बाद भी स्वीकृति दे दी गई।" |
| 8 | रावण दहन में भ्रष्टाचार | VandeMatram News, 3 Oct 2025 https://www.vandematramnews.com/ravana-dahan-becomes-a-symbol-of-corruption-in-ratlam/ | "रतलाम में भ्रष्टाचार का प्रतीक बना रावण दहन"; "50-60 हजार ... करीब 3 लाख रुपये में तैयार कराया।" |
| 9 | टैक्स का पैसा भ्रष्टाचार में | ETV Bharat, 6 Apr 2026 https://www.etvbharat.com/hi/state/ratlam-congress-protest-municipal-corporation-tax-hike-proposal-madhya-pradesh-news-mps26040603982 | "नगर निगम के टैक्स बढ़ाए जाने का विरोध"; "रतलाम नगर निगम में जनता के टैक्स के पैसों पर बड़े-बड़े घोटाले हो गए हैं" |

## Claims with no source found (left on the A-roll, no B-roll)
- अलकापुरी के काम में लोहे में जंग
- लोहार रोड से तोपखाना फोरलेन
- बधियाकरण का पैसा महापौर परिषद ने पास किया
- रावण दहन के बाद फर्म को पैसा दे दिया गया. Bhaskar (2 Oct 2025) quotes the mayor saying the payment would be stopped,
  so no B-roll is used for this line.

## Numbers the speaker says vs. the sources
- **Dogs:** the speaker says 32,000. Sources say 33,630 (cutting: "33 हजार").
- **LED:** the speaker says 2,900. The cutting says 2,966.
- **Lakkadpitha:** the speaker says "9 महीने". Articles say "एक साल / सालभर"; the bulldozer action was on 9 Mar 2026.
- **Mayor's quote:** the speaker says "अधिकारी बिल्कुल नपुंसक हो गए हैं". The printed versions are "सब नपुंसक हैं" and "नपुंसक हो
  गए सभी".

## Audio
- **0–85.9 s:** clean mic.
- **85.9 s onward:** the file falls back to the camera mic. This part is repaired with RNNoise (`models/rnnoise/cb.rnnn`),
  a long-term-spectrum EQ match to the clean part, and a level match (`clean_dialogue.py`). For a cleaner result, run it
  through ElevenLabs Voice Isolator and pass the file with `--isolated`.

## Rebuild
```sh
sh projects/paimal/web/shots.sh                 # re-capture and verify articles (needs network)
python3 projects/paimal/make_words.py           # subtitle words
python3 projects/paimal/clean_dialogue.py       # dialogue repair
python3 projects/paimal/build_edl.py            # cuts, B-rolls, subtitle style -> edl.json
python3 projects/paimal/mix.py                  # dialogue + music + SFX -> audio/mix.wav
python3 docu.py projects/paimal/edl.json --audio projects/paimal/audio/mix.wav --out out/Paimal.mp4
```

RNNoise model (not committed): `mkdir -p models/rnnoise && curl -L -o models/rnnoise/cb.rnnn https://raw.githubusercontent.com/richardpl/arnndn-models/master/cb.rnnn`
