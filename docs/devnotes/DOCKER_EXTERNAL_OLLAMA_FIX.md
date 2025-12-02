# Docker External Ollama Connection Fix

## Problem Description

When Digital Article is deployed in Docker on a remote server, the Settings modal fails to retrieve models from external Ollama instances, returning:

```json
{"provider":"ollama","models":[],"count":0,"available":true}
```

This occurs even though the Ollama instances are accessible and return models when queried directly via their API (`/api/tags`).

## Root Cause Analysis

The issue stems from **Docker network isolation combined with AbstractCore's provider configuration behavior**:

### What We Know

1. **Ollama API works directly**: `curl http://172.20.10.2:11434/api/tags` returns 28+ models
2. **AbstractCore works on local machine**: Running the same code outside Docker successfully retrieves all models
3. **Docker containers are network-isolated**: Containers run in their own network namespace and cannot directly access host machine IPs

### The Bug Flow

```
Frontend Settings Modal
  ↓
GET /api/llm/providers/ollama/models?base_url=http://172.20.10.2:11434
  ↓
Backend (running in Docker container)
  ↓
configure_provider('ollama', base_url='http://172.20.10.2:11434')
  ↓
create_llm('ollama', model='dummy')  ← No base_url parameter passed!
  ↓
llm.list_available_models()  ← Returns 0 models (but no exception!)
  ↓
Response: {"provider":"ollama","models":[],"count":0,"available":true}
```

The critical issue: **From inside the Docker container, `172.20.10.2` is not accessible** because:
- Docker containers run in isolated bridge networks
- Private IPs (`172.20.x.x`, `10.x.x.x`, `192.168.x.x`) on the host machine are not accessible from inside containers
- The configured `base_url` points to an unreachable address from the container's perspective

## Solutions Implemented

### Solution 1: Enhanced Logging (Diagnostic)

Added comprehensive logging to `backend/app/api/llm.py` (lines 202-231) to help identify exactly where the issue occurs:

```python
logger.info(f"🔍 get_provider_models: provider={provider}, base_url_param={base_url}, url_to_use={url_to_use}")
logger.info(f"📍 Configured {provider} with base_url: {url_to_use}")
logger.info(f"🔨 Creating LLM instance: provider={provider}, model='dummy'")
logger.info(f"✅ LLM created. base_url={getattr(llm, 'base_url', 'unknown')}")
logger.info(f"📞 Calling llm.list_available_models()...")
logger.info(f"✅ list_available_models() returned {len(models)} models")
```

### Solution 2: Automatic Fallback (Code Fix)

When zero models are returned, the backend now automatically retries with `base_url` passed as a direct parameter (lines 222-231):

```python
if len(models) == 0:
    logger.warning(f"⚠️ ZERO MODELS RETURNED! This is the bug!")
    # Try direct base_url parameter as fallback
    if url_to_use:
        logger.info(f"🔄 Retrying with direct base_url parameter...")
        llm2 = create_llm(provider, model="dummy", base_url=url_to_use)
        models2 = llm2.list_available_models()
        logger.info(f"✅ Retry with base_url param returned {len(models2)} models")
        return models2
```

### Solution 3: Debug Endpoint (Diagnostic Tool)

Added new debug endpoint `/api/llm/debug/connection` (lines 401-500) to help diagnose connection issues from the remote Docker environment:

```bash
# Usage from remote deployment:
curl "https://alboul-opf279.us.aa.apollo.roche.com/api/llm/debug/connection?base_url=http://172.20.10.2:11434"
```

This endpoint runs 4 tests:
1. **TCP Connection**: Socket-level connectivity test
2. **Direct API Call**: HTTP request to Ollama `/api/tags`
3. **AbstractCore with configure_provider()**: Current implementation
4. **AbstractCore with direct base_url**: Alternative approach

## Deployment Steps

### Step 1: Deploy Updated Backend

```bash
# On remote server, rebuild and restart backend container
cd /path/to/digital-article
docker compose build backend
docker compose up -d backend
```

### Step 2: Test with Debug Endpoint

```bash
# Test first Ollama instance
curl "https://alboul-opf279.us.aa.apollo.roche.com/api/llm/debug/connection?base_url=http://172.20.10.2:11434" | jq

# Test second Ollama instance
curl "https://alboul-opf279.us.aa.apollo.roche.com/api/llm/debug/connection?base_url=http://10.175.156.101:11434" | jq
```

