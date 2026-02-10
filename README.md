# Energia Electrica Argentina - Dashboard CAMMESA

Este proyecto es un dashboard para analizar datos de generación eléctrica de Argentina provistos por CAMMESA (Informe Síntesis Mensual).

## Ver el dashboard localmente

Para evitar problemas de CORS/CDN, serví el sitio con un server local:

```bash
uv run -m http.server  
```

y luego abrí http://localhost:8000 en tu navegador. 

## Datos y transformación

El dashboard consume dos CSV en la raíz del repo:

- `oferta_grupos.csv`: generación mensual por máquina con campos estandarizados y datos de ubicación/grupo.
- `gruposec_adhoc.csv`: mapeo manual de `AGENTE` a `GRUPO ECONÓMICO`.

Los datos actualizados no se versionan en el repo. El script recibe la carpeta del informe mensual (o el `.zip` que la contiene) y se obtiene principalmente desde:

- `Base_Oferta_INFORME_MENSUAL/Generación Local Mensual.xlsx` (hoja `GENERACION`), que trae la generación neta mensual por máquina.
- `Base_Oferta_INFORME_MENSUAL/Potencia Instalada.xlsx` (hoja ` Pot. Instalada Autogeneradores`) para completar potencia instalada de autogeneradores.

La transformación que hacemos es:

- Tomar los campos de generación mensual y renombrarlos al esquema del dashboard.
- Incorporar `grupo_economico` desde `gruposec_adhoc.csv` (nuevos agentes se agregan como `Sin clasificar`).
- Completar geolocalización y metadatos (`lon`, `lat`, `geo_*`) usando el último `oferta_grupos.csv` como lookup por `maquina`.
- Completar `potencia_instalada` usando la base de autogeneradores cuando aplica.

### Actualización de datos

Se incluye un script en `scripts/update_csvs.py` que regenera ambos CSV a partir de [los datasets 
de informe mensual de Cammesa](https://cammesaweb.cammesa.com/informe-sintesis-mensual/)

```bash
uv run scripts/update_csvs.py <ruta-a-zip-o-carpeta>
```

Ejemplos:

- `uv run scripts/update_csvs.py BASE_INFORME_MENSUAL_2025-12.zip`
- `uv run scripts/update_csvs.py BASE_INFORME_MENSUAL_2025-12/`

El script lee las planillas del informe mensual, actualiza `oferta_grupos.csv` y sincroniza `gruposec_adhoc.csv` con nuevos agentes.
