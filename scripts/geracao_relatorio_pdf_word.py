################################## DEFINIÇÃO DOS PARÂMETROS DO CÓDIGO
                                           
# Arquivo shapefile (MESMO ARQUIVO SHAPEFILE GERADO NO ARCGIS):                 #
fc_reference = r"D:\D_Downloads\temp\resultados\fc_reference.shp" 

# Arquivo shapefile de municípios:                                              #
base_mun_uf_2022 = r"D:\D_Downloads\BR_Municipios_2022\BR_Municipios_2022.shp"  

# Diretório dos prints gerados                                                  #
image_dir = r"D:\D_Downloads\temp\resultados"

# Output/nome do arquivo PDF de saída                                           #
pdf_output_path = r"D:\D_Downloads\temp\resultados"
pdf_name = 'Relatório layout'                                                 

#################################################################################


################################################# INICIANDO AUTOMAÇÃO
####################################################    (não alterar)


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os
import geopandas as gpd
from PIL import Image
from pdf2docx import Converter

df = df = gpd.read_file(fc_reference)
df = df.to_crs(3857)
df['area_m2'] = df.geometry.area
df['area_km2'] = df.geometry.area / 1000000
df = df.to_crs(4674)
df['centroide'] = df.geometry.centroid

df_info = gpd.read_file(base_mun_uf_2022)

df = gpd.sjoin(df, df_info, how="left")

df_aggregated = df.groupby(df.index).agg({
    'ITERID': 'first',
    'NM_MUN': lambda x: ', '.join(x.dropna().unique()),
    'SIGLA_UF': lambda x: ', '.join(x.dropna().unique()),
    'geometry': 'first',
    'area_m2': 'first',
    'centroide': 'first'
}).reset_index(drop=True)

def draw_centered_text(c, text, page_width, y_offset, font_size=12):
    c.setFont("Helvetica", font_size)
    text_width = c.stringWidth(text, "Helvetica", font_size)
    x = (page_width - text_width) / 2
    c.drawString(x, y_offset, text)

def draw_text_above_image(c, text, x, y, image_width, font_size=10):
    c.setFont("Helvetica", font_size)
    text_width = c.stringWidth(text, "Helvetica", font_size)
    x_offset = (image_width - text_width) / 2
    c.drawString(x + x_offset, y, text)

def draw_info_below_images(c, info, x, y, image_width, page_width, font_size=10):
    c.setFont("Helvetica", font_size)
    text = f"Área: {info['Área']}, Centróide: {info['Centróide']} - {info['-']}"
    text_width = c.stringWidth(text, "Helvetica", font_size)
    x_offset = (page_width - text_width) / 2
    c.drawString(x_offset, y - 0.5 * inch, text)

def draw_image(c, image_path, x, y, width, height):
    im = Image.open(image_path)
    im = im.resize((int(width), int(height)))
    c.drawImage(image_path, x, y, width, height)

def extract_date_from_image(image_name):
    date_str = image_name.split('_')[-1].split('.png')[0]
    day = date_str[:2]
    month = date_str[2:4]
    year = date_str[4:]
    return f"{day}/{month}/{year}"

def create_pdf(images, output_pdf, df_aggregated, image_dir):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    page_width, page_height = letter

    margin = 1.5 * inch
    spacing = 0.5 * inch
    title_spacing = 0.5 * inch

    image_width = (page_width - (1.5 * margin) - spacing) / 2
    image_height = image_width

    x_offset = margin
    y_offset = page_height - margin - image_height

    for iter_id in sorted(set(img.split('_')[0] for img in images)):
        images_for_id = [img for img in images if img.startswith(iter_id)]

        if len(images_for_id) == 2:
            image_before = images_for_id[0]
            image_after = images_for_id[1]

            date_before = extract_date_from_image(image_before)
            date_after = extract_date_from_image(image_after)

            iter_id_int = int(iter_id.split('ITERID')[1])
            row = df_aggregated[df_aggregated['ITERID'] == iter_id_int].iloc[0]

            area = row['area_m2']
            centroid = row['centroide']
            mun = row['NM_MUN']
            uf = row['SIGLA_UF']

            info = {
                'Área': f"({area:.2f} m²)",
                'Centróide': f"({centroid.x:.6f}, {centroid.y:.6f})",
                '-': f"{mun} ({uf})"
            }

            title = f"{iter_id}"
            draw_centered_text(c, title, page_width, y_offset + image_height + title_spacing)
            
            draw_text_above_image(c, date_before, x_offset, y_offset + image_height + 12, image_width)
            draw_text_above_image(c, date_after, x_offset + image_width + spacing, y_offset + image_height + 12, image_width)

            draw_image(c, os.path.join(image_dir, image_before), x_offset, y_offset, image_width, image_height)
            draw_image(c, os.path.join(image_dir, image_after), x_offset + image_width + spacing, y_offset, image_width, image_height)

            draw_info_below_images(c, info, x_offset, y_offset - 0.1 * inch, image_width, page_width)

            y_offset -= image_height + spacing + title_spacing + 1 * inch

            if y_offset < margin:
                c.showPage()
                y_offset = page_height - margin - image_height

    c.save()

images = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]

output_pdf = f"{pdf_output_path}\\{pdf_name}.pdf"

create_pdf(images, output_pdf, df_aggregated, image_dir)

print(f"Arquivo PDF criado ({output_pdf})")

pdf_file = output_pdf

docx_file = f'{pdf_output_path}\\{pdf_name}.docx'

cv = Converter(pdf_file)

cv.convert(docx_file, start=0, end=None)

cv.close()

print(f'Arquivo WORD criado ({docx_file})')
