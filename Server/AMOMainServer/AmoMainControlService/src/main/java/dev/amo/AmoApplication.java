package dev.amo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** Starts Main Control and its private adapters with vehicle movement disabled. */
@SpringBootApplication
public class AmoApplication {
  public static void main(String[] args) {
    SpringApplication.run(AmoApplication.class, args);
  }
}
