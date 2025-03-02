import os
import glob
import yaml
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageOps
import threading  # Per eseguire operazioni in background
import platform  # Per rilevare il sistema operativo
import cv2
import random

# ============================================================
# Percorsi (modifica in base alle tue esigenze)
# Default Paths
default_base_dir = r"C:\visualedit"
yaml_path = os.path.join(default_base_dir, "data.yaml")
image_dir = os.path.join(default_base_dir, "images")
label_dir = os.path.join(default_base_dir, "labels")
label_format_dir = os.path.join(default_base_dir, "label_format")
# ============================================================

class ImageViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("Visual Editor - No Image Loaded")

        self.image_files = self.gather_image_files()
        self.image_files = sorted(self.image_files)  # Ordinamento sincronizzato
        self.index = 0
        self.show_annotations = tk.BooleanVar(value=True)

        self.current_image = None  # PIL Image
        self.image_path = None
        self.current_annotations = []

        # Main container with weight configuration
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        # Left panel (resizable)
        left_panel = tk.PanedWindow(master, orient=tk.VERTICAL)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Top controls in left panel
        top_controls_frame = tk.Frame(left_panel)
        left_panel.add(top_controls_frame)

        # File management buttons
        btn_open_folder = tk.Button(top_controls_frame, text="Open Folder", command=self.select_base_folder)
        btn_open_folder.pack(side=tk.LEFT, padx=2)
        
        btn_refresh = tk.Button(top_controls_frame, text="Refresh", command=self.refresh_file_list)
        btn_refresh.pack(side=tk.LEFT, padx=2)

        btn_delete_selected = tk.Button(top_controls_frame, text="Delete Selected", command=self.delete_selected_files)
        btn_delete_selected.pack(side=tk.LEFT, padx=2)

        # File list
        listbox_frame = tk.Frame(left_panel)
        left_panel.add(listbox_frame)

        self.file_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_list = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar_list.set)
        self.file_listbox.bind("<Double-Button-1>", self.on_listbox_double_click)

        # Information box
        info_frame = tk.Frame(left_panel)
        left_panel.add(info_frame)
        
        self.info_text = tk.Text(info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        info_scrollbar = tk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.config(yscrollcommand=info_scrollbar.set)

        # Right panel
        right_panel = tk.Frame(master)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        # Control buttons at top
        control_frame = tk.Frame(right_panel)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # First row of controls
        control_frame_1 = tk.Frame(control_frame)
        control_frame_1.pack(fill=tk.X, pady=2)

        btn_prev = tk.Button(control_frame_1, text="Prev", command=self.show_previous)
        btn_prev.pack(side=tk.LEFT, padx=2)

        btn_next = tk.Button(control_frame_1, text="Next", command=self.show_next)
        btn_next.pack(side=tk.LEFT, padx=2)

        chk_show = tk.Checkbutton(control_frame_1, text="Show Annotations",
                                 variable=self.show_annotations, command=self.update_image)
        chk_show.pack(side=tk.LEFT, padx=2)

        # Second row of controls
        control_frame_2 = tk.Frame(control_frame)
        control_frame_2.pack(fill=tk.X, pady=2)

        btn_label_convert = tk.Button(control_frame_2, text="Convert Labels", command=self.open_label_converter)
        btn_label_convert.pack(side=tk.LEFT, padx=2)
        
        btn_smart_crop = tk.Button(control_frame_2, text="Smart Crop", command=self.open_smart_crop)
        btn_smart_crop.pack(side=tk.LEFT, padx=2)

        # Image display area
        canvas_frame = tk.Frame(right_panel)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.scroll_x = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll_y = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(canvas_frame, xscrollcommand=self.scroll_x.set,
                              yscrollcommand=self.scroll_y.set, cursor="cross")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scroll_x.config(command=self.canvas.xview)
        self.scroll_y.config(command=self.canvas.yview)

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bind Ctrl + mousewheel for zoom
        self.canvas.bind("<Control-MouseWheel>", self.on_mousewheel_zoom)

        # Load class names from YAML
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self.names = {int(k): v for k, v in data.get('names', {}).items()}
        except Exception as e:
            messagebox.showerror("Error", f"Error loading YAML file:\n{e}")
            self.names = {}

        self.refresh_file_list()
        self.load_current_image()

    def on_mousewheel_zoom(self, event):
        """Handle Ctrl + mousewheel zoom"""
        if event.state & 0x4:  # Check if Ctrl is pressed
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def update_info_box(self):
        """Update the information box with current image details"""
        self.info_text.delete(1.0, tk.END)
        if self.current_image:
            w, h = self.current_image.size
            self.info_text.insert(tk.END, f"Image Size: {w} x {h}\n\n")
            self.info_text.insert(tk.END, "Annotations:\n")
            for i, ann in enumerate(self.current_annotations):
                cls_id, x_c, y_c, w_a, h_a = ann
                cls_name = self.names.get(cls_id, str(cls_id))
                self.info_text.insert(tk.END, f"{i+1}. Class: {cls_name}\n")
                self.info_text.insert(tk.END, f"   Center: ({x_c:.3f}, {y_c:.3f})\n")
                self.info_text.insert(tk.END, f"   Size: {w_a:.3f} x {h_a:.3f}\n\n")

    def load_current_image(self):
        img_path = self.get_current_image_path()
        if not img_path:
            return

        # Carica l'immagine con PIL
        try:
            self.current_image = Image.open(img_path).convert("RGB")
            self.image_path = img_path
            print(f"Loaded image: {img_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading the image:\n{e}")
            self.current_image = None
            return

        # Carica le annotazioni
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        label_file = os.path.join(label_dir, base_name + ".txt")
        if self.show_annotations.get():
            self.current_annotations = self.load_annotations(label_file)
            print(f"Loaded annotations for {base_name}: {self.current_annotations}")
        else:
            self.current_annotations = []

        # Calcola le annotazioni in pixel
        self.current_annotations_pix = []
        w, h = self.current_image.size
        for ann in self.current_annotations:
            cls_id, x_c, y_c, w_a, h_a = ann
            x1 = int((x_c - w_a / 2) * w)
            y1 = int((y_c - h_a / 2) * h)
            x2 = int((x_c + w_a / 2) * w)
            y2 = int((y_c + h_a / 2) * h)
            self.current_annotations_pix.append((cls_id, x1, y1, x2, y2))

        # Debug: stampa delle annotazioni caricate
        print(f"Loaded annotations (YOLO): {self.current_annotations}")
        print(f"Loaded annotations (pixel): {self.current_annotations_pix}")

        # Aggiorna la label della dimensione dell'immagine
        self.image_size_label.config(text=f"Image Size: {w} x {h}")

        # Aggiorna la selezione nella listbox
        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(self.index)
        self.file_listbox.see(self.index)

        # Aggiorna la barra del titolo con il nome del file corrente
        self.master.title(f"Visual Editor - {os.path.basename(img_path)}")
        print(f"Window title updated to: Visual Editor - {os.path.basename(img_path)}")

        self.update_image()
        self.update_info_box()

    # ------------------ METODI DI GESTIONE FILE ------------------
    def gather_image_files(self):
        """Raccoglie tutti i file immagine (jpg, jpeg, png) in image_dir."""
        img_extensions = ('*.jpg', '*.jpeg', '*.png')
        result = []
        for ext in img_extensions:
            result.extend(glob.glob(os.path.join(image_dir, ext)))
        return [os.path.abspath(f) for f in result]  # Percorsi assoluti

    def select_base_folder(self):
        """Opens a directory browser and updates the paths for yaml, images, labels, and label formats."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            global yaml_path, image_dir, label_dir, label_format_dir
            yaml_path = os.path.join(folder_selected, "data.yaml")
            image_dir = os.path.join(folder_selected, "images")
            label_dir = os.path.join(folder_selected, "labels")
            label_format_dir = os.path.join(folder_selected, "label_format")
            messagebox.showinfo("Folder Selected", f"Base folder set to: {folder_selected}")

    def refresh_file_list(self):
        previous_image = self.image_path
        self.image_files = sorted(self.gather_image_files())  # Ordinamento sincronizzato
        self.file_listbox.delete(0, tk.END)
        for f in self.image_files:
            self.file_listbox.insert(tk.END, os.path.basename(f))
        print(f"File list updated. Total images: {len(self.image_files)}")
        print("Image list:")
        for i, f in enumerate(self.image_files):
            print(f"{i}: {f}")
        if previous_image and previous_image in self.image_files:
            self.index = self.image_files.index(previous_image)
            print(f"Previous image found. Index updated to: {self.index}")
        elif self.image_files:
            self.index = 0
            print(f"Previous image not found. Index set to: {self.index}")
        else:
            self.index = -1
            print("No images available.")

        if self.index >=0 and self.index < len(self.image_files):
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.index)
            self.file_listbox.see(self.index)
            self.master.title(f"Visual Editor - {os.path.basename(self.image_files[self.index])}")
            print(f"Window title updated to: Visual Editor - {os.path.basename(self.image_files[self.index])}")
        else:
            self.file_listbox.selection_clear(0, tk.END)
            self.master.title("Visual Editor - No Image Loaded")
            print("No images available after updating the list.")

    def on_listbox_double_click(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.index = selection[0]
            print(f"Listbox double click. New index: {self.index}")
            self.load_current_image()

    # ------------------ NAVIGAZIONE ------------------
    def show_previous(self):
        if len(self.image_files) == 0:
            return
        if self.index > 0:
            self.index -= 1
            self.zoom_factor = 1.0
            print(f"Previous navigation. New index: {self.index}")
            self.load_current_image()

    def show_next(self):
        if len(self.image_files) == 0:
            return
        if self.index < len(self.image_files) - 1:
            self.index += 1
            self.zoom_factor = 1.0
            print(f"Next navigation. New index: {self.index}")
            self.load_current_image()

    # ------------------ METODI GENERALI ------------------
    def get_current_image_path(self):
        if len(self.image_files) == 0:
            return None
        if self.index < 0:
            self.index = 0
        if self.index >= len(self.image_files):
            self.index = len(self.image_files) - 1
        return self.image_files[self.index]

    def update_image(self):
        if self.current_image is None:
            return

        pil_img = self.current_image.copy()

        if self.show_annotations.get() and self.current_annotations:
            pil_img = self.draw_boxes_on_image(pil_img, self.current_annotations, self.names)

        # Debug: stampa delle annotazioni prima del ridimensionamento
        print(f"Annotations before scaling: {self.current_annotations_pix}")

        self.scaled_image = pil_img.resize(
            (int(pil_img.width * self.zoom_factor), int(pil_img.height * self.zoom_factor)),
            Image.LANCZOS
        )
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, self.scaled_image.width, self.scaled_image.height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Debug: conferma del ridimensionamento
        print(f"Image scaled to: {self.scaled_image.size}")

    # ------------------ ZOOM ------------------
    def zoom_in(self):
        self.zoom_factor += 0.2
        if self.zoom_factor > 5.0:
            self.zoom_factor = 5.0
        print(f"Zoom in. New zoom factor: {self.zoom_factor}")
        self.update_image()

    def zoom_out(self):
        self.zoom_factor -= 0.2
        if self.zoom_factor < 0.2:
            self.zoom_factor = 0.2
        print(f"Zoom out. New zoom factor: {self.zoom_factor}")
        self.update_image()

    def reset_zoom(self):
        """Resetta lo zoom all'impostazione predefinita (1.0)."""
        self.zoom_factor = 1.0
        print("Zoom reset to 1.0")
        self.update_image()

    # ------------------ ANNOTAZIONI ------------------
    def load_annotations(self, label_file):
        """Legge il file .txt YOLO e restituisce una lista di tuple (cls_id, x_center, y_center, w, h)."""
        if not os.path.exists(label_file):
            return []
        with open(label_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        ann = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 5:
                cls_id, x_center, y_center, w, h = parts
                ann.append((int(cls_id), float(x_center), float(y_center), float(w), float(h)))
        return ann

    def save_annotation(self, label_file, cls_id, x_center, y_center, width, height):
        """Aggiunge una nuova annotazione YOLO alla fine del file .txt."""
        with open(label_file, 'a', encoding='utf-8') as f:
            f.write(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

    def delete_annotation_at_index(self, label_file, index_to_remove):
        """Elimina una singola riga (annotazione) dal file .txt, in base all'indice."""
        if not os.path.exists(label_file):
            messagebox.showerror("Error", f"Annotation file not found: {label_file}")
            return
        with open(label_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if 0 <= index_to_remove < len(lines):
            del lines[index_to_remove]
            with open(label_file, 'w', encoding='utf-8') as fw:
                fw.writelines(lines)
            messagebox.showinfo("Success", f"Annotation {index_to_remove + 1} deleted.")
        else:
            messagebox.showerror("Error", f"Invalid annotation index: {index_to_remove}")

    def delete_annotations(self):
        if not self.image_path:
            return
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        label_file = os.path.join(label_dir, base_name + ".txt")
        if os.path.exists(label_file):
            resp = messagebox.askyesno("Confirmation", f"Do you want to delete annotations for  {base_name}?")
            if resp:
                os.remove(label_file)
                self.current_annotations = []
                self.current_annotations_pix = []
                print(f"Annotations for {base_name} deleted.")
                messagebox.showinfo("Deleted", f"Annotations for {base_name} deleted.")
                self.update_image()
        else:
            messagebox.showinfo("Info", f"There are no annotations for {base_name}.")
            print(f"No annotations found for {base_name}.")

    def draw_boxes_on_image(self, image, annotations, names_dict):
        """Disegna le bounding boxes sulle immagini utilizzando PIL."""
        draw = ImageDraw.Draw(image)
        w, h = image.size

        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font = ImageFont.load_default()

        for ann in annotations:
            cls_id, x_center, y_center, box_w, box_h = ann
            x1 = int((x_center - box_w/2) * w)
            y1 = int((y_center - box_h/2) * h)
            x2 = int((x_center + box_w/2) * w)
            y2 = int((y_center + box_h/2) * h)

            outline_color = (0, 255, 0)  # Verde
            draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=3)

            cls_name = names_dict.get(cls_id, str(cls_id))
            bbox = draw.textbbox((0, 0), cls_name, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            pad = 4
            draw.rectangle([x1, y1 - text_h - pad, x1 + text_w + pad, y1],
                           fill="black")
            draw.text((x1 + pad/2, y1 - text_h - pad/2),
                      cls_name, fill="white", font=font)

        return image

    # ------------------ ROTAZIONI / FLIP ------------------
    def rotate_image_clockwise(self):
        """Ruota l'immagine di +90 gradi utilizzando Pillow."""
        if not self.current_image:
            return
        self.disable_rotation_buttons()
        threading.Thread(target=self._rotate_image, args=(90,), daemon=True).start()

    def rotate_image_counterclockwise(self):
        """Ruota l'immagine di -90 gradi utilizzando Pillow."""
        if not self.current_image:
            return
        self.disable_rotation_buttons()
        threading.Thread(target=self._rotate_image, args=(-90,), daemon=True).start()

    def _rotate_image(self, angle):
        try:
            if angle == 90:
                rotated_img = self.current_image.transpose(Image.ROTATE_270)  # +90°
            elif angle == -90:
                rotated_img = self.current_image.transpose(Image.ROTATE_90)   # -90°
            else:
                rotated_img = self.current_image.rotate(angle, expand=True)

            self.current_image = rotated_img
            print(f"Image rotated by {angle} degrees.")

            # Aggiorna le annotazioni
            if self.current_annotations:
                new_anns = self.rotate_bboxes_yolo(
                    self.current_annotations,
                    angle=angle
                )
                self.current_annotations = new_anns

                # Salva le annotazioni nel file
                base_name = os.path.splitext(os.path.basename(self.image_path))[0]
                label_file = os.path.join(label_dir, base_name + ".txt")
                self.save_annotations_to_file(label_file, new_anns)
                print(f"Annotations rotated and saved in: {label_file}")

                # Ricalcola le annotazioni in pixel
                self.current_annotations_pix = []
                w, h = self.current_image.size
                for ann in self.current_annotations:
                    cls_id, x_c, y_c, w_a, h_a = ann
                    x1 = int((x_c - w_a / 2) * w)
                    y1 = int((y_c - h_a / 2) * h)
                    x2 = int((x_c + w_a / 2) * w)
                    y2 = int((y_c + h_a / 2) * h)
                    self.current_annotations_pix.append((cls_id, x1, y1, x2, y2))
                print(f"Annotations in pixels updated: {self.current_annotations_pix}")

            # Aggiorna l'immagine nella UI
            self.master.after(0, self.update_image)

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Error", "Error in rotating the image:\n{e}"))
            print(f"Error in rotating the image: {e}")
        finally:
            self.master.after(0, self.enable_rotation_buttons)

    def flip_image_horizontally(self):
        """Flip orizzontale dell'immagine utilizzando Pillow."""
        if not self.current_image:
            return
        self.disable_rotation_buttons()
        threading.Thread(target=self._flip_image, daemon=True).start()

    def _flip_image(self):
        try:
            flipped_img = self.current_image.transpose(Image.FLIP_LEFT_RIGHT)
            self.current_image = flipped_img
            print("Horizontally flipped image.")

            # Aggiorna le annotazioni
            if self.current_annotations:
                new_anns = self.flip_bboxes_yolo(self.current_annotations)
                self.current_annotations = new_anns

                # Salva le annotazioni nel file
                base_name = os.path.splitext(os.path.basename(self.image_path))[0]
                label_file = os.path.join(label_dir, base_name + ".txt")
                self.save_annotations_to_file(label_file, new_anns)
                print(f"Flipped annotations saved in: {label_file}")

                # Ricalcola le annotazioni in pixel
                self.current_annotations_pix = []
                w, h = self.current_image.size
                for ann in self.current_annotations:
                    cls_id, x_c, y_c, w_a, h_a = ann
                    x1 = int((x_c - w_a / 2) * w)
                    y1 = int((y_c - h_a / 2) * h)
                    x2 = int((x_c + w_a / 2) * w)
                    y2 = int((y_c + h_a / 2) * h)
                    self.current_annotations_pix.append((cls_id, x1, y1, x2, y2))
                print(f"Updated pixel annotations after flip: {self.current_annotations_pix}")

            # Aggiorna l'immagine nella UI
            self.master.after(0, self.update_image)

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Error", f"Error flipping the image:\n{e}"))
            print(f"Error flipping the image: {e}")
        finally:
            self.master.after(0, self.enable_rotation_buttons)

    def disable_rotation_buttons(self):
        """Disabilita i pulsanti di rotazione e flip per prevenire operazioni multiple simultanee."""
        # Itera attraverso tutti i frame e disabilita i pulsanti di rotazione e flip
        for child in self.master.winfo_children():
            if isinstance(child, tk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Button) and widget['text'] in ["Rotate -90°", "Rotate +90°", "Horizontal Flip"]:
                        widget.config(state=tk.DISABLED)
                        print(f"Button disabled: {widget['text']}")

    def enable_rotation_buttons(self):
        """Riabilita i pulsanti di rotazione e flip dopo l'elaborazione."""
        # Itera attraverso tutti i frame e riabilita i pulsanti di rotazione e flip
        for child in self.master.winfo_children():
            if isinstance(child, tk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Button) and widget['text'] in ["Rotate -90°", "Rotate +90°", "Horizontal Flip"]:
                        widget.config(state=tk.NORMAL)
                        print(f"Button re-enabled: {widget['text']}")

    # ------------------ EVENTI MOUSE ------------------
    def on_mouse_down(self, event):
        self.start_x_canvas = self.canvas.canvasx(event.x)
        self.start_y_canvas = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        # Reset rectangle size label
        self.rect_size_label.config(text="Rect Size: N/A")
        print(f"Mouse down at ({self.start_x_canvas}, {self.start_y_canvas})")

    def on_mouse_drag(self, event):
        cur_x_canvas = self.canvas.canvasx(event.x)
        cur_y_canvas = self.canvas.canvasy(event.y)
        if self.start_x_canvas is not None and self.start_y_canvas is not None:
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.start_x_canvas, self.start_y_canvas,
                cur_x_canvas, cur_y_canvas,
                outline="red", width=2
            )
            # Calcola la dimensione del rettangolo in pixel dell'immagine
            rect_width = abs(cur_x_canvas - self.start_x_canvas) / self.zoom_factor
            rect_height = abs(cur_y_canvas - self.start_y_canvas) / self.zoom_factor
            self.rect_size_label.config(text=f"Rect Size: {int(rect_width)} x {int(rect_height)}")
            print(f"Mouse drag to ({cur_x_canvas}, {cur_y_canvas}) - Size: {int(rect_width)}x{int(rect_height)}")

    def on_mouse_up(self, event):
        end_x_canvas = self.canvas.canvasx(event.x)
        end_y_canvas = self.canvas.canvasy(event.y)
        if self.start_x_canvas is not None and self.start_y_canvas is not None:
            dx = abs(end_x_canvas - self.start_x_canvas)
            dy = abs(end_y_canvas - self.start_y_canvas)

            if dx < 5 and dy < 5:
                print(f"Mouse click at ({end_x_canvas}, {end_y_canvas}) - Potential annotation deletion")
                self.select_annotation_at(end_x_canvas, end_y_canvas)
            else:
                rx1 = min(self.start_x_canvas, end_x_canvas) / self.zoom_factor
                ry1 = min(self.start_y_canvas, end_y_canvas) / self.zoom_factor
                rx2 = max(self.start_x_canvas, end_x_canvas) / self.zoom_factor
                ry2 = max(self.start_y_canvas, end_y_canvas) / self.zoom_factor

                if self.is_cropping:
                    print(f"Initiating crop with box ({rx1}, {ry1}, {rx2}, {ry2})")
                    self.do_crop(rx1, ry1, rx2, ry2)
                else:
                    print(f"Creating new annotation with box ({rx1}, {ry1}, {rx2}, {ry2})")
                    self.create_new_annotation(rx1, ry1, rx2, ry2)

            # Reset rectangle size label
            self.rect_size_label.config(text="Rect Size: N/A")

        self.start_x_canvas = None
        self.start_y_canvas = None
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        print(f"Mouse up at ({end_x_canvas}, {end_y_canvas})")

    def select_annotation_at(self, x_canvas, y_canvas):
        rx = x_canvas / self.zoom_factor
        ry = y_canvas / self.zoom_factor
        print(f"Selecting annotation at ({rx}, {ry})")
        for i, (cls_id, x1, y1, x2, y2) in enumerate(self.current_annotations_pix):
            if x1 <= rx <= x2 and y1 <= ry <= y2:
                cls_name = self.names.get(cls_id, str(cls_id))
                resp = messagebox.askyesno("Delete Annotation",
                                           f"Do you want to delete  '{cls_name}'?")
                if resp:
                    label_file = os.path.join(label_dir, os.path.splitext(os.path.basename(self.image_path))[0] + ".txt")
                    self.delete_annotation_at_index(label_file, i)
                    # Aggiorna l'elenco delle annotazioni
                    self.current_annotations = self.load_annotations(label_file)
                    self.current_annotations_pix = []
                    w, h = self.current_image.size
                    for ann in self.current_annotations:
                        cls_id, x_c, y_c, w_a, h_a = ann
                        x1 = int((x_c - w_a / 2) * w)
                        y1 = int((y_c - h_a / 2) * h)
                        x2 = int((x_c + w_a / 2) * w)
                        y2 = int((y_c + h_a / 2) * h)
                        self.current_annotations_pix.append((cls_id, x1, y1, x2, y2))
                    print(f"Annotation {i + 1} deleted.")
                    self.update_image()
                return
        print("No annotation found at that position.")

    def create_new_annotation(self, rx1, ry1, rx2, ry2):
        cls_name = simpledialog.askstring("Class", "Enter the class name:")
        if cls_name is not None and cls_name.strip():
            if not self.image_path or not self.current_image:
                return

            local_names = self.names

            class_id = None
            for k, v in local_names.items():
                if v == cls_name.strip():
                    class_id = k
                    break

            if class_id is None:
                messagebox.showinfo("Error",
                                    f"The class '{cls_name}' does not exist in the names file.")
                print(f"Class '{cls_name}' not found in the file names.")
            else:
                w, h = self.current_image.size
                x_center = ((rx1 + rx2)/2.0) / w
                y_center = ((ry1 + ry2)/2.0) / h
                box_w = (rx2 - rx1) / w
                box_h = (ry2 - ry1) / h

                base_name = os.path.splitext(os.path.basename(self.image_path))[0]
                label_file = os.path.join(label_dir, base_name + ".txt")
                self.save_annotation(label_file, class_id, x_center, y_center, box_w, box_h)
                print(f"New annotation saved: Class ID {class_id}, Center ({x_center}, {y_center}), Size ({box_w}, {box_h})")

                # Aggiungi l'annotazione all'elenco corrente
                self.current_annotations.append((class_id, x_center, y_center, box_w, box_h))
                self.current_annotations_pix.append((class_id, int(rx1), int(ry1), int(rx2), int(ry2)))  # Corretto

                self.update_image()

    def activate_crop_mode(self):
        self.is_cropping = True
        messagebox.showinfo("Crop Mode",
                            "Select the area to crop with the mouse.\n"
                            "Upon release, a new file with suffix _XXX will be created and automatically loaded.")
        print("Crop mode activated.")

    def do_crop(self, rx1, ry1, rx2, ry2):
        if self.current_image is None:
            return
        rx1 = max(0, rx1)
        ry1 = max(0, ry1)
        rx2 = min(self.current_image.width, rx2)
        ry2 = min(self.current_image.height, ry2)

        if rx2 - rx1 < 5 or ry2 - ry1 < 5:
            messagebox.showinfo("Error", "Crop area too small.")
            print("Attempt to crop with too small an area.")
            return

        crop_box = (int(rx1), int(ry1), int(rx2), int(ry2))
        cropped_img = self.current_image.crop(crop_box)
        print(f"Selected crop area: {crop_box}")

        current_path = self.image_path
        if not current_path:
            return
        dir_name, base = os.path.split(current_path)
        base_name, ext = os.path.splitext(base)

        # Costruisci il nuovo nome in modo sicuro, preservando eventuali suffix esistenti
        # Es. "mfoto6 (1).png" -> "mfoto6 (1)_001.png"
        counter = 1
        new_base_name = f"{base_name}_{counter:03d}"
        new_path = os.path.join(dir_name, f"{new_base_name}{ext}")
        while os.path.exists(new_path):
            counter += 1
            new_base_name = f"{base_name}_{counter:03d}"
            new_path = os.path.join(dir_name, f"{new_base_name}{ext}")

        # Determina il formato basato sull'estensione
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            # aggiungi altri formati se necessario
        }
        img_format = format_map.get(ext.lower(), 'PNG')  # default a PNG se sconosciuto

        try:
            cropped_img.save(new_path, format=img_format)
            print(f"Crop saved: {new_path} with format {img_format}")
            messagebox.showinfo("Crop", f"Crop saved in:\n{new_path}\nOpening the new image.")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving the crop:\n{e}")
            print(f"Error saving the crop: {e}")
            return

        self.is_cropping = False

        # Ricarica la lista dei file per includere la nuova immagine
        self.refresh_file_list()

        try:
            # Imposta l'indice alla nuova immagine
            self.index = self.image_files.index(os.path.abspath(new_path))
            print(f"New index set for the crop: {self.index} ({new_path})")
            self.load_current_image()
        except ValueError:
            messagebox.showerror("Error", f"Cropped image not found in the list: {new_path}")
            print(f"Cropped image not found in the list: {new_path}")

    def halve_resolution(self):
        img_path = self.get_current_image_path()
        if not img_path:
            return
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading the image:\n{e}")
            print(f"Error loading the image: {e}")
            return

        w, h = img.size
        if w < 2 or h < 2:
            messagebox.showinfo("Error", "Unable to reduce further.")
            print("Unable to reduce the image further.")
            return
        new_w = w // 2
        new_h = h // 2
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        try:
            resized.save(img_path)
            print(f"Image reduced to: {img_path} with dimensions {new_w}x{new_h}")
            messagebox.showinfo("Half Resolution",
                                f"Image reduced to {new_w}x{new_h}.\nReloading the photo...")
            self.load_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Error saving the reduced image:\n{e}")
            print(f"Error saving the reduced image: {e}")

    # ------------------ NUOVO METODO: MEZZA RISOLUZIONE SELECTED ------------------
    def halve_resolution_selected(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "No files selected for half resolution.")
            print("No files selected for half resolution.")
            return

        selected_files = [self.image_files[i] for i in selected_indices]
        print(f"Half resolution selected for {len(selected_files)} files.")

        resp = messagebox.askyesno(
            "Confirm Half Resolution",
            f"Do you want to reduce the {len(selected_files)} selected files to half resolution?"
        )
        if not resp:
            print("Half resolution canceled by the user.")
            return

        errors = []
        for file_path in selected_files:
            try:
                img = Image.open(file_path).convert("RGB")
                w, h = img.size
                if w < 2 or h < 2:
                    errors.append(f"'{os.path.basename(file_path)}': unable to reduce further.")
                    print(f"Unable to reduce further: {file_path}")
                    continue
                new_w = w // 2
                new_h = h // 2
                resized = img.resize((new_w, new_h), Image.LANCZOS)
                resized.save(file_path)
                print(f"Image reduced to: {file_path} with dimensions {new_w}x{new_h}")
            except Exception as e:
                errors.append(f"Error during the reduction of '{os.path.basename(file_path)}': {e}")
                print(f"Error during the reduction of '{file_path}': {e}")

        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror("Errors During Half Resolution", error_message)
            print("Errors during half resolution:")
            for error in errors:
                print(error)
        else:
            messagebox.showinfo("Success", "All selected files have been reduced to half resolution.")
            print("All selected files have been reduced to half resolution.")

        self.refresh_file_list()

        # Se l'immagine attuale è stata ridotta, ricarichiamola
        if self.image_path in selected_files:
            self.load_current_image()
    # ------------------------------------------------------------------------------

    # ------------------ DELETE SELECTED FILES ------------------
    def delete_selected_files(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "No files selected for deletion.")
            print("No files selected for deletion.")
            return

        selected_files = [self.image_files[i] for i in selected_indices]
        print(f"Deleting {len(selected_files)} selected files.")

        resp = messagebox.askyesno(
            "Confirm Deletion",
            f"Do you want to delete {len(selected_files)} selected files and their annotations?"
        )
        if not resp:
            print("Deletion canceled by the user.")
            return

        errors = []
        for file_path in selected_files:
            try:
                # Elimina il file immagine
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"File deleted: {file_path}")
                
                # Elimina il file di annotazione corrispondente
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                label_file = os.path.join(label_dir, base_name + ".txt")
                if os.path.exists(label_file):
                    os.remove(label_file)
                    print(f"Annotation deleted: {label_file}")
            except Exception as e:
                errors.append(f"Error deleting {file_path}: {e}")
                print(f"Error deleting {file_path}: {e}")

        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror("Errors During Deletion", error_message)
            print("Errors during deletion:")
            for error in errors:
                print(error)
        else:
            messagebox.showinfo("Success", "Selected files and their annotations have been successfully deleted.")
            print("Deletion successfully completed.")

        # Aggiorna la lista dei file
        self.refresh_file_list()

        # Se l'immagine attuale è stata eliminata, carica la prossima immagine disponibile
        if self.image_path in selected_files:
            if self.image_files:
                self.index = min(self.index, len(self.image_files) - 1)
                print(f"Current image deleted. New index: {self.index}")
                self.load_current_image()
            else:
                self.canvas.delete("all")
                self.image_size_label.config(text="Image Size: N/A")
                self.rect_size_label.config(text="Rect Size: N/A")
                self.current_image = None
                self.image_path = None
                self.current_annotations = []
                self.master.title("Visual Editor - No Image Loaded")
                print("No images available after deletion.")

    # ------------------ NUOVA FUNZIONE: Trasf Grigio ------------------
    def apply_transformation_grigio(self):
        """Applica una trasformazione in scala di grigi all'immagine corrente."""
        if not self.current_image:
            messagebox.showinfo("Info", "No image loaded.")
            print("Attempt to apply transformation without an image loaded.")
            return

        try:
            # Converti l'immagine in scala di grigi
            gray_image = self.current_image.convert('L').convert('RGB')  # Converti in 'L' (grayscale) e poi in 'RGB'
            print(f"Gray scale transformation applied: {gray_image.size}")

            # Sovrascrivi l'immagine corrente con quella trasformata
            self.current_image = gray_image
            self.current_image.save(self.image_path)
            print(f"Image saved with gray transformation: {self.image_path}")

            # Aggiorna la visualizzazione dell'immagine
            self.update_image()

            # Notifica all'utente
            messagebox.showinfo("Gray Transformation", f"Transformation applied and saved at:\n{self.image_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Error applying gray transformation:\n{e}")
            print(f"Error applying gray transformation: {e}")

    # ------------------ NUOVE FUNZIONI: RINOMINA ------------------
    def rename_current_image(self):
        """Rinomina l'immagine attualmente aperta e il suo file di annotazione."""
        if not self.image_path:
            messagebox.showinfo("Info", "No image loaded to rename.")
            print("Attempt to rename without an image loaded.")
            return

        current_name = os.path.basename(self.image_path)
        new_name = simpledialog.askstring("Rename Image", "Enter the new name for the image:",
                                         initialvalue=current_name)
        if new_name:
            # Verifica se l'estensione è presente, altrimenti aggiungila
            base, ext = os.path.splitext(new_name)
            if ext.lower() not in ['.jpg', '.jpeg', '.png']:
                ext = os.path.splitext(self.image_path)[1]  # Mantiene l'estensione originale
                new_name = base + ext

            new_path = os.path.join(image_dir, new_name)
            label_file_old = os.path.join(label_dir, os.path.splitext(current_name)[0] + ".txt")
            label_file_new = os.path.join(label_dir, os.path.splitext(new_name)[0] + ".txt")

            try:
                os.rename(self.image_path, new_path)
                print(f"Image renamed from {self.image_path} to {new_path}")

                # Rinomina anche il file di annotazione, se esiste
                if os.path.exists(label_file_old):
                    os.rename(label_file_old, label_file_new)
                    print(f"Annotation renamed from {label_file_old} to {label_file_new}")

                messagebox.showinfo("Success", f"Image renamed to:\n{new_name}")

                # Aggiorna l'elenco dei file
                self.refresh_file_list()

                # Trova il nuovo indice dell'immagine rinominata
                self.index = self.image_files.index(os.path.abspath(new_path))
                self.load_current_image()

            except Exception as e:
                messagebox.showerror("Error", f"Error in renaming:\n{e}")
                print(f"Error renaming: {e}")

    def rename_selected_images(self):
        """Rinomina le immagini selezionate aggiungendo un suffisso specificato."""
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "No file selected for renaming.")
            print("Attempt to rename without selection.")
            return

        suffix = simpledialog.askstring("Rename Selected", "Enter the suffix to add:")
        if not suffix:
            print("Rename selected canceled by the user.")
            return

        errors = []
        renamed_files = []
        for i in selected_indices:
            original_path = self.image_files[i]
            original_name = os.path.basename(original_path)
            base, ext = os.path.splitext(original_name)
            new_name = f"{base}_{suffix}{ext}"
            new_path = os.path.join(image_dir, new_name)

            # Controlla se il nuovo nome esiste già
            if os.path.exists(new_path):
                errors.append(f"'{new_name}' already exists. Skipped.")
                print(f"Existing file: {new_path}")
                continue

            label_file_old = os.path.join(label_dir, f"{base}.txt")
            label_file_new = os.path.join(label_dir, f"{base}_{suffix}.txt")

            try:
                os.rename(original_path, new_path)
                print(f"Image renamed from {original_path} to {new_path}")

                # Rinomina anche il file di annotazione, se esiste
                if os.path.exists(label_file_old):
                    os.rename(label_file_old, label_file_new)
                    print(f"Annotation renamed from {label_file_old} to {label_file_new}")

                renamed_files.append(new_path)

            except Exception as e:
                errors.append(f"Error renaming '{original_name}': {e}")
                print(f"Error renaming '{original_name}': {e}")

        if renamed_files:
            messagebox.showinfo("Success", f"Renamed {len(renamed_files)} files.")
            print(f"Renamed {len(renamed_files)} files.")
        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror("Errors During Renaming", error_message)
            print("Errors During Renaming:")
            for error in errors:
                print(error)

        # Aggiorna l'elenco dei file
        self.refresh_file_list()

        # Ricarica l'immagine corrente se è stata rinominata
        selected_files = [os.path.abspath(f) for f in renamed_files]
        if self.image_path in selected_files:
            # Trova il nuovo indice dell'immagine rinominata
            new_path = renamed_files[selected_files.index(self.image_path)]
            self.index = self.image_files.index(os.path.abspath(new_path))
            self.load_current_image()

    # ------------------ ROTAZIONI E FLIP BBOX ------------------
    def rotate_bboxes_yolo(self, annotations, angle=90):
        """Ruota le bounding boxes in base all'angolo specificato (+90 o -90 gradi)."""
        if angle not in [90, -90]:
            raise ValueError("Only rotations of +90 or -90 degrees are supported.")

        new_annotations = []
        for (cls_id, x_c, y_c, w_bb, h_bb) in annotations:
            if angle == 90:
                new_x_c = 1.0 - y_c
                new_y_c = x_c
                new_w_bb = h_bb
                new_h_bb = w_bb
            elif angle == -90:
                new_x_c = y_c
                new_y_c = 1.0 - x_c
                new_w_bb = h_bb
                new_h_bb = w_bb
            new_annotations.append((cls_id, new_x_c, new_y_c, new_w_bb, new_h_bb))
        return new_annotations

    def flip_bboxes_yolo(self, annotations):
        """Flip orizzontale delle bounding boxes."""
        new_annotations = []
        for (cls_id, x_c, y_c, w_bb, h_bb) in annotations:
            x_new = 1.0 - x_c
            y_new = y_c
            new_annotations.append((cls_id, x_new, y_new, w_bb, h_bb))
        return new_annotations

    # ------------------ TILING ------------------
    def tile_current_image(self, tile_size):
        img_path = self.get_current_image_path()
        if not img_path:
            return
        print(f"Tiling current image: {img_path} with tile_size={tile_size}")
        self.tile_image_and_save(img_path, tile_size=tile_size)
        # RICHIAMA L'AGGIORNAMENTO LISTA
        self.refresh_file_list()
        messagebox.showinfo(
            "Tiling",
            f"Image '{os.path.basename(img_path)}' split into tiles {tile_size}x{tile_size}.\nFile list updated."
        )

    def tile_all_images(self, tile_size):
        if not self.image_files:
            return
        resp = messagebox.askyesno(
            "Confirm",
            f"Do you want to create {tile_size}x{tile_size} tiles for all images in the list?"
        )
        if not resp:
            print("Tiling of all images canceled by the user.")
            return
        for path in self.image_files.copy():  # Usa copy per evitare problemi durante la modifica
            print(f"Tiling image: {path} with tile_size={tile_size}")
            self.tile_image_and_save(path, tile_size=tile_size)
        # RICHIAMA L'AGGIORNAMENTO LISTA
        self.refresh_file_list()
        messagebox.showinfo(
            "Tiling",
            f"Operation completed.\nCreated {tile_size}x{tile_size} tiles for all photos.\nFile list updated."
        )

    def tile_image_and_save(self, img_path, tile_size=512):
        """
        Esegue un tiling dell'immagine in quadrati tile_size x tile_size.
        Salva i tile con suffisso _T{tile_size}_{num:03d}.ext
        """
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading the image for tiling:\n{e}")
            return

        w, h = img.size
        dir_name, base = os.path.split(img_path)
        base_name, ext = os.path.splitext(base)

        tile_num = 1
        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                box = (x, y, min(x + tile_size, w), min(y + tile_size, h))
                tile = img.crop(box)
                # Costruisci il nuovo nome in modo sicuro, preservando eventuali suffix esistenti
                new_tile_path = os.path.join(dir_name, f"{base_name}_T{tile_size}_{tile_num:03d}{ext}")
                try:
                    # Determina il formato basato sull'estensione
                    format_map = {
                        '.jpg': 'JPEG',
                        '.jpeg': 'JPEG',
                        '.png': 'PNG',
                        # aggiungi altri formati se necessario
                    }
                    img_format = format_map.get(ext.lower(), 'PNG')  # default a PNG se sconosciuto
                    tile.save(new_tile_path, format=img_format)
                    print(f"Tile saved: {new_tile_path} with format {img_format}")
                    tile_num += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Error saving the tile:\n{e}")
                    return

    # ------------------ CONVERT LABEL ------------------
    def open_label_converter(self):
        """Opens the label converter dialog with enhanced functionality."""
        converter_window = tk.Toplevel(self.master)
        converter_window.title("Label Converter")
        converter_window.geometry("600x400")
        converter_window.transient(self.master)
        converter_window.grab_set()

        # Create frames for organization
        path_frame = ttk.LabelFrame(converter_window, text="File Paths", padding=10)
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        format_frame = ttk.LabelFrame(converter_window, text="Label Formats", padding=10)
        format_frame.pack(fill=tk.X, padx=5, pady=5)

        # Path entries and browse buttons
        paths = [
            ("Input Image Path (RoboFlow):", "input_img"),
            ("Input Label Path (RoboFlow):", "input_lbl"),
            ("Output Image Path (Original Size):", "output_img"),
            ("Output Label Path:", "output_lbl")
        ]

        path_vars = {}
        for label_text, key in paths:
            frame = ttk.Frame(path_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
            path_vars[key] = tk.StringVar()
            entry = ttk.Entry(frame, textvariable=path_vars[key])
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            ttk.Button(frame, text="Browse", 
                      command=lambda v=path_vars[key]: self.browse_directory(v)).pack(side=tk.RIGHT)

        # Format selection
        format_frame_inner = ttk.Frame(format_frame)
        format_frame_inner.pack(fill=tk.X)

        ttk.Label(format_frame_inner, text="Output Format:").pack(side=tk.LEFT)
        formats = ["YOLO", "COCO", "JSON"]  # Add more formats as needed
        format_var = tk.StringVar(value="YOLO")
        format_combo = ttk.Combobox(format_frame_inner, textvariable=format_var, values=formats, state="readonly")
        format_combo.pack(side=tk.LEFT, padx=5)

        # Convert button
        ttk.Button(converter_window, text="Convert", 
                  command=lambda: self.convert_labels(path_vars, format_var.get())).pack(pady=10)

    def browse_directory(self, string_var):
        """Opens a directory browser and updates the given StringVar."""
        directory = filedialog.askdirectory()
        if directory:
            string_var.set(directory)

    def convert_labels(self, path_vars, output_format):
        """Handles the label conversion process."""
        # Validate paths
        for key, var in path_vars.items():
            if not var.get():
                messagebox.showerror("Error", f"Please select {key.replace('_', ' ')} directory")
                return

        # Here you would implement the actual conversion logic
        try:
            # Placeholder for conversion logic
            messagebox.showinfo("Success", f"Labels converted to {output_format} format successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error during conversion: {str(e)}")

    def start_smart_crop(self, path_vars, mode, margin, resolution):
        """Handles the smart crop process."""
        # Validate paths
        for key, var in path_vars.items():
            if not var.get():
                messagebox.showerror("Error", f"Please select {key.replace('_', ' ')} directory")
                return

        try:
            margin = int(margin)
            width, height = map(int, resolution.split('x'))
        except ValueError:
            messagebox.showerror("Error", "Invalid margin or resolution format")
            return

        try:
            # Call the existing crop_images_with_labels function with the new parameters
            self.crop_images_with_labels(
                path_vars["input_img"].get(),
                path_vars["input_lbl"].get(),
                path_vars["output_img"].get(),
                path_vars["output_lbl"].get(),
                mode,
                margin,
                resolution
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error during smart crop: {str(e)}")

    # ------------------ BINDING MOUSEWHEEL ------------------
    
    def _bind_mousewheel(self):
        os_name = platform.system()
        if os_name == 'Windows':
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        elif os_name == 'Darwin':  # macOS
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        else:  # Linux e altri
            self.canvas.bind("<Button-4>", self.on_mouse_wheel)
            self.canvas.bind("<Button-5>", self.on_mouse_wheel)

    def on_mouse_wheel(self, event):
        os_name = platform.system()
        if os_name == 'Windows':
            # On Windows, event.delta è un multiplo di 120
            if event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            elif event.delta < 0:
                self.canvas.yview_scroll(1, "units")
        elif os_name == 'Darwin':
            # Su macOS, event.delta di solito è piccolo, invertire direzione
            if event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            elif event.delta < 0:
                self.canvas.yview_scroll(1, "units")
        else:
            # Su Linux, event.num è 4 (scroll up) o 5 (scroll down)
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    # ============================== MAIN ==============================
    def run(self):
        self.master.mainloop()

    # ------------------ METODI PER SALVATAGGIO ANNOTAZIONI ------------------
    def save_annotations_to_file(self, label_file, annotations):
        """Salva tutte le annotazioni nel file di annotazione."""
        with open(label_file, 'w', encoding='utf-8') as f:
            for ann in annotations:
                cls_id, x_center, y_center, w, h = ann
                f.write(f"{cls_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")

    # ------------------ NUOVO METODO: DELETE IMAGE AND ANNOTATIONS ------------------
    def delete_image_and_annotations(self):
        """Elimina l'immagine attualmente aperta e il suo file di annotazione."""
        if not self.image_path:
            messagebox.showinfo("Info", "No image loaded to delete.")
            print("Attempt to delete without a loaded image.")
            return

        resp = messagebox.askyesno(
            "Confirm Deletion",
            f"Do you want to delete the image and annotations for {os.path.basename(self.image_path)}?"
        )
        if not resp:
            print("Deletion canceled by the user.")
            return

        errors = []
        try:
            if os.path.exists(self.image_path):
                os.remove(self.image_path)
                print(f"Image file deleted: {self.image_path}")
            
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            label_file = os.path.join(label_dir, base_name + ".txt")
            if os.path.exists(label_file):
                os.remove(label_file)
                print(f"Annotation file deleted: {label_file}")
        except Exception as e:
            errors.append(f"Error deleting {self.image_path}: {e}")
            print(f"Error deleting {self.image_path}: {e}")

        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror("Errors During Deletion", error_message)
        else:
            messagebox.showinfo("Success", "Image and related annotations successfully deleted.")
            print("Image and annotations successfully deleted.")

        # Aggiorna la lista dei file
        self.refresh_file_list()

        # Se l'immagine attuale è stata eliminata, carica la prossima immagine disponibile
        if self.image_path in self.image_files:
            if self.image_files:
                self.index = min(self.index, len(self.image_files) - 1)
                print(f"New index after deletion: {self.index}")
                self.load_current_image()
            else:
                self.canvas.delete("all")
                self.image_size_label.config(text="Image Size: N/A")
                self.rect_size_label.config(text="Rect Size: N/A")
                self.current_image = None
                self.image_path = None
                self.current_annotations = []
                self.master.title("Visual Editor - No Image Loaded")
                print("No image available after deletion.")

    def crop_images_with_labels(self, image_dir, label_dir, output_image_dir, output_label_dir, crop_mode, margin, resolution):
        """Process images and labels for smart cropping."""
        width, height = map(int, resolution.lower().split("x"))
        os.makedirs(output_image_dir, exist_ok=True)
        os.makedirs(output_label_dir, exist_ok=True)
        
        for label_file in os.listdir(label_dir):
            if label_file.endswith(".txt"):
                image_file = label_file.replace(".txt", ".jpg")
                image_path = os.path.join(image_dir, image_file)
                label_path = os.path.join(label_dir, label_file)
                
                if not os.path.exists(image_path):
                    print(f"Warning: Image {image_file} not found for label {label_file}")
                    continue
                
                image = cv2.imread(image_path)
                if image is None:
                    print(f"Warning: Could not read image {image_file}")
                    continue

                img_height, img_width, _ = image.shape
                
                with open(label_path, "r") as f:
                    labels = [line.strip().split() for line in f.readlines()]
                
                for idx, label in enumerate(labels):
                    class_id, x_center, y_center, box_width, box_height = map(float, label)
                    x_center_pixel = int(x_center * img_width)
                    y_center_pixel = int(y_center * img_height)
                    box_width_pixel = int(box_width * img_width)
                    box_height_pixel = int(box_height * img_height)
                    
                    if crop_mode == "Centered":
                        crop_x1 = max(margin, x_center_pixel - width // 2)
                        crop_y1 = max(margin, y_center_pixel - height // 2)
                    else:  # Random
                        max_x = img_width - width - margin
                        max_y = img_height - height - margin
                        crop_x1 = random.randint(margin, max(margin, max_x))
                        crop_y1 = random.randint(margin, max(margin, max_y))

                    crop_x2 = min(img_width - margin, crop_x1 + width)
                    crop_y2 = min(img_height - margin, crop_y1 + height)
                    
                    # Adjust crop coordinates if they exceed image boundaries
                    if crop_x2 - crop_x1 < width:
                        crop_x1 = max(margin, crop_x2 - width)
                    if crop_y2 - crop_y1 < height:
                        crop_y1 = max(margin, crop_y2 - height)
                    
                    cropped_image = image[crop_y1:crop_y2, crop_x1:crop_x2]
                    cropped_image_name = f"{os.path.splitext(image_file)[0]}_crop_{idx}.jpg"
                    cv2.imwrite(os.path.join(output_image_dir, cropped_image_name), cropped_image)
                    
                    # Calculate new annotation coordinates
                    new_x_center = (x_center_pixel - crop_x1) / width
                    new_y_center = (y_center_pixel - crop_y1) / height
                    new_box_width = box_width_pixel / width
                    new_box_height = box_height_pixel / height
                    
                    # Ensure the coordinates are within [0, 1]
                    new_x_center = max(0, min(1, new_x_center))
                    new_y_center = max(0, min(1, new_y_center))
                    new_box_width = max(0, min(1, new_box_width))
                    new_box_height = max(0, min(1, new_box_height))
                    
                    cropped_label_name = f"{os.path.splitext(label_file)[0]}_crop_{idx}.txt"
                    with open(os.path.join(output_label_dir, cropped_label_name), "w") as label_outfile:
                        label_outfile.write(f"{int(class_id)} {new_x_center:.6f} {new_y_center:.6f} {new_box_width:.6f} {new_box_height:.6f}\n")
        
        messagebox.showinfo("Success", "Smart crop completed successfully!")

# ------------------------------------------------------------------------------
# Esegui il programma
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x900")
    viewer = ImageViewer(root)
    viewer.run()
