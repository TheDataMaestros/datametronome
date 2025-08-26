# DataMetronome Deployment Guide

This guide covers deploying DataMetronome in various environments, from local development to production.

## 🏠 Local Development

### Prerequisites

- Python 3.13+
- Git
- SQLite (included with Python)

### Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd datametronome
   
   # Install DataPulse connectors
   pip install -e ./datametronome/pulse/core
   pip install -e ./datametronome/pulse/sqlite
   pip install -e ./datametronome/pulse/postgres
   pip install -e ./datametronome/pulse/postgres-sqlalchemy
   pip install -e ./datametronome/pulse/postgres-psycopg3
   
   # Install Podium API
   pip install -e ./datametronome/podium
   
   # Install Streamlit UI
   pip install -e ./datametronome/ui-streamlit
   ```

2. **Start Podium API:**
   ```bash
   export DATAMETRONOME_SECRET_KEY="your-super-secret-key-that-is-at-least-32-characters-long"
   export DATAMETRONOME_DATABASE_URL="sqlite:///./datametronome.db"
   export DATAMETRONOME_DEBUG="true"
   export DATAMETRONOME_HOST="0.0.0.0"
   export DATAMETRONOME_PORT="8000"
   
   cd datametronome/podium
   python -m datametronome_podium.main
   ```

3. **Start Streamlit UI (new terminal):**
   ```bash
   cd datametronome/ui-streamlit
   streamlit run streamlit_app.py --server.port 8501
   ```

4. **Access the system:**
   - Podium API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Streamlit UI: http://localhost:8501

## 🐳 Docker Development

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

3. **Access services:**
   - Podium API: http://localhost:8000
   - Streamlit UI: http://localhost:8501
   - PostgreSQL: localhost:5432

### Individual Services

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Start only Podium API
docker-compose up -d podium

# Start only Streamlit UI
docker-compose up -d ui
```

## 🚀 Production Deployment

### Docker Production

1. **Build production images:**
   ```bash
   # Build Podium API
   cd datametronome/podium
   docker build -t datametronome-podium:latest .
   
   # Build Streamlit UI
   cd ../ui-streamlit
   docker build -t datametronome-ui:latest .
   ```

2. **Create production docker-compose:**
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   
   services:
     podium:
       image: datametronome-podium:latest
       ports:
         - "8000:8000"
       environment:
         - DATAMETRONOME_SECRET_KEY=${DATAMETRONOME_SECRET_KEY}
         - DATAMETRONOME_DATABASE_URL=${DATAMETRONOME_DATABASE_URL}
         - DATAMETRONOME_DEBUG=false
         - DATAMETRONOME_HOST=0.0.0.0
         - DATAMETRONOME_PORT=8000
       volumes:
         - ./reports:/app/reports
         - ./data:/app/data
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
   
     ui:
       image: datametronome-ui:latest
       ports:
         - "8501:8501"
       environment:
         - PODIUM_API_BASE=http://podium:8000
       depends_on:
         - podium
       restart: unless-stopped
   ```

3. **Deploy:**
   ```bash
   # Set production environment variables
   export DATAMETRONOME_SECRET_KEY="$(openssl rand -hex 32)"
   export DATAMETRONOME_DATABASE_URL="postgresql://user:pass@host:5432/db"
   
   # Deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Kubernetes Production

1. **Create namespace:**
   ```bash
   kubectl create namespace datametronome
   ```

2. **Create secrets:**
   ```bash
   kubectl create secret generic podium-secrets \
     --from-literal=secret-key="$(openssl rand -hex 32)" \
     --from-literal=database-url="postgresql://user:pass@host:5432/db" \
     -n datametronome
   ```

3. **Deploy Podium API:**
   ```yaml
   # podium-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: datametronome-podium
     namespace: datametronome
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: datametronome-podium
     template:
       metadata:
         labels:
           app: datametronome-podium
       spec:
         containers:
         - name: podium
           image: datametronome-podium:latest
           ports:
           - containerPort: 8000
           env:
           - name: DATAMETRONOME_SECRET_KEY
             valueFrom:
               secretKeyRef:
                 name: podium-secrets
                 key: secret-key
           - name: DATAMETRONOME_DATABASE_URL
             valueFrom:
               secretKeyRef:
                 name: podium-secrets
                 key: database-url
           - name: DATAMETRONOME_DEBUG
             value: "false"
           - name: DATAMETRONOME_HOST
             value: "0.0.0.0"
           - name: DATAMETRONOME_PORT
             value: "8000"
           resources:
             requests:
               memory: "256Mi"
               cpu: "250m"
             limits:
               memory: "512Mi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 5
   ```

4. **Create service:**
   ```yaml
   # podium-service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: datametronome-podium
     namespace: datametronome
   spec:
     selector:
       app: datametronome-podium
     ports:
     - protocol: TCP
       port: 80
       targetPort: 8000
     type: ClusterIP
   ```

5. **Create ingress (optional):**
   ```yaml
   # podium-ingress.yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: datametronome-podium
     namespace: datametronome
     annotations:
       nginx.ingress.kubernetes.io/rewrite-target: /
   spec:
     rules:
     - host: api.datametronome.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: datametronome-podium
               port:
                 number: 80
   ```

