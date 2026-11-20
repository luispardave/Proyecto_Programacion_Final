"""
Titulo: db_handler
Nombre Completo: Luis Angel Pardave Garcia
Fecha de creación: 29/10/2026
Descripcion: Recaba y valida los inputs del usuario, maneja la lista de
             conexiones y lee/guarda el formato CSV (Nodos.csv)
"""


import csv
import io
import os
import sqlite3

# ===== CONFIGURACION DEL ARCHIVO CSV =====
RUTA_CSV = os.path.join(os.path.dirname(__file__), "Nodos.csv")
ENCABEZADOS = ["origen", "destino", "peso"]

# ===== CONFIGURACION DE LA BASE DE DATOS SQLITE =====
RUTA_DB = os.path.join(os.path.dirname(__file__), "grafo.db")

# Tabla nodos: cada nodo es una sola letra y no se repite.
# Tabla conexiones: cada conexion une dos nodos existentes, con peso > 0.
# ON DELETE CASCADE: si se borra un nodo, se borran sus conexiones.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS nodos (
    nombre  TEXT PRIMARY KEY CHECK (length(nombre) = 1)
);

CREATE TABLE IF NOT EXISTS conexiones (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    origen   TEXT NOT NULL REFERENCES nodos(nombre) ON DELETE CASCADE,
    destino  TEXT NOT NULL REFERENCES nodos(nombre) ON DELETE CASCADE,
    peso     REAL NOT NULL CHECK (peso > 0),
    UNIQUE (origen, destino),
    CHECK (origen <> destino)
);
"""


# ===== DB: ABRIR CONEXION =====
def conectar(ruta=None):
    """Abre la base de datos (la crea si no existe) con las llaves foraneas
    activadas. Las filas se pueden leer como diccionario: fila["peso"]."""
    conexion = sqlite3.connect(ruta or RUTA_DB)
    # SQLite trae las llaves foraneas apagadas por defecto
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.row_factory = sqlite3.Row
    return conexion


# ===== DB: CREAR TABLAS =====
def crear_tablas(ruta=None):
    """Crea las tablas nodos y conexiones si todavia no existen."""
    conexion = conectar(ruta)
    try:
        with conexion:   # hace commit al terminar (o rollback si falla)
            conexion.executescript(ESQUEMA)
    finally:
        conexion.close()


# ===== DB: GUARDAR EL GRAFO COMPLETO =====
def guardar_grafo_db(nodos, conexiones, ruta=None):
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
            conexion.executemany(
                "INSERT INTO nodos (nombre) VALUES (?)",
                [(nombre,) for nombre in sorted(todos)])
            conexion.executemany(
                "INSERT INTO conexiones (origen, destino, peso) "
                "VALUES (?, ?, ?)",
                [(c["origen"], c["destino"], c["peso"]) for c in conexiones])
    finally:
        conexion.close()


# ===== DB: CARGAR EL GRAFO COMPLETO =====
def cargar_grafo_db(ruta=None):
    """Lee la base de datos y regresa (nodos, conexiones) con el mismo
    formato que usaba el CSV. Si la base no existe la crea vacia."""
    crear_tablas(ruta)
    conexion = conectar(ruta)
    try:
        nodos = [fila["nombre"] for fila in conexion.execute(
            "SELECT nombre FROM nodos ORDER BY nombre")]
        conexiones = []
        # ORDER BY id respeta el orden en que se agregaron
        for fila in conexion.execute(
                "SELECT origen, destino, peso FROM conexiones ORDER BY id"):
            peso = fila["peso"]
            # SQLite guarda el peso como REAL: 4.0 se regresa como 4
            if float(peso).is_integer():
                peso = int(peso)
            conexiones.append({"origen": fila["origen"],
                               "destino": fila["destino"], "peso": peso})
    finally:
        conexion.close()
    return nodos, conexiones


# ===== DB: BORRAR EL REGISTRO DEL GRAFO =====
def limpiar_db(ruta=None):
    """Borra todos los nodos y conexiones (las tablas se conservan)."""
    try:
        guardar_grafo_db([], [], ruta)
        print("Registro de la base de datos borrado.")
    except sqlite3.Error as e:
        print(f"Error: No se pudo limpiar la base de datos: {e}")


# ===== DB: MIGRAR DATOS DE Nodos.csv A LA BASE =====
def migrar_csv_a_db(ruta_csv=None, ruta_db=None):
    """Pasa el grafo de Nodos.csv a la base de datos UNA sola vez: solo si
    la base esta vacia y el CSV tiene datos. Regresa True si migro.
    Puede lanzar ValueError/KeyError (CSV invalido) o sqlite3.Error."""
    nodos_db, _ = cargar_grafo_db(ruta_db)
    if nodos_db:
        return False   # la base ya tiene un grafo, no se sobrescribe
    nodos, conexiones = cargar_grafo_csv(ruta_csv)
    if not nodos:
        return False   # no hay CSV o esta vacio
    guardar_grafo_db(nodos, conexiones, ruta_db)
    return True


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
def validar_nodo(texto):
    """Regresa el nodo en mayuscula o lanza NodoInvalidoError."""
    texto = texto.strip().upper()
    if len(texto) != 1 or not texto.isalpha():
        raise NodoInvalidoError("El nodo debe ser una sola letra (ej: A).")
    return texto


# ===== VALIDACION: PESO INT O FLOAT =====
def validar_peso(texto):
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
def validar_conexion(origen, destino):
    """Lanza ConexionInvalidaError si el origen y el destino son iguales."""
    if origen == destino:
        raise ConexionInvalidaError(
            "El origen y el destino no pueden ser iguales.")


# ===== FORMATO: NUMEROS PARA MOSTRAR =====
def formato_numero(numero):
    """Muestra 4 en vez de 4.0 y el infinito como simbolo."""
    if numero == float("inf"):
        return "∞"
    if float(numero).is_integer():
        return str(int(numero))
    return str(round(numero, 2))


# ===== LISTA DE CONEXIONES: BUSCAR, AGREGAR Y ELIMINAR =====
def buscar_conexion(conexiones, origen, destino, dirigido=False):
    """Regresa la conexion entre origen y destino (o None). Si el grafo no
    es dirigido, A-B y B-A son la misma conexion."""
    for c in conexiones:
        if c["origen"] == origen and c["destino"] == destino:
            return c
        if not dirigido and c["origen"] == destino and c["destino"] == origen:
            return c
    return None


def agregar_conexion(conexiones, origen, destino, peso, dirigido=False):
    """Agrega la conexion o actualiza su peso si ya existe.
    Regresa True si es nueva y False si solo se actualizo."""
    validar_conexion(origen, destino)
    existente = buscar_conexion(conexiones, origen, destino, dirigido)
    if existente:
        existente["peso"] = peso
        return False
    conexiones.append({"origen": origen, "destino": destino, "peso": peso})
    return True


def quitar_nodo(conexiones, nombre):
    """Regresa las conexiones sin las que tocan al nodo."""
    return [c for c in conexiones if nombre not in (c["origen"], c["destino"])]


def etiqueta_conexion(conexion, dirigido=False):
    """Texto para mostrar una conexion, ej: 'A — B  (peso 4)'."""
    flecha = "→" if dirigido else "—"
    return (f"{conexion['origen']} {flecha} {conexion['destino']}  "
            f"(peso {formato_numero(conexion['peso'])})")


# ===== INPUT: PEDIR NODO =====
def pedir_nodo(mensaje):
    """Pide un nodo hasta que sea valido."""
    while True:
        try:
            return validar_nodo(input(mensaje))
        except NodoInvalidoError as e:
            print(f"Error: {e}")


# ===== INPUT: PEDIR PESO DE LA CONEXION =====
def pedir_peso():
    """Pide un peso hasta que sea valido."""
    while True:
        try:
            return validar_peso(input("Peso de la conexion: "))
        except PesoInvalidoError as e:
            print(f"Error: {e}")


# ===== INPUT: REGISTRO DE CONEXIONES DEL GRAFO =====
def pedir_conexiones():
    """Pide las conexiones del grafo y las regresa en una lista."""
    conexiones = []
    print("\n===== REGISTRO DE CONEXIONES =====")

    while True:
        origen = pedir_nodo("Nodo origen: ")
        destino = pedir_nodo("Nodo destino: ")

        try:
            validar_conexion(origen, destino)
        except ConexionInvalidaError as e:
            print(f"Error: {e}")
            continue

        peso = pedir_peso()
        conexiones.append({"origen": origen, "destino": destino, "peso": peso})

        otra = input("¿Agregar otra conexion? (s/n): ").strip().lower()
        if otra != "s":
            return conexiones


# ===== INPUT: NODO DE INICIO Y DESTINO =====
def pedir_ruta(nodos):
    """Pide el nodo de inicio y el de destino, validando que existan."""
    print(f"\nNodos disponibles: {', '.join(nodos)}")

    while True:
        inicio = pedir_nodo("Nodo de inicio: ")
        fin = pedir_nodo("Nodo de destino: ")
        if inicio in nodos and fin in nodos:
            return inicio, fin
        print("Error: Alguno de los nodos no existe en el grafo.")


# ===== CSV: GUARDAR CONEXIONES EN Nodos.csv =====
def guardar_csv(conexiones):
    """Guarda las conexiones en Nodos.csv (los errores se manejan en main)."""
    with open(RUTA_CSV, mode="w", newline="", encoding="utf-8") as file:
        escribir_csv(file, conexiones)
    print("Conexiones guardadas en Nodos.csv")


# ===== CSV: ESCRIBIR CONEXIONES EN UN ARCHIVO O TEXTO =====
def escribir_csv(destino, conexiones, nodos=()):
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


def conexiones_a_texto(conexiones, nodos=()):
    """Regresa las conexiones (y nodos sueltos) como texto CSV."""
    salida = io.StringIO()
    escribir_csv(salida, conexiones, nodos)
    return salida.getvalue()


# ===== CSV: PERSISTENCIA DEL GRAFO DE LA WEB APP =====
def guardar_grafo_csv(nodos, conexiones, ruta=None):
    """Guarda todo el grafo (conexiones y nodos sueltos) en Nodos.csv."""
    ruta = ruta or RUTA_CSV
    with open(ruta, mode="w", newline="", encoding="utf-8") as file:
        escribir_csv(file, conexiones, nodos)


def cargar_grafo_csv(ruta=None):
    """Lee Nodos.csv y regresa (nodos, conexiones). Si el archivo no
    existe regresa listas vacias; si tiene datos invalidos lanza
    ValueError o KeyError (ver leer_conexiones_texto)."""
    ruta = ruta or RUTA_CSV
    if not os.path.exists(ruta):
        return [], []
    with open(ruta, mode="r", encoding="utf-8-sig") as file:
        return leer_conexiones_texto(file.read())


# ===== CSV: LEER Y VALIDAR CONEXIONES DESDE TEXTO =====
def leer_conexiones_texto(texto):
    """Lee un CSV (origen,destino,peso) y regresa (nodos, conexiones).
    Una fila sin destino ni peso es un nodo sin conexiones.
    Lanza KeyError si falta una columna o ValueError si una fila es
    invalida."""
    nodos = set()
    conexiones = []
    reader = csv.DictReader(io.StringIO(texto))
    for num, row in enumerate(reader, start=2):
        try:
            origen = validar_nodo(row["origen"] or "")
            if not (row["destino"] or "").strip() and \
                    not (row["peso"] or "").strip():
                nodos.add(origen)
                continue
            destino = validar_nodo(row["destino"])
            validar_conexion(origen, destino)
            peso = validar_peso(row["peso"])
        except (NodoInvalidoError, PesoInvalidoError,
                ConexionInvalidaError) as e:
            raise ValueError(f"fila {num}: {e}")
        nodos.update([origen, destino])
        conexiones.append({"origen": origen, "destino": destino,
                           "peso": peso})
    return sorted(nodos), conexiones


# ===== CSV: BORRAR REGISTRO DE Nodos.csv =====
def limpiar_csv():
    """Borra el registro de Nodos.csv dejando solo los encabezados."""
    try:
        with open(RUTA_CSV, mode="w", newline="", encoding="utf-8") as file:
            escribir_csv(file, [])
        print("Registro de Nodos.csv borrado.")
    except PermissionError:
        print("Error: No hay permisos para limpiar Nodos.csv")
