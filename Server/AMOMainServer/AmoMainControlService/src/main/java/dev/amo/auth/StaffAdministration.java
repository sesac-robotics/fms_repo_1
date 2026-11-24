package dev.amo.auth;

import dev.amo.ApiError;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Changes staff authorization and revokes sessions that carry the previous authorization. */
@Service
public class StaffAdministration {
  private final AccountRepository accounts;
  private final SessionRepository sessions;
  private final GoogleOperators operators;

  StaffAdministration(
      AccountRepository accounts, SessionRepository sessions, GoogleOperators operators) {
    this.accounts = accounts;
    this.sessions = sessions;
    this.operators = operators;
  }

  public List<Member> members() {
    return accounts.members();
  }

  /** Reads bounded member summaries; the HTTP boundary validates paging inputs. */
  public List<Member> memberPage(String search, int offset, int rows, boolean newest) {
    return accounts.memberPage(search, offset, rows, newest);
  }

  @Transactional
  public Member approve(long actorId, long memberId, boolean approved, Role requested) {
    if (actorId == memberId || requested == Role.PASSENGER) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_STAFF_ROLE_CHANGE");
    }
    requireAdmin(actorId);
    Role existing =
        accounts
            .findById(memberId)
            .map(account -> account.member().role())
            .filter(role -> role != Role.PASSENGER)
            .orElseThrow(() -> new ApiError(HttpStatus.NOT_FOUND, "STAFF_NOT_FOUND"));
    Role role = approved && requested != null ? requested : existing;
    Status status = approved ? Status.ACTIVE : Status.SUSPENDED;
    Member updated =
        accounts
            .changeStaff(memberId, role, status)
            .orElseThrow(() -> new ApiError(HttpStatus.NOT_FOUND, "STAFF_NOT_FOUND"));
    sessions.revokeAccount(memberId);
    accounts.audit(actorId, memberId, approved ? "APPROVE_" + role.name() : "SUSPEND_STAFF");
    return updated;
  }

  /** Approve one Google-only operator account for an existing verified passenger. */
  @Transactional
  public Member addGoogleOperator(long actorId, long passengerId) {
    requireAdmin(actorId);
    var created = operators.add(passengerId);
    if (created.isPresent()) {
      accounts.audit(actorId, created.get().id(), "APPROVE_GOOGLE_OPERATOR");
      return created.get();
    }
    return operators
        .companion(passengerId)
        .orElseThrow(() -> new ApiError(HttpStatus.CONFLICT, "GOOGLE_PASSENGER_REQUIRED"));
  }

  private void requireAdmin(long actorId) {
    accounts.lockActiveAdmins();
    boolean actorActive =
        accounts
            .findById(actorId)
            .map(
                account ->
                    account.member().role() == Role.ADMIN
                        && account.member().status() == Status.ACTIVE)
            .orElse(false);
    if (!actorActive) {
      throw new ApiError(HttpStatus.FORBIDDEN, "ADMIN_REQUIRED");
    }
  }
}
