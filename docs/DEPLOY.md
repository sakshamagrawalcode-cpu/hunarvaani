# Deploy HunarVaani to a server in India (step A13)

Why: on the laptop every prompt and key travels through home Wi-Fi and a Cloudflare quick tunnel
whose address changes on every restart. A small server in India with its own domain removes all
of that: fixed URL, no laptop, no tunnel.

## 1. Which account to make (checked 30 Sep 2026)

| Option | Cost | Region | Good for us? |
|---|---|---|---|
| **Azure for Students** (recommended) | USD 100 credit, **no credit card**, needs a college email | **Central India (Pune)**, South India (Chennai) | Yes. A B2s (2 vCPU, 4 GB) or B2ms (2 vCPU, 8 GB) VM runs the whole stack; the credit covers the demo period |
| Oracle Cloud Always Free | Free forever (2 OCPU + 12 GB ARM since June 2026), card needed to verify | Mumbai, Hyderabad | Yes if a machine is available ("out of host capacity" happens in Mumbai); ARM works with our images |
| Google Cloud free trial | USD 300 credit, card needed | Mumbai, Delhi | Yes, but needs a card |
| AWS free tier | t3.micro, 1 GB RAM | Mumbai, Hyderabad | No: too small for the speech model |
| DigitalOcean via GitHub Student Pack | Student credit **ended on 1 Aug 2026** | Bangalore | No longer free |

Make the **Azure for Students** account at azure.microsoft.com/free/students with the IIIT
Vadodara email. Check the VM price in Azure's pricing calculator before creating it: B2s is
cheaper, B2ms (8 GB) is safer for the speech model; stop the VM when not testing to save credit.

## 2. Create the VM

1. Azure portal → Virtual machines → Create. Image **Ubuntu 24.04 LTS**, region **Central
   India**, size **B2ms** (or B2s), authentication **SSH public key**, disk 30 GB or more.
2. Inbound ports: **22 (SSH), 80 (HTTP), 443 (HTTPS)**.
3. Note the public IP address.

## 3. Point the domain at it (Cloudflare)

In Cloudflare → hunarvaani.co.in → DNS → Add record: type **A**, name **api**, IPv4 = the VM's
IP, proxy status **DNS only** (grey cloud), so Caddy can get the HTTPS certificate itself.

## 4. Install and start (on the VM, over SSH)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
git clone https://github.com/sakshamagrawalcode-cpu/hunarvaani.git   # private repo: use a GitHub token
cd hunarvaani
```

From the laptop (PowerShell, in `C:\Projects\hunarvaani`), copy the secrets and the rendered
prompts, which are not in git:

```powershell
scp .env azureuser@<VM-IP>:~/hunarvaani/.env
scp -r audio azureuser@<VM-IP>:~/hunarvaani/
```

On the VM, set the two server lines in `.env` (`nano .env`):

```
DOMAIN=api.hunarvaani.co.in
PUBLIC_BASE_URL=https://api.hunarvaani.co.in
```

Start everything, create the tables, load the occupations:

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d --build
docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py
docker compose -f infra/docker-compose.yml run --rm worker python scripts/seed_nco.py
curl https://api.hunarvaani.co.in/ready
```

## 5. Point Exotel at it (once; it never changes again)

Exotel → App Bazaar → flow "sih idea" → Voicebot → URL:
`wss://api.hunarvaani.co.in/exotel/ws/<EXOTEL_WS_TOKEN from .env>` → Save.

The console is then at `https://api.hunarvaani.co.in/console/` (same password).

## 6. Everyday

```bash
cd hunarvaani && git pull
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d --build
docker compose -f infra/docker-compose.yml logs -f api
```

Security notes: keep port 5432 closed (the database listens only on the VM itself); keep
`CALLS_PAGE_PASSWORD` strong, since the console is now on the internet.
