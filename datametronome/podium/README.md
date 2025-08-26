# DataMetronome Podium API

> **📁 DIRECTORY TYPE**: Standalone FastAPI Backend Service  
> **🚫 NOT A PYPI PACKAGE** - This is a backend service, not a Python library

The Podium API is the core backend service for DataMetronome, providing data quality monitoring, anomaly detection, and reporting capabilities.

## 🏗️ Architecture

- **FastAPI**: Modern, fast web framework for building APIs
- **DataPulse SQLite**: Pure connector for local data storage
- **JWT Authentication**: Secure user authentication
- **Async-first**: Built for high-performance data processing
- **Reporting Service**: Comprehensive data quality reports

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- SQLite (included with Python)

### Local Development

1. **Install dependencies:**
   ```bash
   cd datametronome/podium
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DATAMETRONOME_SECRET_KEY="your-super-secret-key-that-is-at-least-32-characters-long"
   export DATAMETRONOME_DATABASE_URL="sqlite:///./datametronome.db"
   export DATAMETRONOME_DEBUG="true"
   export DATAMETRONOME_HOST="0.0.0.0"
   export DATAMETRONOME_PORT="8000"
   ```

3. **Run the API:**
   ```bash
   python -m datametronome_podium.main
   ```

4. **Access the API:**
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build and run with Docker Compose:**
   ```bash
   # From project root
   docker-compose up -d
   ```

2. **Or build and run individually:**
   ```bash
   # Build Podium API
   cd datametronome/podium
   docker build -t datametronome-podium .
   
   # Run Podium API
   docker run -d \
     --name podium-api \
     -p 8000:8000 \
     -e DATAMETRONOME_SECRET_KEY="your-secret-key" \
     -e DATAMETRONOME_DATABASE_URL="sqlite:///./datametronome.db" \
     -v $(pwd)/reports:/app/reports \
     datametronome-podium
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATAMETRONOME_SECRET_KEY` | JWT secret key (min 32 chars) | Required |
| `DATAMETRONOME_DATABASE_URL` | Database connection string | `sqlite:///./datametronome.db` |
| `DATAMETRONOME_DEBUG` | Enable debug mode | `false` |
| `DATAMETRONOME_HOST` | Host to bind to | `0.0.0.0` |
| `DATAMETRONOME_PORT` | Port to bind to | `8000` |

### Database

The API uses SQLite by default for simplicity. For production, consider:

- **PostgreSQL**: Use DataPulse PostgreSQL connectors
- **MySQL**: Use DataPulse MySQL connectors
- **Cloud databases**: AWS RDS, Google Cloud SQL, Azure Database

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

### Data Quality
- `GET /api/v1/staves` - List monitoring staves
- `POST /api/v1/staves` - Create monitoring stave
- `GET /api/v1/clefs` - List quality clefs
- `POST /api/v1/clefs` - Create quality clef
- `GET /api/v1/checks` - List quality checks
- `POST /api/v1/checks` - Run quality check

### Reporting
- `GET /api/v1/reports/health` - System health report
- `GET /api/v1/reports/checks` - Check results report
- `GET /api/v1/reports/anomalies` - Anomalies report
- `GET /api/v1/reports/export/csv` - Export to CSV
- `GET /api/v1/reports/export/json` - Export to JSON

## 🔐 Authentication

The API uses JWT tokens for authentication:

1. **Login** to get a token:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin"}'
   ```

2. **Use the token** in subsequent requests:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/v1/reports/health"
   ```

## 🧪 Testing

### Manual Testing

1. **Start the API:**
   ```bash
   python -m datametronome_podium.main
   ```

2. **Test endpoints:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Login
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin"}'
   
   # Get reports (use token from login)
   curl -H "Authorization: Bearer TOKEN" \
     "http://localhost:8000/api/v1/reports/health"
   ```

### Automated Testing

```bash
# Run tests
cd datametronome/podium
python -m pytest

# Run with coverage
python -m pytest --cov=datametronome_podium
```

## 📈 Monitoring

### Health Checks

- **Endpoint**: `/health`
- **Response**: `{"status": "healthy"}`
- **Use case**: Load balancer health checks, container health checks

### Logging

The API logs to stdout/stderr for container-friendly logging:

```bash
# View logs
docker logs podium-api

# Follow logs
docker logs -f podium-api
```

## 🚀 Production Deployment

### Docker Production

```bash
# Build production image
docker build -t datametronome-podium:latest .

# Run with production settings
docker run -d \
  --name podium-api \
  -p 8000:8000 \
  -e DATAMETRONOME_SECRET_KEY="$(openssl rand -hex 32)" \
  -e DATAMETRONOME_DEBUG="false" \
  -e DATAMETRONOME_DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -v /path/to/reports:/app/reports \
  datametronome-podium:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datametronome-podium
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

## 🔧 Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill the process
   kill -9 PID
   ```

2. **Database connection issues:**
   ```bash
   # Check SQLite file
   ls -la datametronome.db
   
   # Remove and recreate if corrupted
   rm datametronome.db
   python -m datametronome_podium.main
   ```

3. **Authentication errors:**
   ```bash
   # Check secret key length
   echo $DATAMETRONOME_SECRET_KEY | wc -c
   
   # Generate new secret key
   export DATAMETRONOME_SECRET_KEY="$(openssl rand -hex 32)"
   ```

### Logs

Enable debug mode for detailed logging:

```bash
export DATAMETRONOME_DEBUG="true"
python -m datametronome_podium.main
```

## 📚 API Documentation

- **Interactive docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. Follow the DataPulse coding standards
2. Write tests for new features
3. Update documentation
4. Submit pull requests

## 📄 License

This project is part of the DataMetronome ecosystem.
