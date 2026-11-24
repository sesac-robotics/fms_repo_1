package dev.amo.web;

import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.StaffAdministration;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Lists local members and approves or suspends staff accounts. */
@RestController
@RequestMapping("/api/admin/members")
class MembersController {
  private final StaffAdministration staff;

  MembersController(StaffAdministration staff) {
    this.staff = staff;
  }

  @GetMapping
  List<Member> members() {
    return staff.members();
  }

  @GetMapping("/page")
  ReadPage<Member> page(
      @RequestParam(defaultValue = "") String q,
      @RequestParam(defaultValue = "0") int offset,
      @RequestParam(defaultValue = "50") int limit,
      @RequestParam(defaultValue = "false") boolean newest) {
    ReadPage.validate(offset, limit, q);
    return ReadPage.from(staff.memberPage(q.strip(), offset, limit + 1, newest), offset, limit);
  }

  @PutMapping("/{id}/approval")
  Member approve(
      @AuthenticationPrincipal Jwt actor,
      @PathVariable long id,
      @Valid @RequestBody Approval body) {
    return staff.approve(Long.parseLong(actor.getSubject()), id, body.approved(), body.role());
  }

  @PutMapping("/{id}/google-operator")
  Member addGoogleOperator(@AuthenticationPrincipal Jwt actor, @PathVariable long id) {
    return staff.addGoogleOperator(Long.parseLong(actor.getSubject()), id);
  }

  record Approval(@NotNull Boolean approved, Role role) {}
}
