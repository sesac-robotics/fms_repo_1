<script setup>
import { onMounted, ref } from "vue";
import { t } from "../i18n";
const dialog = ref(null);
const step = ref(0);
const keys = ["stepOverview", "stepLogs", "stepMenu"];
const emit = defineEmits(["finish"]);
onMounted(() => dialog.value.showModal());

function close() {
  dialog.value.close();
  emit("finish");
}
</script>

<template>
  <dialog ref="dialog" aria-labelledby="guide-title" @cancel.prevent="close">
    <h2 id="guide-title">{{ t("tutorial") }}</h2>
    <p class="muted">{{ step + 1 }} / {{ keys.length }}</p>
    <p>{{ t(keys[step]) }}</p>
    <div class="actions">
      <button type="button" @click="close">{{ t("skip") }}</button>
      <button
        class="primary"
        type="button"
        @click="step === keys.length - 1 ? close() : step++"
      >
        {{ t(step === keys.length - 1 ? "done" : "next") }}
      </button>
    </div>
  </dialog>
</template>
