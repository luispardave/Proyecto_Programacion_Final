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
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE CHECK (length(nombre) = 1)
);

CREATE TABLE conexiones (
    id          INTEGER PRIMARY KEY,
    origen_id   INTEGER NOT NULL REFERENCES nodos(id) ON DELETE CASCADE,
    destino_id  INTEGER NOT NULL REFERENCES nodos(id) ON DELETE CASCADE,
    peso        REAL NOT NULL CHECK (peso > 0),
    UNIQUE (origen_id, destino_id),
    CHECK (origen_id <> destino_id)
);
```

| Regla | Qué evita |
|---|---|
| `PRIMARY KEY` (`id`) en ambas tablas | filas sin identificador único |
| `UNIQUE` en `nodos.nombre` | nodos repetidos |
| `REFERENCES nodos(id) ... ON DELETE CASCADE` | conexiones hacia nodos que no existen; al borrar un nodo se borran sus conexiones |
| `UNIQUE (origen_id, destino_id)` | la misma conexión dos veces |
| `CHECK` | pesos ≤ 0, nodos de más de una letra y conexiones de un nodo consigo mismo |

Al leer, las conexiones se unen con `nodos` (`JOIN`) para cambiar cada id
por el nombre del nodo. Si se abre una `grafo.db` con el esquema anterior
(nodos con `nombre` como PK), se convierte sola al esquema nuevo sin perder
datos.

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

## Tipos de datos (type hints)

Como buena práctica, todas las funciones indican el tipo de cada parámetro
y, después de `->`, el tipo de dato que regresan:

```python
def validar_peso(texto: str) -> int | float:
def cargar_grafo_db(ruta: str | None = None
                    ) -> tuple[list[str], list[Conexion]]:
def dijkstra(self, inicio: str, destino: str) -> tuple[float, list[str]]:
def main() -> None:          # None: la función no regresa nada
```

| Notación | Significado |
|---|---|
| `-> str` | regresa un texto |
| `-> int \| float` | regresa un número entero o decimal |
| `-> bool` | regresa `True` o `False` |
| `-> None` | no regresa nada |
| `str \| None` | un texto o `None` (valor opcional) |
| `list[str]` | lista de textos, ej. `["A", "B"]` |
| `dict[str, float]` | diccionario de texto a número, ej. `{"A": 4}` |
| `tuple[float, list[str]]` | par de valores, ej. `(9, ["A", "B", "E"])` |

Tipos propios del proyecto:

| Tipo | Dónde | Qué representa |
|---|---|---|
| `Conexion` | `db_handler.py` | una conexión: `{"origen": "A", "destino": "B", "peso": 4}` |
| `Arista`, `Resultado`, `Almacen` | `app.py` | conexión, resultado de Dijkstra y datos en memoria (`TypedDict`) |

Los tipos solo documentan el código: Python no los revisa al ejecutar, así
que no cambian el funcionamiento. La notación `X | Y` requiere Python 3.10
o superior (el proyecto usa 3.13.7).
