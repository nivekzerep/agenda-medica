from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '../templates'),
    static_folder='static'
)

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', 'maria1234'),
        database=os.environ.get('DB_NAME', 'agenda_medica'),
        port=int(os.environ.get('DB_PORT', '3307'))
    )

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener la lista de estados posibles
    estados = ['pendiente', 'confirmada', 'cancelada', 'completada']
    
    # Obtener el filtro actual desde los parámetros de la URL
    filtro_actual = request.args.get('status', '')  # Por defecto, no hay filtro
    
    # Construir la consulta SQL con el filtro
    if (filtro_actual and filtro_actual in estados):
        cursor.execute("""
            SELECT c.id_cita, u.nombre AS paciente, m.nombre AS medico, 
                   c.fecha_cita, c.motivo, c.estado
            FROM citas c
            JOIN usuarios u ON c.id_paciente = u.id_usuario
            JOIN usuarios m ON c.id_medico = m.id_usuario
            WHERE c.estado = %s
        """, (filtro_actual,))
    else:
        cursor.execute("""
            SELECT c.id_cita, u.nombre AS paciente, m.nombre AS medico, 
                   c.fecha_cita, c.motivo, c.estado
            FROM citas c
            JOIN usuarios u ON c.id_paciente = u.id_usuario
            JOIN usuarios m ON c.id_medico = m.id_usuario
        """)
    
    citas = cursor.fetchall()
    conn.close()
    
    # Pasar las variables necesarias a la plantilla
    return render_template('index.html', citas=citas, estados=estados, filtro_actual=filtro_actual)

