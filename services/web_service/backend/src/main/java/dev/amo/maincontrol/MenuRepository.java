package dev.amo.maincontrol;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Persists menu display metadata and records modifications in the staff audit trail. */
@Repository
class MenuRepository {
  private final JdbcClient jdbc;

  MenuRepository(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  List<Menu> menus() {
    return jdbc.sql("SELECT * FROM amo_menu ORDER BY position, key")
        .query(MenuRepository::menu)
        .list();
  }

  Optional<Menu> update(Menu menu) {
    return jdbc.sql(
            """
        UPDATE amo_menu SET label_ko = ?, label_en = ?, label_zh = ?, visible = ?, position = ?
        WHERE key = ? RETURNING *
        """)
        .param(menu.labelKo())
        .param(menu.labelEn())
        .param(menu.labelZh())
        .param(menu.visible())
        .param(menu.position())
        .param(menu.key())
        .query(MenuRepository::menu)
        .optional();
  }

  void audit(long actorId, String key) {
    jdbc.sql("INSERT INTO amo_admin_audit (actor_id, action) VALUES (?, ?)")
        .param(actorId)
        .param("MENU_UPDATE:" + key)
        .update();
  }

  private static Menu menu(ResultSet row, int unused) throws SQLException {
    return new Menu(
        row.getString("key"),
        row.getString("label_ko"),
        row.getString("label_en"),
        row.getString("label_zh"),
        row.getBoolean("visible"),
        row.getInt("position"));
  }
}
