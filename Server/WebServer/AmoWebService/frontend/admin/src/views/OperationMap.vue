<script setup>
import { computed } from "vue";
import { preferences } from "../preferences";
import { t } from "../i18n";
import { dimensions, mapPoint } from "../mapGeometry";

const props = defineProps({
  vehicles: { type: Array, default: () => [] },
  lines: { type: Array, default: () => [] },
  demo: Boolean,
  animate: Boolean,
});
const imageUrl = computed(
  () => `/amode-map-v02-fms-${preferences.locale}-${preferences.theme}.svg`,
);
// Clear the four fixed stop labels in the shared v0.2 design before painting a route.
const stopLabels = [
  [260, 563],
  [829, 563],
  [280, 774],
  [894, 848],
];
const markers = computed(() => {
  if (!props.demo) return [];
  return props.vehicles.flatMap((vehicle) => {
    const point = mapPoint(vehicle);
    if (!point) return [];
    const [x, y] = point;
    return [
      {
        id: vehicle.id,
        vehicleNo: vehicle.vehicleNo,
        style: {
          left: `${(x / dimensions.width) * 100}%`,
          top: `${(y / dimensions.height) * 100}%`,
        },
        placeBelow: y < 105,
      },
    ];
  });
});
</script>

<template>
  <section class="panel operation-map">
    <h2>{{ t("map") }}</h2>
    <slot />
    <div class="map">
      <svg
        v-if="lines.length"
        class="route-layer"
        :viewBox="`0 0 ${dimensions.width} ${dimensions.height}`"
        role="img"
        :aria-label="`${t('map')} · ${t('routeRecorded')}`"
      >
        <use :href="imageUrl + '#map-geometry'" aria-hidden="true" />
        <defs>
          <mask
            id="stop-label-clearance"
            maskUnits="userSpaceOnUse"
            x="0"
            y="0"
            v-bind="dimensions"
          >
            <rect v-bind="dimensions" fill="white" />
            <rect
              v-for="[x, y] in stopLabels"
              :key="x"
              :x="x - 23"
              :y="y - 16"
              width="46"
              height="32"
              rx="5"
              fill="black"
            />
          </mask>
        </defs>
        <g mask="url(#stop-label-clearance)">
          <g v-for="(line, index) in lines" :key="index" class="route-line">
            <polyline class="route-halo" :points="line" />
            <polyline class="route-trace" :points="line" />
          </g>
        </g>
        <use :href="imageUrl + '#map-labels'" aria-hidden="true" />
      </svg>
      <img v-else :src="imageUrl" :alt="t('map')" />
      <span
        v-for="marker in markers"
        :key="marker.id"
        class="map-marker"
        :class="{
          'map-marker-below': marker.placeBelow,
          'map-marker-moving': animate,
        }"
        :style="marker.style"
      >
        <span class="map-marker-name">{{ marker.vehicleNo }}</span>
      </span>
    </div>
    <p class="map-caption muted">{{ t("mapNote") }}</p>
    <ul class="map-key" :aria-label="t('mapLegend')">
      <li><span class="key-stop"></span>{{ t("mapStopLine") }}</li>
      <li><span class="key-junction"></span>{{ t("mapJunction") }}</li>
      <li v-if="lines.length">
        <span class="key-route"></span>{{ t("routeRecorded") }}
      </li>
      <li v-if="markers.length">
        <span class="key-vehicle"></span>{{ t("mapDemoVehicle") }}
      </li>
    </ul>
  </section>
</template>
