# Capycoin — VPS Deployment Guide

## Prerequisites on the VPS

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in after this

# Install Nginx and Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## 1. Clone the repo

```bash
sudo mkdir -p /opt/capycoin
sudo chown $USER:$USER /opt/capycoin
git clone git@github.com:vanessa-arruda/capycoin-app.git /opt/capycoin
cd /opt/capycoin
```

---

## 2. Create the .env file

```bash
cp .env.example .env
nano .env
```

Fill in production values:

```env
POSTGRES_PASSWORD=a-strong-random-password
SECRET_KEY=a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

NEXT_PUBLIC_API_URL=https://yourdomain.com/api
```

Generate a strong secret key with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Build and start containers

```bash
make prod-build
make prod-up
```

---

## 4. Run database migrations

```bash
make prod-migrate
```

---

## 5. Set up Nginx

```bash
# Copy the config (replace yourdomain.com with your actual domain)
sudo cp /opt/capycoin/nginx/capycoin.conf /etc/nginx/sites-available/capycoin
sudo sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/capycoin

# Enable the site
sudo ln -s /etc/nginx/sites-available/capycoin /etc/nginx/sites-enabled/capycoin
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Get SSL certificate (HTTPS)

```bash
sudo certbot --nginx -d yourdomain.com
```

Certbot will automatically update the Nginx config for HTTPS and set up auto-renewal.

Verify auto-renewal works:
```bash
sudo certbot renew --dry-run
```

---

## 7. Start on boot (systemd)

```bash
sudo cp /opt/capycoin/systemd/capycoin.service /etc/systemd/system/capycoin.service
sudo systemctl daemon-reload
sudo systemctl enable capycoin
sudo systemctl start capycoin
```

---

## Useful commands

| Command | What it does |
|---|---|
| `make prod-up` | Start all services in background |
| `make prod-down` | Stop all services |
| `make prod-logs` | Stream logs from all services |
| `make prod-migrate` | Run pending database migrations |
| `make prod-build` | Rebuild Docker images |

---

## Updating the app

```bash
cd /opt/capycoin
git pull
make prod-build
make prod-up
make prod-migrate   # only if there are new migrations
```