**Expected output** (if network is the issue):
```json
{
  "tests": {
    "tcp_connection": {
      "status": "failed",
      "error": "[Errno 113] No route to host"
    },
    "direct_api_call": {
      "status": "failed",
      "error": "Connection timeout"
    },
    ...
  }
}
```

### Step 3: Check Backend Logs

```bash
# Watch backend logs during Settings modal testing
docker logs -f digitalarticle-backend

# Look for these log messages:
# 🔍 get_provider_models: provider=ollama, base_url_param=http://172.20.10.2:11434, ...
# 📍 Configured ollama with base_url: http://172.20.10.2:11434
# ✅ LLM created. base_url=http://172.20.10.2:11434
# 📞 Calling llm.list_available_models()...
# ⚠️ ZERO MODELS RETURNED! This is the bug!
# 🔄 Retrying with direct base_url parameter...
```

## Network Configuration Solutions

If the debug endpoint confirms network connectivity is the issue, here are the solutions:

### Option A: Use Docker Host Gateway (Recommended)

If Ollama runs on the Docker host machine, configure Digital Article to use Docker's special hostname:

**In `docker-compose.yml`**:
```yaml
backend:
  environment:
    - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**In Settings Modal**:
- Ollama Base URL: `http://host.docker.internal:11434`

### Option B: Use Host Network Mode

Allow the backend container to use the host's network directly:

**In `docker-compose.yml`**:
```yaml
backend:
  network_mode: "host"
  # Remove ports section - not needed with host mode
```

**⚠️ Warning**: This reduces container isolation and may conflict with other services.

### Option C: Bridge Network with Routing

If Ollama runs on another machine in the network:

1. **Verify network accessibility** from Docker host:
   ```bash
   # From host machine
   curl http://172.20.10.2:11434/api/tags
   ```

2. **Add routing rules** if needed:
   ```bash
   # Example: route traffic to 172.20.10.0/24 subnet
   ip route add 172.20.10.0/24 via <gateway_ip>
   ```

3. **Use docker-compose network configuration**:
   ```yaml
   networks:
     digitalarticle-network:
       driver: bridge
       ipam:
         config:
           - subnet: 172.18.0.0/16
             gateway: 172.18.0.1
   ```

### Option D: Ollama as Docker Service (Best for Production)

Run Ollama itself as a Docker service in the same compose file:

**In `docker-compose.yml`**:
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: digitalarticle-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    networks:
      - digitalarticle-network

  backend:
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434  # Use service name!
    depends_on:
      - ollama
```

**In Settings Modal**:
- Ollama Base URL: `http://ollama:11434`

## Testing Checklist

After deploying the fix:

- [ ] Debug endpoint returns connection results
- [ ] Backend logs show detailed diagnostic messages
- [ ] Settings modal retrieves model list from external Ollama
- [ ] Can select model and generate code successfully
- [ ] Models from both Ollama instances (172.20.10.2 and 10.175.156.101) are accessible

## Files Modified

1. **backend/app/api/llm.py** (lines 193-247, 401-500):
   - Enhanced logging for diagnostics
   - Automatic fallback retry mechanism
   - New debug endpoint

## Troubleshooting

### Issue: Debug endpoint shows "No route to host"

**Solution**: Use Docker host gateway or network mode (see Option A/B above)

### Issue: Debug endpoint shows "Connection refused"

**Possible causes**:
- Ollama service is down
- Ollama port (11434) is not open
- Firewall blocking connection

**Diagnostic**:
```bash
# From Docker host machine
curl http://172.20.10.2:11434/api/tags

# Check if Ollama is running
systemctl status ollama  # or: docker ps | grep ollama
```

### Issue: Debug endpoint shows "Connection timeout"

**Possible causes**:
- Network routing issue
- Ollama behind VPN/firewall
- Docker network misconfiguration

**Diagnostic**:
```bash
# From Docker host machine
ping 172.20.10.2
traceroute 172.20.10.2
telnet 172.20.10.2 11434
```

## Next Steps

1. **Deploy the updated backend** to the remote server
2. **Run the debug endpoint** to identify the exact network issue
3. **Implement the appropriate network solution** (Option A-D above)
4. **Verify Settings modal** shows all models from external Ollama instances
5. **Update CLAUDE.md** with final resolution

## References

- Docker networking: https://docs.docker.com/network/
- AbstractCore documentation: https://github.com/abstractcore/abstractcore
- Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