6. **Deploy:**
   ```bash
   kubectl apply -f podium-deployment.yaml
   kubectl apply -f podium-service.yaml
   kubectl apply -f podium-ingress.yaml
   ```

## 🔧 Configuration Management

### Environment Variables

| Variable | Development | Production |
|----------|-------------|------------|
| `DATAMETRONOME_SECRET_KEY` | `dev-secret-key` | `$(openssl rand -hex 32)` |
| `DATAMETRONOME_DATABASE_URL` | `sqlite:///./datametronome.db` | `postgresql://user:pass@host:5432/db` |
| `DATAMETRONOME_DEBUG` | `true` | `false` |
| `DATAMETRONOME_HOST` | `0.0.0.0` | `0.0.0.0` |
| `DATAMETRONOME_PORT` | `8000` | `8000` |

### Configuration Files

Create `.env` files for different environments:

```bash
# .env.development
DATAMETRONOME_SECRET_KEY=dev-secret-key
DATAMETRONOME_DATABASE_URL=sqlite:///./datametronome.db
DATAMETRONOME_DEBUG=true
DATAMETRONOME_HOST=0.0.0.0
DATAMETRONOME_PORT=8000

# .env.production
DATAMETRONOME_SECRET_KEY=your-production-secret-key
DATAMETRONOME_DATABASE_URL=postgresql://user:pass@host:5432/db
DATAMETRONOME_DEBUG=false
DATAMETRONOME_HOST=0.0.0.0
DATAMETRONOME_PORT=8000
```

## 📊 Monitoring & Observability

### Health Checks

- **Endpoint**: `/health`
- **Response**: `{"status": "healthy"}`
- **Use case**: Load balancer health checks, container health checks

### Logging

```bash
# View logs
docker logs podium-api
kubectl logs -f deployment/datametronome-podium

# Follow logs
docker logs -f podium-api
kubectl logs -f deployment/datametronome-podium
```

### Metrics

The API exposes basic metrics at `/metrics` (if enabled):

```bash
curl http://localhost:8000/metrics
```

## 🔒 Security

### Authentication

- JWT tokens with configurable expiration
- Secure password hashing
- Role-based access control

### Network Security

```bash
# Firewall rules (example)
ufw allow 8000/tcp  # Podium API
ufw allow 8501/tcp  # Streamlit UI
ufw allow 5432/tcp  # PostgreSQL (if external)
```

### SSL/TLS

For production, use a reverse proxy (nginx, traefik) or load balancer with SSL termination:

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name api.datametronome.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up -d --scale podium=3

# Kubernetes
kubectl scale deployment datametronome-podium --replicas=5
```

### Load Balancing

```bash
# Docker Compose with nginx
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - podium
  
  podium:
    image: datametronome-podium:latest
    environment:
      - DATAMETRONOME_SECRET_KEY=${DATAMETRONOME_SECRET_KEY}
    expose:
      - "8000"
```

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts:**
   ```bash
   # Check what's using the port
   lsof -i :8000
   netstat -tulpn | grep :8000
   ```

2. **Database connection issues:**
   ```bash
   # Test database connection
   python -c "import sqlite3; sqlite3.connect('datametronome.db')"
   
   # Check PostgreSQL
   psql -h host -U user -d database
   ```

3. **Authentication errors:**
   ```bash
   # Check secret key
   echo $DATAMETRONOME_SECRET_KEY | wc -c
   
   # Generate new key
   export DATAMETRONOME_SECRET_KEY="$(openssl rand -hex 32)"
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DATAMETRONOME_DEBUG="true"
python -m datametronome_podium.main
```

### Log Analysis

```bash
# Search for errors
docker logs podium-api 2>&1 | grep -i error

# Search for specific patterns
docker logs podium-api 2>&1 | grep "Failed to"
```

## 🔄 Updates & Maintenance

### Rolling Updates

```bash
# Docker
docker-compose pull
docker-compose up -d

# Kubernetes
kubectl set image deployment/datametronome-podium podium=datametronome-podium:latest
```

### Database Migrations

```bash
# Backup current database
cp datametronome.db datametronome.db.backup

# Run migrations (if any)
python -m datametronome_podium.migrations

# Verify data integrity
python -c "import sqlite3; conn = sqlite3.connect('datametronome.db'); print(conn.execute('SELECT COUNT(*) FROM users').fetchone())"
```

### Health Monitoring

```bash
# Check API health
curl -f http://localhost:8000/health || echo "API is down"

# Check database
python -c "from datametronome_podium.core.database import get_db; print('DB OK')"

# Check all services
docker-compose ps
kubectl get pods -n datametronome
```

## 📚 Additional Resources

- [Podium API Documentation](datametronome/podium/README.md)
- [DataPulse Connectors](datametronome/pulse/README.md)
- [Streamlit UI Guide](datametronome/ui-streamlit/README.md)
- [API Reference](http://localhost:8000/docs)

## 🤝 Support

For deployment issues:

1. Check the logs: `docker logs podium-api`
2. Verify environment variables: `env | grep DATAMETRONOME`
3. Test individual components
4. Check the troubleshooting section above
5. Open an issue with logs and configuration details


