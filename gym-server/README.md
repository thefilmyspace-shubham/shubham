# House of Strength — gate test server (Phase 1)

A small server that the eSSL X2008 gate machine pushes punches to (ADMS),
and that sends commands back to the machine. Python standard library only.

What it shows at `http://SERVER-IP:8081/` (login `admin` + your password):
machines that connected, last punches, commands and their result, and the raw
traffic (to see exactly what this firmware sends).

Block / unblock works by deleting the member from the machine and writing them
back from a backup the server keeps. The server refuses to block a member until
their fingerprint backup has arrived, so a fingerprint is never lost.

## 1. Google Cloud VM (free tier)

Compute Engine → VM instances → Create instance:

| Setting | Value |
|---|---|
| Name | `hos-server` |
| Region | `us-central1` (Iowa), `us-west1` or `us-east1` only |
| Machine type | `e2-micro` |
| Boot disk | Ubuntu 24.04 LTS, **Standard persistent disk**, 30 GB |
| Firewall | leave both HTTP / HTTPS unticked (port 8081 is opened below) |

Billing → Budgets & alerts: add a small budget (e.g. ₹100) so any charge emails you.

Open port 8081: VPC network → Firewall → Create firewall rule:
name `allow-adms-8081`, targets *All instances in the network*,
source IPv4 ranges `0.0.0.0/0`, protocols and ports *TCP 8081*.

## 2. Put the server on the VM

On the VM list, click **SSH** next to `hos-server`, then paste:

```bash
sudo mkdir -p /opt/hos && sudo chown $USER /opt/hos
curl -fsSL -o /opt/hos/adms_server.py https://raw.githubusercontent.com/thefilmyspace-shubham/shubham/claude/quirky-brown-y54q7s/gym-server/adms_server.py
```

(If the repository is private, upload the file with the SSH window's
**Upload file** button instead, then `mv ~/adms_server.py /opt/hos/`.)

Run it as a service that restarts on its own (change the password):

```bash
sudo tee /etc/systemd/system/hos.service >/dev/null <<'EOF'
[Unit]
Description=House of Strength ADMS server
After=network-online.target

[Service]
Environment=ADMIN_PASS=CHANGE-ME
Environment=PORT=8081
Environment=DB_PATH=/opt/hos/hos.db
ExecStart=/usr/bin/python3 /opt/hos/adms_server.py
Restart=always
User=nobody
Group=nogroup

[Install]
WantedBy=multi-user.target
EOF
sudo chown nobody:nogroup /opt/hos
sudo systemctl daemon-reload && sudo systemctl enable --now hos
sudo systemctl status hos --no-pager
```

Open `http://EXTERNAL-IP:8081/` in a browser; it asks for `admin` and the password.

## 3. Point the machine at it (at the gym, when it is quiet)

Menu (M/OK) → COMM:

| Screen | Field | Value |
|---|---|---|
| Ethernet | Gateway | `192.168.31.1` |
| Ethernet | DNS | `8.8.8.8` |
| Cloud Server Setting | Server Mode | ADMS |
| Cloud Server Setting | Enable Domain Name | OFF |
| Cloud Server Setting | Server Address | VM's external IP |
| Cloud Server Setting | Server Port | `8081` |

Within a minute the machine should appear under **Machines** on the page.
To go back to the old setup: set Server Address back to `0.0.0.0`.

## Results on the real machine (13 Nov 2026)

eSSL X2008, serial NFZ8252002076, firmware 8.0.4.3, pushver 2.4.1:

- Connected over ADMS; the firmware adds `.aspx` to every path (handled).
- First connect uploaded 258 USER + 258 FP records and the day's punch history.
  The machine reports 262 fingerprints, so a few second-finger templates may be
  missing from the backup — check before blocking members with two fingers.
- New punches arrive within seconds; the old laptop program (port 4370) keeps
  receiving them too.
- Block (`DATA DELETE USERINFO`) → door stayed shut. Unblock (restore USERINFO +
  FINGERTMP from backup) → door opened. All commands returned 0.

## 4. Test checklist

1. Machine appears under Machines.
2. A punch at the gate shows under Last punches within a minute.
3. The old software (laptop program, port 4370) still gets today's attendance.
4. *Fetch one member + fingerprint* with a test member's Biometric ID →
   USER and FP (or BIODATA) rows appear under Stored member records.
5. *Block door* for that test member → their finger no longer opens the door.
6. *Unblock door* → their finger opens the door again.

Use a staff/test ID for 4–6, never a paying member.
