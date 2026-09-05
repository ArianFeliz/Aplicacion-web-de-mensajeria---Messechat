from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from flask_socketio import join_room, emit
from sqlalchemy import or_
from extensions import db, socketio
from models import Chat, Mensaje, Usuario
from estado import calcular_estado

chat_bp = Blueprint("chat", __name__)


def _contactos_ids(user_id):
    chats = Chat.query.filter(
        or_(Chat.usuario1_id == user_id, Chat.usuario2_id == user_id)
    ).all()
    return {c.otro_usuario(user_id).id for c in chats}


def _chats_del_usuario():
    return Chat.query.filter(
        or_(Chat.usuario1_id == current_user.id, Chat.usuario2_id == current_user.id)
    ).all()


@chat_bp.route("/chat")
@chat_bp.route("/chat/<int:chat_id>")
@login_required
def ver_chat(chat_id=None):
    chats = _chats_del_usuario()
    chat_activo = None
    mensajes = []

    if chat_id:
        chat_activo = Chat.query.get_or_404(chat_id)
        if current_user.id not in (chat_activo.usuario1_id, chat_activo.usuario2_id):
            chat_activo = None
        else:
            mensajes = [
                m for m in chat_activo.mensajes.all()
                if str(current_user.id) not in (m.oculto_para or "").split(",")
            ]
            Mensaje.query.filter_by(chat_id=chat_id, leido=False).filter(
                Mensaje.emisor_id != current_user.id
            ).update({"leido": True})
            db.session.commit()

    otro_estado = None
    if chat_activo:
        otro_estado = calcular_estado(chat_activo.otro_usuario(current_user.id))

    return render_template(
        "chat.html", chats=chats, chat_activo=chat_activo, mensajes=mensajes, otro_estado=otro_estado
    )


@chat_bp.route("/api/chat/<int:chat_id>/buscar-contacto")
@login_required
def buscar_en_contactos(chat_id):
    """Filtra la lista de contactos (chats ya aceptados) de la barra lateral,
    a diferencia del buscador general que crea solicitudes nuevas."""
    q = request.args.get("q", "").lower().strip()
    chats = _chats_del_usuario()
    resultado = []
    for c in chats:
        otro = c.otro_usuario(current_user.id)
        if q in otro.usuario_publico.lower():
            resultado.append({"chat_id": c.id, "usuario_publico": otro.usuario_publico, "foto": otro.foto})
    return {"resultados": resultado}


@chat_bp.route("/api/chat/<int:chat_id>/vaciar", methods=["POST"])
@login_required
def vaciar_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if current_user.id not in (chat.usuario1_id, chat.usuario2_id):
        return {"ok": False}, 403
    Mensaje.query.filter_by(chat_id=chat_id).delete()
    db.session.commit()
    return {"ok": True}


@chat_bp.route("/api/usuario/<int:usuario_id>")
@login_required
def ver_perfil_contacto(usuario_id):
    u = Usuario.query.get_or_404(usuario_id)
    return {
        "usuario_publico": u.usuario_publico,
        "foto": u.foto,
        "descripcion": u.descripcion or "",
        "intereses": u.intereses or "",
        "pais": u.pais or "",
        "estado": calcular_estado(u),
    }


@chat_bp.route("/api/mensaje/<int:msg_id>/eliminar/mio", methods=["POST"])
@login_required
def eliminar_mensaje_mio(msg_id):
    msg = Mensaje.query.get_or_404(msg_id)
    ids = set(filter(None, msg.oculto_para.split(",")))
    ids.add(str(current_user.id))
    msg.oculto_para = ",".join(ids)
    db.session.commit()
    return {"ok": True}


@chat_bp.route("/api/mensaje/<int:msg_id>/eliminar/todos", methods=["POST"])
@login_required
def eliminar_mensaje_todos(msg_id):
    msg = Mensaje.query.get_or_404(msg_id)
    if msg.emisor_id != current_user.id:
        return {"ok": False}, 403
    msg.eliminado_para_todos = True
    msg.contenido = ""
    msg.imagen = None
    db.session.commit()

    socketio.emit("mensaje_eliminado", {"msg_id": msg.id}, room=f"chat_{msg.chat_id}")
    return {"ok": True}


# ---------- Tiempo real con Socket.IO ----------

@socketio.on("connect")
def on_connect():
    print(f"[SocketIO] Cliente conectado. Autenticado: {current_user.is_authenticated}")
    if current_user.is_authenticated:
        current_user.en_linea = True
        db.session.commit()
        estado = calcular_estado(current_user)
        for cid in _contactos_ids(current_user.id):
            socketio.emit("estado_usuario", {"usuario_id": current_user.id, "estado": estado},
                           room=f"user_{cid}")


@socketio.on("disconnect")
def on_disconnect():
    if current_user.is_authenticated:
        current_user.en_linea = False
        current_user.ultima_conexion = datetime.utcnow()
        db.session.commit()
        estado = calcular_estado(current_user)
        for cid in _contactos_ids(current_user.id):
            socketio.emit("estado_usuario", {"usuario_id": current_user.id, "estado": estado},
                           room=f"user_{cid}")


@socketio.on("unirse_personal")
def on_unirse_personal():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")


@socketio.on("unirse_chat")
def on_unirse(data):
    print(f"[SocketIO] Uniéndose a sala chat_{data['chat_id']}")
    join_room(f"chat_{data['chat_id']}")


@socketio.on("enviar_mensaje")
def on_enviar_mensaje(data):
    print(f"[SocketIO] enviar_mensaje recibido: {data.get('chat_id')} autenticado={current_user.is_authenticated}")
    if not current_user.is_authenticated:
        return

    chat_id = data["chat_id"]
    contenido = (data.get("contenido") or "").strip()
    imagen = data.get("imagen")

    if not contenido and not imagen:
        return

    msg = Mensaje(chat_id=chat_id, emisor_id=current_user.id, contenido=contenido, imagen=imagen)
    db.session.add(msg)
    db.session.commit()

    emit("nuevo_mensaje", {
        "msg_id": msg.id,
        "chat_id": chat_id,
        "emisor_id": current_user.id,
        "emisor_usuario": current_user.usuario_publico,
        "contenido": contenido,
        "imagen": imagen,
        "fecha_envio": msg.fecha_envio.strftime("%H:%M"),
    }, room=f"chat_{chat_id}")
