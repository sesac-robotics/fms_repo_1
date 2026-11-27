import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "./api";
import { reviewAction } from "./scenarioReviewSteps";

const root = "/admin/demo/scenarios";

export function useScenarioReview() {
  const plans = ref([]);
  const planId = ref("");
  const run = ref(null);
  const selected = ref("");
  const busy = ref(false);
  const error = ref(false);
  const mapError = ref(false);
  const playback = ref(null);
  const history = ref(null);
  const savedRun = ref(null);
  const resetDone = ref(false);
  const controller = new AbortController();
  let uncertainStart;

  function request(path = "", body) {
    return api(root + path, {
      ...(body === undefined ? {} : { method: "POST", body }),
      signal: controller.signal,
    });
  }

  async function snapshot() {
    try {
      const data = await api("/operations", { signal: controller.signal });
      playback.value = data.review;
      mapError.value = false;
      await nextTick();
    } catch {
      if (!controller.signal.aborted) mapError.value = true;
    }
  }

  async function act(action) {
    if (busy.value || controller.signal.aborted) return;
    busy.value = true;
    error.value = false;
    resetDone.value = false;
    try {
      await action();
    } catch {
      if (!controller.signal.aborted) error.value = true;
    } finally {
      busy.value = false;
    }
  }

  async function load() {
    await act(async () => {
      const data = await request();
      plans.value = data.plans;
      run.value = data.latest;
      planId.value = run.value?.plan ?? data.plans[0]?.id ?? "";
      selected.value =
        run.value?.nextStep ??
        data.plans.find((plan) => plan.id === planId.value)?.steps[0] ??
        "";
      await snapshot();
    });
  }

  function advance(step) {
    return request(`/runs/${run.value.id}/steps/${step}`, {});
  }

  async function start(plan, target) {
    if (uncertainStart?.plan !== plan || uncertainStart?.target !== target)
      uncertainStart = { plan, target, id: crypto.randomUUID() };
    run.value = await request("/runs", { plan, id: uncertainStart.id });
    uncertainStart = undefined;
  }

  function newRun() {
    return act(async () => {
      await start(planId.value, null);
      selected.value = run.value.nextStep;
      await snapshot();
    });
  }

  function selectStep(step, { evidenceOnly, prepareOnly }) {
    if (busy.value) return;
    selected.value = step;
    if (evidenceOnly) return;
    const plan = plans.value.find((entry) => entry.id === planId.value);
    const action = reviewAction(plan, run.value, step, prepareOnly);
    if (!action) return;
    return act(async () => {
      if (action === "replay") {
        await start(planId.value, step);
        const prefix = plan.steps;
        while (run.value.nextStep && run.value.nextStep !== step) {
          const index = prefix.indexOf(run.value.nextStep);
          if (index < 0 || index >= prefix.indexOf(step))
            throw new Error("Review cursor is outside the selected prefix");
          const previous = run.value.nextStep;
          run.value = await advance(previous);
          if (run.value.nextStep === previous)
            throw new Error("Review cursor did not advance");
        }
        if (run.value.nextStep !== step)
          throw new Error("Selected review step is unavailable");
        await snapshot();
        // Commit the predecessor marker to the browser before changing coordinates.
        await new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        );
      }
      if (!prepareOnly && !controller.signal.aborted) {
        run.value = await advance(step);
        await snapshot();
      }
    });
  }

  function loadHistory() {
    return act(async () => {
      history.value = (await request("/history")).runs;
      savedRun.value = null;
    });
  }

  function openSavedRun(id) {
    if (!history.value?.some((entry) => entry.id === id)) return;
    return act(async () => {
      savedRun.value = await request(`/runs/${encodeURIComponent(id)}`);
    });
  }

  async function finishReset() {
    run.value = null;
    history.value = null;
    savedRun.value = null;
    uncertainStart = undefined;
    playback.value = null;
    resetDone.value = true;
    await snapshot();
  }

  function resetCurrent() {
    if (!run.value) return;
    return act(async () => {
      await request(`/runs/${encodeURIComponent(run.value.id)}/reset`, {});
      await finishReset();
    });
  }

  function resetHistory(confirm) {
    return act(async () => {
      const { history: counts } = await request();
      if (!counts.runs || !confirm(counts)) return;
      await request("/history/reset", counts);
      await finishReset();
    });
  }

  onMounted(load);
  onBeforeUnmount(() => controller.abort());

  return {
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
  };
}
