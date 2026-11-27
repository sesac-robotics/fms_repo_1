package dev.amo.gateway;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Sends one A-01 development request per IF-02 TCP connection on the local machine. */
@Component
final class MainControlLink {
  static final int MAX_FRAME_BYTES = 1024 * 1024;
  private static final int CONNECT_TIMEOUT_MS = 2_000;
  private static final int RESPONSE_TIMEOUT_MS = 5_000;

  private final ObjectMapper json;
  private final InetSocketAddress address;

  MainControlLink(ObjectMapper json, @Value("${amo.if02-port}") int port) {
    this.json = json;
    this.address = new InetSocketAddress("127.0.0.1", port);
  }

  /**
   * Exchanges a UTF-8 JSON frame with a four-byte big-endian byte count. A timeout or network
   * failure leaves the request outcome unknown. This method owns its socket and never retries.
   */
  Response exchange(Request request) throws IOException {
    byte[] payload = json.writeValueAsBytes(request);
    if (payload.length > MAX_FRAME_BYTES) {
      throw new RequestTooLarge();
    }

    try (var socket = new Socket()) {
      socket.connect(address, CONNECT_TIMEOUT_MS);
      socket.setSoTimeout(RESPONSE_TIMEOUT_MS);
      var output = new DataOutputStream(socket.getOutputStream());
      output.writeInt(payload.length);
      output.write(payload);
      output.flush();

      var input = new DataInputStream(socket.getInputStream());
      int size = input.readInt();
      if (size < 1 || size > MAX_FRAME_BYTES) {
        throw new IOException("Invalid Main Control response size");
      }
      byte[] response = input.readNBytes(size);
      if (response.length != size) {
        throw new EOFException("Incomplete Main Control response");
      }
      var result = json.readValue(response, Response.class);
      if (result == null || result.status() < 200 || result.status() > 599) {
        throw new IOException("Invalid Main Control response status");
      }
      return result;
    }
  }

  record Request(String method, String path, Map<String, List<String>> headers, byte[] body) {}

  record Response(int status, Map<String, List<String>> headers, byte[] body) {}

  static final class RequestTooLarge extends IOException {}
}
