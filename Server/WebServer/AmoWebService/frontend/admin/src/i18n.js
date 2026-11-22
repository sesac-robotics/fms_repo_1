import ko from "./locales/ko";
import en from "./locales/en";
import zh from "./locales/zh";
import { preferences } from "./preferences";

const dictionary = { ko, en, "zh-Hans": zh };
export function t(key) {
  return dictionary[preferences.locale][key] ?? key ?? "—";
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
