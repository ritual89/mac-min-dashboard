from __future__ import annotations

from pathlib import Path

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from mac_mini_api.deps import ExecutorFactory, get_config, get_executor_factory, get_store
from mac_mini_api.schemas import HostOut, WorkloadDetailOut, WorkloadOut
from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.control import (
    ControlCommandError,
    UnsupportedControlError,
    restart_workload,
    stop_workload,
)
from mac_mini_core.logs import LogFetchError, UnsupportedWorkloadKindError, fetch_workload_logs
from mac_mini_core.store import HostRow, WorkloadRow, WorkloadStore


def _host_out(row: HostRow) -> HostOut:
    return HostOut(
        id=row.id,
        display_name=row.display_name,
        tailscale_host=row.tailscale_host,
        os=row.os,
        last_seen=row.last_seen,
    )


def _workload_out(row: WorkloadRow) -> WorkloadOut:
    return WorkloadOut(
        id=row.id,
        host_id=row.host_id,
        kind=row.kind,
        name=row.name,
        monitored=row.monitored,
        pinned=row.pinned,
        status=row.status,
        severity=row.severity,
        severity_reason=row.severity_reason,
        last_seen=row.last_seen,
        metadata=row.metadata,
    )


def _resolve_host_config(config: AppConfig | None, host_id: str) -> HostConfig:
    if config is None:
        msg = "config not configured"
        raise RuntimeError(msg)
    for host in config.hosts:
        if host.id == host_id:
            return host
    msg = f"host {host_id!r} not in config"
    raise HTTPException(status_code=404, detail=msg)


