<script setup>
import { computed, ref } from "vue";
import { reviewText, t, timeOf } from "../i18n";
import { useScenarioReview } from "../scenarioReview";
import OperationMap from "./OperationMap.vue";

const {
  plans,
  planId,
  run,
  selected,
  vehicles,
  busy,
  error,
  mapError,
  load,
  newRun,
  selectStep,
} = useScenarioReview();
const evidenceOnly = ref(false);
const manual = ref(false);
const plan = computed(() =>
  plans.value.find((entry) => entry.id === planId.value),
);
const currentRun = computed(() =>
  run.value?.plan === planId.value ? run.value : null,
);
const observations = computed(() => currentRun.value?.completed ?? []);
const evidence = computed(
  () =>
    observations.value.find((entry) => entry.step === selected.value)?.evidence,
);
const stage = computed(() => observations.value.at(-1)?.step);
const activeVehicles = computed(() =>
  vehicles.value.filter(
    (vehicle) =>
      vehicle.vehicleNo === currentRun.value?.vehicleNumber &&
      vehicle.sample?.epoch === `review-${currentRun.value?.id}`,
  ),
);
const details = [
  "event",
  "status",
  "observedAt",
  "tripId",
  "quoteId",
  "paymentStatus",
  "amountMinor",
  "deltaMinor",
  "currencyCode",
  "proposedDestination",
  "effectiveDestination",
  "revisionId",
  "commandId",
  "cycleId",
  "batteryPercent",
  "receiptReference",
  "distanceMeters",
  "durationSeconds",
];

function choose(step, prepareOnly = false) {
  selectStep(step, {
    prepareOnly,
    evidenceOnly: evidenceOnly.value && !prepareOnly,
    manual: manual.value && plan.value.manualSteps.includes(step),
  });
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
          :disabled="busy || !selected"
          @click="choose(selected, true)"
        >
          {{ t("reviewPrepare") }}
        </button>
        <button type="button" :disabled="busy" @click="load">
          {{ t("refresh") }}
        </button>
      </div>
      <label
        ><input v-model="evidenceOnly" type="checkbox" :disabled="busy" />
        {{ t("reviewEvidenceOnly") }}</label
      >
      <label
        ><input v-model="manual" type="checkbox" :disabled="busy" />
        {{ t("reviewManual") }}</label
      >
      <p v-if="error" role="alert">{{ t("reviewError") }}</p>
      <p v-if="busy" role="status">{{ t("busy") }}</p>
      <ol class="review-steps">
        <li v-for="step in plan?.steps" :key="step">
          <button
            type="button"
            :disabled="busy"
            :aria-pressed="step === selected"
            @click="choose(step)"
          >
            <span aria-hidden="true">{{
              observations.some((entry) => entry.step === step)
                ? "✓"
                : currentRun?.nextStep === step
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
      <section class="panel">
        <h2>{{ t("reviewEvidence") }} · {{ t(selected || null) }}</h2>
        <p v-if="selected">
          {{ reviewText("review_expect_" + selected.toLowerCase()) }}
        </p>
        <p v-if="!evidence">{{ t("empty") }}</p>
        <dl v-else class="details">
          <template
            v-for="key in details.filter((item) => evidence[item] != null)"
            :key="key"
          >
            <dt>{{ reviewText(key) }}</dt>
            <dd>
              {{
                key === "observedAt" ? timeOf(evidence[key]) : t(evidence[key])
              }}
            </dd>
          </template>
        </dl>
      </section>
    </div>
  </div>
</template>
