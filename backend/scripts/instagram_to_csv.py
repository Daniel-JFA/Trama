"""
instagram_to_csv.py
───────────────────
Convierte la descarga de datos de Instagram al formato source,target que TRAMA espera.

Uso:
    python scripts/instagram_to_csv.py /ruta/a/tu/carpeta_instagram

La carpeta debe ser la que descomprimes del ZIP que te envía Instagram.
Genera: trama_instagram.csv en el directorio actual.

Qué extrae:
  - Tus seguidores         → seguidor → @tucuenta
  - A quienes sigues       → @tucuenta → seguido
  - Comentarios que hiciste en posts ajenos → @tucuenta → @autor_del_post
  - Comentarios en tus posts (si están disponibles)
"""

import json
import csv
import os
import sys
import re
from pathlib import Path


def sanitize(handle: str) -> str:
    """Quita @ inicial y espacios, convierte a minúsculas."""
    return handle.strip().lstrip("@").lower()


def load_json(path: Path):
    """Carga un JSON ignorando errores de encoding."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return json.load(f)
    except Exception:
        return None


def extract_string_value(obj):
    """Extrae el valor de string de las estructuras de Instagram (pueden ser anidadas)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        # Instagram usa {"href": "...", "value": "username"} o {"string_map_data": {...}}
        if "value" in obj:
            return obj["value"]
        if "string_map_data" in obj:
            for v in obj["string_map_data"].values():
                if isinstance(v, dict) and "value" in v:
                    return v["value"]
    if isinstance(obj, list) and len(obj) > 0:
        return extract_string_value(obj[0])
    return None


def get_my_username(folder: Path) -> str:
    """Intenta detectar tu propio username desde personal_information."""
    candidates = [
        folder / "personal_information" / "personal_information.json",
        folder / "account_information" / "personal_information.json",
    ]
    for path in candidates:
        if path.exists():
            data = load_json(path)
            if data:
                # Estructura: {"profile_user": [{"string_map_data": {"Username": {"value": "..."}}}]}
                try:
                    prof = data.get("profile_user", [{}])[0]
                    smd = prof.get("string_map_data", {})
                    username = smd.get("Username", {}).get("value", "")
                    if username:
                        return sanitize(username)
                except Exception:
                    pass
    return None


def parse_followers(folder: Path, my_user: str, edges: set):
    """followers_and_following/followers_*.json → seguidor → @yo"""
    ff_dir = folder / "followers_and_following"
    if not ff_dir.exists():
        return
    count = 0
    for fname in sorted(ff_dir.iterdir()):
        if "follower" not in fname.name.lower():
            continue
        data = load_json(fname)
        if not data:
            continue
        # Puede ser lista directa o dict con clave "relationships_followers"
        items = data if isinstance(data, list) else data.get("relationships_followers", [])
        for item in items:
            username = None
            if isinstance(item, dict):
                # {"string_list_data": [{"value": "username", ...}]}
                sld = item.get("string_list_data", [])
                if sld:
                    username = extract_string_value(sld[0])
                if not username:
                    username = extract_string_value(item)
            elif isinstance(item, str):
                username = item
            if username:
                edges.add((sanitize(username), my_user))
                count += 1
    print(f"  ✓ Seguidores: {count} aristas")


def parse_following(folder: Path, my_user: str, edges: set):
    """followers_and_following/following.json → @yo → seguido"""
    ff_dir = folder / "followers_and_following"
    if not ff_dir.exists():
        return
    count = 0
    for fname in ff_dir.iterdir():
        if "following" not in fname.name.lower():
            continue
        data = load_json(fname)
        if not data:
            continue
        items = data if isinstance(data, list) else data.get("relationships_following", [])
        for item in items:
            username = None
            if isinstance(item, dict):
                sld = item.get("string_list_data", [])
                if sld:
                    username = extract_string_value(sld[0])
                if not username:
                    username = extract_string_value(item)
            elif isinstance(item, str):
                username = item
            if username:
                edges.add((my_user, sanitize(username)))
                count += 1
    print(f"  ✓ Siguiendo: {count} aristas")


