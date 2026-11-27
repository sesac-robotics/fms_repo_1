package dev.amo.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** Starts the HTTP entry point for the Web Service. */
@SpringBootApplication
public class AmoWebApplication {
  public static void main(String[] args) {
    SpringApplication.run(AmoWebApplication.class, args);
  }
}
