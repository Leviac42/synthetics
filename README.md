# Synthetic Monitoring System

A containerized synthetic monitoring application designed to measure frontend user experience using browser automation. This system serves as a replacement for AppDynamics, providing real-time performance metrics with visualization support for external Grafana instances.

## 🎯 Overview

This application monitors web applications by simulating real user interactions using Playwright browser automation. It captures critical performance metrics including:

- **Time to First Byte (TTFB)** - Server response time
- **DOM Content Loaded** - Time to parse and build DOM
- **Page Load Time** - Complete page load duration
- **Network Waterfall (HAR)** - Full network activity data

## ✨ Features

- **Browser Automation**: Powered by Playwright for realistic user simulation
- **Scheduled Monitoring**: Cron-based scheduling for automated checks
- **Performance Metrics**: Capture and store detailed timing data
- **Admin Interface**: Web UI for managing monitors (Create/Edit/Delete/Run Now)
- **Grafana Integration**: Pre-built dashboard templates with clear data source placeholders
- **Zero-Config Deployment**: Works out of the box with sensible defaults
- **Container-Native**: Compatible with Docker/Podman and Kubernetes
- **Time-Series Optimized**: PostgreSQL schema optimized for performance queries

## 🛠 Technology Stack

| Component | Technology |
|-----------|-----------|
| **API Framework** | FastAPI |
| **Browser Automation** | Playwright (Python) |
| **Database** | PostgreSQL 15 |
| **Container Runtime** | Docker/Podman |
| **Orchestration** | Kubernetes (MicroK8s, OpenShift, K3s) |
| **Visualization** | Grafana (external) |

## 📋 Requirements

- **Podman/Docker**: For container-based deployment
- **Kubernetes**: Optional, for orchestration (MicroK8s, OpenShift, K3s)
- **Python 3.11+**: For local development
- **Grafana**: External instance for visualization (optional)

## 🚀 Quick Start

### Using Podman/Docker Compose

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd synthetics
   ```

2. **Start the stack**
   ```bash
   podman-compose up -d
   # or with Docker Compose
   docker-compose up -d
   ```

3. **Access the application**
   - Admin UI: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - PostgreSQL: localhost:5432

4. **Create your first monitor**
   - Navigate to the Admin UI
   - Click "Create Monitor"
   - Enter URL and schedule (e.g., `*/5 * * * *` for every 5 minutes)
   - Click "Save"

### Using Kubernetes

1. **Apply the manifests**
   ```bash
   kubectl apply -f k8s/
   ```

2. **Verify deployment**
   ```bash
   kubectl get pods -n synthetics
   kubectl get svc -n synthetics
   ```

3. **Access the application**
   ```bash
   kubectl port-forward -n synthetics svc/synthetics-app 8000:8000
   ```

## 📁 Project Structure

```
synthetics/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application & Admin UI
│   ├── models.py            # Pydantic models for API
│   ├── worker.py            # Playwright worker for monitoring
│   └── database.py          # Database connection & utilities
├── k8s/
│   ├── namespace.yaml       # Kubernetes namespace
│   ├── postgres-deployment.yaml
│   ├── postgres-service.yaml
│   ├── postgres-pvc.yaml    # Persistent volume claim
│   ├── app-deployment.yaml
│   └── app-service.yaml
├── Containerfile            # Container image definition
├── podman-compose.yml       # Docker/Podman compose configuration
├── init.sql                 # Database schema initialization
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🗄 Database Schema

The PostgreSQL schema is optimized for time-series queries:

### Tables

- **`monitors`** - Monitor configurations (URL, schedule, settings)
- **`execution_logs`** - Execution history with status and HAR data
- **`performance_metrics`** - Time-series performance data

### Views

- **`latest_monitor_metrics`** - Aggregated view of latest metrics per monitor

### Indexes

Optimized indexes for:
- Time-series queries (by timestamp)
- Monitor-specific queries
- Status filtering
- Composite queries for Grafana dashboards

## 🔌 API Documentation

