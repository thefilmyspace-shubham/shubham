// academics texts in English, Hindi (Devanagari) and Hinglish (Roman).
// Every key in `en` must be in `hi` and `hinglish` too (TypeScript checks it).

export const en = {} satisfies Record<string, string>;

export const hi: Record<keyof typeof en, string> = {};

export const hinglish: Record<keyof typeof en, string> = {};
