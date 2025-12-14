# Grafana Dashboards for DataMetronome

Pre-configured Grafana dashboards for monitoring DataMetronome Podium API.

## 📊 Dashboards

### DataMetronome Overview (`datametronome-overview.json`)
Main dashboard with key metrics:

- **System Health** - API health status indicator
- **HTTP Request Rate** - Requests per second by endpoint
- **HTTP Response Time** - p50 and p95 latency
- **Data Quality Check Runs** - Check execution rates by status
- **Anomalies Detected** - Anomalies by severity (stacked)
- **Active Data Sources** - Count of monitored data sources
- **Active Checks** - Count of active quality checks

## 🚀 Usage

### With Docker Compose

The dashboards are automatically provisioned when using `docker-compose.prod.yml` with the monitoring profile:

```bash
docker-compose -f docker-compose.prod.yml --profile monitoring up -d
```

Access Grafana at: http://localhost:3000
- Default credentials: admin / admin (change on first login)

### Manual Installation

1. **Add Prometheus Data Source:**
   - Navigate to Configuration > Data Sources
   - Add Prometheus
   - URL: `http://prometheus:9090` (or your Prometheus URL)
   - Click "Save & Test"

2. **Import Dashboard:**
   - Navigate to Dashboards > Import
   - Upload `datametronome-overview.json`
   - Select Prometheus data source
   - Click "Import"

## 📈 Key Metrics

### API Performance
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency distribution
- `http_requests_in_progress` - Active requests

### Data Quality
- `check_runs_total` - Check executions by status
- `check_run_duration_seconds` - Check execution time
- `anomalies_detected_total` - Anomalies by severity

### System Health
- `system_health` - Component health (1=healthy, 0=unhealthy)
- `active_staves` - Number of active data sources
- `active_clefs` - Number of active checks
- `scheduler_jobs` - Number of scheduled jobs

### Database
- `database_queries_total` - Database operations by type
- `database_query_duration_seconds` - Query execution time

## 🎨 Customization

Feel free to customize the dashboards:

1. **Clone the dashboard** (don't modify the original)
2. **Add panels** for your specific metrics
3. **Adjust time ranges** and refresh rates
4. **Create alerts** based on thresholds
5. **Export** your customized dashboard

## 📚 Resources

- [Prometheus Metrics](http://localhost:8000/metrics) - Raw metrics from Podium API
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## 🔧 Troubleshooting

### Dashboard shows "No Data"
1. Verify Prometheus is scraping metrics:
   - Check Prometheus targets: http://localhost:9090/targets
   - Ensure Podium API is running and accessible
2. Check data source configuration in Grafana
3. Verify time range selection

### Metrics not appearing
1. Generate some traffic to the API
2. Run some data quality checks
3. Wait for Prometheus scrape interval (default: 15s)

## 🎯 Best Practices

1. **Set up alerts** for critical metrics:
   - System health < 1 (unhealthy components)
   - High error rates (>5% 5xx responses)
   - High latency (p95 > 1s)
   - Anomaly spikes

2. **Monitor trends** over time:
   - Check success rates
   - Response time trends
   - Anomaly patterns

3. **Use variables** for dynamic dashboards:
   - Filter by stave (data source)
   - Filter by clef (check type)
   - Filter by time range

4. **Create custom views** for your use cases:
   - Per-team dashboards
   - Per-service dashboards
   - Executive summaries
