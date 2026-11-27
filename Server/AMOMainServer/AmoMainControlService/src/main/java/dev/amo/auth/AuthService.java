package dev.amo.auth;

import dev.amo.ApiError;
import dev.amo.auth.Identity.Access;
import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import dev.amo.auth.Identity.User;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Coordinates registration, verified provider identity, and local sessions. */
@Service
public class AuthService {
  private final AccountRepository accounts;
  private final GoogleOperators operators;
  private final SessionRepository sessions;
  private final AmoJwt jwt;
  private final GoogleIdentity google;
  private final PasswordEncoder passwords;
  private final String absentHash;

  AuthService(
      AccountRepository accounts,
      GoogleOperators operators,
      SessionRepository sessions,
      AmoJwt jwt,
      GoogleIdentity google,
      PasswordEncoder passwords) {
    this.accounts = accounts;
    this.operators = operators;
    this.sessions = sessions;
    this.jwt = jwt;
    this.google = google;
    this.passwords = passwords;
    absentHash = passwords.encode(java.util.UUID.randomUUID().toString());
  }

  @Transactional
  public Access login(String email, String password) {
    Account account = accounts.findByEmail(Registration.email(email)).orElse(null);
    String hash =
        account == null || account.passwordHash() == null ? absentHash : account.passwordHash();
    if (!Registration.validPasswordBytes(password)
        || !passwords.matches(password, hash)
        || account == null
        || account.passwordHash() == null) {
      throw new ApiError(HttpStatus.UNAUTHORIZED, "INVALID_CREDENTIALS");
    }
    return activate(account);
  }

  @Transactional
  public Access registerPassenger(String name, String email, String password) {
    String normalizedName = Registration.name(name);
    String normalizedEmail = Registration.email(email);
    String hash = hash(password);
    long profileId = accounts.createPassengerProfile(normalizedName, normalizedEmail);
    return activate(
        insert(normalizedEmail, normalizedName, hash, Role.PASSENGER, Status.ACTIVE, profileId));
  }

  @Transactional
  public Member registerStaff(String name, String email, String password) {
    return insert(
            Registration.email(email),
            Registration.name(name),
            hash(password),
            Role.ADMIN,
            Status.PENDING,
            null)
        .member();
  }

  @Transactional
  public Access loginGoogle(String credential) {
    GoogleIdentity.VerifiedGoogle identity = google.verify(credential);
    Account prior = accounts.findGoogle(identity.subject()).orElse(null);
    if (prior != null) {
      return activate(prior);
    }
    String email = Registration.email(identity.email());
    if (accounts.findByEmail(email).isPresent()) {
      throw new ApiError(HttpStatus.CONFLICT, "SIGN_IN_AND_LINK_GOOGLE");
    }
    String name = Registration.name(identity.name());
    long profileId = accounts.createPassengerProfile(name, email);
    Account account = insert(email, name, null, Role.PASSENGER, Status.ACTIVE, profileId);
    link(account.member().id(), identity.subject());
    return activate(account);
  }

  /** Sign in with an existing staff provider link or an explicitly approved operator binding. */
  @Transactional
  public Access loginStaffGoogle(String credential) {
    var identity = google.verifyStaff(credential);
    var email = Registration.email(identity.email());
    var operator = operators.staffIdentity(identity.subject(), email);
    if (operator.isPresent()) {
      return activate(operator.get());
    }
    if (accounts.findByEmail(email).filter(a -> a.member().role() != Role.PASSENGER).isPresent()) {
      throw new ApiError(HttpStatus.CONFLICT, "SIGN_IN_AND_LINK_GOOGLE");
    }
    throw new ApiError(HttpStatus.FORBIDDEN, "STAFF_ACCOUNT_REQUIRED");
  }

  @Transactional
  public void linkGoogle(long accountId, String credential) {
    GoogleIdentity.VerifiedGoogle identity = google.verify(credential);
    Account account = account(accountId);
    if (!account.member().email().equals(Registration.email(identity.email()))) {
      throw new ApiError(HttpStatus.CONFLICT, "GOOGLE_EMAIL_MISMATCH");
    }
    if (accounts
        .findGoogle(identity.subject())
        .map(existing -> existing.member().id() == accountId)
        .orElse(false)) {
      return;
    }
    if (operators.isCompanion(accountId)) {
      if (operators
          .staffIdentity(identity.subject(), account.member().email())
          .map(a -> a.member().id() == accountId)
          .orElse(false)) {
        return;
      }
      throw new ApiError(HttpStatus.CONFLICT, "GOOGLE_ALREADY_LINKED");
    }
    link(accountId, identity.subject());
  }

  public String googleClientId() {
    return google.webClientId();
  }

  public User me(long accountId) {
    return account(accountId).user();
  }

  public long passengerId(long accountId) {
    Long profileUserId = account(accountId).profileUserId();
    if (profileUserId == null) {
      throw new ApiError(HttpStatus.FORBIDDEN, "PASSENGER_REQUIRED");
    }
    return profileUserId;
  }

  public void logout(Jwt token) {
    sessions.revoke(AmoJwt.sessionId(token), Long.parseLong(token.getSubject()));
  }

  private Account account(long id) {
    return accounts
        .findById(id)
        .filter(a -> a.member().status() == Status.ACTIVE)
        .orElseThrow(() -> new ApiError(HttpStatus.UNAUTHORIZED, "SESSION_INACTIVE"));
  }

  private Access activate(Account account) {
    if (account.member().status() != Status.ACTIVE) {
      throw new ApiError(HttpStatus.FORBIDDEN, "ACCOUNT_" + account.member().status().name());
    }
    return jwt.issue(account);
  }

  private Account insert(
      String email, String name, String hash, Role role, Status status, Long userId) {
    try {
      return accounts.insert(email, name, hash, role, status, userId);
    } catch (DuplicateKeyException e) {
      throw new ApiError(HttpStatus.CONFLICT, "EMAIL_IN_USE");
    }
  }

  private void link(long accountId, String subject) {
    try {
      accounts.linkGoogle(accountId, subject);
    } catch (DuplicateKeyException e) {
      throw new ApiError(HttpStatus.CONFLICT, "GOOGLE_ALREADY_LINKED");
    }
  }

  private String hash(String password) {
    if (password.length() < 10 || !Registration.validPasswordBytes(password)) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_PASSWORD_LENGTH");
    }
    return passwords.encode(password);
  }
}
