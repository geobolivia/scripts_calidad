Este repositorio contiene scripts de analisis de los datos y metadatos de GeoBolivia
* `report_metadata.py`: recupera los principales campos de un catalogo CSW, exportando en CSV y SHP (con las boundingboxes)

Instalación
===========

Para instalar, en Debian/Ubuntu
* recuperar el código

```
sudo aptitude update
sudo aptitude upgrade
sudo aptitude install git
git clone https://github.com/geobolivia/scripts_calidad.git
```
* instalar `python`, `easy_install` (con el paquete `python-setuptools`), `pip` y las librerías

```
sudo aptitude install python python-setuptools
sudo easy_install pip
sudo pip install python-dateutil
sudo aptitude install python-unidecode python-urllib3
sudo easy_install OWSLib
sudo aptitude install python-gdal
```

Uso
===

Para utilizar el script `report_metadata.py`, ir en la carpeta y lanzar

```
./report_metadata-py
```

Los resultados, por omisión, se encuentran en la carpeta `/tmp`.

Limitaciones
============

El script funciona con `OWSLib 0.5`. Parece que los cambios para la versión `0.6` manejar nuevas excepciones que no permiten obtener los resultados.
