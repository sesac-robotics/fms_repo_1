package dev.amo.control.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DevelopmentTcpContractTest {
  private final ObjectMapper json = new ObjectMapper();

  @Test
  void requestFramesAreBoundedAndMustBeComplete() throws IOException {
    byte[] body =
        json.writeValueAsBytes(new ControlWire.Request("GET", "/api/operations", Map.of(), ""));
    assertEquals("/api/operations", decode(body.length, body).path());
    assertThrows(IOException.class, () -> decode(0, body));
    assertThrows(IOException.class, () -> decode(ControlWire.MAX_FRAME + 1, body));
    assertThrows(IOException.class, () -> decode(body.length + 1, body));
  }

  @Test
  void adminLinkForwardsOnlyAuthenticatedSnapshotRequests() throws Exception {
    var backend = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    backend.createContext(
        "/api/operations",
        exchange -> {
          try (exchange) {
            String bearer = exchange.getRequestHeaders().getFirst("Authorization");
            int status = "Bearer local-test".equals(bearer) ? 200 : 401;
            byte[] body = "{}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, body.length);
            exchange.getResponseBody().write(body);
          }
        });
    backend.start();
    try {
      var adapter = new ControlHttpAdapter(backend.getAddress().getPort());
      var headers = Map.of("authorization", List.of("Bearer local-test"));
      var accepted =
          adapter.handle(new ControlWire.Request("GET", "/api/operations", headers, ""), true);
      assertEquals(200, accepted.status());
      assertEquals("{}", new String(ControlWire.decode(accepted.body()), StandardCharsets.UTF_8));
      var noToken = new ControlWire.Request("GET", "/api/operations", Map.of(), "");
      assertEquals(401, adapter.handle(noToken, true).status());
      var outOfScope = new ControlWire.Request("POST", "/api/rides", headers, "");
      assertEquals(404, adapter.handle(outOfScope, true).status());
      var invalidPath = new ControlWire.Request("GET", "//example.org/api/operations", headers, "");
      assertEquals(404, adapter.handle(invalidPath, false).status());
    } finally {
      backend.stop(0);
    }
  }

  @Test
  void bothBoundSocketsUseTheSameFrameButDifferentPathPolicy() throws Exception {
    var backend = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    backend.createContext(
        "/api/health",
        exchange -> {
          try (exchange) {
            int status =
                "scope=dev%20sample".equals(exchange.getRequestURI().getRawQuery()) ? 204 : 400;
            exchange.sendResponseHeaders(status, -1);
          }
        });
    backend.start();
    var ingress = new DevelopmentTcpIngress(json, 0, 0);
    try {
      var ports = ingress.bindDevelopmentPorts(backend.getAddress().getPort());
      var health = new ControlWire.Request("GET", "/api/health?scope=dev%20sample", Map.of(), "");
      assertEquals(204, exchange(ports.webPort(), health).status());
      assertEquals(404, exchange(ports.adminPort(), health).status());
    } finally {
      ingress.stop();
      backend.stop(0);
    }
  }

  @Test
  void signalCommandsPassOnlyThroughTheWebLink() throws Exception {
    var backend = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    backend.createContext(
        "/",
        exchange -> {
          try (exchange) {
            exchange.sendResponseHeaders(202, -1);
          }
        });
    backend.start();
    try {
      var adapter = new ControlHttpAdapter(backend.getAddress().getPort());
      var bearer = Map.of("authorization", List.of("Bearer staff"));
      var command = new ControlWire.Request("POST", "/api/signals/SIG-01/commands", bearer, "");
      assertEquals(202, adapter.handle(command, false).status());
      assertEquals(404, adapter.handle(command, true).status());
      var bad = new ControlWire.Request("POST", "/api/signals/sig_01/commands", bearer, "");
      assertEquals(404, adapter.handle(bad, false).status());
      for (String internal :
          new String[] {"/internal/signals/state", "/internal/signals/SIG-01/commands"}) {
        for (String method : new String[] {"GET", "POST"}) {
          var request = new ControlWire.Request(method, internal, bearer, "");
          assertEquals(404, adapter.handle(request, false).status());
        }
      }
    } finally {
      backend.stop(0);
    }
  }

  private ControlWire.Response exchange(int port, ControlWire.Request request) throws IOException {
    byte[] payload = json.writeValueAsBytes(request);
    try (var client = new Socket("127.0.0.1", port)) {
      client.setSoTimeout(3_000);
      var output = new DataOutputStream(client.getOutputStream());
      output.writeInt(payload.length);
      output.write(payload);
      output.flush();
      var input = new DataInputStream(client.getInputStream());
      return json.readValue(input.readNBytes(input.readInt()), ControlWire.Response.class);
    }
  }

  private ControlWire.Request decode(int length, byte[] payload) throws IOException {
    var buffer = new ByteArrayOutputStream();
    var framed = new DataOutputStream(buffer);
    framed.writeInt(length);
    framed.write(payload);
    return ControlWire.read(
        new DataInputStream(new ByteArrayInputStream(buffer.toByteArray())), json);
  }
}
