package dev.amo.web;

import dev.amo.maincontrol.Operations;
import dev.amo.maincontrol.OperationsService;
import dev.amo.maincontrol.RecordedRoute;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Provides an operations snapshot and PostgreSQL readiness check. */
@RestController
class OperationsController {
  private final OperationsService operations;

  OperationsController(OperationsService operations) {
    this.operations = operations;
  }

  @GetMapping("/api/operations")
  Operations operations() {
    return operations.snapshot();
  }

  @GetMapping("/api/operations/requests/{requestId}/route")
  RecordedRoute recordedRoute(@PathVariable long requestId) {
    return operations.recordedRoute(requestId);
  }

  @GetMapping("/api/health")
  ResponseEntity<Map<String, Object>> health() {
    boolean ready = operations.ready();
    HttpStatus status = ready ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE;
    return ResponseEntity.status(status)
        .body(Map.of("status", ready ? "UP" : "DOWN", "motionEnabled", false));
  }
}
