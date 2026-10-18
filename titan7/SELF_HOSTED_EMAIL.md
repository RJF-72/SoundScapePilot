# Self-Hosted Email System — Redemption Road Music Group

**Domain:** `redemptionroadmg.com`  
**Users:** ray, joni, keith, paige  
**Mail Host:** `mail.redemptionroadmg.com`

---

## 1. DNS Records Required

Create these records at your domain registrar / DNS host.

### A Record
```
mail.redemptionroadmg.com → <your server IPv4>
```

### MX Record
```
redemptionroadmg.com → mail.redemptionroadmg.com (priority 10)
```

### PTR (Reverse DNS)
Have your hosting provider set:
```
<your server IPv4> → mail.redemptionroadmg.com
```

### SPF
```
v=spf1 ip4:<your server IPv4> a:mail.redemptionroadmg.com -all
```

### DKIM
Selector: `rrmg`
```
rrmg._domainkey.redemptionroadmg.com → <DKIM public key>
```

### DMARC (start with monitoring)
```
_dmarc.redemptionroadmg.com → v=DMARC1; p=none; rua=mailto:dmarc@redemptionroadmg.com; adkim=s; aspf=s
```
After deliverability is proven, escalate to:
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@redemptionroadmg.com
```
Finally:
```
v=DMARC1; p=reject; rua=mailto:dmarc@redemptionroadmg.com
```

---

## 2. Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| OS | Ubuntu Server 22.04 LTS or Debian 12 | Ubuntu Server 22.04 LTS |
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Storage | 100 GB SSD | 200 GB SSD |
| Network | 1 static IPv4 | 1 static IPv4 + IPv6 |

### Open Ports
- `25` — SMTP (server-to-server)
- `587` — SMTP submission (users)
- `993` — IMAP over SSL
- `995` — POP3 over SSL (optional)

---

## 3. Mail Stack

| Role | Software |
|------|----------|
| SMTP (send/receive) | Postfix |
| IMAP/POP3 + SASL | Dovecot |
| DKIM signing | OpenDKIM |
| Spam/AV/DKIM/SPF/DMARC | Rspamd |
| TLS certificates | Let's Encrypt (Certbot) |
| Brute-force protection | Fail2ban |

---

## 4. User Accounts

Create these four mailboxes:

- `ray@redemptionroadmg.com`
- `joni@redemptionroadmg.com`
- `keith@redemptionroadmg.com`
- `paige@redemptionroadmg.com`

Storage path (Maildir):
```
/var/mail/vhosts/redemptionroadmg.com/<user>/
```

---

## 5. Postfix Core Configuration

```ini
# /etc/postfix/main.cf
myhostname = mail.redemptionroadmg.com
mydomain = redemptionroadmg.com
myorigin = $mydomain
inet_interfaces = all
mydestination = $myhostname, localhost.$mydomain, localhost
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
home_mailbox = Maildir/
virtual_mailbox_domains = redemptionroadmg.com
virtual_mailbox_base = /var/mail/vhosts
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_uid_maps = static:5000
virtual_gid_maps = static:5000
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous
smtpd_sasl_local_domain = $myhostname
smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination
smtpd_tls_security_level = may
smtpd_tls_cert_file = /etc/letsencrypt/live/mail.redemptionroadmg.com/fullchain.pem
smtpd_tls_key_file = /etc/letsencrypt/live/mail.redemptionroadmg.com/privkey.pem
smtp_tls_security_level = may
```

`/etc/postfix/vmailbox`:
```
ray@redemptionroadmg.com    redemptionroadmg.com/ray/
joni@redemptionroadmg.com   redemptionroadmg.com/joni/
keith@redemptionroadmg.com  redemptionroadmg.com/keith/
paige@redemptionroadmg.com  redemptionroadmg.com/paige/
```

Run:
```bash
postmap /etc/postfix/vmailbox
systemctl restart postfix
```

---

## 6. Dovecot Core Configuration

```ini
# /etc/dovecot/dovecot.conf
protocols = imap pop3 lmtp

