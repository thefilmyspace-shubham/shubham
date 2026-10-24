#!/bin/sh
# Real articles used as B-roll (verified by article_shot.py: exits non-zero if a quote isn't on the page)
cd "$(dirname "$0")/../../.."
W=projects/paimal/web
shot() { name=$1; shift; timeout 200 python3 article_shot.py "$@" > $W/$name.log 2>&1; echo "$name exit=$?"; tail -4 $W/$name.log; }
shot patrika_lakkadpitha "https://www.patrika.com/ratlam-news/angry-traders-protest-21000576" $W/patrika_lakkadpitha \
  --quote "व्यापारियों ने चक्काजाम कर अपना गुस्सा जाहिर किया।"
shot bhaskar_bulldozer "https://www.bhaskar.com/local/mp/ratlam/news/ratlam-fourlane-encroachment-removal-lakkarpeetha-137389751.html" $W/bhaskar_bulldozer \
  --quote "27 मकान-दुकानों के हिस्से हटाए गए"
shot etv_mayor_commissioner "https://www.etvbharat.com/hi/state/ratlam-bussinessmen-protest-against-pending-four-lane-road-work-since-1-year-mps26102104145" $W/etv_mayor_commissioner \
  --quote "चक्काजाम की सूचना पर महापौर प्रहलाद पटेल एवं निगम आयुक्त अनिल भाना मौके पर पहुंचे."
shot bhaskar_mayor_quote "https://www.bhaskar.com/local/mp/ratlam/news/ratlam-mayor-protest-municipal-corporation-commissioner-controversy-139443562.html" $W/bhaskar_mayor_quote \
  --quote "सब नपुंसक हो गए" --quote "महापौर ने नगर निगम के सिस्टम और इंजीनियरों की कार्यप्रणाली पर सवाल उठाए।"
shot vm_mayor "https://www.vandematramnews.com/the-helplessness-of-the-mayor-and-the-commissioner-in-ratlam/" $W/vm_mayor \
  --quote "नगर निगम का सिस्टम लाचार है, नपुंसक हो गए सभी।" --quote "न आपको चिंता है न इंजीनियरों को"
shot news18_mayor "https://hindi.news18.com/amp/news/madhya-pradesh/ratlam-road-project-delay-people-mayor-prahlad-patel-statement-my-system-is-helpless-impotent-local18-10926624.html" $W/news18_mayor \
  --quote "मेरा सिस्टम ही लाचार है और सभी नपुंसक हो गए हैं"
shot vm_commission "https://www.vandematramnews.com/contractors-complain-against-sub-engineer-with-serious-allegations-of-bribery/" $W/vm_commission \
  --quote "निगम के कुछ अधिकारियों द्वारा तय कमीशन से अधिक कमीशन एवं एडवांस कमीशन मांगा जा रहा है" --quote "रतलाम निगम में कमीशन का खेल"
shot bhaskar_dogs "https://www.bhaskar.com/local/mp/ratlam/news/ratlam-dog-sterilization-scam-commissioner-137135437.html" $W/bhaskar_dogs \
  --quote "33 हजार की नसबंदी का दावा, सर्वे में 2204 मिले"
shot vm_ravan "https://www.vandematramnews.com/ravana-dahan-becomes-a-symbol-of-corruption-in-ratlam/" $W/vm_ravan \
  --quote "50-60 हजार रुपये में बनने वाले रावण का पुतला निगम ने करीब 3 लाख रुपये में तैयार कराया।" --quote "रतलाम में भ्रष्टाचार का प्रतीक बना रावण दहन"
shot etv_tax "https://www.etvbharat.com/hi/state/ratlam-congress-protest-municipal-corporation-tax-hike-proposal-madhya-pradesh-news-mps26040603982" $W/etv_tax \
  --quote "रतलाम नगर निगम में जनता के टैक्स के पैसों पर बड़े-बड़े घोटाले हो गए हैं" --quote "नगर निगम के टैक्स बढ़ाए जाने का विरोध"
