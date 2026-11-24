"""Small bearer-authenticated client for the isolated local demo integration tests."""

from __future__ import annotations

import json
from base64 import b64decode
from socket import create_connection
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class DemoHttp:
    """Use the loopback Web gateway, or its private HTTP adapter for diagnostics."""

    def __init__(self, base: str) -> None:
        if not base.startswith('http://127.0.0.1:') or not base[17:].isdigit():
            raise ValueError('AMO_DEMO_HTTP must identify a loopback HTTP port')
        self.base = base

    def send(
        self,
        path: str,
        token: str = '',
        body: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        """Return status and JSON object without surfacing credentials in errors."""
        headers = {'Accept': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        request = Request(self.base + path, data=payload, headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def login(self, role: str) -> str:
        """Sign in as a fictional account created by the demo profile."""
        status, response = self.send(
            '/api/auth/login',
            body={'email': f'{role}@amo.test', 'password': 'AmoDemo!2026'},
        )
        if status != 200 or not isinstance(response.get('token'), str):
            raise RuntimeError(f'Demo login failed for {role}: {status}')
        return str(response['token'])

    def fms_snapshot(self, port: int, token: str) -> tuple[int, dict[str, object]]:
        """Exchange one bounded read-only IF-03 frame with Main Control."""
        payload = json.dumps(
            {
                'method': 'GET',
                'path': '/api/operations',
                'headers': {'Authorization': [f'Bearer {token}']},
                'body': '',
            }
        ).encode()
        with create_connection(('127.0.0.1', port), timeout=10) as connection:
            connection.sendall(len(payload).to_bytes(4, 'big') + payload)
            with connection.makefile('rb') as wire:
                size = int.from_bytes(wire.read(4), 'big')
                if not 0 < size <= 1024 * 1024:
                    raise ValueError('Invalid IF-03 frame size')
                envelope = json.loads(wire.read(size))
        return int(envelope['status']), json.loads(b64decode(envelope['body']))
