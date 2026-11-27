"""Configure application-local trust for the classroom TLS ingress."""

import os
from pathlib import Path

from PyQt6.QtNetwork import QSslCertificate, QSslConfiguration


def configure_classroom_trust() -> None:
    """Add the public PEM certificates named by AMO_LAN_CA_FILE; reject invalid input."""
    certificate_path = os.environ.get('AMO_LAN_CA_FILE')
    if not certificate_path:
        return
    certificates = QSslCertificate.fromData(Path(certificate_path).read_bytes())
    if not certificates:
        raise ValueError('AMO_LAN_CA_FILE must contain a PEM certificate.')
    configuration = QSslConfiguration.defaultConfiguration()
    configuration.addCaCertificates(certificates)
    QSslConfiguration.setDefaultConfiguration(configuration)
