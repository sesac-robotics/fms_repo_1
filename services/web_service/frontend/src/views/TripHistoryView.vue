<script setup>
import { computed, ref, watch } from "vue";
import { api } from "../api";
import { routeLines } from "../mapGeometry";
import { t } from "../i18n";
import OperationMap from "./OperationMap.vue";
import EventTimeline from "./EventTimeline.vue";

const props = defineProps({ data: { type: Object, required: true } });
const picked = ref("");
const route = ref(null);
const state = ref("idle");
const requests = computed(() => props.data.requests ?? []);
const selected = computed(
    () =>
        requests.value.find(({ id }) => String(id) === picked.value) ??
        requests.value[0],
);
const selectedId = computed(() => selected.value?.id);
const lines = computed(() => routeLines(route.value, selectedId.value));
const timeline = computed(() =>
    (props.data.events ?? [])
        .filter(
            ({ requestId }) =>
                selectedId.value != null &&
                String(requestId) === String(selectedId.value),
        )
        .sort((a, b) => Date.parse(a.time) - Date.parse(b.time)),
);
const message = computed(() => {
    if (state.value === "loading") return "routeLoading";
    if (state.value === "error") return "routeError";
    if (!lines.value.length) return "routeEmpty";
    return route.value.truncated ? "routePartial" : "routeRecordedNote";
});

watch(
    [selectedId, () => props.data],
    async ([id], _, onCleanup) => {
        route.value = null;
        if (id == null) {
            state.value = "idle";
            return;
        }
        const request = new AbortController();
        onCleanup(() => request.abort());
        state.value = "loading";
        try {
            const detail = await api(
                `/operations/requests/${encodeURIComponent(id)}/route`,
                {
                    signal: request.signal,
                },
            );
            if (request.signal.aborted) return;
            route.value = detail;
            state.value = "ready";
        } catch {
            if (!request.signal.aborted) state.value = "error";
        }
    },
    { immediate: true, flush: "sync" },
);

function description(request) {
    return `#${request.id} · ${t(request.pickup)} → ${t(request.destination)}`;
}
</script>

<template>
    <div class="operation-grid trip-grid">
        <OperationMap :lines="lines">
            <p v-if="selected" class="route-note" role="status">
                {{ t(message) }}
            </p>
        </OperationMap>
        <section class="panel trip-detail">
            <h2>{{ t("tripRecord") }}</h2>
            <label v-if="requests.length">
                {{ t("tripSelect") }}
                <select
                    :value="String(selected.id)"
                    @change="picked = $event.target.value"
                >
                    <option
                        v-for="request in requests"
                        :key="request.id"
                        :value="String(request.id)"
                    >
                        {{ description(request) }}
                    </option>
                </select>
            </label>
            <p v-else>{{ t("empty") }}</p>
            <template v-if="selected">
                <dl class="details">
                    <dt>{{ t("pickup") }}</dt>
                    <dd>{{ t(selected.pickup) }}</dd>
                    <dt>{{ t("destination") }}</dt>
                    <dd>{{ t(selected.destination) }}</dd>
                    <dt>{{ t("status") }}</dt>
                    <dd>{{ t(selected.status) }}</dd>
                </dl>
                <EventTimeline :events="timeline" :title="t('tripTimeline')" />
            </template>
        </section>
    </div>
</template>
