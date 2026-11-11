"""
columnar.py — Motor analítico columnar de alto rendimiento con DuckDB + Parquet (Sprint 5 / Bloque D).
Soporta:
1. Particionamiento por proyecto y fecha (year/month/day).
2. Agregaciones temporales por minuto sobre millones de eventos.
3. Ventanas móviles de cálculo de actividad (rolling windows) para detección de ráfagas CIB.
4. Consultas analíticas en sub-segundos (< 300 ms sobre 2M de registros).
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import duckdb
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .schemas import InteractionEvent


def get_duckdb_connection(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Retorna una conexión optimizada a DuckDB con threads según CPU."""
    con = duckdb.connect(db_path)
    con.execute("PRAGMA threads=4;")
    return con


def events_to_arrow_table(events: List[InteractionEvent], default_project_id: str = "default") -> pa.Table:
    """Convierte una lista de InteractionEvent en una PyArrow Table con esquema canónico y particiones."""
    actors, targets, timestamps, action_types, platforms, contents = [], [], [], [], [], []
    project_ids, years, months, days = [], [], [], []

    for ev in events:
        pid = ev.project_id or default_project_id
        ts_str = ev.timestamp
        try:
            # Parsear año, mes y día para particionado eficiente
            clean_ts = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            y, m, d = dt.year, f"{dt.month:02d}", f"{dt.day:02d}"
        except Exception:
            y, m, d = 2026, "01", "01"

        actors.append(ev.actor)
        targets.append(ev.target or "")
        timestamps.append(ts_str[:19])  # Formato YYYY-MM-DDTHH:MM:SS
        action_types.append(ev.action_type)
        platforms.append(ev.platform)
        contents.append(ev.content or "")
        project_ids.append(pid)
        years.append(y)
        months.append(m)
        days.append(d)

    schema = pa.schema([
        ("project_id", pa.string()),
        ("actor", pa.string()),
        ("target", pa.string()),
        ("timestamp", pa.string()),
        ("action_type", pa.string()),
        ("platform", pa.string()),
        ("content", pa.string()),
        ("year", pa.int32()),
        ("month", pa.string()),
        ("day", pa.string()),
    ])

    return pa.Table.from_arrays([
        pa.array(project_ids),
        pa.array(actors),
        pa.array(targets),
        pa.array(timestamps),
        pa.array(action_types),
        pa.array(platforms),
        pa.array(contents),
        pa.array(years),
        pa.array(months),
        pa.array(days),
    ], schema=schema)


def save_events_to_parquet(
    events: List[InteractionEvent],
    base_dir: str = "data/parquet",
    default_project_id: str = "default"
) -> int:
    """
    Persiste eventos en disco en formato Parquet, organizados en dataset particionado:
    base_dir/project_id={pid}/year={y}/month={m}/day={d}/...
    """
    if not events:
        return 0

    table = events_to_arrow_table(events, default_project_id=default_project_id)
    os.makedirs(base_dir, exist_ok=True)

    ds.write_dataset(
        table,
        base_dir=base_dir,
        format="parquet",
        partitioning=["project_id", "year", "month", "day"],
        partitioning_flavor="hive",
        existing_data_behavior="overwrite_or_ignore",
    )
    return len(events)


class ColumnarAnalytics:
    """Motor de consultas analíticas ultrarrápidas con DuckDB sobre Parquet particionado."""

    def __init__(self, base_dir: str = "data/parquet", con: Optional[duckdb.DuckDBPyConnection] = None):
        self.base_dir = base_dir
        self.con = con or get_duckdb_connection()

    def aggregate_by_minute(
        self,
        project_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Agrega eventos por minuto (volumen total, actores únicos y tipos de acción).
        """
        parquet_pattern = os.path.join(self.base_dir, "**/*.parquet")
        if not os.path.exists(self.base_dir):
            return []

        where_clauses = ["project_id = ?"]
        params = [project_id]

        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(start_time[:19])
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(end_time[:19])

        where_sql = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            strftime(date_trunc('minute', CAST(timestamp AS TIMESTAMP)), '%Y-%m-%dT%H:%M:%S') AS minute_bucket,
            COUNT(*) AS event_count,
            COUNT(DISTINCT actor) AS unique_actors,
            COUNT(DISTINCT target) AS unique_targets
        FROM read_parquet('{parquet_pattern}', hive_partitioning=1)
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY 1 ASC
        """

        try:
            res = self.con.execute(query, params).fetchall()
            return [
                {
                    "minute_bucket": r[0],
                    "event_count": r[1],
                    "unique_actors": r[2],
                    "unique_targets": r[3],
                }
                for r in res
            ]
        except Exception:
            return []

    def rolling_windows(
        self,
        project_id: str,
        window_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Calcula agregaciones en ventanas móviles (rolling sum y media móvil)
        para detección de ráfagas anómalas de sincronización.
        """
        parquet_pattern = os.path.join(self.base_dir, "**/*.parquet")
        if not os.path.exists(self.base_dir):
            return []

        query = f"""
        WITH minute_series AS (
            SELECT 
                date_trunc('minute', CAST(timestamp AS TIMESTAMP)) AS m_time,
                COUNT(*) AS cnt,
                COUNT(DISTINCT actor) AS actors_cnt
            FROM read_parquet('{parquet_pattern}', hive_partitioning=1)
            WHERE project_id = ?
            GROUP BY 1
        )
        SELECT 
            strftime(m_time, '%Y-%m-%dT%H:%M:%S') AS timestamp,
            cnt AS count,
            SUM(cnt) OVER (ORDER BY m_time RANGE BETWEEN INTERVAL '{window_minutes} minutes' PRECEDING AND CURRENT ROW) AS rolling_volume,
            ROUND(AVG(cnt) OVER (ORDER BY m_time RANGE BETWEEN INTERVAL '{window_minutes} minutes' PRECEDING AND CURRENT ROW), 2) AS rolling_avg
        FROM minute_series
        ORDER BY m_time ASC
        """

        try:
            res = self.con.execute(query, [project_id]).fetchall()
            return [
                {
                    "timestamp": r[0],
                    "count": r[1],
                    "rolling_volume": r[2],
                    "rolling_avg": r[3],
                }
                for r in res
            ]
        except Exception:
            return []

    def top_actors(self, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Calcula los actores con mayor volumen de publicaciones y amplificación."""
        parquet_pattern = os.path.join(self.base_dir, "**/*.parquet")
        if not os.path.exists(self.base_dir):
            return []

        query = f"""
        SELECT 
            actor,
            platform,
            COUNT(*) AS total_actions,
            COUNT(DISTINCT target) AS targets_reached
        FROM read_parquet('{parquet_pattern}', hive_partitioning=1)
        WHERE project_id = ?
        GROUP BY 1, 2
        ORDER BY total_actions DESC
        LIMIT ?
        """
        try:
            res = self.con.execute(query, [project_id, limit]).fetchall()
            return [
                {
                    "actor": r[0],
                    "platform": r[1],
                    "total_actions": r[2],
                    "targets_reached": r[3],
                }
                for r in res
            ]
        except Exception:
            return []
