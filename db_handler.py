"""
Titulo: db_handler
Nombre Completo: Luis Angel Pardave Garcia
Fecha de creación: 24/11/2026
Descripcion: Valida los datos del usuario, maneja la lista de conexiones,
             guarda/carga el grafo en la base de datos SQLite (grafo.db) y
             lo exporta a texto CSV
"""


import csv
import io
import os
import sqlite3
from collections.abc import Iterable
from typing import TextIO

# ===== CONFIGURACION DE LA EXPORTACION CSV =====
ENCABEZADOS: list[str] = ["origen", "destino", "peso"]

# Una conexion del grafo: {"origen": "A", "destino": "B", "peso": 4}
Conexion = dict[str, str | float]

# ===== CONFIGURACION DE LA BASE DE DATOS SQLITE =====
RUTA_DB: str = os.path.join(os.path.dirname(__file__), "grafo.db")

# Tabla nodos: cada nodo tiene un id (PK) y un nombre de una sola letra
#              que no se repite (UNIQUE).
# Tabla conexiones: cada conexion une dos nodos existentes por su id
#                   (llaves foraneas origen_id y destino_id), con peso > 0.
# ON DELETE CASCADE: si se borra un nodo, se borran sus conexiones.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS nodos (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE CHECK (length(nombre) = 1)
);

