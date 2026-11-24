package dev.amo.auth;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import dev.amo.ApiError;
import dev.amo.auth.GoogleIdentity.VerifiedGoogle;
import dev.amo.auth.Identity.Access;
import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;

class AuthServiceGoogleTest {
  private static final String CREDENTIAL = "verified-google-identity";
  private static final String SUBJECT = "google-subject";
  private static final String STAFF_EMAIL = "staff@example.test";
  private static final Account ADMIN =
      new Account(new Member(1, "Admin", STAFF_EMAIL, Role.ADMIN, Status.ACTIVE), "hash", null);

  private final AccountRepository accounts = mock(AccountRepository.class);
  private final GoogleOperators operators = mock(GoogleOperators.class);
  private final AmoJwt jwt = mock(AmoJwt.class);
  private final GoogleIdentity google = mock(GoogleIdentity.class);
  private final AuthService auth =
      new AuthService(
          accounts,
          operators,
          mock(SessionRepository.class),
          jwt,
          google,
          mock(PasswordEncoder.class));

  @Test
  void aVerifiedNewGoogleIdentityReceivesPassengerAccessOnly() {
    String email = "new@example.test";
    String name = "Administrator";
    var passenger =
        new Account(new Member(5, name, email, Role.PASSENGER, Status.ACTIVE), null, 91L);
    verifiedIdentity(email, name);
    when(accounts.createPassengerProfile(name, email)).thenReturn(91L);
    when(accounts.insert(email, name, null, Role.PASSENGER, Status.ACTIVE, 91L))
        .thenReturn(passenger);
    when(jwt.issue(passenger)).thenReturn(new Access("passenger", Instant.EPOCH, passenger.user()));

    assertEquals(Role.PASSENGER, auth.loginGoogle(CREDENTIAL).user().role());
    verify(accounts).insert(email, name, null, Role.PASSENGER, Status.ACTIVE, 91L);
    verify(accounts).linkGoogle(5L, SUBJECT);
  }

  @Test
  void aMatchingUnlinkedStaffEmailCannotGrantStaffAccess() {
    verifiedIdentity(STAFF_EMAIL, "Admin");
    when(accounts.findByEmail(STAFF_EMAIL)).thenReturn(Optional.of(ADMIN));

    var failure = assertThrows(ApiError.class, () -> auth.loginGoogle(CREDENTIAL));

    assertEquals(HttpStatus.CONFLICT, failure.status());
    assertEquals("SIGN_IN_AND_LINK_GOOGLE", failure.code());
    verify(accounts, never()).linkGoogle(anyLong(), anyString());
    verifyNoInteractions(jwt);
  }

  @Test
  void explicitlyLinkedStaffWithTheSameEmailRetainsItsApprovedRole() {
    verifiedIdentity("STAFF@example.test", "Admin");
    when(accounts.findById(1L)).thenReturn(Optional.of(ADMIN));
    when(accounts.findGoogle(SUBJECT)).thenReturn(Optional.empty(), Optional.of(ADMIN));
    when(jwt.issue(ADMIN)).thenReturn(new Access("staff", Instant.EPOCH, ADMIN.user()));

    auth.linkGoogle(1L, CREDENTIAL);
    verify(accounts).linkGoogle(1L, SUBJECT);

    assertEquals(Role.ADMIN, auth.loginGoogle(CREDENTIAL).user().role());
  }

  @Test
  void cannotLinkGoogleWithADifferentVerifiedEmail() {
    verifiedIdentity("other@example.test", "Other");
    when(accounts.findById(1L)).thenReturn(Optional.of(ADMIN));

    var failure = assertThrows(ApiError.class, () -> auth.linkGoogle(1L, CREDENTIAL));

    assertEquals("GOOGLE_EMAIL_MISMATCH", failure.code());
    verify(accounts, never()).linkGoogle(anyLong(), anyString());
    verifyNoInteractions(jwt);
  }

  @Test
  void inactiveStaffCannotLinkOrSignInThroughGoogle() {
    var inactive =
        new Account(
            new Member(1, "Admin", STAFF_EMAIL, Role.ADMIN, Status.SUSPENDED), "hash", null);
    verifiedIdentity(STAFF_EMAIL, "Admin");
    when(accounts.findById(1L)).thenReturn(Optional.of(inactive));
    when(accounts.findGoogle(SUBJECT)).thenReturn(Optional.of(inactive));

    var linkFailure = assertThrows(ApiError.class, () -> auth.linkGoogle(1L, CREDENTIAL));
    var loginFailure = assertThrows(ApiError.class, () -> auth.loginGoogle(CREDENTIAL));

    assertEquals("SESSION_INACTIVE", linkFailure.code());
    assertEquals("ACCOUNT_SUSPENDED", loginFailure.code());
    verify(accounts, never()).linkGoogle(anyLong(), anyString());
    verifyNoInteractions(jwt);
  }

  @Test
  void oneGoogleIdentityKeepsSeparatePassengerAndOperatorSessions() {
    var passenger =
        new Account(new Member(5, "Rider", STAFF_EMAIL, Role.PASSENGER, Status.ACTIVE), null, 91L);
    var operator =
        new Account(new Member(6, "Rider", STAFF_EMAIL, Role.OPERATOR, Status.ACTIVE), null, null);
    verifiedIdentity(STAFF_EMAIL, "Rider");
    when(google.verifyStaff(CREDENTIAL))
        .thenReturn(new VerifiedGoogle(SUBJECT, STAFF_EMAIL, "Rider"));
    when(accounts.findGoogle(SUBJECT)).thenReturn(Optional.of(passenger));
    when(operators.staffIdentity(SUBJECT, STAFF_EMAIL)).thenReturn(Optional.of(operator));
    when(jwt.issue(passenger)).thenReturn(new Access("rider", Instant.EPOCH, passenger.user()));
    when(jwt.issue(operator)).thenReturn(new Access("operator", Instant.EPOCH, operator.user()));

    assertEquals(passenger.user(), auth.loginGoogle(CREDENTIAL).user());
    assertEquals(operator.user(), auth.loginStaffGoogle(CREDENTIAL).user());
  }

  @Test
  void aVerifiedGooglePassengerWithoutStaffApprovalCannotGetAStaffSession() {
    when(google.verifyStaff(CREDENTIAL))
        .thenReturn(new VerifiedGoogle(SUBJECT, STAFF_EMAIL, "Rider"));

    var failure = assertThrows(ApiError.class, () -> auth.loginStaffGoogle(CREDENTIAL));

    assertEquals("STAFF_ACCOUNT_REQUIRED", failure.code());
    verifyNoInteractions(jwt);
  }

  private void verifiedIdentity(String email, String name) {
    when(google.verify(CREDENTIAL)).thenReturn(new VerifiedGoogle(SUBJECT, email, name));
  }
}
