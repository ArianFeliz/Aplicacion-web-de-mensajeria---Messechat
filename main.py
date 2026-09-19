import os
import base64
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from extensions import db, socketio
from models import Usuario, Solicitud, Bloqueo, Preferencia
from paises import PAISES

main_bp = Blueprint("main", __name__)

EXTENSIONES_VALIDAS = {"png", "jpg", "jpeg", "gif", "webp"}


def _extension_valida(nombre_archivo):
    return "." in nombre_archivo and nombre_archivo.rsplit(".", 1)[1].lower() in EXTENSIONES_VALIDAS


# ---------- Perfil ----------

@main_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        current_user.descripcion = request.form.get("descripcion", "").strip()
        current_user.intereses = request.form.get("intereses", "").strip()
        current_user.pais = request.form.get("pais", "").strip()

        archivo = request.files.get("foto")
        if archivo and archivo.filename and _extension_valida(archivo.filename):
            extension = archivo.filename.rsplit(".", 1)[1].lower()
            mime = "jpeg" if extension == "jpg" else extension
            datos = base64.b64encode(archivo.read()).decode("utf-8")
            current_user.foto = f"data:image/{mime};base64,{datos}"

        db.session.commit()
        return redirect(url_for("main.perfil"))

    return render_template("perfil.html", paises=PAISES)


@main_bp.route("/inicio")
@login_required
def inicio():
    solicitudes = Solicitud.query.filter_by(
        receptor_id=current_user.id, estado="pendiente"
    ).all()

    from models import Chat, Mensaje
    from estado import calcular_estado

    todos_los_chats = Chat.query.filter(
        or_(Chat.usuario1_id == current_user.id, Chat.usuario2_id == current_user.id)
    ).all()

    historial = []
    for c in todos_los_chats:
        no_leidos = c.mensajes.filter_by(leido=False).filter(
            Mensaje.emisor_id != current_user.id
        ).count()
        cantidad_total = c.mensajes.count()
        historial.append({
            "chat_id": c.id,
            "otro": c.otro_usuario(current_user.id),
            "no_leidos": no_leidos,
            "cantidad_mensajes": cantidad_total,
            "estado": calcular_estado(c.otro_usuario(current_user.id)),
        })
    historial.sort(key=lambda h: h["cantidad_mensajes"], reverse=True)
    historial = historial[:5]

    conectados_ids = {h["otro"].id for h in historial} | {c.otro_usuario(current_user.id).id for c in todos_los_chats}
    bloqueados_ids = {b.bloqueado_id for b in Bloqueo.query.filter_by(usuario_id=current_user.id).all()}
    me_bloquearon_ids = {b.usuario_id for b in Bloqueo.query.filter_by(bloqueado_id=current_user.id).all()}
    excluir = conectados_ids | bloqueados_ids | me_bloquearon_ids | {current_user.id}

    candidatos = Usuario.query.filter(~Usuario.id.in_(excluir)).order_by(db.func.random()).limit(8).all()
    recomendados = [{"usuario": u, "estado": calcular_estado(u)} for u in candidatos]

    return render_template("inicio.html", solicitudes=solicitudes, historial=historial,
                            recomendados=recomendados)


# ---------- Buscador general (para enviar solicitudes nuevas) ----------

