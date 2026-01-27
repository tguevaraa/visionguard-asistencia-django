import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import os
import sys  # Importante para el .exe
import numpy as np
from datetime import datetime
import pandas as pd
from modelo import SistemaGestion, Empleado

class VisionGuardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VisionGuard AI - Sistema de Asistencia")
        self.root.geometry("1100x650")
        
        self.sistema = SistemaGestion()
        self.webcam = cv2.VideoCapture(0)
        
        # --- BLOQUE DE CARGA ROBUSTA DEL XML (PARA EL .EXE) ---
        # 1. Detectar dónde está corriendo el programa exactamente
        if getattr(sys, 'frozen', False):
            # Si es un .EXE, buscamos en su misma carpeta
            directorio_base = os.path.dirname(sys.executable)
        else:
            # Si es un script (.py), buscamos en la carpeta del archivo
            directorio_base = os.path.dirname(os.path.abspath(__file__))

        # 2. Construir la ruta absoluta al archivo XML
        ruta_xml = os.path.join(directorio_base, "haarcascade_frontalface_default.xml")

        # 3. Cargar el clasificador
        self.face_cascade = cv2.CascadeClassifier(ruta_xml)

        # 4. Verificación de seguridad
        if self.face_cascade.empty():
            # Intentar fallback con la ruta interna de OpenCV (solo sirve en VS Code)
            ruta_xml_backup = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(ruta_xml_backup)
            
            # Si sigue vacío, lanzamos alerta visual
            if self.face_cascade.empty():
                messagebox.showerror("Error CRÍTICO", 
                    f"NO ENCUENTRO EL ARCHIVO XML.\n\n"
                    f"Buscando en:\n{ruta_xml}\n\n"
                    "Asegúrate de copiar 'haarcascade_frontalface_default.xml' junto al .exe")
                sys.exit() 
        # ------------------------------------------------------
        
        # Instanciamos el reconocedor LBPH
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.modelo_entrenado = False
        
        # Diccionario para evitar spam de logs
        self.ultimo_registro = {}
        
        # Intentamos cargar el modelo si ya existe
        if os.path.exists('data/modelo_entrenado.xml'):
            self.recognizer.read('data/modelo_entrenado.xml')
            self.modelo_entrenado = True
            print("Modelo de IA cargado correctamente.")

        self.modo_reconocimiento = False 
        
        # Variables de interfaz
        self.var_id = tk.StringVar()
        self.var_nombre = tk.StringVar()
        self.var_cargo = tk.StringVar()

        self.crear_interfaz()
        self.actualizar_tabla()
        self.mostrar_video()

    def crear_interfaz(self):
        # PANEL IZQUIERDO
        frame_izq = tk.LabelFrame(self.root, text="Controles", padx=10, pady=10)
        frame_izq.place(x=20, y=20, width=450, height=600)

        # Campos
        tk.Label(frame_izq, text="ID (Solo números):").pack(anchor="w")
        tk.Entry(frame_izq, textvariable=self.var_id).pack(fill="x")
        tk.Label(frame_izq, text="Nombre:").pack(anchor="w")
        tk.Entry(frame_izq, textvariable=self.var_nombre).pack(fill="x")
        tk.Label(frame_izq, text="Cargo:").pack(anchor="w")
        tk.Entry(frame_izq, textvariable=self.var_cargo).pack(fill="x")

        # VIDEO
        self.lbl_video = tk.Label(frame_izq, bg="black")
        self.lbl_video.pack(fill="both", expand=True, pady=10)

        # BOTONES DE ACCIÓN
        btn_frame = tk.Frame(frame_izq)
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="📸 Registrar Nuevo", bg="#2196F3", fg="white", 
                  command=self.guardar_empleado_con_foto).pack(side="left", expand=True, fill="x", padx=2)
        
        tk.Button(btn_frame, text="🧠 Entrenar IA", bg="#FF9800", fg="white", 
                  command=self.entrenar_sistema).pack(side="left", expand=True, fill="x", padx=2)
        
        tk.Button(frame_izq, text="📊 Exportar a Excel", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                  command=self.generar_excel).pack(fill="x", pady=5)

        # Botón Interruptor
        self.btn_modo = tk.Button(frame_izq, text="Modo: REGISTRO", bg="gray", fg="white",
                                  command=self.toggle_modo)
        self.btn_modo.pack(fill="x", pady=5)

        # PANEL DERECHO
        frame_der = tk.LabelFrame(self.root, text="Empleados", padx=10, pady=10)
        frame_der.place(x=490, y=20, width=580, height=600)

        columnas = ("ID", "Nombre", "Cargo")
        self.tabla = ttk.Treeview(frame_der, columns=columnas, show="headings")
        for col in columnas: self.tabla.heading(col, text=col)
        self.tabla.pack(fill="both", expand=True)

    def toggle_modo(self):
        self.modo_reconocimiento = not self.modo_reconocimiento
        if self.modo_reconocimiento:
            self.btn_modo.config(text="Modo: RECONOCIMIENTO ACTIVO", bg="#4CAF50")
            if not self.modelo_entrenado:
                messagebox.showwarning("Alerta", "Primero debes entrenar la IA con el botón naranja.")
        else:
            self.btn_modo.config(text="Modo: REGISTRO", bg="gray")

    def mostrar_video(self):
        ret, frame = self.webcam.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                color = (255, 0, 0) # Azul
                texto = "..."
                
                if self.modo_reconocimiento and self.modelo_entrenado:
                    rostro_recortado = gray[y:y+h, x:x+w]
                    # Try-Except por si acaso el recorte es muy pequeño
                    try:
                        id_predicho, confianza = self.recognizer.predict(rostro_recortado)
                        if confianza < 70: 
                            nombre_encontrado = "Desconocido"
                            for emp in self.sistema.empleados:
                                if emp.id__emp == str(id_predicho):
                                    nombre_encontrado = emp.nombre
                                    self.registrar_asistencia(nombre_encontrado)
                                    break
                            
                            texto = f"{nombre_encontrado} ({int(confianza)})"
                            color = (0, 255, 0)
                        else:
                            texto = "Desconocido"
                            color = (0, 0, 255)
                    except:
                        pass
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, texto, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb).resize((400, 300))
            img_tk = ImageTk.PhotoImage(image=img_pil)
            self.lbl_video.configure(image=img_tk)
            self.lbl_video.image = img_tk

        self.root.after(20, self.mostrar_video)

    def registrar_asistencia(self, nombre):
        archivo = "asistencia.log"
        ahora = datetime.now()
        
        if nombre in self.ultimo_registro:
            tiempo_pasado = (ahora - self.ultimo_registro[nombre]).total_seconds()
            if tiempo_pasado < 60: 
                return

        fecha_str = ahora.strftime("%Y-%m-%d %H:%M:%S")
        with open(archivo, "a") as f:
            f.write(f"{fecha_str} - {nombre} ingresó.\n")
            print(f"Asistencia marcada para {nombre}")
            
        self.ultimo_registro[nombre] = ahora

    def entrenar_sistema(self):
        ruta_fotos = "data/rostros"
        if not os.path.exists(ruta_fotos):
            os.makedirs(ruta_fotos)
        
        archivos = os.listdir(ruta_fotos)
        if not archivos:
            messagebox.showerror("Error", "No hay fotos para entrenar. Registra a alguien primero.")
            return

        faces_data = []
        ids = []

        print("Iniciando entrenamiento...")
        for archivo in archivos:
            if archivo.endswith(".jpg"):
                try:
                    path = os.path.join(ruta_fotos, archivo)
                    imagen_pil = Image.open(path).convert('L')
                    imagen_np = np.array(imagen_pil, 'uint8')
                    
                    id_actual = int(os.path.splitext(archivo)[0])
                    
                    faces = self.face_cascade.detectMultiScale(imagen_np)
                    for (x, y, w, h) in faces:
                        faces_data.append(imagen_np[y:y+h, x:x+w])
                        ids.append(id_actual)
                except Exception as e:
                    print(f"Error procesando {archivo}: {e}")

        if ids:
            self.recognizer.train(faces_data, np.array(ids))
            self.recognizer.write('data/modelo_entrenado.xml')
            self.modelo_entrenado = True
            messagebox.showinfo("Éxito", "Sistema entrenado correctamente.")
        else:
            messagebox.showwarning("Error", "No se pudieron procesar rostros.")

    def guardar_empleado_con_foto(self):
        id_emp = self.var_id.get()
        nombre = self.var_nombre.get()
        cargo = self.var_cargo.get()

        if not id_emp.isdigit():
            messagebox.showerror("Error", "El ID debe ser numérico.")
            return

        ret, frame = self.webcam.read()
        if ret:
            ruta_foto = f"data/rostros/{id_emp}.jpg"
            # Asegurar que data/rostros exista
            os.makedirs("data/rostros", exist_ok=True)
            
            cv2.imwrite(ruta_foto, frame)
            
            nuevo_emp = Empleado(id_emp, nombre, cargo)
            if self.sistema.agregar_empleado(nuevo_emp):
                self.actualizar_tabla()
                self.limpiar_campos()
                messagebox.showinfo("Guardado", "Foto guardada. \nRecuerda 'Entrenar IA'.")
            else:
                messagebox.showerror("Error", "El ID ya existe.")

    def generar_excel(self):
        archivo_log = "asistencia.log"
        if not os.path.exists(archivo_log):
            messagebox.showwarning("Aviso", "No hay registros para exportar.")
            return

        try:
            datos = []
            with open(archivo_log, "r") as f:
                for linea in f:
                    partes = linea.strip().split(" - ")
                    if len(partes) >= 2:
                        fecha_hora = partes[0]
                        evento = partes[1]
                        dt_obj = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S")
                        datos.append({
                            "Fecha": dt_obj.date(),
                            "Hora": dt_obj.time(),
                            "Evento": evento,
                            "Estado": "Puntual"
                        })

            df = pd.DataFrame(datos)
            # Nombre con hora para evitar bloqueo de archivo
            nombre_excel = f"Reporte_Asistencia_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
            df.to_excel(nombre_excel, index=False)
            
            messagebox.showinfo("Exportado", f"Archivo creado:\n{nombre_excel}")
            os.startfile(nombre_excel)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el Excel: {e}")
    
    def actualizar_tabla(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        # CORREGIDO: id_emp (un solo guion bajo)
        for emp in self.sistema.empleados: 
            self.tabla.insert("", "end", values=(emp.id__emp, emp.nombre, emp.cargo))

    def limpiar_campos(self):
        self.var_id.set(""); self.var_nombre.set(""); self.var_cargo.set("")

    def __del__(self):
        if self.webcam.isOpened(): self.webcam.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = VisionGuardApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: [app.webcam.release(), root.destroy()])
    root.mainloop()