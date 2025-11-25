# Digital Article - Docker Quick Start

## TL;DR - Get Running in 3 Commands

```bash
# 1. Navigate to project root
cd /path/to/DigitalArticle

# 2. Build the image (5-10 minutes)
docker build -f docker/Dockerfile.unified -t digitalarticle:unified .

# 3. Run the container (first run: 10-30 min for model download)
docker run -d --name digitalarticle -p 80:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified

# 4. Open http://localhost in your browser
```

---

## What You Get

✅ **Ollama LLM** running on port 11434 (internal)
✅ **FastAPI Backend** running on port 8000 (internal)
✅ **React Frontend** served via Nginx on port 80
✅ **Automatic model download** and caching
✅ **Persistent notebooks** and data

---

## Essential Commands

### Monitor Startup
```bash
docker logs -f digitalarticle
# Wait for: "Digital Article - Ready!"
```

### Check Status
```bash
docker exec digitalarticle supervisorctl status
# Should show: ollama, backend, nginx all RUNNING
```

### Stop/Start
```bash
docker stop digitalarticle    # Stop
docker start digitalarticle   # Start
docker restart digitalarticle # Restart
```

### View Service Logs
```bash
docker exec digitalarticle tail -f /var/log/supervisor/backend.log
docker exec digitalarticle tail -f /var/log/supervisor/ollama.log
```

### Cleanup (CAUTION: Deletes all data)
```bash
docker rm -f digitalarticle
docker volume rm digitalarticle-data digitalarticle-models
```

---

## Startup Time

- **First run**: 10-30 minutes (downloading qwen3-coder:30b model)
- **Subsequent runs**: 90-120 seconds (model cached)

---

## System Requirements

- **RAM**: 8GB minimum, 32GB recommended
- **Disk**: 20GB free (2.5GB image + 17GB model)
- **CPU**: 4 cores minimum, 8+ recommended
- **Docker**: Version 20.10+

---

## Troubleshooting

**Can't access http://localhost?**
```bash
# Check container running
docker ps | grep digitalarticle

# Check port mapping
docker port digitalarticle
# Should show: 80/tcp -> 0.0.0.0:80
```

**Model downloads every time?**
```bash
# Check volume mounted
docker inspect digitalarticle | grep -A 5 Mounts
# Should show: digitalarticle-models mounted at /models
```

**Out of memory?**
```bash
# Run with more memory
docker run -d --name digitalarticle -p 80:80 \
  --memory=36g --memory-reservation=8g \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified
```

---

## Full Documentation

- **Complete Guide**: [`docs/DOCKER-DEPLOYMENT.md`](docs/DOCKER-DEPLOYMENT.md)
- **Implementation Details**: [`docs/devnotes/docker-one-image.md`](docs/devnotes/docker-one-image.md)

---

## Docker Compose Alternative

Create `docker-compose-unified.yml`:

```yaml
version: '3.8'
services:
  digitalarticle:
    build:
      context: .
      dockerfile: docker/Dockerfile.unified
    ports:
      - "80:80"
    volumes:
      - digitalarticle-data:/app/data
      - digitalarticle-models:/models
    restart: unless-stopped
volumes:
  digitalarticle-data:
  digitalarticle-models:
```

Then run:
```bash
docker compose -f docker-compose-unified.yml up -d --build
```

---

**Questions?** See [`docs/DOCKER-DEPLOYMENT.md`](docs/DOCKER-DEPLOYMENT.md) for detailed instructions and troubleshooting.
