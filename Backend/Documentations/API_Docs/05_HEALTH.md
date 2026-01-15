# Health & System API

Endpoints for API health checks and system information.

**Tags:** `health`, `root`

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with service status |
| `GET` | `/` | Root endpoint with API info |

---

## GET /health

Check API health including service dependency status.

### Response

**Status:** `200 OK`

```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0",
  "services": {
    "redis": {
      "status": "connected",
      "latency_ms": 2.3
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health status (`healthy`, `degraded`, `unhealthy`) |
| `environment` | string | Current environment (`development`, `staging`, `production`) |
| `version` | string | API version |
| `services` | object | Service dependency status |

### Service Status Object

| Field | Type | Description |
|-------|------|-------------|
| `redis.status` | string | Redis connection status |
| `redis.latency_ms` | float | Redis ping latency |

### Health Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All services operational |
| `degraded` | Some services impaired but API functional |
| `unhealthy` | Critical services down |

### Example

```bash
curl -X GET "http://localhost:8000/health"
```

### Use Cases

**Load Balancer Health Check:**
```bash
# Check if API is ready to receive traffic
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
# Returns: 200 if healthy
```

**Kubernetes Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

**Kubernetes Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## GET /

Root endpoint with basic API information.

### Response

**Status:** `200 OK`

```json
{
  "name": "RABA API",
  "description": "AI-Powered Multi-Agent YouTube Shorts Generator",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | API name |
| `description` | string | API description |
| `version` | string | API version |
| `docs` | string | Swagger UI path |
| `health` | string | Health check path |

### Example

```bash
curl -X GET "http://localhost:8000/"
```

---

## Frontend Integration Guide

### Health Check Service

```javascript
class HealthService {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  // Check API health
  async checkHealth() {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      const data = await res.json();
      return {
        healthy: data.status === 'healthy',
        data
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Get API info
  async getInfo() {
    const res = await fetch(`${this.baseUrl}/`);
    return res.json();
  }

  // Periodic health monitoring
  startMonitoring(intervalMs = 30000, onStatusChange) {
    let lastStatus = null;
    
    const check = async () => {
      const result = await this.checkHealth();
      const currentStatus = result.healthy ? 'healthy' : 'unhealthy';
      
      if (currentStatus !== lastStatus) {
        onStatusChange(currentStatus, result);
        lastStatus = currentStatus;
      }
    };

    check(); // Initial check
    return setInterval(check, intervalMs);
  }
}

// Usage
const health = new HealthService();

// One-time check
const status = await health.checkHealth();
if (!status.healthy) {
  console.error('API is down:', status.error || status.data);
}

// Continuous monitoring
const monitorId = health.startMonitoring(30000, (status, details) => {
  if (status === 'unhealthy') {
    showNotification('API connection lost');
  } else {
    showNotification('API connection restored');
  }
});

// Stop monitoring
clearInterval(monitorId);
```

### Connection Status Component

```javascript
// React component for displaying API connection status
function ConnectionStatus() {
  const [status, setStatus] = useState('checking');
  const [details, setDetails] = useState(null);

  useEffect(() => {
    const health = new HealthService();
    
    const checkHealth = async () => {
      const result = await health.checkHealth();
      setStatus(result.healthy ? 'connected' : 'disconnected');
      setDetails(result.data || result.error);
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const statusColor = {
    checking: 'gray',
    connected: 'green',
    disconnected: 'red'
  }[status];

  return (
    <div className="connection-status">
      <span 
        className="indicator" 
        style={{ backgroundColor: statusColor }}
      />
      <span className="label">
        {status === 'checking' && 'Checking connection...'}
        {status === 'connected' && 'Connected'}
        {status === 'disconnected' && 'Disconnected'}
      </span>
      {details && status === 'connected' && (
        <span className="version">v{details.version}</span>
      )}
    </div>
  );
}
```

### API Wrapper with Health Check

```javascript
class APIClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.healthy = true;
  }

  async ensureHealthy() {
    if (!this.healthy) {
      const health = new HealthService(this.baseUrl);
      const status = await health.checkHealth();
      this.healthy = status.healthy;
      
      if (!this.healthy) {
        throw new Error('API is currently unavailable');
      }
    }
  }

  async fetch(path, options = {}) {
    await this.ensureHealthy();
    
    try {
      const res = await fetch(`${this.baseUrl}${path}`, options);
      
      if (res.status === 503) {
        this.healthy = false;
        throw new Error('Service temporarily unavailable');
      }
      
      return res;
    } catch (error) {
      if (error.name === 'TypeError') {
        // Network error
        this.healthy = false;
      }
      throw error;
    }
  }
}

// Usage
const api = new APIClient();

try {
  const res = await api.fetch('/api/v1/workflows');
  const data = await res.json();
} catch (error) {
  if (error.message.includes('unavailable')) {
    showRetryDialog();
  }
}
```

---

## Deployment Considerations

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Docker Compose

```yaml
services:
  raba-api:
    image: raba-backend:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### Nginx Upstream Health

```nginx
upstream raba_api {
    server 127.0.0.1:8000;
    
    # Health check (requires nginx plus or 3rd party module)
    health_check uri=/health interval=10s fails=3 passes=2;
}
```

### Monitoring Integration

```python
# Prometheus metrics endpoint example
from prometheus_client import Counter, Histogram, generate_latest

health_checks = Counter('health_checks_total', 'Total health checks')
health_latency = Histogram('health_check_latency_seconds', 'Health check latency')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```
