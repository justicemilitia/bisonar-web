from flask import Blueprint

saas_bp = Blueprint('saas', __name__, url_prefix='/saas')

from saas.api.routes import api_bp
saas_bp.register_blueprint(api_bp, url_prefix='/api/v1')