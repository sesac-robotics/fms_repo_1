package dev.amo.control.adapters;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PreDestroy;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.Semaphore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.context.annotation.Profile;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/** Serves bounded loopback IF-02 and read-only IF-03 connections in the demo profile. */
@Component
@Profile("demo")
final class DevelopmentTcpIngress {
  private static final System.Logger LOG = System.getLogger(DevelopmentTcpIngress.class.getName());

  private final ObjectMapper json;
  private final int webPort;
  private final int adminPort;
  private final ExecutorService work = Executors.newVirtualThreadPerTaskExecutor();
  private final Semaphore connections = new Semaphore(32);
  private ServerSocket web;
  private ServerSocket admin;

  DevelopmentTcpIngress(
      ObjectMapper json,
      @Value("${amo.tcp.web-port}") int webPort,
      @Value("${amo.tcp.admin-port}") int adminPort) {
    this.json = json;
    this.webPort = webPort;
    this.adminPort = adminPort;
  }

  @EventListener
  void start(ApplicationReadyEvent event) throws IOException {
    var context = (ServletWebServerApplicationContext) event.getApplicationContext();
    bindDevelopmentPorts(context.getWebServer().getPort());
  }

  BoundPorts bindDevelopmentPorts(int privateHttpPort) throws IOException {
    var adapter = new ControlHttpAdapter(privateHttpPort);
    try {
      web = bind(webPort);
      admin = bind(adminPort);
      work.execute(() -> accept(web, adapter, false));
      work.execute(() -> accept(admin, adapter, true));
      return new BoundPorts(web.getLocalPort(), admin.getLocalPort());
    } catch (IOException failure) {
      stop();
      throw failure;
    }
  }

  record BoundPorts(int webPort, int adminPort) {}

  private static ServerSocket bind(int port) throws IOException {
    var server = new ServerSocket();
    try {
      server.bind(new InetSocketAddress("127.0.0.1", port), 32);
      return server;
    } catch (IOException failure) {
      server.close();
      throw failure;
    }
  }

  private void accept(ServerSocket server, ControlHttpAdapter adapter, boolean adminPort) {
    while (!server.isClosed()) {
      try {
        Socket client = server.accept();
        if (!connections.tryAcquire()) {
          client.close();
          continue;
        }
        try {
          work.execute(() -> handle(client, adapter, adminPort));
        } catch (RejectedExecutionException stopped) {
          connections.release();
          client.close();
          return;
        }
      } catch (IOException failure) {
        if (!server.isClosed()) {
          LOG.log(System.Logger.Level.WARNING, "Local TCP accept failed");
        }
      }
    }
  }

  private void handle(Socket client, ControlHttpAdapter adapter, boolean adminPort) {
    try (client) {
      client.setSoTimeout(10_000);
      var input = new DataInputStream(client.getInputStream());
      var output = new DataOutputStream(client.getOutputStream());
      ControlWire.Response result;
      try {
        var request = ControlWire.read(input, json);
        result = adapter.handle(request, adminPort);
      } catch (IllegalArgumentException invalid) {
        result = ControlWire.Response.error(400, "INVALID_CONTROL_REQUEST");
      }
      ControlWire.write(output, json, result);
    } catch (IOException failure) {
      LOG.log(System.Logger.Level.DEBUG, "Local TCP exchange closed");
    } catch (InterruptedException interrupted) {
      Thread.currentThread().interrupt();
    } finally {
      connections.release();
    }
  }

  @PreDestroy
  void stop() {
    close(web);
    close(admin);
    work.shutdownNow();
  }

  private static void close(ServerSocket socket) {
    if (socket != null) {
      try {
        socket.close();
      } catch (IOException failure) {
        LOG.log(System.Logger.Level.DEBUG, "Local TCP listener was closed");
      }
    }
  }
}
