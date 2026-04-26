# HTTPS deployment with Let's Encrypt

This project is set up to work best on a single domain:

- frontend on `https://t2planer.ru/`
- backend proxied through `https://t2planer.ru/api/`

That layout avoids CORS pain and gives Google Calendar OAuth a valid HTTPS redirect URI.

## 1. DNS

Point your domain to the server IP:

- `t2planer.ru` -> `A` record -> your server IP

Wait until DNS resolves correctly:

```bash
dig +short t2planer.ru
```

## 2. Server packages

Install nginx and certbot:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create directories for static files and ACME challenges:

```bash
sudo mkdir -p /var/www/t2-schedule
sudo mkdir -p /var/www/letsencrypt
sudo chown -R www-data:www-data /var/www/t2-schedule /var/www/letsencrypt
```

## 3. Initial HTTP config

Use [deploy/nginx/t2-schedule-http.conf.template](/abs/path/c:/Users/asala/projects/t2-schedule/deploy/nginx/t2-schedule-http.conf.template) as the starting nginx config.

Copy it to the server and replace:

- domain values are already prefilled for `t2planer.ru`

Suggested target path on server:

```bash
sudo nano /etc/nginx/sites-available/t2-schedule
```

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/t2-schedule /etc/nginx/sites-enabled/t2-schedule
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 4. Build and publish frontend

On the server:

```bash
cd ~/t2-schedule/frontend
npm install
npm run build
sudo rm -rf /var/www/t2-schedule/*
sudo cp -r ~/t2-schedule/frontend/dist/* /var/www/t2-schedule/
sudo chown -R www-data:www-data /var/www/t2-schedule
sudo chmod -R 755 /var/www/t2-schedule
```

## 5. Get Let's Encrypt certificate

Once the domain resolves and nginx serves HTTP:

```bash
sudo certbot --nginx -d t2planer.ru
```

If you want to keep config changes manual, use webroot mode instead:

```bash
sudo certbot certonly --webroot -w /var/www/letsencrypt -d t2planer.ru
```

## 6. Switch nginx to HTTPS config

Use [deploy/nginx/t2-schedule-https.conf.template](/abs/path/c:/Users/asala/projects/t2-schedule/deploy/nginx/t2-schedule-https.conf.template).

Replace:

- certificate paths and server name are already prefilled for `t2planer.ru`

Then reload nginx:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Backend env for production

Update `backend/.env` on the server:

```env
CORS_ORIGINS=https://t2planer.ru
FRONTEND_APP_URL=https://t2planer.ru
GOOGLE_REDIRECT_URI=https://t2planer.ru/api/integrations/google/callback
```

If you use Gmail SMTP or another provider, also set:

```env
EMAIL_ENABLED=true
EMAIL_FROM=yourmail@example.ru
EMAIL_FROM_NAME=T2 Schedule
SMTP_HOST=...
SMTP_PORT=465
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_USE_SSL=true
```

Then restart backend:

```bash
cd ~/t2-schedule
docker compose up --build -d
docker compose exec -T backend alembic upgrade head
```

## 8. Frontend env for production

The frontend is already prepared for same-domain deployment:

```env
VITE_API_BASE_URL=/api
```

## 9. Validation checklist

Check frontend:

```bash
curl -I https://t2planer.ru/
```

Check backend through nginx:

```bash
curl -I https://t2planer.ru/api/health
```

Check certificate renewal timer:

```bash
systemctl list-timers | grep certbot
```

Dry-run renewal:

```bash
sudo certbot renew --dry-run
```

## 10. Google Calendar OAuth target

After HTTPS is live, use this redirect URI in Google Cloud Console:

```text
https://t2planer.ru/api/integrations/google/callback
```

That is the main blocker that prevented the calendar integration from working on a raw IP.
