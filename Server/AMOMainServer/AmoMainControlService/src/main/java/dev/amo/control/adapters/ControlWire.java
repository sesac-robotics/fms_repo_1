package dev.amo.control.adapters;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;
import java.util.Map;

/** Encodes one bounded loopback development exchange for IF-02 or IF-03. */
final class ControlWire {
  static final int MAX_FRAME = 1_048_576;

  private ControlWire() {}

  record Request(String method, String path, Map<String, List<String>> headers, String body) {}

  record Response(int status, Map<String, List<String>> headers, String body) {
    static Response error(int status, String code) {
      var payload = ("{\"code\":\"" + code + "\"}").getBytes(StandardCharsets.UTF_8);
      return new Response(
          status, Map.of("content-type", List.of("application/json")), encode(payload));
    }
  }

  static Request read(DataInputStream input, ObjectMapper json) throws IOException {
    int size = input.readInt();
    if (size <= 0 || size > MAX_FRAME) {
      throw new IOException("Invalid development TCP frame length");
    }
    byte[] payload = input.readNBytes(size);
    if (payload.length != size) {
      throw new EOFException("Incomplete development TCP frame");
    }
    return json.readValue(payload, Request.class);
  }

  static void write(DataOutputStream output, ObjectMapper json, Response response)
      throws IOException {
    byte[] payload = json.writeValueAsBytes(response);
    if (payload.length > MAX_FRAME) {
      payload = json.writeValueAsBytes(Response.error(502, "CONTROL_RESPONSE_TOO_LARGE"));
    }
    output.writeInt(payload.length);
    output.write(payload);
    output.flush();
  }

  static byte[] decode(String body) {
    return Base64.getDecoder().decode(body);
  }

  static String encode(byte[] body) {
    return Base64.getEncoder().encodeToString(body);
  }
}
