package dev.amo.auth;

import java.time.Instant;

/** Local account, access session, and public authentication representations. */
public final class Identity {
  private Identity() {}

  public enum Role {
    ADMIN,
    OPERATOR,
    PASSENGER
  }

  public enum Status {
    ACTIVE,
    PENDING,
    SUSPENDED
  }

  /** Account identity with a separate, optional operations membership ID. */
  public record User(long id, String name, String email, Role role, Long profileUserId) {}

  public record Member(long id, String name, String email, Role role, Status status) {}

  public record Access(String token, Instant expiresAt, User user) {}

  record Account(Member member, String passwordHash, Long profileUserId) {
    User user() {
      return new User(member.id(), member.name(), member.email(), member.role(), profileUserId);
    }
  }
}
