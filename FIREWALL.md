-- Active: 1777028065987@@127.0.0.1@3306@flightlogs
# Firewall Rules for Production Deployment

Configure these rules using your firewall platform of choice (cloud provider security
groups, hardware firewall, OS-level firewall, etc.). The rules are derived from the
services defined in `docker-compose.prod.yml`.

## Inbound Rules

| Port / Protocol | Source         | Purpose                                             |
|-----------------|----------------|-----------------------------------------------------|
| 22/TCP          | Admin IPs only | SSH — server administration                         |
| 80/TCP          | Any            | HTTP — Caddy ACME challenge + redirect to HTTPS     |
| 443/TCP         | Any            | HTTPS — main application (Caddy)                    |
| 443/UDP         | Any            | HTTP/3 QUIC — modern browser optimization (Caddy)   |

Deny all other inbound traffic by default.

No mail server runs on this host. Inbound email forwarding is handled by ImprovMX
(external service) — no ports 25, 587, or 993 need to be open.

- **SSH (22/TCP):** Restrict to known admin IP addresses rather than allowing from any
  source. If your platform supports it, consider moving SSH to a non-standard port.
- **8000/TCP and 3306/TCP must never be opened.** The FastAPI backend and MariaDB
  database have no `ports:` mapping in `docker-compose.prod.yml` and communicate
  exclusively within Docker's internal network. Exposing either port would allow
  direct unauthenticated access to the API or database.

## Outbound Rules

| Port / Protocol    | Destination                                          | Purpose                                    |
|--------------------|------------------------------------------------------|--------------------------------------------|
| 80/TCP, 443/TCP    | Any                                                  | Let's Encrypt ACME — TLS cert issuance and renewal |
| 443/TCP            | opensky-network.org, auth.opensky-network.org        | OpenSky Network live flight data API       |
| 443/TCP            | adsbexchange.com, downloads.adsbexchange.com         | ADS-B Exchange live flight data API        |
| 443/TCP            | accounts.google.com, oauth2.googleapis.com           | Google OAuth (only if Google login is enabled) |
| 2525/TCP           | mail-au.smtp2go.com                                  | Outbound email delivery via smtp2go        |
| 443/TCP            | ghcr.io, registry-1.docker.io                        | Docker image pulls from container registries |
| 80/TCP, 443/TCP    | Any                                                  | OS and package updates                     |

If your firewall defaults to allow-all outbound, no explicit outbound rules are needed.
The table above documents expected egress for auditing and allow-listing purposes.

## Internal Network (Docker)

The `backend` (port 8000) and `db` (port 3306) services have no `ports:` entries in
`docker-compose.prod.yml`. They are reachable only within Docker's internal network —
Caddy proxies inbound HTTPS requests to the backend by service name (`backend:8000`),
and the backend connects to the database by service name (`db:3306`). No host-level
firewall rules are needed for these services, and none should be added.

---

## Verification Commands

```bash
# Confirm which ports are listening on the host (run on the server)
sudo ss -tlnp
sudo ss -ulnp   # UDP (for QUIC)

# From an external machine: confirm public ports are reachable
curl -I https://chemtrail-tracker.com

# From an external machine: confirm internal ports are NOT reachable (should time out)
# nc -zv <SERVER_IP> 8000
# nc -zv <SERVER_IP> 3306
# nc -zv <SERVER_IP> 25    # should also time out — no mail server on host
```
