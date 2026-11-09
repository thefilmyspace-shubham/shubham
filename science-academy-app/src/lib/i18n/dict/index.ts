// All UI texts, one file per area. Each area file has en, hi and hinglish.
import * as academics from "./academics";
import * as admin from "./admin";
import * as core from "./core";
import * as fees from "./fees";
import * as groups from "./groups";
import * as students from "./students";

export const DICT_EN = { ...core.en, ...students.en, ...fees.en, ...academics.en, ...groups.en, ...admin.en };
export type DictKey = keyof typeof DICT_EN;
export const DICT_HI: Record<DictKey, string> = { ...core.hi, ...students.hi, ...fees.hi, ...academics.hi, ...groups.hi, ...admin.hi };
export const DICT_HINGLISH: Record<DictKey, string> = {
  ...core.hinglish,
  ...students.hinglish,
  ...fees.hinglish,
  ...academics.hinglish,
  ...groups.hinglish,
  ...admin.hinglish,
};
