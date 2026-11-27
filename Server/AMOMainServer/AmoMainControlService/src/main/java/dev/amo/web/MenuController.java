package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.maincontrol.Menu;
import dev.amo.maincontrol.MenuService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Lists display metadata and updates it with administrator authorization. */
@RestController
class MenuController {
  private final MenuService menus;

  MenuController(MenuService menus) {
    this.menus = menus;
  }

  @GetMapping({"/api/admin/menu", "/api/menu"})
  List<Menu> menu() {
    return menus.menus();
  }

  @PutMapping("/api/admin/menu/{key}")
  Menu update(
      @PathVariable String key, @AuthenticationPrincipal Jwt actor, @Valid @RequestBody Edit body) {
    if (body.key() != null && !key.equals(body.key())) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "MENU_KEY_MISMATCH");
    }
    return menus.update(
        Long.parseLong(actor.getSubject()),
        new Menu(
            key,
            body.labelKo().strip(),
            body.labelEn().strip(),
            body.labelZh().strip(),
            body.visible(),
            body.position()));
  }

  record Edit(
      String key,
      @NotBlank @Size(max = 80) String labelKo,
      @NotBlank @Size(max = 80) String labelEn,
      @NotBlank @Size(max = 80) String labelZh,
      @NotNull Boolean visible,
      @NotNull @Min(0) Integer position) {}
}
