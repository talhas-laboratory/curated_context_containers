# Home Server Deployment (Tailscale + GHCR)

This guide assumes VPN-only access via Tailscale and a reverse proxy at `http://llc.<tailnet>`.

## Server Details (fill in)
- **LAN IP:** `192.168.0.102`
- **Tailnet name:** `<tailnet>` (example: `talha`)
- **Host name:** `<host>` (example: `talhas-laboratory`)

## 1) Install Tailscale on the server
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname <host>
```

Enable MagicDNS in the Tailscale admin console, then add a DNS entry:
- **Record:** `llc`
- **Target:** the server's tailnet IP (from `tailscale ip -4`)

Verify on your laptop:
```bash
ping llc.<tailnet>
```

## 2) Firewall (ufw)
Allow HTTP only on the Tailscale interface and SSH on the LAN:
```bash
sudo ufw allow in on tailscale0 to any port 80 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 22 proto tcp
sudo ufw status verbose
```

## 3) Prepare persistent storage
```bash
sudo mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
sudo chown -R $USER:$USER /srv/llc
```

Copy manifests:
```bash
rsync -a manifests/ /srv/llc/manifests/
```

## 4) Configure environment
```bash
cp docker/.env.home.example docker/.env.home
```

Edit `docker/.env.home`:
- Set `LLC_FRONTEND_IMAGE`, `LLC_MCP_IMAGE`, `LLC_WORKERS_IMAGE` to your GHCR tags.
- Set `LLC_MCP_TOKEN` and any API keys.
- Set `MCP_CORS_ORIGINS=http://llc.<tailnet>`.

## 5) Update proxy hostname
Edit `docker/Caddyfile` and replace `llc.<tailnet>` with your tailnet domain.

## 6) GHCR login (server)
Use a GHCR PAT with `packages:read`:
```bash
echo "<PAT>" | docker login ghcr.io -u <gh-user> --password-stdin
```

## 7) Start the stack
```bash
docker compose -f docker/compose.home.yaml --env-file docker/.env.home up -d
```

Or use the helper script:
```bash
scripts/deploy_home_server.sh
```

## 8) Verify
```bash
curl http://llc.<tailnet>/api/health
docker compose -f docker/compose.home.yaml ps
```

Open the UI:
- `http://llc.<tailnet>`

## 9) Agent MCP gateway (laptop)
```bash
export LLC_BASE_URL="http://llc.<tailnet>/api"
export LLC_MCP_TOKEN="<token>"
python -m llc_mcp_gateway.server
```

## 10) Upgrade workflow
Pull new images and restart:
```bash
docker compose -f docker/compose.home.yaml --env-file docker/.env.home pull
docker compose -f docker/compose.home.yaml --env-file docker/.env.home up -d
```

Optional smoke test:
```bash
scripts/compose_smoke_test.sh
```

## 11) Backup / Restore
See `single_source_of_truth/runbooks/BACKUP_AND_RESTORE.md`.
