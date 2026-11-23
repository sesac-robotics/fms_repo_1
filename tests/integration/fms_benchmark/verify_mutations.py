"""Exercise existing menu and staff approval contracts via the native Qt panels."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from uuid import uuid4

from amo_fms.comparison import ComparisonApplication
from amo_fms.comparison_members import MembersPanel
from amo_fms.comparison_menus import MenuPanel
from amo_fms.config import Config, Preferences
from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QTabWidget


def register_fixture(origin: str, email: str, password: str) -> None:
    """Create one pending staff record in the isolated demo service."""
    body = json.dumps(
        {'email': email, 'name': 'Synthetic reviewer', 'password': password}
    )
    request = Request(
        origin + '/api/auth/register/admin',
        data=body.encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=8) as response:
        if response.status != 202 or json.load(response)['status'] != 'PENDING':
            raise ValueError('Expected pending staff fixture.')


def main() -> int:
    """Verify the member transition and menu save with independent readbacks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = Config.from_environment()
    password = os.environ['AMO_BENCH_DEMO_PASSWORD']
    email = f'bench-staff-{uuid4().hex[:12]}@example.invalid'
    register_fixture(config.endpoint, email, password)
    app = QApplication([])
    settings = QSettings(str(args.output / 'mutations.ini'), QSettings.Format.IniFormat)
    settings.setValue('walkthrough/enabled', False)
    window = ComparisonApplication(config, Preferences(settings))
    window.show()
    state = 'load-members'
    original = ''
    marker = 'Benchmark overview'

    def exercise() -> None:
        nonlocal state, original
        tabs = window.centralWidget().findChild(QTabWidget)
        if tabs is None:
            return
        members = tabs.findChild(MembersPanel)
        menus = tabs.findChild(MenuPanel)
        if state == 'load-members':
            tabs.setCurrentWidget(members)
            members._search.setText(email)
            members._start()
            state = 'approve'
        elif state == 'approve' and members._rows:
            if members._rows[0]['status'] != 'PENDING':
                raise ValueError('Search returned unexpected staff status.')
            members._table.selectRow(0)
            with patch.object(
                QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes
            ):
                members._review(True)
            state = 'approval-readback'
        elif state == 'approval-readback' and not members._reply:
            if members._rows[0]['status'] != 'ACTIVE':
                raise ValueError('Staff update did not persist.')
            print('Pending staff approved and read back as ACTIVE.', flush=True)
            tabs.setCurrentWidget(menus)
            menus.load()
            state = 'edit-menu'
        elif state == 'edit-menu' and menus._rows and not menus._pending:
            menus._items.setCurrentText('overview')
            original = menus._labels['labelEn'].text()
            menus._labels['labelEn'].setText(marker)
            menus._save()
            state = 'restore-menu'
        elif state == 'restore-menu' and not menus._pending:
            menus._items.setCurrentText('overview')
            if menus._labels['labelEn'].text() != marker:
                raise ValueError('Saved menu label did not persist.')
            menus._labels['labelEn'].setText(original)
            menus._save()
            state = 'confirm-restore'
        elif state == 'confirm-restore' and not menus._pending:
            menus._items.setCurrentText('overview')
            if menus._labels['labelEn'].text() != original:
                raise ValueError('Original label was not restored.')
            print('Menu update and original-label restoration read back.', flush=True)
            app.quit()

    def tick() -> None:
        try:
            exercise()
        except Exception as error:
            print(error, flush=True)
            app.exit(1)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(250)
    window._api.login('admin@amo.test', password)
    QTimer.singleShot(25_000, lambda: app.exit(1))
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
