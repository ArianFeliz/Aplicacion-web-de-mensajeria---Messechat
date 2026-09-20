# MesseChat

App web de mensajería en tiempo real hecha con **Flask + Flask-SocketIO** y base de datos **PostgreSQL en Neon**.

## 1. Instalar dependencias

```
python -m venv venv
venv\Scripts\activate        # en Windows
source venv/bin/activate     # en Mac/Linux

pip install -r requirements.txt
```

## 2. Configurar la base de datos

1. Crea un proyecto gratis en https://neon.tech
2. Copia la cadena de conexión ("Connection string")
3. Copia `.env.example` y renómbralo a `.env`
4. Pega tu cadena de conexión en `DATABASE_URL` y pon cualquier texto largo en `SECRET_KEY`

> Si no configuras `.env`, la app usa un archivo local `messechat.db` (SQLite) para poder probarla sin Neon.

## 3. Ejecutar la app

```
python app.py
```

Abre **http://localhost:5000**

## Funciones incluidas

- Registro en 4 pasos con contraseña segura (mínimo 8 caracteres, letras y números, confirmación) y aceptación obligatoria de Términos de Uso / Política de Privacidad (textos de ejemplo — reemplázalos antes de publicar la app a usuarios reales)
- Login / Logout con confirmación al cerrar sesión
- Solicitudes de amistad en tiempo real: enviar, aceptar, rechazar, con notificación instantánea y contador en vivo
- Bloquear / desbloquear usuarios
- Chat en tiempo real (Socket.IO) con burbujas estilo WhatsApp, adjuntar imágenes, copiar/borrar mensajes (para mí o para todos), menú de 3 puntos (ver perfil, vaciar chat, bloquear)
- Estado de actividad en tiempo real (Activo / Inactivo / Activo hace X tiempo), con opción de ocultarlo en Configuración
- Perfil editable: foto, descripción, gustos, país
- Inicio con buscador general, historial de conversaciones (con mensajes no leídos), y personas recomendadas
- Configuración: paleta de colores, tamaño y tipo de letra, modo claro/oscuro
- Diseño con barra lateral consistente en toda la app

## Pendiente / ideas para seguir mejorando

- Migrar de SQLite a Neon en un ambiente de producción real
- Verificación de correo al registrarse
- Notificaciones push del navegador
- Reemplazar los textos de Términos/Privacidad por unos reales (revisados por un abogado) antes de un lanzamiento público

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
