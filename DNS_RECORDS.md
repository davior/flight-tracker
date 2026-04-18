# DNS Records for chemtrail-tracker.com Mail Server

Configure these records at your DNS registrar/nameserver. Set the `A` record first
so Caddy can complete its ACME challenge before the mailserver starts.

## Required Records

### A — Mail subdomain

```
mail.chemtrail-tracker.com.    IN  A    <YOUR_SERVER_PUBLIC_IP>
```

### MX — Inbound mail routing

```
chemtrail-tracker.com.         IN  MX  10  mail.chemtrail-tracker.com.
```

### SPF — Authorize the mail server to send on behalf of the domain

```
chemtrail-tracker.com.         IN  TXT  "v=spf1 mx ~all"
```

### DKIM — Email signature authentication

Run `./scripts/setup-mailserver.sh` first. It prints the exact record value.
The selector is `mail` by default, so the DNS name is:

```
mail._domainkey.chemtrail-tracker.com.  IN  TXT  "v=DKIM1; k=rsa; p=<PUBLIC_KEY>"
```

The full value is also in `mailserver/config/opendkim/keys/chemtrail-tracker.com/mail.txt`
after the setup script has run.

### DMARC — Policy for authentication failures

```
_dmarc.chemtrail-tracker.com.  IN  TXT  "v=DMARC1; p=quarantine; rua=mailto:accounts@chemtrail-tracker.com"
```

### PTR — Reverse DNS (set at your VPS/hosting provider, not your DNS registrar)

In your VPS control panel, configure the reverse DNS entry for your server's
public IP to resolve to `mail.chemtrail-tracker.com`. This is required by many
receiving mail servers to accept your outbound email.

---

## First-Deploy Sequence

1. Set the `A` record above (DNS must resolve before deploying)
2. Deploy: `./scripts/deploy.sh`
3. Wait ~60s for the mailserver container to become healthy
4. Run: `./scripts/setup-mailserver.sh` (creates account + generates DKIM keys)
5. Add the remaining DNS records (MX, SPF, DKIM, DMARC, PTR) using the DKIM key from step 4
6. Verify the account exists: `docker compose -f docker-compose.prod.yml exec mailserver setup email list`
7. After DNS propagates (~24h), verify with https://www.mail-tester.com

## Verification Commands

```bash
# Check SMTP port is listening
telnet mail.chemtrail-tracker.com 587

# List configured accounts
docker compose -f docker-compose.prod.yml exec mailserver setup email list

# View mail logs
docker compose -f docker-compose.prod.yml logs mailserver
```
