package dev.amo.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.amo.gateway.MainControlLink.Request;
import dev.amo.gateway.MainControlLink.Response;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class WebApiGatewayTest {
  private final ObjectMapper json = new ObjectMapper();

  @Test
  void relaysJsonAndOnlyAllowedHeadersWithoutLosingMultipleCookies() throws Exception {
    byte[] posted = bytes("{\"serviceType\":\"ONE_WAY\"}");
    byte[] reply = bytes("{\"id\":17}");
    try (var peer = listen();
        var tasks = Executors.newVirtualThreadPerTaskExecutor()) {
      var request =
          tasks.submit(
              () -> {
                try (var connection = peer.accept()) {
                  connection.setSoTimeout(1000);
                  var input = new DataInputStream(connection.getInputStream());
                  var frame = json.readValue(input.readNBytes(input.readInt()), Request.class);
                  var response =
                      new Response(
                          201,
                          Map.of(
                              "Content-Type", List.of("application/json"),
                              "Set-Cookie", List.of("access=one; HttpOnly", "xsrf=two"),
                              "Connection", List.of("close")),
                          reply);
                  byte[] encoded = json.writeValueAsBytes(response);
                  var output = new DataOutputStream(connection.getOutputStream());
                  output.writeInt(encoded.length);
                  output.write(encoded);
                  return frame;
                }
              });

      MockMvcBuilders.standaloneSetup(gateway(peer))
          .build()
          .perform(
              post("/api/rides?scope=demo")
                  .header("Authorization", "Bearer local-test")
                  .header("Cookie", "access=one")
                  .header("X-XSRF-TOKEN", "two")
                  .header("Origin", "http://localhost:5175")
                  .header("X-Forwarded-For", "1.2.3.4")
                  .contentType("application/json")
                  .content(posted))
          .andExpect(status().isCreated())
          .andExpect(content().bytes(reply))
          .andExpect(header().stringValues("Set-Cookie", "access=one; HttpOnly", "xsrf=two"))
          .andExpect(header().doesNotExist("Connection"));

      var frame = request.get(2, TimeUnit.SECONDS);
      assertThat(frame.method()).isEqualTo("POST");
      assertThat(frame.path()).isEqualTo("/api/rides?scope=demo");
      assertThat(frame.body()).isEqualTo(posted);
      assertThat(frame.headers())
          .containsEntry("authorization", List.of("Bearer local-test"))
          .containsEntry("cookie", List.of("access=one"))
          .containsEntry("x-xsrf-token", List.of("two"))
          .containsEntry("origin", List.of("http://localhost:5175"))
          .doesNotContainKey("x-forwarded-for");
    }
  }

  @Test
  void rejectsOversizedBodiesAndNonApiTargetsBeforeConnecting() throws Exception {
    try (var peer = listen()) {
      var gateway = gateway(peer);
      var tooLarge = new MockHttpServletRequest("POST", "/api/rides");
      tooLarge.setContent(new byte[768_001]);
      assertThat(gateway.forward(tooLarge).getStatusCode().value()).isEqualTo(413);

      var unsafePath = new MockHttpServletRequest("POST", "/api/../auth/token");
      assertThat(gateway.forward(unsafePath).getStatusCode().value()).isEqualTo(400);
    }
  }

  @Test
  void returnsGatewayErrorAfterAnInvalidFrameWithoutResendingThePost() throws Exception {
    try (var peer = listen();
        var tasks = Executors.newVirtualThreadPerTaskExecutor()) {
      var received =
          tasks.submit(
              () -> {
                try (var connection = peer.accept()) {
                  connection.setSoTimeout(1000);
                  var input = new DataInputStream(connection.getInputStream());
                  var frame = json.readValue(input.readNBytes(input.readInt()), Request.class);
                  var output = new DataOutputStream(connection.getOutputStream());
                  output.writeInt(MainControlLink.MAX_FRAME_BYTES + 1);
                  return frame;
                }
              });
      var request = new MockHttpServletRequest("POST", "/api/rides");
      request.setContent(bytes("{}"));
      var result = gateway(peer).forward(request);
      assertThat(result.getStatusCode().value()).isEqualTo(502);
      assertThat(new String(result.getBody(), StandardCharsets.UTF_8))
          .contains("MAIN_CONTROL_UNAVAILABLE");
      assertThat(received.get(2, TimeUnit.SECONDS).method()).isEqualTo("POST");
      peer.setSoTimeout(50);
      org.junit.jupiter.api.Assertions.assertThrows(
          java.net.SocketTimeoutException.class, peer::accept);
    }
  }

  private WebApiGateway gateway(ServerSocket peer) {
    return new WebApiGateway(new MainControlLink(json, peer.getLocalPort()));
  }

  private static ServerSocket listen() throws Exception {
    var server = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"));
    server.setSoTimeout(2000);
    return server;
  }

  private static byte[] bytes(String value) {
    return value.getBytes(StandardCharsets.UTF_8);
  }
}
