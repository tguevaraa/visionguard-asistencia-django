import json
import os

class Empleado:
    def __init__(self,id__emp, nombre, cargo):
        self.id__emp = id__emp
        self.nombre = nombre
        self.cargo = cargo
    
    def to_dict(self):
        return{"id__emp": self.id__emp,
                "nombre": self.nombre,
                "cargo": self.cargo}

class SistemaGestion:
    def __init__(self, archivo_db='data/empleados.json'):
        self.archivo_db = archivo_db
        self.empleados = []
        self.cargar_datos()
    
    def agregar_empleado(self, empleado):
        for emp in self.empleados:
            if emp.id__emp == empleado.id__emp:
                print(f"Empleado con ID {empleado.id__emp} ya existe.")
                return False
            
        self.empleados.append(empleado)
        self.guardar_datos()
        print(f"Empleado {empleado.nombre} agregado con éxito.")
        return True
    
    def guardar_datos(self):
        os.makedirs(os.path.dirname(self.archivo_db), exist_ok=True)
        data = [emp.to_dict() for emp in self.empleados]
        with open(self.archivo_db, 'w') as f:
            json.dump(data, f, indent=4)

    def cargar_datos(self):
        if not os.path.exists(self.archivo_db):
            return
        try:
            with open(self.archivo_db, 'r') as f:
                data = json.load(f)
                self.empleados = [Empleado(d['id__emp'], d['nombre'], d['cargo']) for d in data]
        except (json.JSONDecodeError, FileNotFoundError):
            self.empleados = []

    def listar_empleados(self):
        if not self.empleados:
            print("No hay empleados registrados.")
            return
        print("\n-- Lista de Empleados ---")
        for empleado in self.empleados:
            print(f"ID: {empleado.id__emp} | Nombre: {empleado.nombre} | Cargo: {empleado.cargo}")
        print("--------------------------\n")