@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE tipo_usuario = 'paciente'")
    pacientes = cursor.fetchall()
    cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE tipo_usuario = 'medico'")
    medicos = cursor.fetchall()

    if request.method == 'POST':
        id_paciente = request.form['id_paciente']
        id_medico = request.form['id_medico']
        fecha_cita = request.form['fecha_cita']
        motivo = request.form['motivo']

        cursor.execute(
            "INSERT INTO citas (id_paciente, id_medico, fecha_cita, motivo, estado) VALUES (%s, %s, %s, %s, 'pendiente')",
            (id_paciente, id_medico, fecha_cita, motivo)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    conn.close()
    return render_template('agendar.html', pacientes=pacientes, medicos=medicos)

@app.route('/editar/<int:id_cita>', methods=['GET', 'POST'])
def editar(id_cita):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM citas WHERE id_cita = %s", (id_cita,))
    cita = cursor.fetchone()

    cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE tipo_usuario = 'paciente'")
    pacientes = cursor.fetchall()
    cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE tipo_usuario = 'medico'")
    medicos = cursor.fetchall()

    if request.method == 'POST':
        id_paciente = request.form['id_paciente']
        id_medico = request.form['id_medico']
        fecha_cita = request.form['fecha_cita']
        motivo = request.form['motivo']
        estado = request.form['estado']  # Capturar el estado del formulario

        cursor.execute(
            """
            UPDATE citas
            SET id_paciente = %s, id_medico = %s, fecha_cita = %s, motivo = %s, estado = %s
            WHERE id_cita = %s
            """,
            (id_paciente, id_medico, fecha_cita, motivo, estado, id_cita)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    conn.close()
    return render_template('editar.html', cita=cita, pacientes=pacientes, medicos=medicos)

@app.route('/eliminar/<int:id_cita>')
def eliminar(id_cita):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM citas WHERE id_cita = %s", (id_cita,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/eliminar_canceladas')
def eliminar_canceladas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM citas WHERE estado = 'cancelada'")
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/pacientes')
def listar_pacientes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE tipo_usuario = 'paciente'")
    pacientes = cursor.fetchall()
    conn.close()
    return render_template('pacientes.html', pacientes=pacientes)

@app.route('/pacientes/agregar', methods=['GET', 'POST'])
def agregar_paciente():
    error = None
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        
        # Validaciones del lado del servidor
        if not nombre.isalpha():
            error = "El nombre solo puede contener letras."
        elif not apellido.isalpha():
            error = "El apellido solo puede contener letras."
        elif len(telefono) != 10 or not telefono.isdigit():
            error = "El teléfono debe contener exactamente 10 dígitos."
        elif '@' not in email or '.' not in email:
            error = "El correo electrónico no es válido."
        
        if error:
            return render_template('agregar_paciente.html', error=error)
        
        # Insertar el nuevo paciente en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, telefono, direccion, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s, 'paciente')
        """, (nombre, apellido, email, telefono, direccion))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_pacientes'))
    
    return render_template('agregar_paciente.html', error=error)

@app.route('/pacientes/editar/<int:id_usuario>', methods=['GET', 'POST'])
def editar_paciente(id_usuario):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = %s AND tipo_usuario = 'paciente'", (id_usuario,))
    paciente = cursor.fetchone()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        
        cursor.execute("""
            UPDATE usuarios
            SET nombre = %s, apellido = %s, email = %s, telefono = %s, direccion = %s
            WHERE id_usuario = %s AND tipo_usuario = 'paciente'
        """, (nombre, apellido, email, telefono, direccion, id_usuario))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_pacientes'))
    
    conn.close()
    return render_template('editar_paciente.html', paciente=paciente)

@app.route('/pacientes/eliminar/<int:id_usuario>')
def eliminar_paciente(id_usuario):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s AND tipo_usuario = 'paciente'", (id_usuario,))
    conn.commit()
    conn.close()
    return redirect(url_for('listar_pacientes'))

@app.route('/medicos')
def listar_medicos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE tipo_usuario = 'medico'")
    medicos = cursor.fetchall()
    conn.close()
    return render_template('medicos.html', medicos=medicos)

@app.route('/medicos/agregar', methods=['GET', 'POST'])
def agregar_medico():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener las especialidades para el formulario
    cursor.execute("SELECT id_especialidad AS id, nombre_especialidad AS nombre FROM especialidades")
    especialidades = cursor.fetchall()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        especialidad_id = request.form['especialidad_id']
        
        if not nombre or not apellido or not email or not especialidad_id:
            error = "Todos los campos obligatorios deben ser completados."
            return render_template('agregar_medico.html', especialidades=especialidades, error=error)
        
        # Insertar el nuevo médico en la base de datos
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, telefono, direccion, tipo_usuario, especialidad_id)
            VALUES (%s, %s, %s, %s, %s, 'medico', %s)
        """, (nombre, apellido, email, telefono, direccion, especialidad_id))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_medicos'))
    
    conn.close()
    return render_template('agregar_medico.html', especialidades=especialidades)

@app.route('/medicos/editar/<int:id_usuario>', methods=['GET', 'POST'])
def editar_medico(id_usuario):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener los datos del médico
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = %s AND tipo_usuario = 'medico'", (id_usuario,))
    medico = cursor.fetchone()
    
    # Obtener las especialidades para el formulario
    cursor.execute("SELECT id_especialidad AS id, nombre_especialidad AS nombre FROM especialidades")
    especialidades = cursor.fetchall()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        especialidad_id = request.form['especialidad_id']
        
        # Actualizar los datos del médico
        cursor.execute("""
            UPDATE usuarios
            SET nombre = %s, apellido = %s, email = %s, telefono = %s, direccion = %s, especialidad_id = %s
            WHERE id_usuario = %s AND tipo_usuario = 'medico'
        """, (nombre, apellido, email, telefono, direccion, especialidad_id, id_usuario))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_medicos'))
    
    conn.close()
    return render_template('editar_medico.html', medico=medico, especialidades=especialidades)

@app.route('/medicos/eliminar/<int:id_usuario>')
def eliminar_medico(id_usuario):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s AND tipo_usuario = 'medico'", (id_usuario,))
    conn.commit()
    conn.close()
    return redirect(url_for('listar_medicos'))

if __name__ == '__main__':
    app.run(debug=True)