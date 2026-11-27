<script setup>
import { computed, ref } from "vue";
import { t } from "../i18n";
import { useScenarioReview } from "../scenarioReview";
import { availableSteps, reviewSteps } from "../scenarioReviewSteps";
import OperationMap from "./OperationMap.vue";
import ScenarioReviewEvidence from "./ScenarioReviewEvidence.vue";
import ScenarioReviewHistory from "./ScenarioReviewHistory.vue";

const {
  plans,
  planId,
  run,
  selected,
  playback,
  busy,
  error,
  mapError,
  history,
  savedRun,
  resetDone,
  load,
  newRun,
  selectStep,
  loadHistory,
  openSavedRun,
  resetCurrent,
  resetHistory,
} = useScenarioReview();
const evidenceOnly = ref(false);
const plan = computed(() =>
  plans.value.find((entry) => entry.id === planId.value),
);
const currentRun = computed(() =>
  run.value?.plan === planId.value ? run.value : null,
);
const observations = computed(() => currentRun.value?.completed ?? []);
const offered = computed(() => availableSteps(currentRun.value));
const steps = computed(() => reviewSteps(plan.value, currentRun.value));
const evidence = computed(
  () =>
    observations.value.find((entry) => entry.step === selected.value)?.evidence,
);
const stage = computed(() => observations.value.at(-1)?.step);
const activeVehicles = computed(() => {
  const review = playback.value;
  if (review?.runId !== currentRun.value?.id || !review?.schematicPoint)
    return [];
  return [
    { id: review.runId, vehicleNo: review.vehicle, ...review.schematicPoint },
  ];
});
function choose(step, prepareOnly = false) {
  selectStep(step, {
    prepareOnly,
    evidenceOnly: evidenceOnly.value && !prepareOnly,
  });
}

function confirmReset() {
  resetHistory(({ runs, observations }) =>
    window.confirm(
      `${t("reviewResetConfirm")}\n${t("reviewHistory")}: ${runs} · ${t("reviewEvidence")}: ${observations}`,
    ),
  );
}
</script>

<template>
  <div class="operation-grid">
    <section class="panel stack" :aria-busy="busy">
      <label>
        {{ t("reviewPlan") }}
        <select
          v-model="planId"
          :disabled="busy"
          @change="selected = plan?.steps[0] ?? ''"
        >
          <option v-for="entry in plans" :key="entry.id" :value="entry.id">
            {{ t(entry.id) }}
          </option>
        </select>
      </label>
      <div class="actions">
        <button type="button" :disabled="busy || !plan" @click="newRun">
          {{ t("reviewStart") }}
        </button>
        <button
          type="button"
          :disabled="busy || !plan?.steps.includes(selected)"
          @click="choose(selected, true)"
        >
          {{ t("reviewPrepare") }}
        </button>
        <button type="button" :disabled="busy" @click="load">
          {{ t("refresh") }}
        </button>
        <button type="button" :disabled="busy" @click="loadHistory">
          {{ t("reviewHistory") }}
        </button>
        <button type="button" :disabled="busy || !run" @click="resetCurrent">
          {{ t("reviewCloseCurrent") }}
        </button>
        <button type="button" :disabled="busy" @click="confirmReset">
          {{ t("reviewResetHistory") }}
        </button>
      </div>
      <label
        ><input v-model="evidenceOnly" type="checkbox" :disabled="busy" />
        {{ t("reviewEvidenceOnly") }}</label
      >
      <p v-if="error" role="alert">{{ t("reviewError") }}</p>
      <p v-if="busy" role="status">{{ t("busy") }}</p>
      <p v-if="resetDone" role="status">{{ t("reviewResetDone") }}</p>
      <ol class="review-steps">
        <li v-for="step in steps" :key="step">
          <button
            type="button"
            :disabled="busy"
            :aria-pressed="step === selected"
            @click="choose(step)"
          >
            <span aria-hidden="true">{{
              observations.some((entry) => entry.step === step)
                ? "✓"
                : offered.includes(step)
                  ? "▶"
                  : "·"
            }}</span>
            {{ t(step) }}
          </button>
        </li>
      </ol>
    </section>
    <div class="stack">
      <OperationMap :vehicles="activeVehicles" animate>
        <p v-if="currentRun" role="status">
          {{ currentRun.vehicleNumber }} · {{ t(stage) }}
          <span v-if="currentRun.requestId">
            · {{ t("requests") }} #{{ currentRun.requestId }}</span
          >
        </p>
        <p v-if="mapError" role="alert">{{ t("error") }}</p>
      </OperationMap>
      <ScenarioReviewEvidence :step="selected" :evidence="evidence" />
      <ScenarioReviewHistory
        v-if="history"
        :runs="history"
        :saved-run="savedRun"
        :busy="busy"
        @open="openSavedRun"
      />
    </div>
  </div>
</template>
