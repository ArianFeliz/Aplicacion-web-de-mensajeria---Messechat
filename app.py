import os
from flask import Flask
from config import Config
from extensions import db, socketio, login_manager, bcrypt
from models import Usuario


def crear_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    from auth import auth_bp
    from main import main_bp
    from chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)

    @app.context_processor
    def inyectar_solicitudes_pendientes():
        from flask_login import current_user
        if current_user.is_authenticated:
            from models import Solicitud
            n = Solicitud.query.filter_by(receptor_id=current_user.id, estado="pendiente").count()
            return {"solicitudes_pendientes": n}
        return {"solicitudes_pendientes": 0}

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()

    return app


app = crear_app()

if __name__ == "__main__":
    # eventlet/gevent recomendado en producción; el server de desarrollo
    # de Flask-SocketIO alcanza para probar localmente.
    puerto = int(os.environ.get("PORT", 5000))
    modo_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=puerto, debug=modo_debug,
                 use_reloader=False, allow_unsafe_werkzeug=True)
