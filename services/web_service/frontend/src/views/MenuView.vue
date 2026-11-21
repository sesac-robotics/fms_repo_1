<script setup>
import { ref } from "vue";
import { api } from "../api";
import { t } from "../i18n";

defineProps({ items: { type: Array, required: true } });
const emit = defineEmits(["changed"]);
const message = ref("");
const busy = ref(null);

async function save(item, event) {
    const form = new FormData(event.currentTarget);
    const body = {
        ...item,
        labelKo: String(form.get("ko")).trim(),
        labelEn: String(form.get("en")).trim(),
        labelZh: String(form.get("zh")).trim(),
        position: Number(form.get("order")),
        visible: form.has("visible"),
    };
    if (![body.labelKo, body.labelEn, body.labelZh].every(Boolean)) {
        message.value = "error";
        return;
    }
    busy.value = item.key;
    message.value = "";
    try {
        await api("/admin/menu/" + encodeURIComponent(item.key), {
            method: "PUT",
            body,
        });
        message.value = "saved";
        emit("changed");
    } catch {
        message.value = "error";
    } finally {
        busy.value = null;
    }
}
</script>

<template>
    <section class="panel stack">
        <div>
            <h2>{{ t("menu") }}</h2>
            <p class="muted">{{ t("menuHint") }}</p>
        </div>
        <p v-if="message" role="status">{{ t(message) }}</p>
        <p v-if="!items.length">{{ t("empty") }}</p>
        <form
            v-for="item in items"
            :key="item.key"
            class="menu-form"
            @submit.prevent="save(item, $event)"
        >
            <strong>{{ t(item.key) }}</strong>
            <label
                >한국어<input
                    name="ko"
                    required
                    maxlength="80"
                    :value="item.labelKo"
            /></label>
            <label
                >English<input
                    name="en"
                    required
                    maxlength="80"
                    :value="item.labelEn"
            /></label>
            <label
                >简体中文<input
                    name="zh"
                    required
                    maxlength="80"
                    :value="item.labelZh"
            /></label>
            <label
                >{{ t("order")
                }}<input
                    name="order"
                    type="number"
                    required
                    min="0"
                    max="999"
                    :value="item.position"
            /></label>
            <label class="toggle"
                ><input
                    name="visible"
                    type="checkbox"
                    :checked="item.visible"
                />{{ t("visible") }}</label
            >
            <button type="submit" class="primary" :disabled="busy !== null">
                {{ t("save") }}
            </button>
        </form>
    </section>
</template>
