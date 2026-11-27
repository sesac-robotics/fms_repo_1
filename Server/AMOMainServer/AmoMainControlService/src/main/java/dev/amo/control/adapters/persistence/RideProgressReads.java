package dev.amo.control.adapters.persistence;

/** Shared bounded read fragments for operators. Each caller supplies a request row alias r. */
final class RideProgressReads {
  private RideProgressReads() {}

  static final String APPLIED_ROUTE =
      """
      LEFT JOIN LATERAL (
        SELECT c.revision_id, p.place_key AS target
        FROM dispatches d JOIN trips t ON t.dispatch_id = d.id
        JOIN ride_route_changes c ON c.trip_id = t.id
        JOIN places p ON p.id = c.target_place_id
        WHERE d.request_id = r.id AND c.applied_at IS NOT NULL
        ORDER BY c.revision_id DESC LIMIT 1
      ) applied ON TRUE
      """;

  static final String HISTORY =
      """
      LEFT JOIN LATERAL (
        SELECT COALESCE(p.result, 'QUOTED') AS status
        FROM ride_fare_quotes q
        LEFT JOIN ride_payment_attempts p ON p.quote_id = q.id
        WHERE q.request_id = r.id AND q.route_revision_id IS NULL
        ORDER BY (p.result = 'SUCCEEDED') DESC NULLS LAST, p.id DESC LIMIT 1
      ) initial ON TRUE
      LEFT JOIN LATERAL (
        SELECT revision.status,
               COALESCE(p.result, CASE WHEN c.accepted_key IS NOT NULL AND c.delta_minor = 0
                   THEN 'NOT_REQUIRED' ELSE 'QUOTED' END) AS payment
        FROM dispatches d JOIN trips t ON t.dispatch_id = d.id
        JOIN ride_route_changes c ON c.trip_id = t.id
        JOIN route_revisions revision ON revision.id = c.revision_id
        JOIN ride_fare_quotes q ON q.route_revision_id = c.revision_id
        LEFT JOIN ride_payment_attempts p ON p.quote_id = q.id
        WHERE d.request_id = r.id
        ORDER BY c.revision_id DESC, (p.result = 'SUCCEEDED') DESC NULLS LAST, p.id DESC LIMIT 1
      ) changed ON TRUE
      LEFT JOIN ride_fare_settlements fare ON fare.request_id = r.id
      LEFT JOIN demo_depot_cycles depot ON depot.request_id = r.id
      """;
}