CREATE TABLE IF NOT EXISTS conexiones (
    id          INTEGER PRIMARY KEY,
    origen_id   INTEGER NOT NULL REFERENCES nodos(id) ON DELETE CASCADE,
    destino_id  INTEGER NOT NULL REFERENCES nodos(id) ON DELETE CASCADE,
    peso        REAL NOT NULL CHECK (peso > 0),
    UNIQUE (origen_id, destino_id),
    CHECK (origen_id <> destino_id)
);
"""


# ===== DB: ABRIR CONEXION =====
def conectar(ruta: str | None = None) -> sqlite3.Connection:
    """Abre la base de datos (la crea si no existe) con las llaves foraneas
    activadas. Las filas se pueden leer como diccionario: fila["peso"]."""
    conexion = sqlite3.connect(ruta or RUTA_DB)
    # SQLite trae las llaves foraneas apagadas por defecto
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.row_factory = sqlite3.Row
    return conexion


# ===== DB: CREAR TABLAS =====
def crear_tablas(ruta: str | None = None) -> None:
    """Crea las tablas nodos y conexiones si todavia no existen.
    Si encuentra el esquema viejo (nodos sin columna id) lo convierte al
    nuevo sin perder los datos guardados."""
    conexion = conectar(ruta)
    try:
        columnas = [fila["name"] for fila in
                    conexion.execute("PRAGMA table_info(nodos)")]
        if columnas and "id" not in columnas:
            _migrar_esquema_viejo(conexion)
        with conexion:   # hace commit al terminar (o rollback si falla)
            conexion.executescript(ESQUEMA)
    finally:
        conexion.close()


# ===== DB: MIGRAR DEL ESQUEMA VIEJO (PK = nombre) AL NUEVO (PK = id) =====
def _migrar_esquema_viejo(conexion: sqlite3.Connection) -> None:
    """Lee los datos del esquema viejo, borra las tablas viejas, crea las
    nuevas y vuelve a insertar los datos, todo en una sola transaccion."""
    nodos = [fila["nombre"] for fila in conexion.execute(
        "SELECT nombre FROM nodos ORDER BY nombre")]
    conexiones = [dict(fila) for fila in conexion.execute(
        "SELECT origen, destino, peso FROM conexiones ORDER BY id")]
    with conexion:
        # BEGIN explicito: sqlite3 no abre transaccion solo para DROP/CREATE
        conexion.execute("BEGIN")
        conexion.execute("DROP TABLE conexiones")
        conexion.execute("DROP TABLE nodos")
        for sentencia in ESQUEMA.split(";"):
            if sentencia.strip():
                conexion.execute(sentencia)
        _insertar_grafo(conexion, nodos, conexiones)


# ===== DB: INSERTAR NODOS Y CONEXIONES (USO INTERNO) =====
def _insertar_grafo(conexion: sqlite3.Connection, nodos: Iterable[str],
                    conexiones: list[Conexion]) -> None:
    """Inserta los nodos, obtiene el id de cada uno y con esos ids inserta
    las conexiones. No hace commit: lo hace quien la llama."""
    conexion.executemany(
        "INSERT INTO nodos (nombre) VALUES (?)",
        [(nombre,) for nombre in sorted(nodos)])
    # Diccionario nombre -> id para armar las llaves foraneas
    ids = {fila["nombre"]: fila["id"] for fila in
           conexion.execute("SELECT id, nombre FROM nodos")}
    conexion.executemany(
        "INSERT INTO conexiones (origen_id, destino_id, peso) "
        "VALUES (?, ?, ?)",
        [(ids[c["origen"]], ids[c["destino"]], c["peso"])
         for c in conexiones])


# ===== DB: GUARDAR EL GRAFO COMPLETO =====
def guardar_grafo_db(nodos: Iterable[str], conexiones: list[Conexion],
                     ruta: str | None = None) -> None:
    """Reemplaza el grafo guardado por el actual (nodos sueltos incluidos).
    Todo ocurre en una sola transaccion: si algo falla no se borra nada.
    Los errores (sqlite3.Error) se manejan en quien la llama."""
    crear_tablas(ruta)
    # Tambien se guardan los nodos que solo aparecen en las conexiones
    todos = set(nodos)
    for c in conexiones:
        todos.update([c["origen"], c["destino"]])

    conexion = conectar(ruta)
    try:
        with conexion:
            # Se borran primero las conexiones por la llave foranea
            conexion.execute("DELETE FROM conexiones")
            conexion.execute("DELETE FROM nodos")
            _insertar_grafo(conexion, todos, conexiones)
    finally:
        conexion.close()


# ===== DB: CARGAR EL GRAFO COMPLETO =====
def cargar_grafo_db(ruta: str | None = None
                    ) -> tuple[list[str], list[Conexion]]:
    """Lee la base de datos y regresa (nodos, conexiones) con el mismo
    formato que usaba el CSV. Si la base no existe la crea vacia."""
    crear_tablas(ruta)
    conexion = conectar(ruta)
    try:
        nodos = [fila["nombre"] for fila in conexion.execute(
            "SELECT nombre FROM nodos ORDER BY nombre")]
        conexiones = []
        # JOIN con nodos (dos veces) para cambiar cada id por su nombre.
        # ORDER BY c.id respeta el orden en que se agregaron.
        for fila in conexion.execute(
                "SELECT o.nombre AS origen, d.nombre AS destino, c.peso "
                "FROM conexiones AS c "
                "JOIN nodos AS o ON o.id = c.origen_id "
                "JOIN nodos AS d ON d.id = c.destino_id "
                "ORDER BY c.id"):
            peso = fila["peso"]
            # SQLite guarda el peso como REAL: 4.0 se regresa como 4
            if float(peso).is_integer():
                peso = int(peso)
            conexiones.append({"origen": fila["origen"],
                               "destino": fila["destino"], "peso": peso})
    finally:
        conexion.close()
    return nodos, conexiones


# ===== EXCEPCIONES PERSONALIZADAS =====
class NodoInvalidoError(Exception):
    """Se lanza cuando el nodo no es una sola letra."""
    pass


class PesoInvalidoError(Exception):
    """Se lanza cuando el peso no es un numero int o float mayor a 0."""
    pass


class ConexionInvalidaError(Exception):
    """Se lanza cuando el origen y el destino de una conexion son iguales."""
    pass


# ===== VALIDACION: NODO DE UNA SOLA LETRA =====
def validar_nodo(texto: str) -> str:
    """Regresa el nodo en mayuscula o lanza NodoInvalidoError."""
    texto = texto.strip().upper()
    if len(texto) != 1 or not texto.isalpha():
        raise NodoInvalidoError("El nodo debe ser una sola letra (ej: A).")
    return texto


# ===== VALIDACION: PESO INT O FLOAT =====
def validar_peso(texto: str) -> int | float:
    """Regresa el peso como int o float, o lanza PesoInvalidoError."""
    texto = texto.strip()
    # Solo digitos y como maximo un punto decimal
    if not texto.replace(".", "", 1).isdigit():
        raise PesoInvalidoError("El peso debe ser un número (ej: 5 o 2.5).")

    if "." in texto:
        peso = float(texto)
    else:
        peso = int(texto)

    if peso <= 0:
        raise PesoInvalidoError("El peso debe ser mayor a 0.")
    return peso


# ===== VALIDACION: CONEXION ENTRE DOS NODOS DISTINTOS =====
def validar_conexion(origen: str, destino: str) -> None:
    """Lanza ConexionInvalidaError si el origen y el destino son iguales."""
    if origen == destino:
        raise ConexionInvalidaError(
            "El origen y el destino no pueden ser iguales.")


# ===== FORMATO: NUMEROS PARA MOSTRAR =====
def formato_numero(numero: float) -> str:
    """Muestra 4 en vez de 4.0 y el infinito como simbolo."""
    if numero == float("inf"):
        return "∞"
    if float(numero).is_integer():
        return str(int(numero))
    return str(round(numero, 2))


# ===== LISTA DE CONEXIONES: BUSCAR, AGREGAR Y ELIMINAR =====
def buscar_conexion(conexiones: list[Conexion], origen: str, destino: str,
                    dirigido: bool = False) -> Conexion | None:
    """Regresa la conexion entre origen y destino (o None). Si el grafo no
    es dirigido, A-B y B-A son la misma conexion."""
    for c in conexiones:
        if c["origen"] == origen and c["destino"] == destino:
            return c
        if not dirigido and c["origen"] == destino and c["destino"] == origen:
            return c
    return None


def agregar_conexion(conexiones: list[Conexion], origen: str, destino: str,
                     peso: float, dirigido: bool = False) -> bool:
    """Agrega la conexion o actualiza su peso si ya existe.
    Regresa True si es nueva y False si solo se actualizo."""
    validar_conexion(origen, destino)
    existente = buscar_conexion(conexiones, origen, destino, dirigido)
    if existente:
        existente["peso"] = peso
        return False
    conexiones.append({"origen": origen, "destino": destino, "peso": peso})
    return True


def quitar_nodo(conexiones: list[Conexion], nombre: str) -> list[Conexion]:
    """Regresa las conexiones sin las que tocan al nodo."""
    return [c for c in conexiones if nombre not in (c["origen"], c["destino"])]


def etiqueta_conexion(conexion: Conexion, dirigido: bool = False) -> str:
    """Texto para mostrar una conexion, ej: 'A — B  (peso 4)'."""
    flecha = "→" if dirigido else "—"
    return (f"{conexion['origen']} {flecha} {conexion['destino']}  "
            f"(peso {formato_numero(conexion['peso'])})")


# ===== CSV: ESCRIBIR CONEXIONES EN UN ARCHIVO O TEXTO (EXPORTAR) =====
def escribir_csv(destino: TextIO, conexiones: list[Conexion],
                 nodos: Iterable[str] = ()) -> None:
    """Escribe encabezados y conexiones en un archivo abierto o StringIO.
    Los nodos sin conexiones se guardan como 'A,,' (sin destino ni peso)."""
    writer = csv.DictWriter(destino, fieldnames=ENCABEZADOS)
    writer.writeheader()
    writer.writerows(conexiones)
    conectados = {c["origen"] for c in conexiones} | {
        c["destino"] for c in conexiones}
    for nombre in nodos:
        if nombre not in conectados:
            writer.writerow({"origen": nombre, "destino": "", "peso": ""})


def conexiones_a_texto(conexiones: list[Conexion],
                       nodos: Iterable[str] = ()) -> str:
    """Regresa las conexiones (y nodos sueltos) como texto CSV."""
    salida = io.StringIO()
    escribir_csv(salida, conexiones, nodos)
    return salida.getvalue()
