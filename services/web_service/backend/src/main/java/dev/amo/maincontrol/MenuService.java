package dev.amo.maincontrol;

import dev.amo.ApiError;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Updates approved menu entries; permissions are enforced by the HTTP security adapter. */
@Service
public class MenuService {
  private final MenuRepository repository;

  MenuService(MenuRepository repository) {
    this.repository = repository;
  }

  public List<Menu> menus() {
    return repository.menus();
  }

  @Transactional
  public Menu update(long actorId, Menu requested) {
    if (requested.key().equals("settings") && !requested.visible()) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "SETTINGS_MUST_REMAIN_VISIBLE");
    }
    Menu menu =
        repository
            .update(requested)
            .orElseThrow(() -> new ApiError(HttpStatus.NOT_FOUND, "MENU_NOT_FOUND"));
    repository.audit(actorId, menu.key());
    return menu;
  }
}
