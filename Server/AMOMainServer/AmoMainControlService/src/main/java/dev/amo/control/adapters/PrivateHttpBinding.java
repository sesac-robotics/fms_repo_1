package dev.amo.control.adapters;

import java.net.InetAddress;
import java.net.UnknownHostException;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.boot.web.servlet.server.ConfigurableServletWebServerFactory;
import org.springframework.stereotype.Component;

/** Keeps the compatibility HTTP controllers behind the process-local development adapter. */
@Component
final class PrivateHttpBinding
    implements WebServerFactoryCustomizer<ConfigurableServletWebServerFactory> {
  @Override
  public void customize(ConfigurableServletWebServerFactory factory) {
    try {
      factory.setAddress(InetAddress.getByAddress(new byte[] {127, 0, 0, 1}));
    } catch (UnknownHostException impossible) {
      throw new IllegalStateException(impossible);
    }
  }
}
