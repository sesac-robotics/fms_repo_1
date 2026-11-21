import assert from "node:assert/strict";
import test from "node:test";
import { board, mapPoint, routeLines } from "../src/mapGeometry.js";

const bottomLeft = { xM: 0, yM: 0 };
const topRight = { xM: board.widthM, yM: board.heightM };
const response = {
    requestId: 42,
    mapVersion: "v0.2",
    frameId: "schematic_v02",
    segments: [[bottomLeft, topRight]],
};

test("does not retain the previous request's geometry or guess a missing route", () => {
    assert.deepEqual(routeLines(response, 41), []);
    assert.deepEqual(routeLines(response, undefined), []);
    assert.deepEqual(routeLines({ ...response, segments: [] }, 42), []);
    assert.deepEqual(
        routeLines({ ...response, frameId: "unregistered" }, 42),
        [],
    );
});

test("uses the v0.2 board's origin and keeps discontinuous lines apart", () => {
    assert.deepEqual(mapPoint(bottomLeft), [0, 958]);
    assert.deepEqual(mapPoint(topRight), [1046, 0]);
    assert.deepEqual(
        routeLines(
            {
                ...response,
                segments: [
                    [bottomLeft, topRight],
                    [topRight, bottomLeft],
                ],
            },
            42,
        ),
        ["0.00,958.00 1046.00,0.00", "1046.00,0.00 0.00,958.00"],
    );
});

test("rejects a segment with a bad point instead of bridging the gap", () => {
    const wrong = { xM: 3, yM: 1 };
    assert.deepEqual(
        routeLines(
            {
                ...response,
                segments: [[bottomLeft, wrong, topRight], [bottomLeft]],
            },
            42,
        ),
        [],
    );
});
