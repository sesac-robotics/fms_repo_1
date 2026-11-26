# Direct classroom access

Run this ingress on the Linux presenter laptop alongside the existing classroom
stack. It exposes the Admin Web and gateway through one HTTPS origin, and the
read-only FMS IF-03 snapshot protocol over a separate TLS TCP port. The ingress
joins the host network and owns two listeners on the specified Wi-Fi IPv4
address. Main Control, IF-02 and PostgreSQL retain their existing loopback
connections. Android is the classroom passenger client.

## Presenter setup

1. Verify the classroom stack and its existing PostgreSQL mount and endpoint.
   Check `curl -fsS http://127.0.0.1:18085/api/health` for `UP` and
   `motionEnabled: false`. Start an existing stopped stack using
   `~/.local/state/amo-classroom/start-stack`.
2. Obtain a server certificate matching the chosen DNS name or Wi-Fi IP.
   With a private CA, give teammates the public CA PEM and its SHA-256
   fingerprint over a trusted channel. Keep the CA private key and the
   ingress PEM (server certificate chain and private key) on the presenter
   laptop, outside the repository. An IP certificate must include the IP in
   its subject alternative names and must be reissued if that address changes.
3. Run from the repository root using the approved Wi-Fi address and allowed
   classroom subnet. The HTTPS and IF-03 TLS ports default to 9443 and 18487.

```bash
export AMO_LAN_BIND='<presenter-wifi-ip>'
export AMO_LAN_CIDR='<allowed-classroom-cidr>'
export AMO_LAN_TLS_PEM=/absolute/path/to/classroom-chain-and-key.pem
export AMO_LAN_UID="$(id -u)" AMO_LAN_GID="$(id -g)"
docker compose -f docker/classroom-lan.compose.yaml config -q
docker compose -f docker/classroom-lan.compose.yaml up -d
```

Stopping this ingress is independent of the classroom stack. Run
`docker compose -f docker/classroom-lan.compose.yaml down` with the same
configuration. Keep the former remote-access service running during transition
if it is still in use.

## Team laptop setup

Use the HTTPS origin supplied by the presenter. If there is no OAuth-approved
HTTPS hostname, run the Admin Web frontend locally from
`Server/WebServer/AmoWebService/frontend/admin` using Node.js 24 and npm.
Run `npm ci` once and keep the frontend terminal open.

```bash
export NODE_EXTRA_CA_CERTS=/absolute/path/to/classroom-ca.pem
export AMO_API_URL='https://<presenter-wifi-ip>:9443'
npm run dev -- --port 5175 --strictPort
```

Configure the existing Google Web OAuth client to allow
`http://localhost:5175` for this workflow. Google excludes non-loopback IP
addresses from allowed JavaScript origins. The local frontend sends API
requests directly to the presenter over HTTPS. With an approved, trusted
HTTPS hostname, use that origin for both Web and API and skip the local
frontend. Register the exact browser origin with Google in either mode.

From the PyQt application directory, start each app in its own terminal
with the same settings. The following is the IP-only setup.

```bash
export AMO_FMS_API='https://<presenter-wifi-ip>:9443'
export AMO_ADMIN_WEB_URL=http://localhost:5175
export AMO_LAN_CA_FILE=/absolute/path/to/classroom-ca.pem
export AMO_FMS_TCP_PORT=18487
export AMO_SCENARIO_REVIEW=1
uv run --locked amo-fms
# In the other terminal, with the same environment:
uv run --locked amo-admin
```

The FMS obtains the IF-03 hostname from the API origin. Qt verifies the TLS
certificate before sending the staff bearer token. The local launcher
defaults still use plain TCP on IPv4 loopback. The staff browser uses one session on the configured Web origin, with
independent connection approval for each PyQt app. Android uses a separate
passenger session. Build its debug APK with `-PamoApiUrl=<HTTPS-origin>`
and, for a private CA, `-PamoLanCaFile=/absolute/path/to/classroom-ca.pem`.
The debug APK trusts that CA for the configured API host. For Google sign-in,
use a team-signed APK whose package and signing certificate SHA-1 are already
registered with the existing OAuth project, or register the team's authorized
debug signing certificates. Keep signing keys private.

Verify on a separate device on the same Wi-Fi. Check HTTPS health and browser
login, connect each native app using the same browser session, and confirm
the FMS vehicle list and the Admin operations view. On the Google Play AVD
or device, complete Google sign-in and open passenger history. Run the Taxi
review from one Admin window and compare the same request ID and applied
destination across the clients. Check motion remains disabled. Report these
results independently.


## Google sign-in data in Amo DB

On first passenger sign-in, Main Control stores the normalized email and
Google display name in `amo_accounts` and creates a linked passenger profile
in `users`. The account row includes its ID, role, status, creation time and
profile ID. The profile starts with the email as contact information. The
provider issuer and stable Google subject are stored with the account ID in
`amo_provider_links`.

A separately approved staff account stores its own role and status and
references the original passenger account when it shares that Google
identity. AMO session rows store the session ID, account ID, expiry and
revocation time. Desktop handoff stores a short-lived code digest, challenge,
callback port, source session and account identifiers, and expiry. Google
passwords, Google ID tokens, and Google profile photos are not persisted by
this flow. First-time Google accounts have no AMO password hash.
