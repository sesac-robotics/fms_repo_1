<script setup>
import { t } from "../i18n";
import { preferences } from "../preferences";
import EventTimeline from "./EventTimeline.vue";

defineProps({
  results: { type: Array, required: true },
  events: { type: Array, required: true },
});

function passRate(result) {
  if (result.total <= 0) return "—";
  return new Intl.NumberFormat(preferences.locale, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(result.pass / result.total);
}
</script>

<template>
  <div class="operation-grid test-grid">
    <section class="panel test-summary">
      <h2>{{ t("testSummary") }}</h2>
      <p v-if="!results.length">{{ t("empty") }}</p>
      <article v-for="result in results" :key="result.name" class="result">
        <div class="result-title">
          <strong>{{ t(result.name) }}</strong>
          <small
            >{{ result.pass }} / {{ result.total }} ·
            {{ passRate(result) }}</small
          >
        </div>
        <progress
          v-if="result.total > 0"
          :value="result.pass"
          :max="result.total"
          :aria-label="t(result.name)"
        ></progress>
        <small
          >{{ t("latency") }} {{ result.latencyMs }} {{ t("unitMs") }}</small
        >
      </article>
      <p v-if="results.length" class="muted">
        {{ t("modelComparisonEmpty") }}
      </p>
    </section>
    <aside class="panel">
      <EventTimeline :events="events" :title="t('recentLogs')" />
    </aside>
  </div>
</template>
