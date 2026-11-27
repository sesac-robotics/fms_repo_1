import ko from "./locales/ko";
import en from "./locales/en";
import zh from "./locales/zh";
import reviewKo from "./locales/review-ko";
import reviewEn from "./locales/review-en";
import reviewZh from "./locales/review-zh";
import { preferences } from "./preferences";

const dictionary = { ko, en, "zh-Hans": zh };
const review = { ko: reviewKo, en: reviewEn, "zh-Hans": reviewZh };

export function reviewText(key) {
  return review[preferences.locale][key] ?? t(key);
}

export function t(key) {
  return (
    dictionary[preferences.locale][key] ??
    review[preferences.locale][key] ??
    key ??
    "—"
  );
}

/** Return the localized staff label for an API role code. */
export function staffLabel(role) {
  if (role === "ADMIN") return t("defaultAdmin");
  if (role === "OPERATOR") return t("OPERATOR");
  return t();
}

export function timeOf(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(preferences.locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}