### Endpoints

#### Monitors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/monitors` | List all monitors |
| POST | `/api/monitors` | Create a new monitor |
| GET | `/api/monitors/{id}` | Get monitor details |
| PUT | `/api/monitors/{id}` | Update a monitor |
| DELETE | `/api/monitors/{id}` | Delete a monitor |
| POST | `/api/monitors/execute` | Execute monitor immediately |

#### Execution Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/execution-logs` | List execution logs |
| GET | `/api/execution-logs/{id}` | Get execution log details |
| GET | `/api/execution-logs/monitor/{monitor_id}` | Get logs for specific monitor |

#### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/grafana` | Download Grafana dashboard JSON |

### Example: Create Monitor

```bash
curl -X POST http://localhost:8000/api/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Homepage Check",
    "url": "https://example.com",
    "schedule_cron": "*/5 * * * *",
    "enabled": true,
    "timeout_seconds": 30,
    "tags": {"environment": "production", "team": "frontend"}
  }'
```

## 📊 Grafana Integration

### Download Dashboard

1. Navigate to the Admin UI
2. Click "Download Grafana Dashboard"
3. Import the JSON file into your Grafana instance

### Configure Data Source

The dashboard JSON contains clear placeholders that need to be replaced:

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "${DS_POSTGRESQL}"  // Replace with your Grafana data source UID
  }
}
```

**Steps:**
1. Create a PostgreSQL data source in Grafana pointing to your database
2. Note the data source UID (e.g., `P1234567890`)
3. Replace `${DS_POSTGRESQL}` in the dashboard JSON with your UID
4. Import the dashboard

### Dashboard Panels

The dashboard includes panels for:
- TTFB trends over time
- DOM Content Loaded metrics
- Page Load Time analysis
- Monitor status overview
- Error rate tracking
- Performance comparison across monitors

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `postgres` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `synthetics` | Database name |
| `DB_USER` | `synthetics` | Database user |
| `DB_PASSWORD` | `synthetics123` | Database password |

### Cron Scheduling

Monitors use standard cron expressions:

```
*/5 * * * *    # Every 5 minutes
0 * * * *      # Every hour
0 9 * * 1-5    # 9 AM on weekdays
*/30 9-17 * *  # Every 30 minutes during business hours
```

## 🔒 Security Considerations

- **Rootless Containers**: Containerfile is compatible with rootless Podman
- **Limited Capabilities**: App container runs with dropped capabilities
- **Database Credentials**: Change defaults for production deployments
- **Network Isolation**: Services run in isolated network

## 🧪 Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set up PostgreSQL**
   ```bash
   # Using Docker
   docker run -d \
     -e POSTGRES_DB=synthetics \
     -e POSTGRES_USER=synthetics \
     -e POSTGRES_PASSWORD=synthetics123 \
     -p 5432:5432 \
     postgres:15-alpine
   ```

3. **Initialize database**
   ```bash
   psql -h localhost -U synthetics -d synthetics -f init.sql
   ```

4. **Run the application**
   ```bash
   python -m app.main
   ```

## 📈 Monitoring & Observability

### Health Checks

- **PostgreSQL**: `pg_isready` health check every 10s
- **Application**: FastAPI health endpoint at `/health`

### Logs

Application logs include:
- Monitor execution status
- Performance metrics captured
- Error messages and stack traces
- Worker scheduling information

## 🐛 Troubleshooting

### Common Issues

**Monitor timeouts**
- Increase `timeout_seconds` in monitor configuration
- Check network connectivity to target URLs

**Database connection errors**
- Verify PostgreSQL is running and accessible
- Check environment variables match database configuration

**Playwright browser launch failures**
- Ensure Chromium is installed: `playwright install chromium`
- Check container has sufficient resources

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- Documentation is updated
- Container builds successfully

## 📄 License

[Specify your license here]

## 🔗 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Playwright for Python](https://playwright.dev/python/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review logs for error details

---

**Built with ❤️ for synthetic monitoring**
