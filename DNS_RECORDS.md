# DNS Records for chemtrail-tracker.com

Configure these records at your DNS registrar/nameserver.

Outbound email is handled by **smtp2go**. Inbound forwarding is handled by
**ImprovMX**. No mail server runs on this host — ports 25, 587, and 993 are
not exposed.

## Records to Delete

If migrating from the old self-hosted mailserver, remove these:

| Type | Name                               | Reason                              |
|------|------------------------------------|-------------------------------------|
| A    | `mail.chemtrail-tracker.com`       | No longer hosting a mail server     |
| TXT  | `mail._domainkey.chemtrail-tracker.com` | DKIM key for old docker-mailserver |

## Required Records

### A — Domain routing

| Name                    | Value                  |
|-------------------------|------------------------|
| `chemtrail-tracker.com` | your server's public IP |
| `www.chemtrail-tracker.com` | your server's public IP |

Caddy needs both A records in place **before** first deployment to complete
the Let's Encrypt ACME challenge.

### MX — Inbound mail routing (ImprovMX)

Sign up at https://improvmx.com, add your domain, and use the values they
display. They look like:

```
chemtrail-tracker.com.  IN  MX  10  mx1.improvmx.com.
chemtrail-tracker.com.  IN  MX  20  mx2.improvmx.com.
```

Configure forwarding rules in the ImprovMX dashboard
(e.g. accounts@ → yourpersonal@gmail.com).

### SPF — Authorise smtp2go and ImprovMX to send on behalf of the domain

```
chemtrail-tracker.com.  IN  TXT  "v=spf1 include:spf.smtp2go.net include:spf.improvmx.com ~all"
```

### DKIM — smtp2go (via CNAME)

smtp2go provides these in their dashboard under **Sender Domains**. The
records below are illustrative — use the exact values smtp2go gives you.

```
s1018965._domainkey.chemtrail-tracker.com.  IN  CNAME  dkim.smtp2go.net.
em1018965.chemtrail-tracker.com.            IN  CNAME  return.smtp2go.net.
link.chemtrail-tracker.com.                 IN  CNAME  track.smtp2go.net.
```

### DMARC — Policy for authentication failures

```
_dmarc.chemtrail-tracker.com.  IN  TXT  "v=DMARC1; p=quarantine; rua=mailto:accounts@chemtrail-tracker.com"
```

---

## Setup Sequence

1. Sign up for smtp2go → navigate to **Sender Domains** → authenticate your
   domain → add the DKIM CNAME and SPF records they provide
2. Sign up for ImprovMX → add `chemtrail-tracker.com` → add MX records →
   create forwarding rules (accounts@ → personal inbox)
3. Set `.env` SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
   `SMTP_PASSWORD`) from the smtp2go dashboard
4. Deploy: `./scripts/deploy.sh`
5. After DNS propagates (~30 min–24h), verify with https://www.mail-tester.com

## Verification Commands

```bash
# Check SPF record
dig TXT chemtrail-tracker.com

# Check MX records
dig MX chemtrail-tracker.com

# Check DKIM CNAME
dig CNAME s1018965._domainkey.chemtrail-tracker.com

# Send a test email via smtp2go (replace credentials)
curl -s --ssl-reqd \
  --url "smtps://mail-au.smtp2go.com:465" \
  --user "chemtrail-tracker.com:<SMTP_PASSWORD>" \
  --mail-from "accounts@chemtrail-tracker.com" \
  --mail-rcpt "test@example.com" \
  --upload-file - <<EOF
Subject: Test

Hello from Flight Tracker.
EOF
```
