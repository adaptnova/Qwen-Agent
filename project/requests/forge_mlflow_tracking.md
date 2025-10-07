# Forge Launch Request — MLflow Tracking Server

- **Request ID**: NOVA-P2-MLFLOW-001
- **Date**: 2025-10-07
- **Owner**: Chase (NovaOps)
- **Assignee**: Forge (PlatformOps)

## Objective
Deploy an internal MLflow tracking server so NovaOps can log benchmark runs for the thinking-model fleet and maintain experiment history from the outset.

## Requirements
- Host: shared analytics VM or container (Ubuntu 24.04, Python 3.10+).
- Storage: local disk (`/data/mlflow`) with ≥200 GB free; S3-compatible bucket optional.
- Authentication: reverse proxy (nginx) with Nova SSO or static token; restrict access to NovaOps group.

## Setup Steps
1. Install dependencies:
   ```bash
   python3 -m venv /data/mlflow/venv
   source /data/mlflow/venv/bin/activate
   pip install --upgrade pip
   pip install mlflow[extras]==2.16.0 psycopg2-binary gunicorn
   ```
2. Provision backend store (PostgreSQL recommended):
   ```bash
   createdb mlflow_db
   ```
   Record DSN in `/data/mlflow/mlflow.env`.
3. Prepare artifact root:
   ```bash
   mkdir -p /data/mlflow/artifacts
   chown -R novaops:novaops /data/mlflow/artifacts
   ```
4. Create systemd service `/etc/systemd/system/mlflow.service`:
   ```ini
   [Unit]
   Description=MLflow Tracking Server
   After=network.target

   [Service]
   Type=simple
   EnvironmentFile=/data/mlflow/mlflow.env
   WorkingDirectory=/data/mlflow
   ExecStart=/data/mlflow/venv/bin/mlflow server \
       --backend-store-uri ${MLFLOW_BACKEND_URI} \
       --default-artifact-root ${MLFLOW_ARTIFACT_ROOT:-file:/data/mlflow/artifacts} \
       --host 0.0.0.0 --port 5100
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
5. Optionally front with nginx + TLS cert; expose as `https://mlflow.nova.internal`.
6. Share connection details and token with NovaOps:
   - Tracking URI
   - Artifact root path/bucket
   - Credentials file (if applicable)

## Validation
- `curl http://<host>:5100/` returns HTML page.
- `mlflow ui` accessible through reverse proxy.
- Run smoke command from NovaOps host:
  ```bash
  python -c "import mlflow; mlflow.set_tracking_uri('http://<host>:5100'); mlflow.set_experiment('Nova-Test'); mlflow.start_run(); mlflow.log_param('ping','ok'); mlflow.end_run()"
  ```
- Confirm run appears in UI.

## Dependencies / Notes
- Coordinate firewall rules with NetOps.
- Ensure nightly backups for PostgreSQL database and artifact directory.
- Provide Terraform/Ansible snippets if automation preferred.

## Contact
- Chase (NovaOps): chase@novaops.internal
- Atlas (NovaOps): atlas@novaops.internal

