#!/usr/bin/python
# -*- coding: utf-8 -*-

""" producir un reporte de los metadatos de un catalago CSW
args:
"""

import csv, codecs, cStringIO
from owslib.csw import CatalogueServiceWeb
import dateutil.parser
import math
import datetime
import osgeo.osr
from osgeo import ogr
from unidecode import unidecode

# Class for writing in CSV without encoding problems
# See: http://docs.python.org/2/library/csv.html#csv-examples
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def getcswrecords(csw, maxiter=None, maxrecordsinit=None, factormult=None):
    if maxiter is None:
        maxiter=100
    if maxrecordsinit is None:
        maxrecordsinit=5
    if factormult is None:
        factormult=2
    # Logica para recuperar todos los metadatos
    cswrecords=dict()
    startposition=0
    maxrecords=maxrecordsinit
    more=True
    iter=0
    matches = None
    while iter < maxiter and more:
        iter = iter+1
        if matches and startposition + maxrecords > matches:
            maxrecords = matches - startposition

        print str(iter) + " - startposition: " + str(startposition) + " - maxrecords: " + str(maxrecords)
        try:
            csw.getrecords(outputschema='http://www.isotc211.org/2005/gmd',esn='full', startposition=startposition, maxrecords=maxrecords)
        except:
            print 'Error in getting csw records'

        matches=csw.results['matches']

        if len(csw.records)==maxrecords:
            cswrecords=dict(cswrecords.items() + csw.records.items())
            startposition+=len(csw.records)
            maxrecords=maxrecords*factormult
            if startposition >= matches:
                more=False
        else:
            # There is an error in the list of records
            if maxrecords > 1:
                # We divide the list of records
                maxrecords=1
            else:
                # We only asked for one record and it failed -> we bypass it
                startposition=startposition+1
                maxrecords=maxrecords*factormult

    print str(len(cswrecords)) + ' metadata correctly fetched'
    print str(matches - len(cswrecords)) + ' metadata with error'
    return cswrecords

# Search for all keywords and concatenate as CSV
def extractrecordkeywords(r):
    keywords=''
    for k1 in r.identification.keywords:
        for k2 in k1['keywords']:
            keywords+=k2+','
    if keywords[-1:]==',':
        keywords=keywords[:-1]
    return keywords

# Concatenate URL, nombre
def extractrecordonline(fields, online):
    wmsserver=''
    wmslayer=''
    urldl=''
    urllibre=''
    for o in online:
        if o.protocol == 'OGC:WMS-1.1.1-http-get-map':
            wmsserver=o.url
            wmslayer=o.name
        if o.protocol == 'WWW:DOWNLOAD-1.0-http--download':
            urldl=o.url
        if o.protocol == 'WWW:LINK-1.0-http--link':
            urllibre=o.url
            if o.name and o.url:
                urllibre+=" (" + o.name + ")"
    fields['wmsserver']=wmsserver
    fields['wmslayer']=wmslayer
    fields['urldl']=urldl
    fields['urllibre']=urllibre
    return fields

def extractrecordfirstcontact(fields, c):
    o=''
    if len(c) > 0:
        o=c[0].organization
    fields['contactorg']=o;
    return fields

def getrecordfields(r):
    date=r.identification.date[0].date
    fields = {
        'id': r.identifier,
        'title': r.identification.title,
        'year': str(dateutil.parser.parse(date).year) if date else '',
        'bb': r.identification.extent.boundingBox,
        'keywords': extractrecordkeywords(r)
        }
    fields = extractrecordonline(fields, r.distribution.online)
    fields = extractrecordfirstcontact(fields, r.identification.contact)
    return fields

def getrecordfieldsintable(r, fieldskeys):
    fields = getrecordfields(r)
    return [fields[k] for k in fieldskeys]

def prepareforcsv(cswrecords, fieldskeys, fieldsprops):
    matrix=[[fieldsprops[k]['name'] for k in fieldskeys]]
    for rec in cswrecords:
        r=cswrecords[rec]
        if r:
            matrix.append(getrecordfieldsintable(r, fieldskeys))

    # Transpose the matrix
    matrix=zip(*matrix)

    return matrix

# Export to a CSV file
def exporttocsv(cswrecords, fieldskeys, fieldsprops):
    matrix=prepareforcsv(cswrecords, fieldskeys, fieldsprops)
    filename = '/tmp/catalogo_geobolivia_02.csv'
    item_length = len(matrix[0])
    with open(filename, mode='wb') as test_file:
        file_writer = UnicodeWriter(test_file)
        for i in range(item_length):
            file_writer.writerow([x[i] if x[i] else '' for x in matrix])

