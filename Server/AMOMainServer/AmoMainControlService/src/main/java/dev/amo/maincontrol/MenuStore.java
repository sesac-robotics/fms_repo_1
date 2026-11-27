package dev.amo.maincontrol;

import java.util.List;
import java.util.Optional;

/** Storage operations required by the menu administration use case. */
interface MenuStore {
  List<Menu> menus();

  Optional<Menu> update(Menu menu);

  void audit(long actorId, String key);
}
