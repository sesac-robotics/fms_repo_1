import { reactive, watch } from "vue";

export const languages = [
    { code: "ko", label: "한국어" },
    { code: "en", label: "English" },
    { code: "zh-Hans", label: "简体中文" },
];

const storageKey = "amo.admin.preferences";
const defaults = {
    locale: navigator.language.startsWith("zh")
        ? "zh-Hans"
        : navigator.language.startsWith("en")
          ? "en"
          : "ko",
    theme: matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light",
    tutorialEnabled: true,
    tutorialSeen: false,
};

function restore() {
    try {
        const read = JSON.parse(localStorage.getItem(storageKey) ?? "{}");
        return {
            locale: languages.some(({ code }) => code === read.locale)
                ? read.locale
                : defaults.locale,
            theme: ["light", "dark"].includes(read.theme)
                ? read.theme
                : defaults.theme,
            tutorialEnabled: read.tutorialEnabled !== false,
            tutorialSeen: read.tutorialSeen === true,
        };
    } catch {
        return defaults;
    }
}

export const preferences = reactive(restore());
watch(
    preferences,
    (value) => {
        const root = document.documentElement;
        root.lang = value.locale;
        root.dataset.theme = value.theme;
        try {
            localStorage.setItem(storageKey, JSON.stringify(value));
        } catch {
            // Keep the current browser tab usable when storage is unavailable.
        }
    },
    { immediate: true },
);
