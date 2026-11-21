<script setup>
import { nextTick, ref } from "vue";
import { api } from "../api";
import { installGoogleButton } from "../google";
import { t } from "../i18n";
import { preferences } from "../preferences";

const element = ref(null);
const state = ref("");
const shown = ref(false);

async function link() {
    state.value = "";
    try {
        const { clientId } = await api("/auth/google/config");
        if (!clientId) {
            state.value = "googleMissing";
            return;
        }
        shown.value = true;
        await nextTick();
        await installGoogleButton(element.value, {
            clientId,
            locale: preferences.locale,
            theme: preferences.theme,
            credential: async (credential) => {
                try {
                    await api("/auth/google/link", {
                        method: "POST",
                        body: { credential },
                    });
                    state.value = "googleLinked";
                    shown.value = false;
                } catch {
                    state.value = "googleError";
                }
            },
        });
    } catch {
        state.value = "googleError";
        shown.value = false;
    }
}
</script>

<template>
    <div class="stack">
        <div>
            <button type="button" @click="link">{{ t("googleLink") }}</button>
        </div>
        <div v-if="shown" ref="element" class="google-button"></div>
        <p v-if="state" role="status">{{ t(state) }}</p>
    </div>
</template>