# /etc/dovecot/conf.d/10-mail.conf
mail_location = maildir:/var/mail/vhosts/%d/%n
mail_uid = 5000
mail_gid = 5000

# /etc/dovecot/conf.d/10-auth.conf
disable_plaintext_auth = yes
auth_mechanisms = plain login
passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}
userdb {
  driver = static
  args = uid=5000 gid=5000 home=/var/mail/vhosts/%d/%n
}

# /etc/dovecot/conf.d/10-master.conf
service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0666
    user = postfix
    group = postfix
  }
}

# /etc/dovecot/conf.d/10-ssl.conf
ssl = required
ssl_cert = </etc/letsencrypt/live/mail.redemptionroadmg.com/fullchain.pem
ssl_key = </etc/letsencrypt/live/mail.redemptionroadmg.com/privkey.pem
```

Create password file:
```bash
doveadm pw -s SHA512-CRYPT
# Add lines to /etc/dovecot/users:
# ray@redemptionroadmg.com:{SHA512-CRYPT}$6$...
```

---

## 7. OpenDKIM

Generate keys:
```bash
opendkim-genkey -b 2048 -d redemptionroadmg.com -s rrmg
chown opendkim:opendkim rrmg.private
```

Add public key to DNS as shown in section 1.

`/etc/opendkim.conf`:
```
Domain                  redemptionroadmg.com
Selector                rrmg
KeyFile                 /etc/opendkim/keys/redemptionroadmg.com/rrmg.private
Socket                  inet:8891@localhost
```

Configure Postfix to use OpenDKIM:
```ini
smtpd_milters = inet:localhost:8891
non_smtpd_milters = $smtpd_milters
```

---

## 8. SoundScape Pilot SMTP Settings

In the SoundScape Pilot app, open **Settings → SMTP** and enter:

| Field | Value |
|-------|-------|
| SMTP Host | `mail.redemptionroadmg.com` |
| Port | `587` |
| Username | `ray@redemptionroadmg.com` (or joni/keith/paige) |
| Password | User's mailbox password |

SoundScape Pilot will rotate senders automatically among:
- ray@redemptionroadmg.com
- joni@redemptionroadmg.com
- keith@redemptionroadmg.com
- paige@redemptionroadmg.com

---

## 9. Sending Policy

| Limit | Value |
|-------|-------|
| Global rate | 5,000 emails/hour |
| Per user | 1,000 emails/hour |
| Max recipients/message | 100 |
| Max message size | 10 MB |

---

## 10. Backups

Back up daily:
- `/etc/postfix/`
- `/etc/dovecot/`
- `/etc/opendkim/`
- `/var/mail/vhosts/`
- DKIM private key

---

## 11. Monitoring

Watch:
- `mailq` queue length
- `/var/log/mail.log` delivery failures
- Authentication failures
- Disk usage on `/var/mail/vhosts/`
- TLS certificate expiry

---

## 12. Security Checklist

- [ ] Firewall blocks everything except 25, 587, 993, 995, 22
- [ ] Fail2ban enabled for SSH, SMTP auth, IMAP auth
- [ ] Strong mailbox passwords (16+ chars or app passwords)
- [ ] Disable plaintext auth
- [ ] TLS enforced on all client-facing services
- [ ] rDNS matches `mail.redemptionroadmg.com`
- [ ] SPF, DKIM, DMARC records published
- [ ] No open relay (test at mxtoolbox.com)
- [ ] Daily encrypted backups

---

## 13. SoundScape Pilot Integration

The app is pre-configured for `redemptionroadmg.com`. All owner accounts, signatures, and SMTP defaults point to this domain. Set real credentials in the app or via environment variables:

```powershell
$env:TITAN_SMTP_HOST = "mail.redemptionroadmg.com"
$env:TITAN_SMTP_PORT = "587"
$env:TITAN_SMTP_USER = "ray@redemptionroadmg.com"
$env:TITAN_SMTP_PASS = "your-app-password"
```

---

*Redemption Road Music Group — self-hosted, self-owned, zero third-party dependencies.*
