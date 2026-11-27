<script setup>
import { onBeforeUnmount, ref } from "vue";
import { api } from "../api";
import { t, timeOf } from "../i18n";

const props = defineProps({ resource: { type: String, required: true } });
const size = 50;
const offset = ref(0);
const matching = ref(0);
const rows = ref([]);
const query = ref("");
const from = ref("");
const until = ref("");
const loading = ref(false);
const error = ref(false);
let current;

async function read(target) {
  current?.abort();
  const request = new AbortController();
  current = request;
  loading.value = true;
  error.value = false;
  const params = new URLSearchParams({
    q: query.value.trim(),
    limit: size,
    offset: target,
  });
  if (from.value) params.set("from", from.value + "T00:00:00Z");
  if (until.value) params.set("until", until.value + "T00:00:00Z");
  try {
    const result = await api("/operations/" + props.resource + "?" + params, {
      signal: request.signal,
    });
    if (request !== current) return;
    offset.value = target;
    rows.value = result.rows;
    matching.value = result.matching;
  } catch {
    if (request === current) error.value = true;
  } finally {
    if (request === current) loading.value = false;
  }
}

onBeforeUnmount(() => {
  current?.abort();
  current = null;
});
</script>

<template>
  <section class="panel stack">
    <form class="actions" @submit.prevent="read(0)">
      <label
        >{{ t("historySearch") }} <input v-model="query" maxlength="100"
      /></label>
      <label>{{ t("fromUtc") }} <input v-model="from" type="date" /></label>
      <label>{{ t("untilUtc") }} <input v-model="until" type="date" /></label>
      <button :disabled="loading">{{ t("historySearch") }}</button>
    </form>
    <p v-if="error" role="alert">{{ t("error") }}</p>
    <p role="status">{{ t("matchingRows") }} {{ matching }}</p>
    <ul v-if="rows.length">
      <li v-for="row in rows" :key="row.id">
        <template v-if="resource === 'trip-history'">
          #{{ row.id }} · {{ row.serviceType }} · {{ t(row.status) }} ·
          {{ timeOf(row.receivedAt) }}
        </template>
        <template v-else>
          {{ row.name }} · {{ timeOf(row.recordedAt) }} · {{ row.passed }}/{{
            row.total
          }}
          · {{ row.latencyMs }} ms
        </template>
      </li>
    </ul>
    <div class="actions">
      <button
        type="button"
        :disabled="loading || offset === 0"
        @click="read(offset - size)"
      >
        {{ t("previousPage") }}
      </button>
      <button
        type="button"
        :disabled="loading || offset + size >= matching"
        @click="read(offset + size)"
      >
        {{ t("next") }}
      </button>
    </div>
  </section>
</template>
