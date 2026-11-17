"""Default WhatsApp message texts, in English, with several versions each.

A different version goes each time (by turn for each member), so the messages feel fresh and
WhatsApp sees less identical text. The owner can change every text on the WhatsApp page;
versions are separated by a line with only --- on it.

Placeholders: {name} member's name, {date} end date (DD-MM-YYYY), {amount} money,
{link} joining form link. Staff texts also have {minutes} {shift} {n} {hours}.
No phone numbers in any message (the owner's choice).
"""
SEP = "\n---\n"

DEFAULTS = {
    "expiring": [
        "Hi {name},\nWe would like to inform you that your gym membership expires on {date}.\n\n"
        "We truly appreciate your dedication to fitness and would love to see you continue your journey with us. 💪 "
        "Kindly renew your membership at your convenience to stay consistent and achieve your goals. 🏆\n\n"
        "For any assistance, just reply to this message or visit the reception.\n\n"
        "Thank you for being a valued member.\nHouse of Strength Gym",

        "Hey {name}! ⏳\nJust a heads-up: your House of Strength membership ends on {date}.\n\n"
        "You've been putting in the work, so don't let the streak break now! 🔥 Renew at the reception or reply here "
        "and we'll sort it out for you.\n\nSee you on the floor! 🏋️\nHouse of Strength Gym",

        "Hi {name} 👋\nYour membership is about to wrap up on {date}.\n\n"
        "Consistency is what builds results, and you're on the right track. 💯 Renew before the date so your gym "
        "access continues without a break.\n\nQuestions? Just reply to this message.\nHouse of Strength Gym",
    ],
    "expired": [
        "Hi {name},\nYour House of Strength membership ended on {date}. We miss seeing you at the gym! 💪\n\n"
        "Renew today to keep your gym access and pick up right where you left off.\n\n"
        "Reply here or visit the reception, we're happy to help.\nHouse of Strength Gym",

        "Hey {name}! 🏋️\nYour membership expired on {date}, and your spot on the floor is waiting for you.\n\n"
        "Don't lose the progress you've worked so hard for. Renew now and keep the momentum going! 🔥\n\n"
        "House of Strength Gym",

        "Hi {name} 👋\nQuick reminder: your membership ended on {date}, so your gate access will stop soon unless it's renewed.\n\n"
        "Drop by the reception or reply to this message, and we'll get you back in action in no time. 💪\n\n"
        "House of Strength Gym",
    ],
    "due": [
        "Hi {name},\nThis is a gentle reminder that {amount} is pending on your House of Strength account.\n\n"
        "Kindly clear it at the reception on your next visit. Thank you for your support! 🙏\n\nHouse of Strength Gym",

        "Hey {name} 👋\nJust a quick note: there's a balance of {amount} on your membership.\n\n"
        "You can settle it at the reception whenever you're in next. Keep training hard! 💪\n\nHouse of Strength Gym",

        "Hi {name},\nFriendly reminder: {amount} is still due on your account with us.\n\n"
        "Please clear it at your convenience at the reception. If you've already paid, kindly ignore this message. 😊\n\n"
        "House of Strength Gym",
    ],
    "birthday": [
        "Happy Birthday, {name}! 🎉\nWishing you a fantastic year ahead filled with health, happiness, and gains! 💪 "
        "Keep crushing your fitness goals, and we're here to support you every step of the way. 🏋️‍♂️ "
        "Have an amazing day! 🎂\n🎈 From your Gym Family!\nHouse of Strength Gym",

        "Happy Birthday, {name}! 🎂🎈\nAnother year stronger! May this year bring you new PRs, great health and lots of "
        "happiness. 💪\n\nEnjoy your special day!\nYour House of Strength Gym family",

        "Cheers to you, {name}! 🥳\nWishing you a very Happy Birthday from all of us at House of Strength. Keep shining, "
        "keep lifting, and keep inspiring everyone around you! 🏆\n\nHave a great one! 🎉\nHouse of Strength Gym",
    ],
    "absent": [
        "Hi {name} 👋\nWe haven't seen you at the gym for a few days. Everything okay?\n\n"
        "Even a short workout keeps the momentum going. We'd love to see you back soon! 💪\n\nHouse of Strength Gym",

        "Hey {name}! 🏋️\nYour trainers and workout buddies are missing you at House of Strength.\n\n"
        "Come back this week and let's get you back on track! 🔥\n\nHouse of Strength Gym",

        "Hi {name},\nIt's been a while since your last visit. Remember, consistency beats intensity! 💯\n\n"
        "Your membership is active, so make the most of it. See you soon!\nHouse of Strength Gym",
    ],
    "form": [
        "Hi {name},\n\nWelcome to the House of Strength family! 💪 We're excited to have you with us.\n\n"
        "To complete your membership, please fill in your joining form here:\n{link}\n\n"
        "It takes just 2 minutes. You can also fill the attached PDF and send it back on this chat. 📄\n\n"
        "Once done, our team will register your fingerprint for gym entry. 🏋️\n\nSee you at the gym!\nHouse of Strength Gym",

        "Hi {name} 👋\nThank you for choosing House of Strength! 🏋️\n\n"
        "Please fill in your joining form so we can set up your membership:\n{link}\n\n"
        "Prefer the PDF? Fill the attached form and send it back here. 📄\n\nWelcome to the family! 💪\nHouse of Strength Gym",

        "Hello {name}! 🎉\nGreat to have you at House of Strength.\n\n"
        "One quick step before you start: please fill in your joining form here:\n{link}\n\n"
        "Or fill the attached PDF and reply with it. Then we'll register your fingerprint at the reception. ✅\n\n"
        "House of Strength Gym",
    ],
    "greet": [
        "Hi {name}, this is House of Strength Gym. 👋",
        "Hello {name}! Greetings from House of Strength Gym. 💪",
        "Hi {name} 👋 House of Strength Gym here.",
    ],
    "inquiry": [
        "Hi {name}, this is House of Strength Gym. 👋 Thank you for your interest in joining us!\n\n"
        "When would you like to visit? You can also try a free trial session. 💪",

        "Hello {name}! 🏋️ Thanks for reaching out to House of Strength Gym.\n\n"
        "We'd love to show you around. When is a good time for you to drop by? Your first trial session is on us!",

        "Hi {name} 👋 Following up from House of Strength Gym.\n\n"
        "Still thinking about starting your fitness journey? Come in for a free trial and meet our trainers. 🔥",
    ],
    "staff_notice": [
        "Hi {name}, you checked in {minutes} minutes late today ({date}) for your {shift} shift. This is your first late "
        "arrival this month, so please treat this as a NOTICE. Let's be on time from tomorrow. 🙏\nHouse of Strength Gym",

        "Hi {name}, a quick note: today ({date}) you were {minutes} minutes late for the {shift} shift. This is your 1st late "
        "arrival this month (NOTICE). Thank you for being on time going forward.\nHouse of Strength Gym",
    ],
    "staff_warning": [
        "Hi {name}, you were {minutes} minutes late today ({date}) for your {shift} shift. This is your second late arrival "
        "this month, so this is a WARNING. From the next late arrival, {hours} hour(s) of salary will be deducted.\n"
        "House of Strength Gym",

        "Hi {name}, today ({date}) you reached {minutes} minutes after your {shift} shift started. That's your 2nd late arrival "
        "this month (WARNING). Any further late arrival means a {hours}-hour salary deduction.\nHouse of Strength Gym",
    ],
    "staff_deduct": [
        "Hi {name}, you were {minutes} minutes late today ({date}) for your {shift} shift. As this is late arrival no. {n} "
        "this month, {hours} hour(s) of salary ({amount}) will be deducted as per gym policy.\nHouse of Strength Gym",

        "Hi {name}, today ({date}) you were {minutes} minutes late for the {shift} shift (late no. {n} this month). "
        "As per policy, {amount} ({hours} hour) will be deducted from your salary.\nHouse of Strength Gym",
    ],
}


def joined(kind):
    return SEP.join(DEFAULTS.get(kind, []))
