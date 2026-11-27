import assert from "node:assert/strict";
import test from "node:test";
import { reviewAction, reviewSteps } from "../src/scenarioReviewSteps.js";

const plan = {
  id: "TAXI_APPLIED",
  steps: ["STOP_WAIT", "ROUTE_APPLIED", "REDEPART"],
};

test("plays an offered branch on the current run, outside the catalog path", () => {
  const run = {
    plan: plan.id,
    nextStep: "ROUTE_APPLIED",
    availableSteps: ["ROUTE_APPLIED", "ROUTE_FAILED"],
    completed: [{ step: "STOP_WAIT" }],
  };
  assert.deepEqual(reviewSteps(plan, run), [
    "STOP_WAIT",
    "ROUTE_APPLIED",
    "ROUTE_FAILED",
    "REDEPART",
  ]);
  assert.equal(reviewAction(plan, run, "ROUTE_FAILED", false), "advance");
  assert.equal(reviewAction(plan, run, "ROUTE_FAILED", true), null);
});

test("keeps the chosen outcome and prevents accidental replay during recovery", () => {
  const run = {
    plan: plan.id,
    nextStep: "RESUME_APPROVED",
    availableSteps: ["RESUME_APPROVED"],
    completed: [{ step: "STOP_WAIT" }, { step: "ROUTE_FAILED" }],
  };
  assert.deepEqual(reviewSteps(plan, run), [
    "STOP_WAIT",
    "ROUTE_FAILED",
    "RESUME_APPROVED",
    "REDEPART",
  ]);
  assert.equal(reviewAction(plan, run, "REDEPART", false), null);
  assert.equal(reviewAction(plan, run, "RESUME_APPROVED", false), "advance");
});
