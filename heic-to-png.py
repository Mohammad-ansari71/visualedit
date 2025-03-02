import os
from PIL import Image
import pillow_heif
import multiprocessing

# Registra il decoder HEIF con eventuali opzioni (ad esempio per disabilitare le thumbnail se vuoi la massima risoluzione).
pillow_heif.register_heif_opener(disable_thumbnail=False)

def convert_heif_to_png(task):
    """
    Funzione che verrà eseguita in parallelo dai vari processi.
    task è una tupla (input_file, output_file).
    """
    input_file, output_file = task
    
    try:
        # Apre il file HEIC con Pillow (grazie a pillow-heif)
        img = Image.open(input_file)
        
        # Salva l'immagine come PNG
        img.save(output_file, "PNG")
        print(f"Conversione completata: {output_file}")
    except Exception as e:
        print(f"Errore durante la conversione di {input_file}: {e}")

def parallel_heic_conversion(input_dir, output_dir, num_workers=None):
    """
    Converte tutti i file .HEIC presenti in input_dir in PNG, salvandoli in output_dir,
    usando multiprocessing. num_workers indica il numero di processi (se None, usa tutti i core).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Crea la lista dei task
    tasks = []
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".heic"):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(
                output_dir,
                os.path.splitext(filename)[0] + ".png"
            )
            tasks.append((input_file, output_file))
    
    # Se non specificato, num_workers = numero di core disponibili
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
    
    # Crea un pool di processi e mappa la funzione su tutti i task
    with multiprocessing.Pool(num_workers) as pool:
        pool.map(convert_heif_to_png, tasks)

if __name__ == "__main__":
    input_folder = r"C:\Users\Utente\Desktop\P-ANNOTATION\IMAGES\TRAIN"
    output_folder = r"C:\Users\Utente\Desktop\P-ANNOTATION\IMAGES\TRAIN2"
    
    # Esempio: avvia tanti processi quanti core logici
    parallel_heic_conversion(input_folder, output_folder, num_workers=None)
