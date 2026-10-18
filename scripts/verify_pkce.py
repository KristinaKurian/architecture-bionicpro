#!/usr/bin/env python3
"""Static PKCE configuration checks; not a browser/end-to-end OAuth test."""
import json
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
realm = json.loads((repo_root / 'keycloak/realm-export.json').read_text(encoding='utf-8'))
clients = [c for c in realm['clients'] if c['clientId'] == 'reports-frontend']
assert len(clients) == 1, 'Expected one frontend Keycloak client'
client = clients[0]
assert client['publicClient'] is True
assert client['standardFlowEnabled'] is True
assert client['implicitFlowEnabled'] is False
assert client['directAccessGrantsEnabled'] is False
assert client['serviceAccountsEnabled'] is False
assert client['attributes']['pkce.code.challenge.method'] == 'S256'
assert client['redirectUris'] == ['http://localhost:3000/']
assert client['webOrigins'] == ['http://localhost:3000']

app = (repo_root / 'frontend/src/App.tsx').read_text(encoding='utf-8')
assert "pkceMethod: 'S256'" in app
assert "flow: 'standard'" in app
assert 'initOptions={keycloakInitOptions}' in app
print('PASS: PKCE S256 is enabled in React and required by Keycloak.')
