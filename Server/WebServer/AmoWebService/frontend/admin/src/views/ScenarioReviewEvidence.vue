<script setup>
import { reviewText, t, timeOf } from "../i18n";

defineProps({
  step: { type: String, default: "" },
  evidence: { type: Object, default: null },
});

const details = [
  "event",
  "status",
  "reason",
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
</script>

<template>
  <section class="panel">
    <h2>{{ t("reviewEvidence") }} · {{ t(step || null) }}</h2>
    <p v-if="step">{{ reviewText("review_expect_" + step.toLowerCase()) }}</p>
    <p v-if="!evidence">{{ t("empty") }}</p>
    <dl v-else class="details">
      <template
        v-for="key in details.filter((item) => evidence[item] != null)"
        :key="key"
      >
        <dt>{{ reviewText(key) }}</dt>
        <dd>
          {{ key === "observedAt" ? timeOf(evidence[key]) : t(evidence[key]) }}
        </dd>
      </template>
    </dl>
  </section>
</template>
