<script setup>
import { computed, ref, watch } from "vue";
import { t } from "../i18n";
import ScenarioReviewEvidence from "./ScenarioReviewEvidence.vue";

const props = defineProps({
  runs: { type: Array, required: true },
  savedRun: { type: Object, default: null },
  busy: Boolean,
});
const emit = defineEmits(["open"]);
const selectedRun = ref("");
const selectedStep = ref("");
const evidence = computed(
  () =>
    props.savedRun?.completed.find((item) => item.step === selectedStep.value)
      ?.evidence,
);

watch(
  () => props.runs,
  (runs) => {
    selectedRun.value = runs[0]?.id ?? "";
  },
  { immediate: true },
);
watch(
  () => props.savedRun,
  (run) => {
    selectedStep.value = run?.completed[0]?.step ?? "";
  },
);
</script>

<template>
  <section class="panel stack">
    <h2>{{ t("reviewHistory") }}</h2>
    <p v-if="!runs.length">{{ t("empty") }}</p>
    <template v-else>
      <label>
        {{ t("reviewRun") }}
        <select v-model="selectedRun" :disabled="busy">
          <option v-for="entry in runs" :key="entry.id" :value="entry.id">
            {{ t(entry.plan) }} · {{ entry.id }}
          </option>
        </select>
      </label>
      <button
        type="button"
        :disabled="busy || !selectedRun"
        @click="emit('open', selectedRun)"
      >
        {{ t("reviewOpenRecord") }}
      </button>
    </template>
    <label v-if="savedRun?.completed.length">
      {{ t("reviewEvidence") }}
      <select v-model="selectedStep" :disabled="busy">
        <option
          v-for="entry in savedRun.completed"
          :key="entry.step"
          :value="entry.step"
        >
          {{ t(entry.step) }}
        </option>
      </select>
    </label>
  </section>
  <ScenarioReviewEvidence
    v-if="savedRun"
    :step="selectedStep"
    :evidence="evidence"
  />
</template>
