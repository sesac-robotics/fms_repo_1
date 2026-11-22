package dev.amo.control.domain;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * Observed route segments for one request. Coordinates are metres from the bottom-left of the v0.2
 * schematic. Empty segments leave map metadata unset.
 */
public record RecordedRoute(
    long requestId,
    String mapVersion,
    String frameId,
    List<List<Point>> segments,
    boolean truncated) {
  public static final int MAX_SAMPLES = 2_000;
  static final String MAP_VERSION = "v0.2";
  static final String FRAME_ID = "schematic_v02";
  private static final double MAP_WIDTH_M = 2.44;
  private static final double MAP_HEIGHT_M = 2.225;

  /** Position in metres in the response map frame. */
  public record Point(double xM, double yM) {}

  public record Sample(
      String mapVersion,
      String frameId,
      String epoch,
      long sequence,
      Instant observedAt,
      Double xM,
      Double yM) {
    boolean canPlot() {
      return MAP_VERSION.equals(mapVersion)
          && FRAME_ID.equals(frameId)
          && epoch != null
          && !epoch.isBlank()
          && sequence >= 0
          && observedAt != null
          && inBounds(xM, MAP_WIDTH_M)
          && inBounds(yM, MAP_HEIGHT_M);
    }

    boolean follows(Sample previous) {
      return epoch.equals(previous.epoch)
          && sequence - 1 == previous.sequence
          && observedAt.isAfter(previous.observedAt);
    }

    private static boolean inBounds(Double value, double limit) {
      return value != null && value >= 0 && value <= limit;
    }
  }

  public static RecordedRoute from(long requestId, List<Sample> newestFirst) {
    var segments = new ArrayList<List<Point>>();
    var current = new ArrayList<Point>();
    Sample previous = null;
    for (var sample :
        newestFirst.subList(0, Math.min(newestFirst.size(), MAX_SAMPLES)).reversed()) {
      if (!sample.canPlot()) {
        finishSegment(segments, current);
        previous = null;
        continue;
      }
      if (previous != null && !sample.follows(previous)) {
        finishSegment(segments, current);
      }
      var point = new Point(sample.xM(), sample.yM());
      if (current.isEmpty() || !point.equals(current.getLast())) {
        current.add(point);
      }
      previous = sample;
    }
    finishSegment(segments, current);
    boolean hasRoute = !segments.isEmpty();
    return new RecordedRoute(
        requestId,
        hasRoute ? MAP_VERSION : null,
        hasRoute ? FRAME_ID : null,
        List.copyOf(segments),
        newestFirst.size() > MAX_SAMPLES);
  }

  private static void finishSegment(List<List<Point>> segments, List<Point> points) {
    if (points.size() >= 2) {
      segments.add(List.copyOf(points));
    }
    points.clear();
  }
}
