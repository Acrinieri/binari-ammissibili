# Deployment guide

These notes summarise the steps shared with the sysadmin team to run the project on the production host (`141.95.126.170`) together with the existing `nginx-proxy` stack.

## Prerequisites

- Docker Engine and Docker Compose plugin available on the host.
- Existing external Docker network: `service-tier`.
- DNS entry `rfi.b4service.it` already pointing to the server IP.
- Outbound network access in order to pull container base images.

## First run

```bash
sudo mkdir -p /srv/binari
sudo chown ubuntu:ubuntu /srv/binari
cd /srv/binari

git clone https://github.com/Acrinieri/binari-ammissibili.git .
git checkout master
```

Review or customise environment variables:

```bash
cp .env.example .env
# edit .env if needed (not required for the default setup)
```

Build and start the stack:

```bash
docker compose build
docker compose up -d
```

`nginx-proxy` picks the frontend automatically thanks to the `VIRTUAL_HOST`/`LETSENCRYPT_HOST` variables defined in `docker-compose.yml`. Both containers join the `service-tier` network, so the proxy can reach the frontend (`binari-frontend`) while the frontend talks to the backend using the public hostname.

The backend is mounted under `/api` via `VIRTUAL_PATH=/api`, while the frontend is served at `/`. During the build the React app reads `REACT_APP_API_BASE=/api`, so no additional configuration is required on the client.

## Useful commands

- Inspect running containers:
  ```bash
  docker compose ps
  ```
- Tail logs:
  ```bash
  docker compose logs -f backend
  docker compose logs -f frontend
  ```
- Re-deploy after pulling new code:
  ```bash
  git pull
  docker compose build --no-cache
  docker compose up -d
  ```
- Stop and remove the stack:
  ```bash
  docker compose down
  ```

## Notes

- Certificates: `nginx-proxy` together with `docker-letsencrypt-nginx-proxy-companion` (if present) will request certificates for `rfi.b4service.it`. No extra action is required besides keeping DNS up to date.
- Firewall: ensure ports 80/443 are open to the public if not already handled globally.
- Rollback: keep the previous image/containers by avoiding `--no-cache` during rebuilds. In case of issues, run `docker compose down` followed by `docker compose pull` / `up` with a previously tagged image.
