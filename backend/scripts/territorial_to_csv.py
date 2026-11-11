"""
territorial_to_csv.py — Adaptador de Estructura Territorial y Gremios para TRAMA.

Convierte bases de datos de campaña territorial (líderes barriales, ediles,
coordinadores comunales, gremios, sindicatos y empresarios) en el grafo de red
que TRAMA procesa para identificar la capilaridad de tu campaña política.

Formatos soportados de entrada:
1. Formato Relacional de Campaña:
   - source: Nombre o handle del líder / coordinador / gremio
   - target: Nombre del territorio, barrio, gremio o candidato al que apoya
   - role: (opcional) 'Coordinador', 'Líder Barrial', 'Empresario', 'Gremio'
   - territory: (opcional) 'Comuna 1', 'Zona Rural', 'Centro', etc.

2. Generación de Plantilla de Ejemplo:
   python territorial_to_csv.py --demo
   -> Genera 'campana_territorial_ejemplo.csv' listo para importar en TRAMA.
"""

import csv
import sys
import argparse
from pathlib import Path


SAMPLE_TERRITORIAL_NETWORK = [
    # Núcleo de Campaña y Candidato
    ("@MiCandidato", "@JefeDeCampana"),
    ("@MiCandidato", "@CoordinadorTerritorial"),
    ("@MiCandidato", "@EstrategiaDigital"),
    ("@MiCandidato", "@VoceroJuventudes"),
    
    # Estructura Comuna 1 (Norte)
    ("@CoordinadorTerritorial", "@LiderComuna1_Carlos"),
    ("@LiderComuna1_Carlos", "@JAC_BarrioEsperanza"),
    ("@LiderComuna1_Carlos", "@ColectivoMadresComuna1"),
    ("@JAC_BarrioEsperanza", "@PresidenteDeportesComuna1"),
    
    # Estructura Comuna 2 (Sur - Voto Popular)
    ("@CoordinadorTerritorial", "@LiderComuna2_Marta"),
    ("@LiderComuna2_Marta", "@ComiteMujeresSur"),
    ("@LiderComuna2_Marta", "@AsociacionComerciantesSur"),
    ("@ComiteMujeresSur", "@RedComunitariaSalud"),
    
    # Gremios y Sector Productivo
    ("@MiCandidato", "@PresidenteCamaraComercio"),
    ("@PresidenteCamaraComercio", "@GremioTransportadores"),
    ("@PresidenteCamaraComercio", "@AsociacionHotelera"),
    ("@GremioTransportadores", "@SindicatoConductores"),
    
    # Sector Académico y Juventudes
    ("@VoceroJuventudes", "@LiderEstudiantilUni"),
    ("@LiderEstudiantilUni", "@ColectivoAmbientalCampus"),
    ("@LiderEstudiantilUni", "@RedArtistasUrbanos"),
    
    # Puentes entre Sectores (Brokers naturales)
    ("@LiderComuna2_Marta", "@GremioTransportadores"),
    ("@ColectivoAmbientalCampus", "@ColectivoMadresComuna1"),
    ("@PresidenteCamaraComercio", "@LiderComuna1_Carlos"),
]


def generate_sample_csv(output_path: Path):
    """Crea un dataset territorial de demostración para importar en TRAMA."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])
        for src, tgt in SAMPLE_TERRITORIAL_NETWORK:
            writer.writerow([src, tgt])
    print(f"✓ Plantilla de campaña territorial generada en: {output_path}")
    print(f"  Total de interacciones/enlaces territoriales: {len(SAMPLE_TERRITORIAL_NETWORK)}")
    print("  Importa este archivo desde el botón 'Importar CSV' en TRAMA.")


def convert_field_table(input_path: Path, output_path: Path):
    """
    Convierte tablas con columnas variables (líder, barrio, apoyo, etc.)
    al formato estricto 'source,target' para el motor de grafos.
    """
    edges = set()
    with open(input_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Buscar columnas comunes
            src = row.get("source") or row.get("lider") or row.get("responsable") or row.get("nombre")
            tgt = row.get("target") or row.get("apoya_a") or row.get("territorio") or row.get("comuna") or row.get("gremio")
            if src and tgt:
                src_clean = "@" + src.strip().lstrip("@").replace(" ", "_")
                tgt_clean = "@" + tgt.strip().lstrip("@").replace(" ", "_")
                if src_clean != tgt_clean:
                    edges.add((src_clean, tgt_clean))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])
        for src, tgt in sorted(edges):
            writer.writerow([src, tgt])

    print(f"✓ Convertidas {len(edges)} relaciones territoriales a: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Adaptador Territorial de Campaña para TRAMA")
    parser.add_argument("--demo", action="store_true", help="Generar dataset territorial de ejemplo")
    parser.add_argument("--input", "-i", type=str, help="Ruta al archivo CSV de territorio")
    parser.add_argument("--output", "-o", type=str, default="red_territorial_trama.csv", help="Archivo CSV de salida")

    args = parser.parse_args()

    if args.demo:
        out = Path(args.output) if args.output != "red_territorial_trama.csv" else Path("campana_territorial_ejemplo.csv")
        generate_sample_csv(out)
        return

    if args.input:
        convert_field_table(Path(args.input), Path(args.output))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
