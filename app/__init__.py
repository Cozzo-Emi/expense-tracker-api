from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from app.config import Config
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Inicializamos las extensiones
db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(config_class)

    # Vinculamos a la app
    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)

    # Registramos el Blueprint de nuestras rutas (que crearemos en el paso 4)
    from app.routes import api
    app.register_blueprint(api, url_prefix='/api')

    return app