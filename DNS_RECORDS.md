# DNS Records for chemtrail-tracker.com

Configure these records at your DNS registrar/nameserver.

Outbound email is handled by **Brevo** (or your chosen relay). Inbound forwarding
is handled by **ImprovMX** (or Cloudflare Email Routing). No mail server runs on
this host — ports 25, 587, and 993 are not exposed.

## Required Records

### MX — Inbound mail routing (ImprovMX)

ImprovMX provides two MX records. Sign up at https://improvmx.com, add your
domain, and use the values they display. They look like:

```
chemtrail-tracker.com.  IN  MX  10  mx1.improvmx.com.
chemtrail-tracker.com.  IN  MX  20  mx2.improvmx.com.
```

Configure forwarding rules in the ImprovMX dashboard
(e.g. accounts@ → yourpersonal@gmail.com).

### SPF — Authorize Brevo to send on behalf of the domain

Brevo's SPF include (verify the current value in their dashboard under
Senders & IPs → Domains):

```
chemtrail-tracker.com.  IN  TXT  "v=spf1 include:sendinblue.com ~all"
```

If you also want to allow ImprovMX to forward on behalf of the domain, add
their include too (check their docs for the current value):

```
chemtrail-tracker.com.  IN  TXT  "v=spf1 include:sendinblue.com include:spf.improvmx.com ~all"
```

### DKIM — Email signature authentication (Brevo)

Brevo provides the exact record value in their dashboard under
Senders & IPs → Domains → authenticate your domain. The selector and key
look like:

```
mail._domainkey.chemtrail-tracker.com.  IN  TXT  "v=DKIM1; k=rsa; p=<PUBLIC_KEY_FROM_BREVO>"
```

### DMARC — Policy for authentication failures

```
_dmarc.chemtrail-tracker.com.  IN  TXT  "v=DMARC1; p=quarantine; rua=mailto:accounts@chemtrail-tracker.com"
```

---

## Setup Sequence

1. Sign up for Brevo → navigate to **SMTP & API → SMTP** tab → copy credentials
   into `.env` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`)
2. In Brevo, go to **Senders & IPs → Domains** → authenticate your domain →
   add the DKIM and SPF records they provide
3. Sign up for ImprovMX → add `chemtrail-tracker.com` → add MX records →
   create forwarding rules (accounts@ → personal inbox)
4. Deploy: `./scripts/deploy.sh`
5. After DNS propagates (~30 min–24h), verify with https://www.mail-tester.com

## Verification Commands

```bash
# Check SPF record
dig TXT chemtrail-tracker.com

# Check MX records
dig MX chemtrail-tracker.com

# Check DKIM record
dig TXT mail._domainkey.chemtrail-tracker.com

# Send a test email via Brevo SMTP (replace credentials)
curl -s smtp://smtp-relay.brevo.com:587 \
  --user "your-brevo-login@example.com:your-smtp-key" \
  --mail-from "accounts@chemtrail-tracker.com" \
  --mail-rcpt "test@example.com" \
  --upload-file - <<EOF
Subject: Test

Hello from Flight Tracker.
EOF
```
