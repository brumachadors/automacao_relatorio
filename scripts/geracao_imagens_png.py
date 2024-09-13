################################## DEFINIÇÃO DOS PARÂMETROS DO CÓDIGO

# Escala (ex. 1: 2.000):                                           #
input_scale = 2000                                                

# Caminho do arquivo shapefile:                                    #
aoi_input = r'D:\D_Downloads\temp\shapes\area_change.shp'             

# Caminho da pasta contendo as imagens:                            #
raster_dir = r'D:\D_Downloads\temp\img_report_true'                         

# Definir pasta destino:                                           #
out_path = r'D:\D_Downloads\temp\resultados'                  

# Cor da borda do shape [R, G, B, Transparency]:                   #
rgb_code_outline = [255, 0, 0, 100]
rgb_code_fill = [255, 0, 0, 0]

# Espessura da linha:                                              #
border_size = 2

#####################################################################


################################################# INICIANDO AUTOMAÇÃO
####################################################    (não alterar)

import arcpy, os, sys
from arcpy import env
from arcpy.sa import *
import time

aprx = arcpy.mp.ArcGISProject('CURRENT')
createdMap = aprx.createMap("ASM_automacao_screenshot")
map = createdMap
map.openView()

aoi_filename_i = aoi_input.split("\\")[-1].split(".")[0]
aoi_filename = "fc_reference" 

gdb_name = f"tmp_geodatabase.gdb"
gdb_path = os.path.join(out_path, gdb_name)    
arcpy.management.CreateFileGDB(out_path, gdb_name)

aoi_gdb = f"{gdb_path}\\{aoi_filename}"
arcpy.conversion.FeatureClassToFeatureClass(aoi_input, gdb_path, aoi_filename)

for remove_all in map.listLayers():
    map.removeLayer(remove_all) 

raster_list = [raster for raster in os.listdir(raster_dir) if raster.endswith(".tif")]

input_raster_list = []

for raster in raster_list:
    raster_path = os.path.join(raster_dir, raster)
    input_raster_list.append(raster_path)
    
for raster in input_raster_list:
    arcpy.env.overwriteOutput = True
    insert_raster = map.addDataFromPath(raster)
    
    raster_name = raster.split("\\")[-1].split(".")[0]
    
    tmp_bbox_name = f"tmp_bbox_{raster_name}"
    tmp_bbox_out = os.path.join(gdb_path, tmp_bbox_name)
    arcpy.ddd.RasterDomain(raster, tmp_bbox_out, 'POLYGON')
    
    layers = map.listLayers()
    
    for layer in layers:
        if layer.name == tmp_bbox_name:
            map.removeLayer(layer)
    
    aoi = map.addDataFromPath(aoi_gdb)

    tmp_bbox_out = map.addDataFromPath(tmp_bbox_out)
    
    desc = arcpy.da.Describe(aoi_input)
    field_names = [field.name for field in desc["fields"]]
    print(field_names)

    if "ITERID" not in field_names:
        arcpy.management.AddField(aoi_input, "ITERID", "SHORT")

    with arcpy.da.UpdateCursor(aoi_input, ["FID", "ITERID"]) as cursor:
        for row in cursor:
            row[1] = row[0]
            cursor.updateRow(row)  
    
    layers = map.listLayers()

    for layer in layers:
        if layer.name == aoi_filename:
            aoi = layer
        elif layer.name == tmp_bbox_name:
            tmp_bbox = layer

    sym = aoi.symbology
    sym.updateRenderer('SimpleRenderer')
    sym.renderer.symbol.color = {'RGB' : rgb_code_fill}
    sym.renderer.symbol.outlineColor = {'RGB' : rgb_code_outline}
    sym.renderer.symbol.size = border_size
    aoi.symbology = sym

    sym = tmp_bbox.symbology
    sym.updateRenderer('SimpleRenderer')
    sym.renderer.symbol.color = {'RGB' : [255, 0, 0, 0]}
    sym.renderer.symbol.outlineColor = {'RGB' : [0, 0, 255, 100]}
    sym.renderer.symbol.size = 1.5
    tmp_bbox.symbology = sym

    with arcpy.da.SearchCursor(aoi, ['ITERID', 'Shape@']) as cursor:
        for row in cursor:
            oid = row[0]
            polygon = row[1]

            query = f"ITERID = {oid}"
            aoi.definitionQuery = query
            
            arcpy.management.SelectLayerByLocation(aoi, "INTERSECT", tmp_bbox)
            selection_result_count = arcpy.management.GetCount(aoi)
            
            if int(selection_result_count[0]) > 0: # True
                mv = aprx.activeView
                m = mv.map
                ext = mv.getLayerExtent(aoi, True, True)
                mv.camera.setExtent(ext)
                cam = mv.camera
                cam.scale = input_scale
                
                arcpy.management.SelectLayerByAttribute(aoi,"CLEAR_SELECTION")
                
                output_png = os.path.join(out_path, f'ITERID{oid}_{raster_name}.png')
                mv.exportToPNG(output_png, width=700, height=500, resolution=96)
                
    arcpy.management.Delete(tmp_bbox_out)
    for remove_all in map.listLayers():
        map.removeLayer(remove_all)

arcpy.conversion.FeatureClassToShapefile(aoi_gdb, out_path)
arcpy.management.Delete(gdb_path)

for tmp_map in aprx.listMaps():
    if tmp_map.name == "ASM_automacao_screenshot":
        aprx.deleteItem(tmp_map)