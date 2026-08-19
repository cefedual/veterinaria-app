from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE BASE DE DATOS ---
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE BASE DE DATOS ---
DB_NAME = "veterinaria.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS clientes (dui TEXT PRIMARY KEY, nombre TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS mascotas (id INTEGER PRIMARY KEY AUTOINCREMENT, dui_cliente TEXT, nombre_mascota TEXT, peso_kg REAL, FOREIGN KEY(dui_cliente) REFERENCES clientes(dui))")
    cursor.execute("CREATE TABLE IF NOT EXISTS historial (id INTEGER PRIMARY KEY AUTOINCREMENT, mascota_id INTEGER, fecha TEXT, tipo TEXT, descripcion TEXT, producto_usado TEXT, proxima_cita TEXT, estado_cita TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS historial_pesos (mascota_id INTEGER, fecha TEXT, peso REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock INTEGER)")

    # Aquí es donde va el bloque de seguridad, dentro de la función
    try:
        cursor.execute("ALTER TABLE mascotas ADD COLUMN peso_kg REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE historial ADD COLUMN producto_usado TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES AUXILIARES ---
def query_db(query, args=(), fetch=True):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(query, args)
  res = cursor.fetchall() if fetch else None
  conn.commit()
  conn.close()
  return res


# --- INTERFAZ ---
st.title("🐾 Vértice - Gestión Veterinaria Pro")

menu = st.sidebar.selectbox(
    "Menú", ["Dashboard / Avisos", "Registrar Paciente", "Pacientes", "Inventario"]
)

# 1. DASHBOARD Y AVISADOR DE CITAS (Mañana)
if menu == "Dashboard / Avisos":
  st.header("📅 Gestión de Agenda")
  manana = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

  st.subheader(f"Recordatorios para mañana: {manana}")
  citas_manana = query_db("""
        SELECT m.nombre_mascota, c.nombre, c.telefono 
        FROM historial h 
        JOIN mascotas m ON h.mascota_id = m.id 
        JOIN clientes c ON m.dui_cliente = c.dui 
        WHERE h.proxima_cita = ? AND h.estado_cita = 'Pendiente'""", (manana,))

  if citas_manana:
    for mascota, dueño, tel in citas_manana:
      mensaje = (
          f"Hola {dueño}, le recordamos la cita de {mascota} mañana en"
          " Vértice. ¡Le esperamos!"
      )
      st.warning(f"📢 **Avisar a:** {dueño} (Tel: {tel or 'Sin teléfono'})")
      st.code(mensaje)
  else:
    st.info("No hay citas programadas para mañana.")

# 2. REGISTRAR PACIENTE
elif menu == "Registrar Paciente":
  st.header("📝 Nuevo Registro de Cliente y Mascota")
  with st.form("form_registro"):
    dui = st.text_input("DUI del Cliente")
    nombre_c = st.text_input("Nombre Completo del Dueño")
    nombre_m = st.text_input("Nombre de la Mascota")
    peso_ini = st.number_input("Peso Inicial (kg)", min_value=0.0, step=0.1)

    if st.form_submit_button("Guardar Registro"):
      if not dui or not nombre_c or not nombre_m:
        st.error("Por favor completa los campos obligatorios.")
      else:
        query_db(
            "INSERT OR IGNORE INTO clientes (dui, nombre) VALUES (?,?)",
            (dui, nombre_c),
            fetch=False,
        )
        query_db(
            "INSERT INTO mascotas (dui_cliente, nombre_mascota, peso_kg) VALUES"
            " (?,?,?)",
            (dui, nombre_m, peso_ini),
            fetch=False,
        )
        st.success(
            f"¡Cliente {nombre_c} y mascota {nombre_m} registrados con éxito!"
        )


# 3. PACIENTES (Búsqueda inteligente por propietario/mascota)
elif menu == "Pacientes":
    st.header("🔍 Buscar Paciente")
    busqueda = st.text_input("Ingresa nombre de mascota o nombre de dueño")
    
    if busqueda:
        # Buscamos combinando tablas para tener claro quién es quién
        sql = """
            SELECT m.id, m.nombre_mascota, c.nombre, c.dui 
            FROM mascotas m
            JOIN clientes c ON m.dui_cliente = c.dui
            WHERE m.nombre_mascota LIKE ? OR c.nombre LIKE ?
        """
        resultados = query_db(sql, (f"%{busqueda}%", f"%{busqueda}%"))
        
        if resultados:
            st.write(f"Se encontraron {len(resultados)} coincidencias:")
            # Creamos una lista de opciones para que tú elijas sin error
            opciones = {f"{r[1]} (Dueño: {r[2]} - DUI: {r[3]})": r[0] for r in resultados}
            seleccion = st.selectbox("Selecciona al paciente correcto:", list(opciones.keys()))
            
            mid = opciones[seleccion]
            
            # Una vez seleccionado, desplegamos su historial único
            # (Aquí va el resto de la lógica que ya tenías para el expander)
            m_info = query_db("SELECT nombre_mascota, peso_kg FROM mascotas WHERE id = ?", (mid,))[0]
            m_nom, m_peso = m_info
            
            with st.expander(f"Expediente de {m_nom} | Peso: {m_peso or 0}kg", expanded=True):
                # ... (Aquí va tu lógica de gráfica e historial que ya funciona)
                # (Recuerda mantener el resto del código del bloque expander aquí)
                st.write("### Historial de Gestiones:")
                # ... (y el formulario de gestión debajo)
        else:
            st.warning("No se encontró ese nombre.")
            
# 4. INVENTARIO
# 4. INVENTARIO CON EDICIÓN Y BORRADO
elif menu == "Inventario":
    st.header("📦 Inventario de Insumos")
    
    # --- AGREGAR NUEVO ---
    with st.expander("➕ Agregar nuevo producto"):
        with st.form("nuevo_prod"):
            n_prod = st.text_input("Nombre del producto")
            n_cant = st.number_input("Cantidad inicial", min_value=0, step=1)
            if st.form_submit_button("Guardar"):
                query_db("INSERT OR REPLACE INTO inventario (producto, stock) VALUES (?,?)", (n_prod, n_cant), fetch=False)
                st.success("Guardado")
                st.rerun()

    # --- LISTAR Y EDITAR/BORRAR ---
    st.subheader("Control de Stock")
    data_inv = query_db("SELECT producto, stock FROM inventario")
    
    if data_inv:
        for prod, stock in data_inv:
            cols = st.columns([3, 1, 1, 1])
            cols[0].write(f"**{prod}**")
            
            # Edición de cantidad
            nuevo_stock = cols[1].number_input("Stock", value=stock, key=f"s_{prod}")
            
            # Botones de acción
            if cols[2].button("💾", key=f"upd_{prod}"):
                query_db("UPDATE inventario SET stock = ? WHERE producto = ?", (nuevo_stock, prod), fetch=False)
                st.rerun()
            
            if cols[3].button("🗑️", key=f"del_{prod}"):
                query_db("DELETE FROM inventario WHERE producto = ?", (prod,), fetch=False)
                st.rerun()
    else:
        st.info("Inventario vacío.")