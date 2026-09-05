from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import Usuario, Preferencia

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def inicio_seccion():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    return render_template("inicio_seccion.html")


# ---------- Registro en 4 pasos (datos temporales en sesión) ----------

@auth_bp.route("/registro", methods=["GET", "POST"])
def registro_credenciales():
    if request.method == "POST":
        correo = request.form["correo"].strip().lower()
        contrasena = request.form["contrasena"]
        confirmar = request.form.get("confirmar_contrasena", "")
        acepta = request.form.get("acepta_terminos")

        if Usuario.query.filter_by(correo=correo).first():
            flash("Ese correo ya está registrado.")
            return redirect(url_for("auth.registro_credenciales"))

        if not acepta:
            flash("Debes aceptar los Términos de Uso y la Política de Privacidad para continuar.")
            return redirect(url_for("auth.registro_credenciales"))

        if len(contrasena) < 8 or not any(c.isdigit() for c in contrasena) or not any(c.isalpha() for c in contrasena):
            flash("La contraseña debe tener al menos 8 caracteres, incluyendo letras y números.")
            return redirect(url_for("auth.registro_credenciales"))

        if contrasena != confirmar:
            flash("Las contraseñas no coinciden.")
            return redirect(url_for("auth.registro_credenciales"))

        session["registro"] = {
            "correo": correo,
            "contrasena_hash": bcrypt.generate_password_hash(contrasena).decode("utf-8"),
        }
        return redirect(url_for("auth.registro_usuario"))
    return render_template("registro_credenciales.html")


@auth_bp.route("/registro/usuario", methods=["GET", "POST"])
def registro_usuario():
    if "registro" not in session:
        return redirect(url_for("auth.registro_credenciales"))

    if request.method == "POST":
        usuario_publico = request.form["usuario_publico"].strip()

        if Usuario.query.filter_by(usuario_publico=usuario_publico).first():
            flash("Ese nombre de usuario ya existe, elige otro.")
            return redirect(url_for("auth.registro_usuario"))

        session["registro"]["usuario_publico"] = usuario_publico
        session.modified = True
        return redirect(url_for("auth.registro_perfil"))
    return render_template("registro_usuario.html")


@auth_bp.route("/registro/perfil", methods=["GET", "POST"])
def registro_perfil():
    if "registro" not in session:
        return redirect(url_for("auth.registro_credenciales"))

    if request.method == "POST":
        session["registro"]["descripcion"] = request.form.get("descripcion", "").strip()
        session.modified = True
        return redirect(url_for("auth.registro_intereses"))
    return render_template("registro_perfil.html")


@auth_bp.route("/registro/intereses", methods=["GET", "POST"])
def registro_intereses():
    if "registro" not in session:
        return redirect(url_for("auth.registro_credenciales"))

    if request.method == "POST":
        intereses = request.form.get("intereses", "").strip()
        datos = session.pop("registro")

        nuevo = Usuario(
            correo=datos["correo"],
            contrasena_hash=datos["contrasena_hash"],
            usuario_publico=datos["usuario_publico"],
            descripcion=datos.get("descripcion", ""),
            intereses=intereses,
        )
        db.session.add(nuevo)
        db.session.flush()  # para tener nuevo.id antes del commit

        db.session.add(Preferencia(usuario_id=nuevo.id))
        db.session.commit()

        login_user(nuevo)
        return redirect(url_for("main.inicio"))
    return render_template("registro_intereses.html")


# ---------- Login / Logout ----------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"].strip().lower()
        contrasena = request.form["contrasena"]

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and bcrypt.check_password_hash(usuario.contrasena_hash, contrasena):
            login_user(usuario)
            return redirect(url_for("main.inicio"))

        flash("Correo o contraseña incorrectos.")
        return redirect(url_for("auth.login"))
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.inicio_seccion"))
