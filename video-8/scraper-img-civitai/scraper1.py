import requests
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import os
import re
from tqdm import tqdm

# Configuración
api_key = "token-de-tu-api-de-civitai-aqui"
headers = {"Authorization": f"Bearer {api_key}"}
tag_choose = input("Ingresa el tag de las imágenes: ")
initial_url = "https://civitai.com/api/v1/images?nsfw=false&tags=" + tag_choose
print(initial_url)

download_path = input("Ingresa la ruta donde quieres guardar las imágenes: ")
min_width = 100
min_height = 100
max_images = int(input("Ingresa el número máximo de imágenes a descargar: "))

# Extensiones de video a ignorar
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.gif'}

def is_video_url(url):
    """Verifica si la URL es un video basándose en la extensión"""
    url_lower = url.lower()
    return any(url_lower.endswith(ext) or ext in url_lower for ext in VIDEO_EXTENSIONS)

# Crear directorio si no existe
if not os.path.exists(download_path):
    os.makedirs(download_path)

# Regex para limpiar el texto del prompt
tag_re = re.compile(r'<.*?>')
downloaded_urls = set()

if os.path.exists("downloaded_urls.log"):
    with open("downloaded_urls.log", "r") as log_file:
        downloaded_urls = set(line.strip() for line in log_file.readlines())

with open("downloaded_urls.log", "a") as log_file:
    next_url = initial_url
    total_saved = 0
    videos_skipped = 0
    
    while next_url and total_saved < max_images:
        response = requests.get(next_url, headers=headers)
        response_data = response.json()
        
        if 'metadata' in response_data and 'nextPage' in response_data['metadata']:
            next_url = response_data['metadata']['nextPage']
        else:
            next_url = None
        
        # Filtrar imágenes (excluyendo videos)
        filtered_images = [
            image for image in response_data['items'] if 
            image['stats']['heartCount'] > 5 and 
            image['meta'] and 'prompt' in image['meta'] and
            image['width'] >= min_width and 
            image['height'] >= min_height and
            image['url'] not in downloaded_urls and
            not is_video_url(image['url'])  # Excluir videos
        ]
        
        # Contar videos saltados en este lote
        videos_in_batch = sum(1 for img in response_data['items'] if is_video_url(img['url']))
        videos_skipped += videos_in_batch
        
        for image in tqdm(filtered_images, desc="Guardando imágenes y metadatos", unit="imagen"):
            image_url = image['url']
            if image_url in downloaded_urls:
                continue
            
            try:
                image_response = requests.get(image_url)
                img = Image.open(BytesIO(image_response.content))
                
                # Convertir imagen a RGB si es necesario
                if img.mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                
                image_id = image['id']
                
                # Guardar imagen
                img_filename = os.path.join(download_path, f"{image_id}.jpg")
                img.save(img_filename)
                
                # Guardar meta.prompt como archivo de texto
                meta_prompt = tag_re.sub('', image['meta']['prompt'])
                meta_filename = os.path.join(download_path, f"{image_id}.txt")
                with open(meta_filename, "w", encoding='utf-8') as meta_file:
                    meta_file.write(meta_prompt)
                
                log_file.write(image_url + "\n")
                downloaded_urls.add(image_url)
                total_saved += 1
                
                if total_saved >= max_images:
                    break
                    
            except UnidentifiedImageError:
                print(f"\nNo se pudo identificar la imagen desde URL: {image_url}")
            except Exception as e:
                print(f"\nError descargando {image_url}: {e}")

print(f"\n{'='*50}")
print(f"Descarga completada!")
print(f"Imágenes guardadas: {total_saved}")
print(f"Videos ignorados: {videos_skipped}")
print(f"{'='*50}")