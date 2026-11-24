package dev.amo.fares.application;

import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.Estimate;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.Fare.Quote;
import dev.amo.fares.domain.Fare.Receipt;
import java.time.Instant;
import java.util.Optional;

/** Transactional persistence for one-way fares. All writes hold the owning request lock. */
public interface FareStore {
  /** Locks an owned one-way request and reads trusted server-side fare inputs. */
  Optional<Request> lock(long requestId, long passengerId);

  /** Reads terms for the initial request, independent of assignment or trip creation. */
  Optional<Quote> initialQuote(long requestId);

  /** Stores one initial quote with UTC timestamps and no trip association. */
  Quote saveInitialQuote(long requestId, Estimate estimate, Instant now);

  /** Reads the previously recorded attempt for this quote and replay key. */
  Optional<Attempt> attempt(long quoteId, String key);

  /** Reads the latest status for a quote, preferring a previously successful attempt. */
  Optional<Attempt> latestAttempt(long quoteId);

  /** Records a mock attempt and its event atomically without exposing the instrument. */
  Attempt saveAttempt(
      Quote quote, String key, String method, long amountMinor, PaymentStatus outcome, Instant now);

  /** Persists the first hold reason in the audit trail without recording a payment attempt. */
  void recordHold(long requestId, Long quoteId, PaymentStatus reason);

  /** Reads a previously issued receipt for the owned request. */
  Optional<Receipt> receipt(long requestId);

  /** Reads completed trip and alighting evidence for exactly this trip and request. */
  Optional<CloseEvidence> closeEvidence(long requestId, long tripId);

  /** Stores a single finalized charge and event against the eligible evidence. */
  Receipt settle(long requestId, CloseEvidence evidence, Quote quote, Instant now);

  /** Projected request and private inputs. The estimate can be absent. */
  record Request(long id, String status, String destination, String method, Estimate estimate) {}

  /** Persisted confirmation from the same completed trip. */
  record CloseEvidence(long tripId, long dispatchId, long alightingCheckId) {}
}
