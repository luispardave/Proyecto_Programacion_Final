"""
Titulo: main
Nombre Completo: Luis Angel Pardave Garcia
Fecha de creación: 29/10/2026
Descripcion: Archivo principal. Abre la web app de Streamlit (app.py), que
             es la unica interfaz del programa.
             Ejecutar con:  py main.py
"""


import importlib.util
import os
import subprocess
import sys

# Ruta de app.py (junto a este archivo, sin importar desde donde se ejecute)
RUTA_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")


# ===== LANZAR LA WEB APP =====
def main():
    """Ejecuta 'streamlit run app.py' con el mismo Python que corre este
    archivo, asi funciona aunque 'streamlit' no este en el PATH."""
    if importlib.util.find_spec("streamlit") is None:
        print("Error: Streamlit no esta instalado. Instala las dependencias "
              "con:  py -m pip install -r requirements.txt")
        sys.exit(1)

    print("Abriendo Dijkstra-Visualizer en el navegador... "
          "(Ctrl + C para cerrar)")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", RUTA_APP],
                       check=False)
    # Ctrl + C detiene el servidor de Streamlit
    except KeyboardInterrupt:
        print("\nPrograma cerrado por el usuario.")


if __name__ == "__main__":
    main()
