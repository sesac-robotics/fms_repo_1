package dev.amo.maincontrol;

import dev.amo.maincontrol.MainControlFailure.Reason;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Updates approved menu entries; permissions are enforced by the HTTP security adapter. */
@Service
public class MenuService {
  private final MenuStore repository;

  MenuService(MenuStore repository) {
    this.repository = repository;
  }

  /** Returns the stored entries in display order. */
  public List<Menu> menus() {
    return repository.menus();
  }

  /** Updates display metadata and records the actor in the same transaction. */
  @Transactional
  public Menu update(long actorId, Menu requested) {
    if (requested.key().equals("settings") && !requested.visible()) {
      throw new MainControlFailure(Reason.SETTINGS_MUST_REMAIN_VISIBLE);
    }
    Menu menu =
        repository
            .update(requested)
            .orElseThrow(() -> new MainControlFailure(Reason.MENU_NOT_FOUND));
    repository.audit(actorId, menu.key());
    return menu;
  }
}
