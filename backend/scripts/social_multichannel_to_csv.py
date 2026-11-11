"""
social_multichannel_to_csv.py — Adaptador de Conversación Multicanal para TRAMA.

Unifica exportaciones de:
- X / Twitter (menciones, retuits, respuestas, citas)
- TikTok (menciones en comentarios, respuestas a creadores)
- Facebook (comentarios en páginas de debate y grupos)

Genera: trama_multicanal.csv listo para ser cargado y analizado en TRAMA.
"""

import csv
import re
import argparse
from pathlib import Path


def clean_handle(handle: str) -> str:
    """Normaliza un handle para asegurar consistencia entre redes."""
    if not handle:
        return ""
    h = handle.strip()
    h = re.sub(r"[^\w@]", "", h)
    if not h.startswith("@"):
        h = "@" + h
    return h.lower()


def process_multichannel_csv(input_path: Path, output_path: Path):
    """Procesa un CSV con columnas de redes sociales y extrae pares source-target."""
    edges = set()
    with open(input_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Reconoce diferentes nombres de columnas comunes en herramientas de extracción
            src = row.get("source") or row.get("author") or row.get("user") or row.get("from") or row.get("usuario")
            tgt = row.get("target") or row.get("mentioned") or row.get("reply_to") or row.get("to") or row.get("destinatario")
            
            # En caso de campo de texto que contiene menciones
            text = row.get("text") or row.get("content") or row.get("comment") or row.get("tweet")
            
            if src and tgt:
                src_c = clean_handle(src)
                tgt_c = clean_handle(tgt)
                if src_c and tgt_c and src_c != tgt_c:
                    edges.add((src_c, tgt_c))
            elif src and text:
                src_c = clean_handle(src)
                mentions = re.findall(r"@[\w_]+", text)
                for m in mentions:
                    tgt_c = clean_handle(m)
                    if src_c and tgt_c and src_c != tgt_c:
                        edges.add((src_c, tgt_c))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])
        for src, tgt in sorted(edges):
            writer.writerow([src, tgt])

    print(f"✓ Procesadas {len(edges)} interacciones multicanal exportadas a: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Conversor Multicanal de Redes Sociales para TRAMA")
    parser.add_argument("--input", "-i", required=True, help="Archivo CSV de origen")
    parser.add_argument("--output", "-o", default="trama_multicanal.csv", help="Archivo CSV destino")

    args = parser.parse_args()
    process_multichannel_csv(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
