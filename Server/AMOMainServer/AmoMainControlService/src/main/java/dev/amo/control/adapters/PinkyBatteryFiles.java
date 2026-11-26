package dev.amo.control.adapters;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.amo.control.application.PinkyBatteryReadings;
import dev.amo.control.domain.Operations.PinkyBattery;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Reads local collector snapshots from a read-only directory, without accessing PostgreSQL. */
@Component
class PinkyBatteryFiles implements PinkyBatteryReadings {
  private static final Pattern NAME = Pattern.compile("PP_[0-9]{5}\\.json");
  private static final int MAX_BYTES = 4096;
  private final ObjectMapper json;
  private final Path directory;

  PinkyBatteryFiles(ObjectMapper json, @Value("${AMO_PINKY_BATTERY_DIRECTORY:}") String directory) {
    this.json = json;
    this.directory = directory.isBlank() ? null : Path.of(directory);
  }

  @Override
  public List<PinkyBattery> latest() {
    if (directory == null) {
      return List.of();
    }
    Instant now = Instant.now();
    try (Stream<Path> paths = Files.list(directory)) {
      return paths
          .filter(path -> NAME.matcher(path.getFileName().toString()).matches())
          .sorted()
          .limit(32)
          .map(path -> read(path, now))
          .toList();
    } catch (IOException | java.io.UncheckedIOException ex) {
      return List.of();
    }
  }

  private PinkyBattery read(Path path, Instant now) {
    String id = path.getFileName().toString().replace(".json", "");
    var unavailable = new PinkyBattery(id, null, null, null, false);
    if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) {
      return unavailable;
    }
    try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
      byte[] bytes = input.readNBytes(MAX_BYTES + 1);
      if (bytes.length > MAX_BYTES) {
        return unavailable;
      }
      var node = json.readTree(bytes);
      if (node == null || !node.isObject()) {
        return unavailable;
      }
      boolean simulated = node.path("simulated").asBoolean(false);
      var empty = new PinkyBattery(id, null, null, null, simulated);
      if (!"connected".equals(node.path("state").asText())) {
        return empty;
      }
      Instant observedAt = Instant.parse(node.path("observedAt").asText());
      double percent = node.path("batteryPercent").asDouble(Double.NaN);
      double voltage = node.path("batteryVoltage").asDouble(Double.NaN);
      if (observedAt.isAfter(now)
          || !observedAt.isAfter(now.minusSeconds(15))
          || !node.path("batteryPercent").isNumber()
          || !node.path("batteryVoltage").isNumber()
          || !(percent >= 0 && percent <= 100 && voltage >= 0 && voltage <= 20)) {
        return empty;
      }
      return new PinkyBattery(id, percent, voltage, observedAt, simulated);
    } catch (IOException | DateTimeParseException ex) {
      return unavailable;
    }
  }
}
