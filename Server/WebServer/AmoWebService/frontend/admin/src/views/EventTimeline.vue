<script setup>
import { t, timeOf } from "../i18n";
defineProps({
  events: { type: Array, required: true },
  title: { type: String, required: true },
});
</script>

<template>
  <section class="event-timeline">
    <h2>{{ title }}</h2>
    <p v-if="!events.length">{{ t("empty") }}</p>
    <ol v-else>
      <li v-for="event in events" :key="event.id">
        <time :datetime="event.time">{{ timeOf(event.time) }}</time>
        <strong>{{ t(event.type) }}</strong>
        <small v-if="event.vehicle">{{ event.vehicle }}</small>
        <p v-if="event.detail">{{ t(event.detail) }}</p>
      </li>
    </ol>
  </section>
</template>
