"""Run a native Qt client with the isolated benchmark's synthetic staff account."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from time import time

from amo_fms.admin import AdminApplication
from amo_fms.comparison_history import HistoryPanel
from amo_fms.comparison_members import MembersPanel
from amo_fms.config import Config, Preferences
from amo_fms.main import Application
from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QApplication, QTabWidget

SEARCHES = ('bench-passenger-999', 'ONE_WAY', 'Benchmark')


def main() -> int:
    """Open a visible fleet or admin window and run the timed schedule."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('baseline', 'admin'))
    parser.add_argument('directory', type=Path)
    parser.add_argument('start', type=float)
    parser.add_argument('duration', type=float)
    args = parser.parse_args()
    app = QApplication([])
    settings = QSettings(
        str(args.directory / f'{args.mode}.ini'), QSettings.Format.IniFormat
    )
    settings.setValue('walkthrough/enabled', False)
    settings.setValue('language', 'en')
    client = AdminApplication if args.mode == 'admin' else Application
    window = client(
        Config.from_environment(fleet=args.mode != 'admin'), Preferences(settings)
    )
    window.resize(990, 800)
    window.show()

    def exercise(index: int) -> None:
        tabs = window.centralWidget().findChild(QTabWidget)
        if tabs is None:
            raise RuntimeError('Admin workspace was not created.')
        key = ('members', 'trips', 'tests')[index]
        navigation = tabs.tabBar()
        position = next(i for i in range(tabs.count()) if navigation.tabData(i) == key)
        tabs.setCurrentIndex(position)
        panel = tabs.widget(position)
        if isinstance(panel, MembersPanel):
            panel._search.setText(SEARCHES[index])
            panel._start()
        elif isinstance(panel, HistoryPanel):
            panel._inputs['q'].setText(SEARCHES[index])
            panel.search()

    def begin() -> None:
        window._api.login('admin@amo.test', os.environ['AMO_BENCH_DEMO_PASSWORD'])
        if args.mode != 'baseline':
            for slot in range(6 if args.duration >= 42 else 3):
                index = slot % 3
                offset = 3000 + slot * 7000
                QTimer.singleShot(offset, lambda index=index: exercise(index))
        QTimer.singleShot(round(args.duration * 1000), app.quit)

    QTimer.singleShot(max(0, round((args.start - time()) * 1000)), begin)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