@main_bp.route("/api/buscar-usuarios")
@login_required
def buscar_usuarios():
    """Filtrado en tiempo real mientras se escribe. Excluye al propio usuario
    y calcula el estado de relación con cada resultado (ninguno / pendiente /
    aceptada / bloqueado) para que el frontend muestre el botón correcto."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    bloqueados_ids = {b.bloqueado_id for b in
                       Bloqueo.query.filter_by(usuario_id=current_user.id).all()}
    me_bloquearon_ids = {b.usuario_id for b in
                          Bloqueo.query.filter_by(bloqueado_id=current_user.id).all()}

    resultados = (
        Usuario.query.filter(
            Usuario.usuario_publico.ilike(f"%{q}%"),
            Usuario.id != current_user.id,
        ).limit(15).all()
    )

    data = []
    for u in resultados:
        if u.id in bloqueados_ids or u.id in me_bloquearon_ids:
            continue  # no aparece en la búsqueda para ninguno de los dos

        estado = "ninguno"
        sol = Solicitud.query.filter(
            or_(
                and_(Solicitud.emisor_id == current_user.id, Solicitud.receptor_id == u.id),
                and_(Solicitud.emisor_id == u.id, Solicitud.receptor_id == current_user.id),
            )
        ).order_by(Solicitud.fecha.desc()).first()

        if sol:
            estado = sol.estado if sol.estado != "rechazada" else "ninguno"

        data.append({
            "id": u.id,
            "usuario_publico": u.usuario_publico,
            "foto": u.foto,
            "estado": estado,
        })
    return jsonify(data)


@main_bp.route("/api/solicitud/enviar/<int:receptor_id>", methods=["POST"])
@login_required
def enviar_solicitud(receptor_id):
    ya_bloqueado = Bloqueo.query.filter_by(
        usuario_id=receptor_id, bloqueado_id=current_user.id
    ).first()
    if ya_bloqueado:
        return jsonify({"ok": False, "mensaje": "No puedes enviar solicitud a este usuario."}), 403

    existente = Solicitud.query.filter_by(
        emisor_id=current_user.id, receptor_id=receptor_id, estado="pendiente"
    ).first()
    if existente:
        return jsonify({"ok": False, "mensaje": "Ya enviaste una solicitud."}), 400

    nueva = Solicitud(emisor_id=current_user.id, receptor_id=receptor_id)
    db.session.add(nueva)
    db.session.commit()

    socketio.emit("nueva_solicitud", {
        "solicitud_id": nueva.id,
        "usuario_publico": current_user.usuario_publico,
        "descripcion": current_user.descripcion or "",
        "intereses": current_user.intereses or "",
        "foto": current_user.foto,
    }, room=f"user_{receptor_id}")

    return jsonify({"ok": True})


@main_bp.route("/api/solicitud/<int:solicitud_id>/<accion>", methods=["POST"])
@login_required
def responder_solicitud(solicitud_id, accion):
    sol = Solicitud.query.get_or_404(solicitud_id)
    if sol.receptor_id != current_user.id:
        return jsonify({"ok": False}), 403

    if accion == "aceptar":
        sol.estado = "aceptada"
        from models import Chat
        chat = Chat(usuario1_id=sol.emisor_id, usuario2_id=sol.receptor_id)
        db.session.add(chat)
    elif accion == "rechazar":
        sol.estado = "rechazada"
    else:
        return jsonify({"ok": False}), 400

    db.session.commit()
    return jsonify({"ok": True})


# ---------- Bloqueos ----------

@main_bp.route("/bloqueados")
@login_required
def bloqueados():
    lista = Bloqueo.query.filter_by(usuario_id=current_user.id).all()
    return render_template("bloqueados.html", bloqueos=lista)


@main_bp.route("/api/bloquear/<int:usuario_id>", methods=["POST"])
@login_required
def bloquear(usuario_id):
    if not Bloqueo.query.filter_by(usuario_id=current_user.id, bloqueado_id=usuario_id).first():
        db.session.add(Bloqueo(usuario_id=current_user.id, bloqueado_id=usuario_id))
        db.session.commit()
    return jsonify({"ok": True})


@main_bp.route("/api/desbloquear/<int:usuario_id>", methods=["POST"])
@login_required
def desbloquear(usuario_id):
    Bloqueo.query.filter_by(usuario_id=current_user.id, bloqueado_id=usuario_id).delete()
    db.session.commit()
    return jsonify({"ok": True})


# ---------- Configuración (paleta, tamaño y tipo de letra) ----------

@main_bp.route("/configuracion", methods=["GET", "POST"])
@login_required
def configuracion():
    pref = current_user.preferencia or Preferencia(usuario_id=current_user.id)

    if request.method == "POST":
        pref.color_primario = request.form.get("color_primario", pref.color_primario)
        pref.color_fondo = request.form.get("color_fondo", pref.color_fondo)
        pref.tamano_letra = request.form.get("tamano_letra", pref.tamano_letra)
        pref.tipo_letra = request.form.get("tipo_letra", pref.tipo_letra)
        pref.mostrar_estado = request.form.get("mostrar_estado") == "on"
        db.session.add(pref)
        db.session.commit()
        return redirect(url_for("main.configuracion"))

    return render_template("configuracion.html", pref=pref)


@main_bp.route("/api/configuracion/restablecer", methods=["POST"])
@login_required
def restablecer_configuracion():
    pref = current_user.preferencia
    pref.color_primario = "#FF9644"
    pref.color_fondo = "#FFFDF1"
    pref.tamano_letra = "mediano"
    pref.tipo_letra = "Poppins"
    pref.mostrar_estado = True
    db.session.commit()
    return jsonify({"ok": True})
