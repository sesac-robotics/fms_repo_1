<script setup>
import { languages, preferences } from "../preferences";
import { t } from "../i18n";
import GoogleLink from "./GoogleLink.vue";
defineEmits(["replay", "menus"]);
defineProps({ admin: Boolean });
</script>

<template>
    <section class="panel settings-panel">
        <h1>{{ t("settings") }}</h1>
        <label
            >{{ t("language") }}
            <select v-model="preferences.locale">
                <option
                    v-for="language in languages"
                    :key="language.code"
                    :value="language.code"
                >
                    {{ language.label }}
                </option>
            </select>
        </label>
        <label
            >{{ t("appearance") }}
            <select v-model="preferences.theme">
                <option value="light">{{ t("light") }}</option>
                <option value="dark">{{ t("dark") }}</option>
            </select>
        </label>
        <label class="toggle"
            ><input v-model="preferences.tutorialEnabled" type="checkbox" />{{
                t("showTutorial")
            }}</label
        >
        <div class="actions">
            <button type="button" @click="$emit('replay')">
                {{ t("replay") }}
            </button>
            <button v-if="admin" type="button" @click="$emit('menus')">
                {{ t("menu") }}
            </button>
        </div>
        <GoogleLink />
    </section>
</template>