def parse_comments(folder: Path, my_user: str, edges: set):
    """
    comments/post_comments_1.json y reels_comments.json
    Extrae: @yo → @autor_mencionado (si hay @handle en el texto)
    o bien: @yo → post (anónimo si no hay handle mencionado)
    """
    comments_dir = folder / "comments"
    if not comments_dir.exists():
        return
    count = 0
    mention_re = re.compile(r"@([\w.]+)")
    for fname in comments_dir.iterdir():
        if not fname.name.endswith(".json"):
            continue
        data = load_json(fname)
        if not data:
            continue
        # Puede ser lista o dict con "comments_media_comments" etc.
        items = data if isinstance(data, list) else []
        if not items:
            for key in data:
                if isinstance(data[key], list):
                    items.extend(data[key])
        for item in items:
            if not isinstance(item, dict):
                continue
            # Extraer texto del comentario
            text = ""
            sld = item.get("string_list_data", [])
            if sld and isinstance(sld, list):
                text = extract_string_value(sld[0]) or ""
            # Si el texto menciona @alguien, crear arista yo → alguien
            mentions = mention_re.findall(text)
            for m in mentions:
                if m.lower() != my_user:
                    edges.add((my_user, sanitize(m)))
                    count += 1
            # Si hay "title" (autor del post en algunos formatos)
            title = item.get("title", "")
            if title and isinstance(title, str):
                m2 = mention_re.findall(title)
                for m in m2:
                    if m.lower() != my_user:
                        edges.add((my_user, sanitize(m)))
                        count += 1
    print(f"  ✓ Comentarios (menciones): {count} aristas")


def parse_liked_posts(folder: Path, my_user: str, edges: set):
    """
    likes/liked_posts.json → @yo → @autor (si se puede extraer)
    Instagram no siempre incluye el autor, pero a veces está en el title o href.
    """
    likes_dir = folder / "likes"
    if not likes_dir.exists():
        return
    count = 0
    mention_re = re.compile(r"instagram\.com/([^/?#]+)")
    for fname in likes_dir.iterdir():
        if not fname.name.endswith(".json"):
            continue
        data = load_json(fname)
        if not data:
            continue
        items = data if isinstance(data, list) else []
        if not items:
            for key in data:
                if isinstance(data[key], list):
                    items.extend(data[key])
        for item in items:
            if not isinstance(item, dict):
                continue
            # Buscar en string_list_data el href
            sld = item.get("string_list_data", [])
            for entry in (sld if isinstance(sld, list) else []):
                href = entry.get("href", "") if isinstance(entry, dict) else ""
                m = mention_re.search(href)
                if m:
                    author = sanitize(m.group(1))
                    if author and author not in ("p", "reel", "stories", "tv") and author != my_user:
                        edges.add((my_user, author))
                        count += 1
                        break
    print(f"  ✓ Posts con 'me gusta': {count} aristas")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/instagram_to_csv.py /ruta/carpeta_instagram")
        print("     La carpeta es la que descomprimes del ZIP de Instagram.")
        sys.exit(1)

    folder = Path(sys.argv[1]).expanduser().resolve()
    if not folder.exists():
        print(f"Error: no existe la carpeta {folder}")
        sys.exit(1)

    print(f"\nLeyendo datos de Instagram en: {folder}")

    my_user = get_my_username(folder)
    if not my_user:
        my_user = input("No pude detectar tu username. Escríbelo (sin @): ").strip().lower()
    print(f"  Tu cuenta: @{my_user}\n")

    edges = set()
    parse_followers(folder, my_user, edges)
    parse_following(folder, my_user, edges)
    parse_comments(folder, my_user, edges)
    parse_liked_posts(folder, my_user, edges)

    if len(edges) < 3:
        print(f"\n⚠ Solo se encontraron {len(edges)} aristas. Verifica que la carpeta sea correcta.")
        print("  Debe contener subcarpetas como 'followers_and_following', 'comments', 'likes'.")
        sys.exit(1)

    out_path = Path("trama_instagram.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])
        for src, tgt in sorted(edges):
            writer.writerow([src, tgt])

    print(f"\n✅ CSV generado: {out_path.resolve()}")
    print(f"   {len(edges)} interacciones, {len(set(s for s,_ in edges) | set(t for _,t in edges))} cuentas únicas")
    print(f"\nAhora importa ese CSV en TRAMA con el botón 'Importar CSV'.")


if __name__ == "__main__":
    main()
