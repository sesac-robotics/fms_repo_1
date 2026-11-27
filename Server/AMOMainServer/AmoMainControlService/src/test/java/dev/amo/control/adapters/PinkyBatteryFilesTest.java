package dev.amo.control.adapters;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class PinkyBatteryFilesTest {
  @TempDir Path directory;

  @Test
  void publishesFourIndependentSimulatedReadingsAndExpiresOldMeasurements() throws Exception {
    var ids = List.of("PP_26135", "PP_26137", "PP_26141", "PP_26142");
    var timestamp = Instant.now();
    for (int index = 0; index < ids.size(); index++) {
      write(ids.get(index), timestamp, 61 + index, 7.5 + index / 8.0);
    }
    Files.writeString(directory.resolve("pinky.json"), "{}");
    var reader = new PinkyBatteryFiles(new ObjectMapper(), directory.toString());
    var readings = reader.latest();
    assertThat(readings).extracting(row -> row.deviceId()).containsExactlyElementsOf(ids);
    assertThat(readings).extracting(row -> row.percent()).containsExactly(61.0, 62.0, 63.0, 64.0);
    assertThat(readings).extracting(row -> row.voltage()).containsExactly(7.5, 7.625, 7.75, 7.875);
    assertThat(readings).allMatch(row -> row.simulated() && timestamp.equals(row.observedAt()));

    write(ids.getFirst(), timestamp.minusSeconds(20), 61, 7.5);
    var expired = reader.latest().getFirst();
    assertThat(expired.percent()).isNull();
    assertThat(expired.voltage()).isNull();
    assertThat(expired.simulated()).isTrue();
  }

  private void write(String id, Instant time, int percent, double voltage) throws Exception {
    Files.writeString(
        directory.resolve(id + ".json"),
        """
        {"state":"connected","observedAt":"%s","batteryPercent":%d,"batteryVoltage":%s,"simulated":true}
        """
            .formatted(time, percent, voltage));
  }
}
