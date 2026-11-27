<script setup>
import { computed } from "vue";
import { t } from "../i18n";
import { preferences } from "../preferences";
import { parseVisionReadings } from "../visionReadings";

const props = defineProps({ entries: { type: Array, default: undefined } });
const readings = computed(() => parseVisionReadings(props.entries));
const dateTime = computed(
  () =>
    new Intl.DateTimeFormat(preferences.locale, {
      dateStyle: "short",
      timeStyle: "medium",
    }),
);
</script>

<template>
  <section class="panel" aria-labelledby="vision-readings-title">
    <h2 id="vision-readings-title">{{ t("visionReadings") }}</h2>
    <p v-if="!readings.length">{{ t("visionNoReport") }}</p>
    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">{{ t("vehicle") }}</th>
            <th scope="col">{{ t("visionSource") }}</th>
            <th scope="col">{{ t("visionOutcome") }}</th>
            <th scope="col">{{ t("visionFrame") }}</th>
            <th scope="col">{{ t("visionCapturedAt") }}</th>
            <th scope="col">{{ t("visionReceivedAt") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in readings" :key="row.vehicleNo + ':' + row.source">
            <td>{{ row.vehicleNo }}</td>
            <td>{{ row.source }}</td>
            <td>
              {{ t(row.outcomeKey)
              }}<template v-if="row.label"> ({{ row.label }})</template>
            </td>
            <td>{{ row.frameId }}</td>
            <td>
              <time :datetime="row.capturedAt" :title="row.capturedAt">
                {{ dateTime.format(new Date(row.capturedAt)) }}
              </time>
            </td>
            <td>
              <time :datetime="row.receivedAt" :title="row.receivedAt">
                {{ dateTime.format(new Date(row.receivedAt)) }}
              </time>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
