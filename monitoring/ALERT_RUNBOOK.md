# KigaPrio Alerts

## Critical (Fix Immediately)
- **App Down** → `docker compose restart backend`
- **Redis Down** → `docker compose restart redis`
- **Database Issues** → `docker compose restart pocketbase`

## Check Later
- High memory/CPU → Restart services if needed
- Lots of failed logins → Check logs, might just be someone forgetting password

## How to Check If Things Work
```bash
# Is it up?
curl https://kiga.dhjd.de/api/v1/health

# Any errors?
docker compose logs backend --tail=50

# Fix most things
docker compose restart backend redis
```

## If Nothing Works
1. Restart everything: `docker compose restart`
2. Still broken? Check disk space: `df -h`
3. Still broken? Check the logs and Google the error
