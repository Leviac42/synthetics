Role & Objective: Act as a Senior Python DevOps Architect. I need a complete, containerized synthetic monitoring application stack to replace AppDynamics. The goal is to measure frontend user experience using browser automation and visualize the data in an external Grafana instance.

Core Technology Stack:

Language: Python (Use FastAPI or Flask for the API and Orchestrator).

Engine: Playwright for Python (for browser automation).

Database: PostgreSQL (for storing metrics, configurations, and logs).

Frontend: A lightweight HTML/JS interface (served by the Python app) for management.

Deployment: Container-native (Docker/Podman) and Kubernetes-ready (MicroK8s, OpenShift, K3s).

Functional Requirements:

Synthetic Worker (Python + Playwright):

A background service/worker that executes Playwright scripts based on schedules stored in the DB.

Metrics: It must capture Time to First Byte (TTFB), DOM Content Loaded, Page Load Time, and capture full Network Waterfall (HAR) data.

Data Ingestion: Parse these metrics and insert them into the PostgreSQL database.

Admin Interface & API:

A web UI to manage monitors (Create/Edit/Delete/Run Now).

Dashboard Export Feature: The UI must have a "Download Grafana Dashboard" button.

This button should serve a pre-built .json file compatible with the PostgreSQL schema you design.

Crucial: The JSON must contain clear placeholders/comments (e.g., "${DS_PROMETHEUS}" or ``) indicating exactly where the user needs to define their specific Grafana Data Source UID to make the panels work.

Data Persistence:

Design a SQL schema optimized for time-series queries. Tables should include monitors, execution_logs, and performance_metrics.

Non-Functional & Deployment Requirements:

Zero-Config Deployment: The stack must run "out of the box" with hardcoded sensible defaults. Do not rely on external environment variables for the initial boot (e.g., default to internal postgres user/pass if not provided).

Podman & Kubernetes Friendly:

Ensure the Containerfile is compatible with rootless Podman.

Storage & Persistence:

Kubernetes: The Postgres service must utilize a PersistentVolumeClaim (PVC). Do not specify a storageClassName in the manifest; rely on the cluster's default storage class to ensure compatibility across MicroK8s, OpenShift, and K3s.

Podman/Docker: In the compose file, map the Postgres data directory (/var/lib/postgresql/data) to a standard named volume.

Deliverables:

Project file structure.

init.sql schema for PostgreSQL.

Python code for the API and Playwright Worker.

The Grafana Dashboard JSON template (embedded in the Python code or as a static file to be served).

podman-compose.yml and Kubernetes YAML manifests (Deployment, Service, PVC).