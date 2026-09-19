from datetime import datetime
from flask_login import UserMixin
from extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)

    usuario_publico = db.Column(db.String(50), unique=True, nullable=False)
    foto = db.Column(db.Text, default=None)  # data URI base64, ej. "data:image/png;base64,..."
    descripcion = db.Column(db.String(300), default="")
    intereses = db.Column(db.String(300), default="")  # separados por coma
    pais = db.Column(db.String(60), default="")  # ej. "🇩🇴 República Dominicana"

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    en_linea = db.Column(db.Boolean, default=False)
    ultima_conexion = db.Column(db.DateTime, default=datetime.utcnow)

    preferencia = db.relationship("Preferencia", backref="usuario", uselist=False)

    def __repr__(self):
        return f"<Usuario {self.usuario_publico}>"


class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)
    emisor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    receptor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    estado = db.Column(db.String(20), default="pendiente")  # pendiente/aceptada/rechazada
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    emisor = db.relationship("Usuario", foreign_keys=[emisor_id])
    receptor = db.relationship("Usuario", foreign_keys=[receptor_id])


class Bloqueo(db.Model):
    __tablename__ = "bloqueos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    bloqueado_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    bloqueado = db.relationship("Usuario", foreign_keys=[bloqueado_id])


class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    usuario1_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    usuario2_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)

    usuario1 = db.relationship("Usuario", foreign_keys=[usuario1_id])
    usuario2 = db.relationship("Usuario", foreign_keys=[usuario2_id])
    mensajes = db.relationship("Mensaje", backref="chat", lazy="dynamic",
                                order_by="Mensaje.fecha_envio")

    def otro_usuario(self, usuario_actual_id):
        return self.usuario2 if self.usuario1_id == usuario_actual_id else self.usuario1


class Mensaje(db.Model):
    __tablename__ = "mensajes"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False)
    emisor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    contenido = db.Column(db.Text, default="")
    imagen = db.Column(db.Text)  # imagen adjunta en base64, opcional
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    eliminado_para_todos = db.Column(db.Boolean, default=False)
    oculto_para = db.Column(db.String(200), default="")  # ids de usuario separados por coma

    emisor = db.relationship("Usuario", foreign_keys=[emisor_id])


class Preferencia(db.Model):
    __tablename__ = "preferencias"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False)

    color_primario = db.Column(db.String(7), default="#FF9644")
    color_fondo = db.Column(db.String(7), default="#FFFDF1")
    tamano_letra = db.Column(db.String(10), default="mediano")  # chico/mediano/grande
    tipo_letra = db.Column(db.String(50), default="Poppins")
    mostrar_estado = db.Column(db.Boolean, default=True)
