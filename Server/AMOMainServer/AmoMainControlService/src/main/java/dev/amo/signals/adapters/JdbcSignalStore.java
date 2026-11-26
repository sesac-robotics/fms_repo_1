package dev.amo.signals.adapters;

import dev.amo.signals.application.SignalStore;
import dev.amo.signals.domain.SignalCommand;
import dev.amo.signals.domain.SignalCommand.Pending;
import dev.amo.signals.domain.SignalCommand.Timing;
import dev.amo.signals.domain.SignalState;
import dev.amo.signals.domain.SignalState.Mode;
import dev.amo.signals.domain.SignalState.Phase;
import dev.amo.signals.domain.SignalState.Received;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Keeps signal state and the command queue in the existing AMO PostgreSQL database. */
@Repository
class JdbcSignalStore implements SignalStore {
  private final JdbcClient jdbc;

  JdbcSignalStore(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  public void saveState(SignalState s, Instant receivedAt) {
    jdbc.sql(
            """
            INSERT INTO signal_latest
                (signal_id, phase, mode, hold_target, remaining_ms, north_green_ms, east_green_ms,
                 yellow_ms, all_red_ms, plan_pending, device_seq, device_uptime_ms, last_command,
                 command_result, received_at)
            VALUES (:id, :phase, :mode, :hold, :remaining, :ng, :eg, :y, :ar, :pending, :seq,
                    :uptime, :command, :result, :received)
            ON CONFLICT (signal_id) DO UPDATE
            SET phase = EXCLUDED.phase, mode = EXCLUDED.mode, hold_target = EXCLUDED.hold_target,
                remaining_ms = EXCLUDED.remaining_ms, north_green_ms = EXCLUDED.north_green_ms,
                east_green_ms = EXCLUDED.east_green_ms, yellow_ms = EXCLUDED.yellow_ms,
                all_red_ms = EXCLUDED.all_red_ms, plan_pending = EXCLUDED.plan_pending,
                device_seq = EXCLUDED.device_seq, device_uptime_ms = EXCLUDED.device_uptime_ms,
                last_command = EXCLUDED.last_command, command_result = EXCLUDED.command_result,
                received_at = EXCLUDED.received_at
            """)
        .param("id", s.signalId())
        .param("phase", s.phase().name())
        .param("mode", s.mode().name())
        .param("hold", s.holdTarget() == null ? null : s.holdTarget().name())
        .param("remaining", s.remainingMs())
        .param("ng", s.plan().northGreenMs())
        .param("eg", s.plan().eastGreenMs())
        .param("y", s.plan().yellowMs())
        .param("ar", s.plan().allRedMs())
        .param("pending", s.planPending())
        .param("seq", s.seq())
        .param("uptime", s.uptimeMs())
        .param("command", s.lastCommand())
        .param("result", s.commandResult())
        .param("received", receivedAt.atOffset(ZoneOffset.UTC))
        .update();
  }

  @Override
  public List<Received> latest() {
    return jdbc.sql("SELECT * FROM signal_latest ORDER BY signal_id")
        .query((row, index) -> received(row))
        .list();
  }

  @Override
  public boolean hasReported(String signalId) {
    return jdbc.sql("SELECT EXISTS (SELECT 1 FROM signal_latest WHERE signal_id = :id)")
        .param("id", signalId)
        .query(Boolean.class)
        .single();
  }

  @Override
  public long queue(String signalId, SignalCommand command, long requestedBy, Instant at) {
    return jdbc.sql(
            """
            INSERT INTO signal_commands (signal_id, command, requested_by, requested_at)
            VALUES (:id, :command, :by, :at) RETURNING id
            """)
        .param("id", signalId)
        .param("command", command.text())
        .param("by", requestedBy)
        .param("at", at.atOffset(ZoneOffset.UTC))
        .query(Long.class)
        .single();
  }

  @Override
  public List<Pending> claim(String signalId, Instant deliveredAt) {
    // SKIP LOCKED lets two bridge polls overlap without handing out a command twice.
    return jdbc
        .sql(
            """
            WITH next AS (
                SELECT id FROM signal_commands
                WHERE signal_id = :id AND delivered_at IS NULL
                ORDER BY id FOR UPDATE SKIP LOCKED
            )
            UPDATE signal_commands c SET delivered_at = :at
            FROM next WHERE c.id = next.id
            RETURNING c.id, c.signal_id, c.command
            """)
        .param("id", signalId)
        .param("at", deliveredAt.atOffset(ZoneOffset.UTC))
        .query((row, index) -> new Pending(row.getLong(1), row.getString(2), row.getString(3)))
        .list()
        .stream()
        .sorted((a, b) -> Long.compare(a.id(), b.id()))
        .toList();
  }

  private static Received received(ResultSet row) throws SQLException {
    String hold = row.getString("hold_target");
    var state =
        new SignalState(
            row.getString("signal_id"),
            row.getLong("device_seq"),
            Phase.valueOf(row.getString("phase")),
            Mode.valueOf(row.getString("mode")),
            hold == null ? null : Phase.valueOf(hold),
            row.getInt("remaining_ms"),
            row.getLong("device_uptime_ms"),
            new Timing(
                row.getInt("north_green_ms"),
                row.getInt("east_green_ms"),
                row.getInt("yellow_ms"),
                row.getInt("all_red_ms")),
            row.getBoolean("plan_pending"),
            row.getString("last_command"),
            row.getString("command_result"));
    return new Received(state, row.getObject("received_at", OffsetDateTime.class).toInstant());
  }
}
