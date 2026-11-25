"""
Titulo: grafo
Nombre Completo: Luis Angel Pardave Garcia
Fecha de creación: 24/11/2026
Descripcion: Clase Grafo con algoritmo de Dijkstra. Se arma desde las
             listas de nodos y conexiones guardadas en la base de datos
             (ver Grafo.desde_listas y db_handler.cargar_grafo_db)
"""


from collections.abc import Iterable


# ===== CLASE NODO =====
class Nodo:
    def __init__(self, nombre: str) -> None:
        self.nombre: str = nombre
        self.vecinos: dict[str, float] = {}   # {vecino: peso}


# ===== CLASE GRAFO =====
class Grafo:
    def __init__(self, dirigido: bool = False) -> None:
        self.nodos: dict[str, Nodo] = {}
        # Si es dirigido, la conexion solo va de origen a destino
        self.dirigido: bool = dirigido

    # ----- Agregar un nodo (si no existe) -----
    def agregar_nodo(self, nombre: str) -> None:
        if nombre not in self.nodos:
            self.nodos[nombre] = Nodo(nombre)

    # ----- Agregar conexion entre dos nodos -----
    def agregar_conexion(self, origen: str, destino: str,
                         peso: float) -> None:
        self.agregar_nodo(origen)
        self.agregar_nodo(destino)
        self.nodos[origen].vecinos[destino] = peso
        if not self.dirigido:
            self.nodos[destino].vecinos[origen] = peso

    # ----- Armar el grafo desde listas de nodos y conexiones -----
    @classmethod
    def desde_listas(cls, nodos: Iterable[str],
                     conexiones: Iterable[dict[str, str | float]],
                     dirigido: bool = False) -> "Grafo":
        """Crea un Grafo con nodos sueltos y conexiones
        [{"origen", "destino", "peso"}, ...]."""
        grafo = cls(dirigido=dirigido)
        for nombre in nodos:
            grafo.agregar_nodo(nombre)
        for c in conexiones:
            grafo.agregar_conexion(c["origen"], c["destino"], c["peso"])
        return grafo

    # ----- Matriz de adyacencia -----
    def matriz_adyacencia(self, orden: Iterable[str] | None = None
                          ) -> tuple[list[str], list[list[float | None]]]:
        """Regresa (orden, matriz) donde matriz[i][j] es el peso de ir del
        nodo i al nodo j, o None si no hay conexion."""
        orden = list(orden or sorted(self.nodos))
        matriz = [[self.nodos[f].vecinos.get(c) for c in orden]
                  for f in orden]
        return orden, matriz

    # ----- Recorrido tramo por tramo de un camino -----
    def recorrido(self, camino: list[str]
                  ) -> list[tuple[str, str, float, float]]:
        """Regresa [(origen, siguiente, peso, acumulado), ...]."""
        tramos = []
        acumulado = 0
        for i in range(len(camino) - 1):
            origen = camino[i]
            siguiente = camino[i + 1]
            peso = self.nodos[origen].vecinos[siguiente]
            acumulado += peso
            tramos.append((origen, siguiente, peso, acumulado))
        return tramos

    # ----- Dijkstra: distancias minimas desde el nodo de inicio -----
    def calcular_distancias(self, inicio: str, destino: str | None = None
                            ) -> tuple[dict[str, float],
                                       dict[str, str | None]]:
        """Regresa (distancias, anteriores). Si no se da destino, calcula
        la distancia minima a todos los nodos."""
        distancias = {}
        anteriores = {}
        visitados = set()

        # Inicializar distancias en infinito
        for nombre in self.nodos:
            distancias[nombre] = float("inf")
            anteriores[nombre] = None

        distancias[inicio] = 0

        while len(visitados) < len(self.nodos):
            # Buscar el nodo no visitado con menor distancia
            nodo_actual = None
            menor_distancia = float("inf")

            for nombre in self.nodos:
                if nombre not in visitados:
                    if distancias[nombre] < menor_distancia:
                        menor_distancia = distancias[nombre]
                        nodo_actual = nombre

            if nodo_actual is None:
                break

            if nodo_actual == destino:
                break

            visitados.add(nodo_actual)
            nodo = self.nodos[nodo_actual]

            # Actualizar distancias de los vecinos
            for vecino, peso in nodo.vecinos.items():
                nueva_distancia = distancias[nodo_actual] + peso

                if nueva_distancia < distancias[vecino]:
                    distancias[vecino] = nueva_distancia
                    anteriores[vecino] = nodo_actual

        return distancias, anteriores

    # ----- Algoritmo de Dijkstra (camino mas corto) -----
    def dijkstra(self, inicio: str, destino: str) -> tuple[float, list[str]]:
        distancias, anteriores = self.calcular_distancias(inicio, destino)

        # Si el destino no es alcanzable no hay camino
        if distancias[destino] == float("inf"):
            return distancias[destino], []

        # Reconstruir el camino desde el destino hacia el inicio
        camino = []
        actual = destino

        while actual is not None:
            camino.append(actual)
            actual = anteriores[actual]

        camino.reverse()
        return distancias[destino], camino
