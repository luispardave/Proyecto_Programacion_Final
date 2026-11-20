# DIJKSTRA-VISUALIZER // Dijkstra Pathfinder

Web app en Streamlit para crear un grafo, verlo en un lienzo interactivo y
calcular el camino más corto con el algoritmo de Dijkstra. El grafo se guarda
en una base de datos **SQLite**.

## Cómo ejecutarla

```
py -m pip install -r requirements.txt
py main.py
```

`main.py` abre la app en el navegador (equivale a `streamlit run app.py`).
Para cerrarla presiona `Ctrl + C` en la terminal.

## Secciones

1. **Crear Grafo**: agrega nodos (una letra) y aristas con peso; los nodos se pueden arrastrar en el lienzo.
2. **Matriz/Tabla**: matriz de adyacencia, tabla de conexiones, eliminar elementos, guardar en la base de datos y exportar a CSV.
3. **Ejecutar Dijkstra**: elige inicio y destino; resalta el camino y muestra el recorrido tramo por tramo.
4. **Historial**: recorridos ejecutados en la sesión.
5. **Ajustes**: grafo dirigido / no dirigido, grafo de ejemplo y reinicio.

## Base de datos (SQLite)

El grafo se guarda en `grafo.db`, en la carpeta del proyecto. El archivo se
crea solo la primera vez que se abre la app y no se sube al repositorio
(está en `.gitignore`). `sqlite3` viene incluido en Python, así que no hay
que instalar nada extra.

- La base se lee **una sola vez** al iniciar la app.
- Los cambios se escriben solo al presionar **Guardar en la base de datos**,
  y se guarda todo en una sola transacción: si algo falla, el grafo anterior
  queda intacto.

### Esquema

```sql
CREATE TABLE nodos (
    nombre  TEXT PRIMARY KEY CHECK (length(nombre) = 1)
);

CREATE TABLE conexiones (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    origen   TEXT NOT NULL REFERENCES nodos(nombre) ON DELETE CASCADE,
    destino  TEXT NOT NULL REFERENCES nodos(nombre) ON DELETE CASCADE,
    peso     REAL NOT NULL CHECK (peso > 0),
    UNIQUE (origen, destino),
    CHECK (origen <> destino)
);
```

| Regla | Qué evita |
|---|---|
| `PRIMARY KEY` en `nodos` | nodos repetidos |
| `REFERENCES ... ON DELETE CASCADE` | conexiones hacia nodos que no existen; al borrar un nodo se borran sus conexiones |
| `UNIQUE (origen, destino)` | la misma conexión dos veces |
| `CHECK` | pesos ≤ 0, nodos de más de una letra y conexiones de un nodo consigo mismo |

## Exportar a CSV

El botón **Exportar** descarga el grafo **guardado en la base de datos** como
`grafo.csv` (los cambios sin guardar no se incluyen):

```
origen,destino,peso
A,B,4
B,C,2.5
Z,,
```

Una fila sin destino ni peso (`Z,,`) es un nodo sin conexiones.

## Estructura del proyecto

| Archivo | Contenido |
|---|---|
| `main.py` | Lanzador: abre la web app |
| `app.py` | Interfaz de Streamlit |
| `grafo.py` | Clases `Nodo` y `Grafo`, algoritmo de Dijkstra |
| `db_handler.py` | Validaciones, base de datos SQLite y exportación CSV |
| `estilos.py` | Temas de color, CSS y acomodo de los nodos en el lienzo |
