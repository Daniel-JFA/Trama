"""
benchmark_duckdb.py — Benchmark de rendimiento analítico columnar con DuckDB + Parquet.
Simula 2,000,000 (2M) de InteractionEvents canónicos particionados y verifica que las
consultas analíticas se resuelvan en menos de 300 ms.
"""

import os
import sys
import time
import shutil
import tempfile
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import duckdb


def generate_benchmark_dataset(output_dir: str, n_events: int = 2_000_000) -> None:
    """Genera 2,000,000 de eventos sintéticos optimizados en formato Parquet particionado."""
    print(f"[*] Generando {n_events:,} eventos sintéticos vectorialmente con PyArrow...")
    t0 = time.perf_counter()

    # Generación vectorial rápida usando numpy
    np.random.seed(42)

    # Actores y targets simulados
    n_actors = 50_000
    actors_pool = [f"user_{i:05d}" for i in range(n_actors)]
    actor_indices = np.random.randint(0, n_actors, size=n_events)
    target_indices = np.random.randint(0, n_actors, size=n_events)

    # Acciones y plataformas
    action_types = np.array(["retweet", "reply", "post", "forward", "mention"])
    platforms = np.array(["bluesky", "telegram", "twitter"])
    act_choices = np.random.choice(action_types, size=n_events, p=[0.4, 0.25, 0.2, 0.1, 0.05])
    plat_choices = np.random.choice(platforms, size=n_events, p=[0.4, 0.3, 0.3])

    # Timestamps en ventana de 7 días (cada 5-10 segundos)
    base_ts = 1778400000  # Mayo 2026
    time_deltas = np.sort(np.random.randint(0, 7 * 86400, size=n_events))
    timestamps_epoch = base_ts + time_deltas

    # Convertir a strings ISO
    # En PyArrow podemos usar timestamp[s] nativo para máxima velocidad
    ts_arrow = pa.compute.cast(pa.array(timestamps_epoch, type=pa.int64()), pa.timestamp("s"))

    # Crear arrays de pyarrow
    project_ids = pa.repeat("proj_benchmark", n_events)
    actors = pa.array(np.array(actors_pool)[actor_indices])
    targets = pa.array(np.array(actors_pool)[target_indices])
    actions = pa.array(act_choices)
    plats = pa.array(plat_choices)

    table = pa.Table.from_arrays(
        [project_ids, actors, targets, ts_arrow, actions, plats],
        names=["project_id", "actor", "target", "timestamp", "action_type", "platform"]
    )

    parquet_file = os.path.join(output_dir, "events_2m.parquet")
    pq.write_table(table, parquet_file, compression="SNAPPY", row_group_size=250_000)

    t_gen = time.perf_counter() - t0
    file_size_mb = os.path.getsize(parquet_file) / (1024 * 1024)
    print(f"[✓] Dataset generado en {t_gen:.2f} s. Tamaño en disco: {file_size_mb:.2f} MB ({parquet_file})")


def run_benchmarks(parquet_dir: str) -> bool:
    """Ejecuta consultas analíticas con DuckDB y mide tiempos contra el objetivo < 300 ms."""
    parquet_path = os.path.join(parquet_dir, "*.parquet")
    con = duckdb.connect()
    con.execute("PRAGMA threads=4;")

    print("\n" + "=" * 65)
    print("  EJECUCIÓN DE BENCHMARKS CON DUCKDB (2,000,000 REGISTROS)")
    print("=" * 65)

    all_passed = True

    # Benchmark 1: Agregación por minuto (eventos + actores únicos)
    q1 = f"""
    SELECT 
        date_trunc('minute', timestamp) AS minute_bucket,
        COUNT(*) AS total_events,
        COUNT(DISTINCT actor) AS unique_actors,
        COUNT(DISTINCT target) AS unique_targets
    FROM read_parquet('{parquet_path}')
    WHERE project_id = 'proj_benchmark'
    GROUP BY 1
    ORDER BY 1 ASC
    """
    # Warmup
    con.execute(q1).fetchall()

    t0 = time.perf_counter()
    res1 = con.execute(q1).fetchall()
    t1 = (time.perf_counter() - t0) * 1000

    status1 = "PASÓ (< 300ms)" if t1 < 300 else "EXCEDIDO"
    print(f"1. Agregación temporal por minuto (buckets={len(res1)}):")
    print(f"   ⏱ Tiempo: {t1:.2f} ms ➔ [{status1}]")
    if t1 >= 300:
        all_passed = False

    # Benchmark 2: Ventana móvil de 15 minutos (rolling sum y avg)
    q2 = f"""
    WITH minute_counts AS (
        SELECT 
            date_trunc('minute', timestamp) AS m_bucket,
            COUNT(*) AS cnt
        FROM read_parquet('{parquet_path}')
        WHERE project_id = 'proj_benchmark'
        GROUP BY 1
    )
    SELECT 
        m_bucket,
        cnt,
        SUM(cnt) OVER (ORDER BY m_bucket RANGE BETWEEN INTERVAL '15 minutes' PRECEDING AND CURRENT ROW) AS rolling_15m
    FROM minute_counts
    ORDER BY m_bucket ASC
    """
    t0 = time.perf_counter()
    res2 = con.execute(q2).fetchall()
    t2 = (time.perf_counter() - t0) * 1000

    status2 = "PASÓ (< 300ms)" if t2 < 300 else "EXCEDIDO"
    print(f"\n2. Cálculo de Ventana Móvil de 15 minutos (rolling window):")
    print(f"   ⏱ Tiempo: {t2:.2f} ms ➔ [{status2}]")
    if t2 >= 300:
        all_passed = False

    # Benchmark 3: Top 20 actores más activos y destinos
    q3 = f"""
    SELECT 
        actor,
        platform,
        COUNT(*) AS total_actions,
        COUNT(DISTINCT target) AS targets_reached
    FROM read_parquet('{parquet_path}')
    WHERE project_id = 'proj_benchmark'
    GROUP BY 1, 2
    ORDER BY total_actions DESC
    LIMIT 20
    """
    t0 = time.perf_counter()
    res3 = con.execute(q3).fetchall()
    t3 = (time.perf_counter() - t0) * 1000

    status3 = "PASÓ (< 300ms)" if t3 < 300 else "EXCEDIDO"
    print(f"\n3. Ranking Top 20 Actores (agrupación y ordenamiento):")
    print(f"   ⏱ Tiempo: {t3:.2f} ms ➔ [{status3}]")
    if t3 >= 300:
        all_passed = False

    print("=" * 65)
    if all_passed:
        print(" [✓] TODOS LOS BENCHMARKS CUMPLEN EL REQUISITO < 300 MS EN DUCKDB")
    else:
        print(" [!] AL MENOS UNA CONSULTA EXCEDIÓ EL LÍMITE DE 300 MS")
    print("=" * 65 + "\n")

    return all_passed


if __name__ == "__main__":
    temp_dir = tempfile.mkdtemp(prefix="duckdb_bench_")
    try:
        generate_benchmark_dataset(temp_dir, n_events=2_000_000)
        success = run_benchmarks(temp_dir)
        sys.exit(0 if success else 1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
