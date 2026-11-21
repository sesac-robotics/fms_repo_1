package dev.amo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** AMO HTTP entry point. Vehicle movement is unavailable in this application. */
@SpringBootApplication
public class AmoApplication {
  public static void main(String[] args) {
    SpringApplication.run(AmoApplication.class, args);
  }
}