def create_app(
    store: WorkloadStore | None = None,
    *,
    config: AppConfig | None = None,
    executor_factory: ExecutorFactory | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Mac Mini Dashboard")
    app.state.store = store
    app.state.config = config
    app.state.executor_factory = executor_factory

    @app.get("/api/hosts", response_model=list[HostOut])
    def list_hosts(store: WorkloadStore = Depends(get_store)) -> list[HostOut]:
        return [_host_out(row) for row in store.list_hosts()]

    @app.get("/api/workloads", response_model=list[WorkloadOut])
    def list_workloads(
        monitored: bool | None = Query(default=None),
        host_id: str | None = Query(default=None),
        severity: str | None = Query(default=None),
        store: WorkloadStore = Depends(get_store),
    ) -> list[WorkloadOut]:
        rows = store.list_workloads(
            monitored=monitored,
            host_id=host_id,
            severity=severity,
        )
        return [_workload_out(row) for row in rows]

    @app.get("/api/workloads/{workload_id}", response_model=WorkloadDetailOut)
    def get_workload(
        workload_id: str,
        store: WorkloadStore = Depends(get_store),
    ) -> WorkloadDetailOut:
        row = store.get_workload(workload_id)
        if row is None:
            raise HTTPException(status_code=404, detail="workload not found")
        return WorkloadDetailOut(**_workload_out(row).model_dump())

    @app.get("/api/workloads/{workload_id}/logs", response_class=Response)
    def get_workload_logs(
        workload_id: str,
        tail: int = Query(default=200, ge=1, le=10_000),
        store: WorkloadStore = Depends(get_store),
        config: AppConfig | None = Depends(get_config),
        executor_factory: ExecutorFactory | None = Depends(get_executor_factory),
    ) -> Response:
        row = store.get_workload(workload_id)
        if row is None:
            raise HTTPException(status_code=404, detail="workload not found")

        if executor_factory is None:
            msg = "executor_factory not configured"
            raise RuntimeError(msg)

        host_row = store.get_host(row.host_id)
        if host_row is None:
            raise HTTPException(status_code=404, detail="host not found")

        host_config = _resolve_host_config(config, row.host_id)
        executor = executor_factory(host_config)

        try:
            body = fetch_workload_logs(row, host_row, executor, tail=tail)
        except UnsupportedWorkloadKindError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LogFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return Response(content=body, media_type="text/plain; charset=utf-8")

    @app.get("/api/audit", response_model=list[WorkloadOut])
    def list_audit(store: WorkloadStore = Depends(get_store)) -> list[WorkloadOut]:
        rows = store.list_workloads(monitored=False)
        return [_workload_out(row) for row in rows]

    @app.post("/api/workloads/{workload_id}/pin")
    def pin_workload(
        workload_id: str,
        store: WorkloadStore = Depends(get_store),
    ) -> dict[str, str]:
        if not store.pin_workload(workload_id):
            raise HTTPException(status_code=404, detail="workload not found")
        return {"status": "pinned"}

    @app.delete("/api/workloads/{workload_id}/pin")
    def unpin_workload(
        workload_id: str,
        store: WorkloadStore = Depends(get_store),
        config: AppConfig | None = Depends(get_config),
    ) -> dict[str, str]:
        rules = config.promote if config else PromoteRulesConfig()
        if not store.unpin_workload(workload_id, rules):
            raise HTTPException(status_code=404, detail="workload not found")
        return {"status": "unpinned"}

    @app.post("/api/workloads/{workload_id}/restart")
    def restart_workload_endpoint(
        workload_id: str,
        store: WorkloadStore = Depends(get_store),
        config: AppConfig | None = Depends(get_config),
        executor_factory: ExecutorFactory | None = Depends(get_executor_factory),
    ) -> dict[str, str]:
        row = store.get_workload(workload_id)
        if row is None:
            raise HTTPException(status_code=404, detail="workload not found")
        if executor_factory is None:
            msg = "executor_factory not configured"
            raise RuntimeError(msg)
        host_config = _resolve_host_config(config, row.host_id)
        executor = executor_factory(host_config)
        try:
            restart_workload(row, executor)
        except UnsupportedControlError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ControlCommandError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"status": "restarted"}

    @app.post("/api/workloads/{workload_id}/stop")
    def stop_workload_endpoint(
        workload_id: str,
        confirm: bool = Query(default=False),
        store: WorkloadStore = Depends(get_store),
        config: AppConfig | None = Depends(get_config),
        executor_factory: ExecutorFactory | None = Depends(get_executor_factory),
    ) -> dict[str, str]:
        if not confirm:
            raise HTTPException(status_code=400, detail="confirm=1 required")
        row = store.get_workload(workload_id)
        if row is None:
            raise HTTPException(status_code=404, detail="workload not found")
        if executor_factory is None:
            msg = "executor_factory not configured"
            raise RuntimeError(msg)
        host_config = _resolve_host_config(config, row.host_id)
        executor = executor_factory(host_config)
        try:
            stop_workload(row, executor)
        except UnsupportedControlError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ControlCommandError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"status": "stopped"}

    @app.get("/api/settings")
    def get_settings(
        store: WorkloadStore = Depends(get_store),
    ) -> dict[str, bool]:
        return store.get_settings()

    @app.patch("/api/settings")
    def patch_settings(
        patch: dict[str, bool] = Body(...),
        store: WorkloadStore = Depends(get_store),
    ) -> dict[str, str]:
        unknown = store.update_settings(patch)
        if unknown:
            msg = f"unknown settings: {', '.join(sorted(unknown))}"
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "updated"}

    if static_dir is None or not static_dir.is_dir():

        @app.get("/", response_class=HTMLResponse)
        def ui_not_built() -> str:
            return (
                "<h1>Mac Mini Dashboard API is running</h1>"
                "<p>UI not built. From repo root:</p>"
                "<pre>cd apps/web && npm ci && npm run build</pre>"
                "<p>Then restart the API and reload this page.</p>"
                "<p>API: <a href='/api/workloads?monitored=true'>/api/workloads</a></p>"
            )

    if static_dir is not None and static_dir.is_dir():
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="not found")
            index = static_dir / "index.html"
            if not index.is_file():
                raise HTTPException(status_code=404, detail="ui not built")
            return FileResponse(index)

    return app
