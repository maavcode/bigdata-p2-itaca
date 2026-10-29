"""Ingesta ITACA: lee las tablas de PostgreSQL y las guarda como JSON en data/raw.

Uso (desde la raíz del repositorio):
    .venv/bin/python ingesta/ingesta_itaca_bd.py

El NIA se anonimiza con un hash (alumnos.nia y calificaciones.alumno).
"""

import hashlib
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Tablas a ingestar y columnas que se guardan en el JSON
TABLAS = {
    "alumnos": [
        "nia", "sexo", "nacionalidad", "provincia", "municipio", "ensenanza",
        "curso", "grupo", "turno", "linea", "modalidad", "repite",
        "estado_matricula", "tipo_matricula", "fecha_matricula",
        "fecha_ingreso_centro", "anyo",
    ],
    "calificaciones": [
        "evaluacion", "alumno", "ensenanza", "curso", "contenido",
        "bloque_contenido", "nota_numerica", "tipo_nota", "anyo",
    ],
    "contenidos": ["codigo", "nombre_cas", "nombre_val", "ensenanza", "curso", "anyo"],
    "cursos": [
        "codigo", "nombre_cas", "nombre_val", "abreviatura", "ensenanza", "padre", "anyo",
    ],
}

# Columna que contiene el NIA en cada tabla
COLUMNA_NIA = {"alumnos": "nia", "calificaciones": "alumno"}

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingesta_itaca_bd")


def anonimizar_nia(nia):
    """Devuelve los 10 primeros caracteres del SHA-256 del NIA."""
    if nia is None:
        return None
    return hashlib.sha256(str(nia).encode("utf-8")).hexdigest()[:10]


def conectar():
    """Abre la conexión con las variables POSTGRES_* del .env."""
    load_dotenv(RAIZ / ".env")
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PW"),
    )


def extraer_tabla(conn, tabla, columnas, cache_hash):
    """Lee las columnas indicadas de una tabla y anonimiza el NIA si procede."""
    campos = ", ".join(f'"{c}"' for c in columnas)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f'SELECT {campos} FROM "{tabla}"')
        filas = [dict(f) for f in cur.fetchall()]

    columna = COLUMNA_NIA.get(tabla)
    if columna:
        for fila in filas:
            original = fila[columna]
            if original not in cache_hash:
                cache_hash[original] = anonimizar_nia(original)
            fila[columna] = cache_hash[original]
    return filas


def guardar_json(tabla, filas, fecha):
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    ruta = DIR_RAW / f"{tabla}_{fecha}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2, default=str)
    return ruta


def main():
    fecha = date.today().isoformat()
    conn = None
    cache_hash = {}  # un único hash por NIA original, compartido entre tablas
    try:
        conn = conectar()
        for tabla, columnas in TABLAS.items():
            filas = extraer_tabla(conn, tabla, columnas, cache_hash)
            ruta = guardar_json(tabla, filas, fecha)
            log.info("%s: %d filas -> %s", tabla, len(filas), ruta.relative_to(RAIZ))
    except psycopg2.Error as e:
        log.error("Error de PostgreSQL: %s", e)
        return 1
    except OSError as e:
        log.error("Error escribiendo en disco: %s", e)
        return 1
    finally:
        if conn is not None:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