# Output results to a SHP
def exporttoshp(cswrecords, fieldskeys, fieldsprops):
    spatialReference = osgeo.osr.SpatialReference()
    spatialReference.ImportFromProj4('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    driver = osgeo.ogr.GetDriverByName('ESRI Shapefile')
    name='/tmp/tmp' + str(datetime.datetime.now()) + '.shp'
    name='/tmp/catalogo_geobolivia_02.shp'
    shapeData = driver.CreateDataSource(name)

    layer = shapeData.CreateLayer('layer1', spatialReference, osgeo.ogr.wkbPolygon)
    layerDefinition = layer.GetLayerDefn()

    ### Shapefile fields
    for k in fieldskeys:
        # id
        fieldDefn = ogr.FieldDefn(k, ogr.OFTString)
        fieldDefn.SetWidth(fieldsprops[k]['width'])
        layer.CreateField(fieldDefn)

    for rec in cswrecords:
        r=cswrecords[rec]
        fields = getrecordfields(r)
        if 'bb' in fields and hasattr(fields['bb'], 'minx'):
            bb=fields['bb']
            # Create ring
            ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
            west=float(bb.minx)
            east=float(bb.maxx)
            south=float(bb.miny)
            north=float(bb.maxy)
            ring.AddPoint(west, south)
            ring.AddPoint(west, north)
            ring.AddPoint(east, north)
            ring.AddPoint(east, south)
            polygon = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
            polygon.AddGeometry(ring)

            featureIndex = 0
            feature = osgeo.ogr.Feature(layerDefinition)
            feature.SetGeometry(polygon)
            feature.SetFID(featureIndex)

            for k in fieldskeys:
                if fields[k]:
                    feature.SetField(k, unidecode(fields[k]))

            layer.CreateFeature(feature)

    shapeData.Destroy()

def setdefaultfieldsprops():
    fieldsprops={
        'id': {
            'name': 'id',
            'oft': ogr.OFTString,
            'width': 64,
            },
        'year': {
            'name': u'A\u00F1o',
            'oft': ogr.OFTInteger,
            'width': 4,
            },
        'contactorg': {
            'name': 'contacto',
            'oft': ogr.OFTString,
            'width': 128,
            },
        'title': {
            'name': 'titulo',
            'oft': ogr.OFTString,
            'width': 128,
            },
        'keywords': {
            'name': 'keywords',
            'oft': ogr.OFTString,
            'width': 128,
            },
        'wmsserver': {
            'name': 'wmsserver',
            'oft': ogr.OFTString,
            'width': 255,
            },
        'wmslayer': {
            'name': 'wmslayer',
            'oft': ogr.OFTString,
            'width': 255,
            },
        'urldl': {
            'name': 'urldl',
            'oft': ogr.OFTString,
            'width': 255,
            },
        'urllibre': {
            'name': 'urllibre',
            'oft': ogr.OFTString,
            'width': 255,
            }
        }
    return fieldsprops

def checkfields(fieldskeys=None):
    fieldspropsdefault=setdefaultfieldsprops()

    if fieldskeys is None:
        fieldskeys=fieldspropsdefault.keys()

    fieldsprops=dict()
    for k in fieldskeys:
        try:
            fieldsprops[k]=fieldspropsdefault[k]
        except Exception:
            print "Unknown key: " + k + " - discarded"
            pass
    fieldskeys=fieldsprops.keys()

    if len(fieldskeys) == 0:
        [fieldskeys, fieldsprops] = checkfields(fieldspropsdefault.keys())

    return [fieldskeys, fieldsprops]

# Connect to the catalog
csw = CatalogueServiceWeb('http://geo.gob.bo/geonetwork/srv/es/csw')

# Select fields to export
#fieldskeys=['id', 'title', 'urllibre', 'urldl']
#[fieldskeys, fieldsprops] = checkfields(fieldskeys)
[fieldskeys, fieldsprops] = checkfields()

# Get the metadata
cswrecords = getcswrecords(csw, maxiter=200)

# Export to Shapefile
exporttoshp(cswrecords, fieldskeys, fieldsprops)

# Export to CSV
exporttocsv(cswrecords, fieldskeys, fieldsprops)
