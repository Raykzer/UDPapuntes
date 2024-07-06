import os
from pdf2image import convert_from_path

def extract_manga_names(response):
    entries = response.split('Manga: ')[1:]
    mangas = []
    for entry in entries:
        name, promo = entry.split('|Promoción: ')
        mangas.append((name.strip(), promo.strip()))
    return mangas

def search_pdfs(manga_name, directory):
    for file in os.listdir(directory):
        if file.endswith('.pdf') and manga_name in file:
            return os.path.join(directory, file)
    return None

def convert_pdf_to_image(pdf_path, output_dir):
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    image_filename = os.path.basename(pdf_path) + '.png'
    image_path = os.path.join(output_dir, image_filename)
    images[0].save(image_path, 'PNG')
    return image_filename  # Return only the filename

def create_pdf_thumbnail(pdf_path, thumbnail_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # Cargar la primera página
    pix = page.get_pixmap()
    pix.save(thumbnail_path)