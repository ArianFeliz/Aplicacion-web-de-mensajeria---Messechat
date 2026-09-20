# MesseChat

App web de mensajería en tiempo real hecha con **Flask + Flask-SocketIO** y base de datos **PostgreSQL en Neon**.

ABRE AQUÍ https://aplicacion-web-de-mensajeria-messechat.onrender.com

## Estructura del proyecto

```
messechat/
  app.py            <- arranca la app
  config.py         <- configuración (.env)
  extensions.py     <- db, socketio, login, bcrypt
  models.py         <- tablas: Usuario, Solicitud, Bloqueo, Chat, Mensaje, Preferencia
  estado.py         <- cálculo de "Activo / Inactivo / hace X tiempo"
  paises.py         <- lista de países con bandera
  auth.py           <- registro y login
  main.py           <- inicio, buscador, solicitudes, bloqueos, perfil, configuración
  chat.py           <- pantalla de chat y eventos en tiempo real
  templates/        <- todas las pantallas (HTML)
  static/css/style.css   <- estilos, paleta y modo oscuro
```
