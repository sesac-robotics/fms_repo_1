/** Return the server's permitted steps, including the legacy single-step shape. */
export function availableSteps(run) {
  return run?.availableSteps ?? (run?.nextStep ? [run.nextStep] : []);
}

/** Merge ordered observations, offered branches and remaining catalog steps. */
export function reviewSteps(plan, run) {
  if (!plan) return [];
  const seen = (run?.completed ?? []).map((entry) => entry.step);
  const outcome =
    seen.includes("ROUTE_APPLIED") || seen.includes("ROUTE_FAILED");
  const future = outcome
    ? plan.steps.filter(
        (step) => !["ROUTE_APPLIED", "ROUTE_FAILED"].includes(step),
      )
    : plan.steps;
  return [...new Set([...seen, ...availableSteps(run), ...future])];
}

/** Select an in-place action, an explicit replay, or no action during recovery. */
export function reviewAction(plan, run, step, prepareOnly) {
  if (!plan) return null;
  if (run?.plan === plan.id && !prepareOnly) {
    if (availableSteps(run).includes(step)) return "advance";
    if (["LINK_RESTORED", "RESUME_APPROVED"].includes(run.nextStep))
      return null;
  }
  return plan.steps.includes(step) ? "replay" : null;
}
