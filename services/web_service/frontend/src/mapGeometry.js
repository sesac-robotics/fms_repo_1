export const board = Object.freeze({ widthM: 2.44, heightM: 2.225 });
export const dimensions = Object.freeze({ width: 1046, height: 958 });

/** Converts a bottom-left v0.2 coordinate in metres to SVG pixels, or null. */
export function mapPoint({ xM, yM }) {
    if (!within(xM, board.widthM) || !within(yM, board.heightM)) return null;
    return [
        (xM / board.widthM) * dimensions.width,
        (1 - yM / board.heightM) * dimensions.height,
    ];
}

function within(value, limit) {
    return Number.isFinite(value) && value >= 0 && value <= limit;
}

/** Builds independent lines only for a response matching the current request and frame. */
export function routeLines(route, requestId) {
    if (
        requestId == null ||
        !route ||
        String(route.requestId) !== String(requestId) ||
        route.mapVersion !== "v0.2" ||
        route.frameId !== "schematic_v02" ||
        !Array.isArray(route.segments)
    ) {
        return [];
    }
    return route.segments.flatMap((segment) => {
        if (!Array.isArray(segment)) return [];
        const points = segment.map((point) => (point ? mapPoint(point) : null));
        if (points.length < 2 || points.some((point) => !point)) return [];
        return [
            points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" "),
        ];
    });
}
