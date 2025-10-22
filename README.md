# Rick and Morty — Análisis de personajes, episodios y localizaciones

**Tipo:** Proyecto exploratorio (EDA) en Jupyter Notebook  
**Stack:** Python · requests · pandas · numpy · matplotlib · seaborn  
**Fuente de datos:** [Rick and Morty API](https://rickandmortyapi.com/)

## 🎯 Objetivo

Explorar el universo de **Rick y Morty** con la API pública, construir diccionarios auxiliares para resolver referencias (URLs → entidades), **convertir endpoints en datos “reales”** y analizar:

- Distribución de **especies** y **estado** (Vivo/Muerto/Desconocido)  
- **Localizaciones** más peligrosas  
- **Apariciones por episodio** y **temporadas con más muertes**  
- Diferencias entre episodios **canónicos** (con *Evil Rick* o *Evil Morty*) y el resto  
- Mortalidad de **Ricks y Mortys** frente a los **humanos**

## 🗂 Estructura del proyecto

- `notebooks/`  
  └ `rick_and_morty.ipynb` — notebook principal  
- `data/`  
  └ `transformed_data.pkl` — **caché binaria** para evitar repetir llamadas a la API  
- `README.md` — este archivo

> La caché guarda los 3 *DataFrames* transformados: `df_characters`, `df_locations`, `df_episodes`.

## 📦 Requisitos

```bash
python >= 3.10
pip install pandas numpy requests matplotlib seaborn
```

## ▶️ Cómo ejecutar

1) Clona el repo y crea un entorno (opcional):  
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scriptsctivate
pip install -r requirements.txt  # o instala a mano las libs listadas arriba
```

2) Abre el notebook:  
```bash
jupyter lab  # o jupyter notebook
```

3) Ejecuta todas las celdas.  
- Si **existe** `data/transformed_data.pkl`, el notebook **cargará** los datos transformados.  
- Si **no existe**, **descargará** todas las páginas de la API, transformará los datos y **guardará la caché**.

## 🔗 Pipeline de datos

### 1) Diccionarios auxiliares (para resolver referencias)
- `dict_character`: clave = **URL de personaje**, valor = **JSON de personaje**  
- `dict_character_id`: clave = **id de personaje**, valor = **JSON de personaje**  
- `dict_episodes_id`: clave = **id de episodio**, valor = **JSON de episodio**  
- `dict_locations_id`: clave = **id de localización**, valor = **JSON de localización**

> Estos diccionarios permiten **traducir listas de URLs** (que vienen en las columnas) a **datos legibles** (nombres, ids, etc.) con acceso O(1).

### 2) Descarga de datos (API paginada)

Dos estrategias:

- **Lenta, por id**: `get_all_slow(data_base_name)`  
- **Rápida, por páginas**: `get_all_fast(data_base_name)` y `complete_data(dataframe_name)`  
  - Paginación estimada: `character=42`, `episode=3`, `location=7`

### 3) Transformaciones principales

- **Characters** (`df_characters`):
  - `origin` y `location` → **`*_nueva`** con el nombre (via `fix_col_dict`)  
  - Drop: `image`, `episode`, `url`, `created`

- **Locations** (`df_locations`):
  - `residents` (URLs) → **nombres** (via `fix_url`)  
  - `nº_residents` = longitud de `residents`  
  - Drop: `url`, `created`

- **Episodes** (`df_episodes`):
  - `characters` (URLs) → **nombres** (via `fix_url`)  
  - `air_date` → `datetime`  
  - `season`, `episode_season` extraídos de `episode` (p.ej. `S03E01`)  
  - Reordenado de columnas: `['id','name','air_date','season','episode_season','characters']`

### 4) Caché local (para evitar re-descargar)

- Archivo: `data/transformed_data.pkl`  
- Funciones: `save_file()`, `file_exists()`, `load_file()`  
- Flujo:
  - `if file_exists(): load_file()`
  - `else: fetch_data() -> transform_data() -> save_file()`

## 🧪 Funciones clave (resumen)

- **Descarga**: `get_all_fast`, `complete_data`, `fetch_data`  
- **Transformación**: `transform_to_json`, `fix_col_dict`, `fix_url`, `trasnform_data` *(typo en nombre original conservado si ya está en el notebook)*  
- **Caché**: `save_file`, `load_file`, `file_exists`

## 📊 Análisis y visualizaciones

> Las visualizaciones usan **seaborn/matplotlib**. Algunas tienen **orden y etiquetas manuales** para mejorar la lectura.

- **Especies** de personajes (conteo total)  
- **Estado por especie** (Vivo/Muerto/Desconocido)  
- **Top orígenes** (planetas más frecuentes)  
- **Género** (global y por estado)  
- **Localizaciones más peligrosas** (top 10 por muertes)  
- **Muertes por especie** en las 5 localizaciones más peligrosas  
- **Apariciones por personaje** (top 10; variante sin la familia Smith)  
- **Episodios canónicos** (marcados si aparece *Evil Rick* o *Evil Morty*)  
- **Géneros con más apariciones por episodio** (con y sin estado)  
- **Temporadas más mortales** y **capítulos con más muertes** (incluye heatmap temporada/episodio)  
- **Muertes en capítulos canónicos** (comparativa)  
- **Caso de estudio**: capítulo más mortal `S03E01`  
- **Ricks & Mortys** vs **Humanos**: mortalidad relativa

> Nota técnica: para marcar episodios **canónicos** se filtra si alguno de los personajes del episodio contiene `Evil Rick` o `Evil Morty`.

## ⚠️ Limitaciones y notas

- La API devuelve **URLs** a entidades relacionadas; de ahí el uso de **diccionarios** para resolverlas rápidamente.  
- La API está **paginada** (máx. 20 resultados por página); por eso hay funciones para **descarga completa**.  
- Los gráficos dependen del estado real de la API en el momento de la consulta (pueden **variar** si la API cambia).  
- El *notebook* asume **conectividad a internet** en la primera ejecución (para poblar la caché).

## 💡 Ideas de mejora

- Exportar *datasets* transformados a **CSV/Parquet**.  
- Separar lógica en **módulos Python** (paquete `src/` con `data.py`, `transform.py`, `plots.py`).  
- Añadir **tests** para `transform_to_json`, `fix_url`, `fix_col_dict`.  
- Parametrizar rango de temporadas, filtros por especie/estado, etc.

## 📜 Licencia / uso de datos

Los datos se consumen desde **Rick and Morty API** (uso público con atribución).  
Este repositorio contiene solo código y transformaciones con fines educativos.

---

### Fragmento mínimo (instalación y carga de caché)

```python
import os, pickle, pandas as pd

FILE_PATH = "data/transformed_data.pkl"

def file_exists(path=FILE_PATH) -> bool:
    return os.path.exists(path)

def save_file(obj, path=FILE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load_file(path=FILE_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)

if file_exists():
    df_characters, df_locations, df_episodes = load_file()
else:
    # fetch_data() y trasnform_data() definidos en el notebook
    data_raw = fetch_data()
    df_characters, df_locations, df_episodes = trasnform_data(data_raw)
    save_file((df_characters, df_locations, df_episodes))
```
