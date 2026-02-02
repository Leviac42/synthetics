"""FastAPI application for synthetic monitoring"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .database import get_db_cursor, init_pool
from .models import (
    MonitorCreate, MonitorUpdate, MonitorResponse,
    ExecutionLogResponse, ExecuteNowRequest
)
from .worker import worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background worker task
worker_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting synthetic monitoring application")
    init_pool()
    
    # Start background worker
    global worker_task
    worker_task = asyncio.create_task(worker.run_scheduled_monitors())
    
    yield
    
    # Shutdown
    logger.info("Shutting down synthetic monitoring application")
    worker.stop()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Synthetic Monitoring API",
    description="Browser automation-based synthetic monitoring system",
    version="1.0.0",
    lifespan=lifespan
)


# Routes
@app.get("/", response_class=HTMLResponse)
async def get_admin_ui():
    """Serve the admin UI"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Synthetic Monitoring - Admin</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header { 
            background: white;
            padding: 20px 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        h1 { color: #2c3e50; font-size: 24px; margin-bottom: 10px; }
        .subtitle { color: #7f8c8d; font-size: 14px; }
        .actions { margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap; }
        button { 
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-primary:hover { background: #2980b9; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-success:hover { background: #27ae60; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn-secondary:hover { background: #7f8c8d; }
        .card { 
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .monitors-grid { 
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .monitor-card { 
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .monitor-card:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .monitor-header { 
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .monitor-title { 
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .monitor-url { 
            color: #3498db;
            font-size: 13px;
            word-break: break-all;
        }
        .status-badge { 
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-enabled { background: #d5f4e6; color: #27ae60; }
        .status-disabled { background: #fadbd8; color: #e74c3c; }
        .monitor-meta { 
            display: flex;
            gap: 15px;
            margin: 15px 0;
            font-size: 12px;
            color: #7f8c8d;
        }
        .monitor-actions { 
            display: flex;
            gap: 8px;
            margin-top: 15px;
        }
        .monitor-actions button { 
            padding: 8px 12px;
            font-size: 12px;
            flex: 1;
        }
        .modal { 
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content { 
            background: white;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 500px;
            max-height: 90vh;
            overflow-y: auto;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label { 
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #2c3e50;
            font-size: 14px;
        }
        .form-group input, .form-group select { 
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus { 
            outline: none;
            border-color: #3498db;
        }
        .form-actions { 
            display: flex;
            gap: 10px;
            margin-top: 25px;
        }
        .form-actions button { flex: 1; }
        .loading { 
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
        .empty-state { 
            text-align: center;
            padding: 60px 20px;
            color: #7f8c8d;
        }
        .empty-state-icon { 
            font-size: 48px;
            margin-bottom: 20px;
            opacity: 0.3;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Synthetic Monitoring</h1>
            <p class="subtitle">Browser automation-based monitoring with Playwright</p>
        </header>

        <div class="card">
            <div class="actions">
                <button class="btn-primary" onclick="openCreateModal()">➕ Create Monitor</button>
                <button class="btn-success" onclick="downloadGrafanaDashboard()">📊 Download Grafana Dashboard</button>
                <button class="btn-secondary" onclick="loadMonitors()">🔄 Refresh</button>
            </div>
        </div>

        <div id="monitors-container">
            <div class="loading">Loading monitors...</div>
        </div>
    </div>

    <!-- Create/Edit Monitor Modal -->
    <div id="monitor-modal" class="modal">
        <div class="modal-content">
            <h2 id="modal-title">Create Monitor</h2>
            <form id="monitor-form" onsubmit="saveMonitor(event)">
                <input type="hidden" id="monitor-id">
                <div class="form-group">
                    <label>Monitor Name *</label>
                    <input type="text" id="monitor-name" required placeholder="Production Homepage">
                </div>
                <div class="form-group">
                    <label>URL *</label>
                    <input type="url" id="monitor-url" required placeholder="https://example.com">
                </div>
                <div class="form-group">
                    <label>Schedule (Cron) *</label>
                    <input type="text" id="monitor-schedule" required value="*/5 * * * *" placeholder="*/5 * * * *">
                    <small style="color: #7f8c8d;">Example: */5 * * * * = every 5 minutes</small>
                </div>
                <div class="form-group">
                    <label>Timeout (seconds)</label>
                    <input type="number" id="monitor-timeout" value="30" min="5" max="300">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select id="monitor-enabled">
                        <option value="true">Enabled</option>
                        <option value="false">Disabled</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn-primary">Save Monitor</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let monitors = [];

        async function loadMonitors() {
            try {
                const response = await fetch('/api/monitors');
                monitors = await response.json();
                renderMonitors();
            } catch (error) {
                console.error('Failed to load monitors:', error);
                document.getElementById('monitors-container').innerHTML = 
                    '<div class="card"><p style="color: #e74c3c;">Failed to load monitors</p></div>';
            }
        }

        function renderMonitors() {
            const container = document.getElementById('monitors-container');
            
            if (monitors.length === 0) {
                container.innerHTML = `
                    <div class="card empty-state">
                        <div class="empty-state-icon">📭</div>
                        <h3>No monitors configured</h3>
                        <p>Create your first monitor to start tracking frontend performance</p>
                    </div>
                `;
                return;
            }

            const html = `
                <div class="monitors-grid">
                    ${monitors.map(monitor => `
                        <div class="monitor-card">
                            <div class="monitor-header">
                                <div>
                                    <div class="monitor-title">${escapeHtml(monitor.name)}</div>
                                    <div class="monitor-url">${escapeHtml(monitor.url)}</div>
                                </div>
                                <span class="status-badge status-${monitor.enabled ? 'enabled' : 'disabled'}">
                                    ${monitor.enabled ? 'Enabled' : 'Disabled'}
                                </span>
                            </div>
                            <div class="monitor-meta">
                                <span>⏰ ${monitor.schedule_cron}</span>
                                <span>⏱️ ${monitor.timeout_seconds}s timeout</span>
                            </div>
                            <div class="monitor-actions">
                                <button class="btn-success" onclick="runMonitorNow(${monitor.id})">▶️ Run Now</button>
                                <button class="btn-primary" onclick="editMonitor(${monitor.id})">✏️ Edit</button>
                                <button class="btn-danger" onclick="deleteMonitor(${monitor.id})">🗑️</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            container.innerHTML = html;
        }

        function escapeHtml(text) {
            const map = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'};
            return text.toString().replace(/[&<>"']/g, m => map[m]);
        }

        function openCreateModal() {
            document.getElementById('modal-title').textContent = 'Create Monitor';
            document.getElementById('monitor-form').reset();
            document.getElementById('monitor-id').value = '';
            document.getElementById('monitor-modal').classList.add('active');
        }

        function editMonitor(id) {
            const monitor = monitors.find(m => m.id === id);
            if (!monitor) return;

            document.getElementById('modal-title').textContent = 'Edit Monitor';
            document.getElementById('monitor-id').value = monitor.id;
            document.getElementById('monitor-name').value = monitor.name;
            document.getElementById('monitor-url').value = monitor.url;
            document.getElementById('monitor-schedule').value = monitor.schedule_cron;
            document.getElementById('monitor-timeout').value = monitor.timeout_seconds;
            document.getElementById('monitor-enabled').value = monitor.enabled.toString();
            document.getElementById('monitor-modal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('monitor-modal').classList.remove('active');
        }

        async function saveMonitor(event) {
            event.preventDefault();
            
            const id = document.getElementById('monitor-id').value;
            const data = {
                name: document.getElementById('monitor-name').value,
                url: document.getElementById('monitor-url').value,
                schedule_cron: document.getElementById('monitor-schedule').value,
                timeout_seconds: parseInt(document.getElementById('monitor-timeout').value),
                enabled: document.getElementById('monitor-enabled').value === 'true'
            };

            try {
                const url = id ? `/api/monitors/${id}` : '/api/monitors';
                const method = id ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    closeModal();
                    await loadMonitors();
                } else {
                    const error = await response.json();
                    alert('Error: ' + (error.detail || 'Failed to save monitor'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function deleteMonitor(id) {
            if (!confirm('Are you sure you want to delete this monitor?')) return;

            try {
                const response = await fetch(`/api/monitors/${id}`, {method: 'DELETE'});
                if (response.ok) {
                    await loadMonitors();
                } else {
                    alert('Failed to delete monitor');
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function runMonitorNow(id) {
            try {
                const response = await fetch('/api/monitors/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({monitor_id: id})
                });
                
                const result = await response.json();
                if (result.status === 'success') {
                    alert(`Monitor executed successfully!\\n\\nTTFB: ${result.ttfb_ms?.toFixed(2)}ms\\nDOM Content Loaded: ${result.dom_content_loaded_ms?.toFixed(2)}ms\\nPage Load: ${result.page_load_time_ms?.toFixed(2)}ms`);
                } else {
                    alert('Monitor execution failed: ' + (result.error_message || 'Unknown error'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function downloadGrafanaDashboard() {
            window.location.href = '/api/grafana/dashboard';
        }

        // Load monitors on page load
        loadMonitors();

        // Close modal on outside click
        document.getElementById('monitor-modal').addEventListener('click', (e) => {
            if (e.target.id === 'monitor-modal') closeModal();
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/monitors", response_model=List[MonitorResponse])
async def list_monitors():
    """List all monitors"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name, url, schedule_cron, enabled, timeout_seconds, 
                   tags, created_at, updated_at
            FROM monitors
            ORDER BY created_at DESC
        """)
        monitors = cursor.fetchall()
        return monitors


@app.post("/api/monitors", response_model=MonitorResponse, status_code=201)
async def create_monitor(monitor: MonitorCreate):
    """Create a new monitor"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO monitors 
            (name, url, schedule_cron, enabled, timeout_seconds, tags)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, url, schedule_cron, enabled, timeout_seconds, 
                      tags, created_at, updated_at
        """, (
            monitor.name,
            str(monitor.url),
            monitor.schedule_cron,
            monitor.enabled,
            monitor.timeout_seconds,
            json.dumps(monitor.tags)
        ))
        result = cursor.fetchone()
        return result


@app.get("/api/monitors/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: int):
    """Get a specific monitor"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name, url, schedule_cron, enabled, timeout_seconds,
                   tags, created_at, updated_at
            FROM monitors
            WHERE id = %s
        """, (monitor_id,))
        monitor = cursor.fetchone()
        
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        return monitor


@app.put("/api/monitors/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(monitor_id: int, monitor: MonitorUpdate):
    """Update a monitor"""
    updates = []
    values = []
    
    for field, value in monitor.model_dump(exclude_unset=True).items():
        if field == "url" and value:
            value = str(value)
        if field == "tags" and value:
            value = json.dumps(value)
        updates.append(f"{field} = %s")
        values.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(monitor_id)
    
    with get_db_cursor() as cursor:
        cursor.execute(f"""
            UPDATE monitors
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, url, schedule_cron, enabled, timeout_seconds,
                      tags, created_at, updated_at
        """, values)
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        return result


@app.delete("/api/monitors/{monitor_id}", status_code=204)
async def delete_monitor(monitor_id: int):
    """Delete a monitor"""
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM monitors WHERE id = %s RETURNING id", (monitor_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Monitor not found")


@app.post("/api/monitors/execute")
async def execute_monitor_now(request: ExecuteNowRequest, background_tasks: BackgroundTasks):
    """Execute a monitor immediately"""
    result = await worker.run_monitor_now(request.monitor_id)
    return result


@app.get("/api/monitors/{monitor_id}/logs", response_model=List[ExecutionLogResponse])
async def get_monitor_logs(monitor_id: int, limit: int = 50):
    """Get execution logs for a monitor"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT 
                el.id,
                el.monitor_id,
                el.started_at,
                el.completed_at,
                el.status,
                el.error_message,
                el.har_data,
                MAX(CASE WHEN pm.metric_name = 'ttfb_ms' THEN pm.metric_value END) as ttfb_ms,
                MAX(CASE WHEN pm.metric_name = 'dom_content_loaded_ms' THEN pm.metric_value END) as dom_content_loaded_ms,
                MAX(CASE WHEN pm.metric_name = 'page_load_time_ms' THEN pm.metric_value END) as page_load_time_ms
            FROM execution_logs el
            LEFT JOIN performance_metrics pm ON el.id = pm.execution_log_id
            WHERE el.monitor_id = %s
            GROUP BY el.id
            ORDER BY el.started_at DESC
            LIMIT %s
        """, (monitor_id, limit))
        logs = cursor.fetchall()
        return logs


@app.get("/api/grafana/dashboard")
async def get_grafana_dashboard():
    """Download Grafana dashboard JSON template"""
    dashboard = {
        "__inputs": [
            {
                "name": "DS_POSTGRESQL",
                "label": "PostgreSQL",
                "description": "PostgreSQL data source for synthetic monitoring",
                "type": "datasource",
                "pluginId": "postgres",
                "pluginName": "PostgreSQL"
            }
        ],
        "__requires": [
            {
                "type": "grafana",
                "id": "grafana",
                "name": "Grafana",
                "version": "8.0.0"
            },
            {
                "type": "datasource",
                "id": "postgres",
                "name": "PostgreSQL",
                "version": "1.0.0"
            },
            {
                "type": "panel",
                "id": "timeseries",
                "name": "Time series",
                "version": ""
            },
            {
                "type": "panel",
                "id": "stat",
                "name": "Stat",
                "version": ""
            }
        ],
        "annotations": {
            "list": []
        },
        "editable": True,
        "gnetId": None,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": [
            {
                "datasource": "${DS_POSTGRESQL}",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisLabel": "",
                            "axisPlacement": "auto",
                            "barAlignment": 0,
                            "drawStyle": "line",
                            "fillOpacity": 10,
                            "gradientMode": "none",
                            "lineInterpolation": "linear",
                            "lineWidth": 2,
                            "pointSize": 5,
                            "scaleDistribution": {"type": "linear"},
                            "showPoints": "never",
                            "spanNulls": True
                        },
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "red", "value": 80}
                            ]
                        },
                        "unit": "ms"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
                "id": 1,
                "options": {
                    "legend": {
                        "calcs": ["mean", "max"],
                        "displayMode": "table",
                        "placement": "right"
                    },
                    "tooltip": {"mode": "multi"}
                },
                "pluginVersion": "8.0.0",
                "targets": [
                    {
                        "datasource": "${DS_POSTGRESQL}",
                        "format": "time_series",
                        "group": [],
                        "metricColumn": "none",
                        "rawQuery": True,
                        "rawSql": """
-- IMPORTANT: Replace '${DS_POSTGRESQL}' with your actual PostgreSQL data source UID
SELECT 
  pm.recorded_at AS time,
  m.name || ' - ' || pm.metric_name as metric,
  pm.metric_value as value
FROM performance_metrics pm
JOIN execution_logs el ON pm.execution_log_id = el.id
JOIN monitors m ON el.monitor_id = m.id
WHERE 
  $__timeFilter(pm.recorded_at)
  AND pm.metric_name IN ('ttfb_ms', 'dom_content_loaded_ms', 'page_load_time_ms')
ORDER BY pm.recorded_at
                        """,
                        "refId": "A",
                        "select": [[{"params": ["value"], "type": "column"}]],
                        "timeColumn": "time",
                        "where": [{"name": "$__timeFilter", "params": [], "type": "macro"}]
                    }
                ],
                "title": "Performance Metrics Over Time",
                "type": "timeseries"
            },
            {
                "datasource": "${DS_POSTGRESQL}",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 1000},
                                {"color": "red", "value": 3000}
                            ]
                        },
                        "unit": "ms"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 4, "w": 8, "x": 0, "y": 8},
                "id": 2,
                "options": {
                    "colorMode": "background",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "textMode": "auto"
                },
                "pluginVersion": "8.0.0",
                "targets": [
                    {
                        "datasource": "${DS_POSTGRESQL}",
                        "format": "table",
                        "rawQuery": True,
                        "rawSql": """
SELECT 
  AVG(pm.metric_value) as value
FROM performance_metrics pm
WHERE 
  pm.metric_name = 'ttfb_ms'
  AND $__timeFilter(pm.recorded_at)
                        """,
                        "refId": "A"
                    }
                ],
                "title": "Average TTFB",
                "type": "stat"
            },
            {
                "datasource": "${DS_POSTGRESQL}",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 2000},
                                {"color": "red", "value": 5000}
                            ]
                        },
                        "unit": "ms"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 4, "w": 8, "x": 8, "y": 8},
                "id": 3,
                "options": {
                    "colorMode": "background",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "textMode": "auto"
                },
                "pluginVersion": "8.0.0",
                "targets": [
                    {
                        "datasource": "${DS_POSTGRESQL}",
                        "format": "table",
                        "rawQuery": True,
                        "rawSql": """
SELECT 
  AVG(pm.metric_value) as value
FROM performance_metrics pm
WHERE 
  pm.metric_name = 'page_load_time_ms'
  AND $__timeFilter(pm.recorded_at)
                        """,
                        "refId": "A"
                    }
                ],
                "title": "Average Page Load Time",
                "type": "stat"
            },
            {
                "datasource": "${DS_POSTGRESQL}",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "mappings": [
                            {"options": {"0": {"color": "red", "index": 1, "text": "Down"}}, "type": "value"},
                            {"options": {"1": {"color": "green", "index": 0, "text": "Up"}}, "type": "value"}
                        ],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None}
                            ]
                        }
                    },
                    "overrides": []
                },
                "gridPos": {"h": 4, "w": 8, "x": 16, "y": 8},
                "id": 4,
                "options": {
                    "colorMode": "background",
                    "graphMode": "none",
                    "justifyMode": "auto",
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "textMode": "auto"
                },
                "pluginVersion": "8.0.0",
                "targets": [
                    {
                        "datasource": "${DS_POSTGRESQL}",
                        "format": "table",
                        "rawQuery": True,
                        "rawSql": """
SELECT 
  CASE WHEN status = 'success' THEN 1 ELSE 0 END as value
FROM execution_logs
ORDER BY completed_at DESC
LIMIT 1
                        """,
                        "refId": "A"
                    }
                ],
                "title": "Latest Check Status",
                "type": "stat"
            }
        ],
        "refresh": "30s",
        "schemaVersion": 27,
        "style": "dark",
        "tags": ["synthetic", "monitoring", "performance"],
        "templating": {"list": []},
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Synthetic Monitoring Dashboard",
        "uid": "synthetic-monitoring",
        "version": 1,
        "description": "Dashboard for synthetic monitoring metrics. **SETUP REQUIRED**: Replace ${DS_POSTGRESQL} with your PostgreSQL data source UID in all panel queries."
    }
    
    return JSONResponse(
        content=dashboard,
        headers={
            "Content-Disposition": "attachment; filename=synthetic-monitoring-dashboard.json"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
