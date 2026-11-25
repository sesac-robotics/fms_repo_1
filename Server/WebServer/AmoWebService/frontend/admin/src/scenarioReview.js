import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "./api";

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

  function advance(step, manual = false) {
    return request(`/runs/${run.value.id}/steps/${step}`, { manual });
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

  function selectStep(step, { evidenceOnly, manual, prepareOnly }) {
    if (busy.value) return;
    selected.value = step;
    if (evidenceOnly) return;
    return act(async () => {
      if (
        prepareOnly ||
        run.value?.plan !== planId.value ||
        run.value?.nextStep !== step
      ) {
        await start(planId.value, step);
        const prefix = plans.value.find(
          (plan) => plan.id === planId.value,
        ).steps;
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
        run.value = await advance(step, manual);
        await snapshot();
      }
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
    load,
    newRun,
    selectStep,
  };
}
