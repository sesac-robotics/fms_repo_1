<script setup>
import { computed } from "vue";
import TripHistoryView from "./TripHistoryView.vue";
import OperationMap from "./OperationMap.vue";
import HistoryBrowse from "./HistoryBrowse.vue";
import TestResults from "./TestResults.vue";
import { t, timeOf } from "../i18n";
const props = defineProps({
  data: { type: Object, required: true },
  view: { type: String, required: true },
  demo: Boolean,
});

const requests = computed(() => props.data.requests || []);
const visibleEvents = computed(() => props.data.events || []);
const reportedEvents = new Set([
  "VEHICLE_STOP_CONFIRMED",
  "STOP_CONFIRMED",
  "TRIP_STARTED",
  "TRIP_ENDED",
  "TRIP_COMPLETED",
  "JUNCTION_EXIT",
]);
function measurement(value, unit) {
  return Number.isFinite(value) ? value.toFixed(3) + " " + unit : "—";
}

function eventKind(kind) {
  if (reportedEvents.has(kind)) {
    return t(props.demo ? "simulatedObservation" : "observed");
  }
  return ["CALL_RECEIVED", "REQUEST_RECEIVED"].includes(kind) ||
    kind?.endsWith("REQUESTED")
    ? t("reception")
    : "";
}
</script>

<template>
  <div class="stack">
    <HistoryBrowse
      v-if="view === 'trips'"
      key="trip-history"
      resource="trip-history"
    />
    <HistoryBrowse
      v-if="view === 'tests'"
      key="test-history"
      resource="test-history"
    />
    <TripHistoryView v-if="view === 'trips'" :data="data" />
    <template v-if="view === 'overview'">
      <div class="operation-grid">
        <OperationMap :vehicles="data.vehicles || []" :demo="demo" />
        <section class="panel">
          <h2>{{ t("vehicles") }}</h2>
          <p v-if="!data.vehicles?.length">{{ t("empty") }}</p>
          <article
            v-for="vehicle in data.vehicles"
            :key="vehicle.id"
            class="vehicle"
          >
            <strong>{{ vehicle.vehicleNo }}</strong>
            <span
              class="state"
              :class="{
                warning: vehicle.connection === 'DISCONNECTED',
              }"
              >{{ t(vehicle.status) }}</span
            >
            <small
              >{{ t(vehicle.connection) }} · {{ t("battery") }}
              {{ vehicle.batteryPercent ?? "—" }}%</small
            >
            <small
              >{{ t("reportedYaw") }} {{ measurement(vehicle.yawRad, "rad") }} ·
              {{ t("reportedSpeed") }}
              {{ measurement(vehicle.speedMps, "m/s") }}</small
            >
          </article>
          <h2 class="group-heading">{{ t("requests") }}</h2>
          <p v-if="!requests.length">{{ t("empty") }}</p>
          <article
            v-for="request in requests"
            :key="request.id"
            class="vehicle"
          >
            <strong
              >{{ t(request.pickup) }} → {{ t(request.destination) }}</strong
            >
            <small>{{ t(request.status) }}</small>
          </article>
        </section>
      </div>
    </template>
    <section v-if="view === 'logs' || view === 'overview'" class="panel">
      <h2>{{ t("logs") }}</h2>
      <p v-if="!visibleEvents.length">{{ t("empty") }}</p>
      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{{ t("time") }}</th>
              <th>{{ t("vehicle") }}</th>
              <th>{{ t("event") }}</th>
              <th>{{ t("detail") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in visibleEvents" :key="item.id">
              <td>{{ timeOf(item.time) }}</td>
              <td>{{ item.vehicle || "—" }}</td>
              <td>
                <strong>{{ t(item.type) }}</strong
                ><small v-if="eventKind(item.type)">{{
                  eventKind(item.type)
                }}</small>
              </td>
              <td>{{ t(item.detail) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <TestResults
      v-if="view === 'tests'"
      :results="data.tests || []"
      :events="visibleEvents.slice(0, 4)"
    />
    <section v-if="view === 'codes'" class="panel">
      <h2>{{ t("codes") }}</h2>
      <dl class="details">
        <template v-for="station in ['S1', 'S2', 'S3', 'S4']" :key="station">
          <dt>{{ station }}</dt>
          <dd>{{ t(station) }}</dd>
        </template>
      </dl>
    </section>
  </div>
</template>
