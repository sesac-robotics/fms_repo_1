"""Small bearer-authenticated client for the isolated local demo integration tests."""

from __future__ import annotations

import json
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
