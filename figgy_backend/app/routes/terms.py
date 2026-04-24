from flask import Blueprint, jsonify, request
from app.models import terms_store

# Blueprint
terms_bp = Blueprint('terms', __name__, url_prefix='/api/terms')

@terms_bp.route('/', methods=['GET'])
def get_terms():
    """GET /api/terms - Retrieves T&C based on language and version."""
    lang = request.args.get('language', 'English')
    version = request.args.get('version', '1.0')
    
    terms_data = terms_store.get_terms(language=lang, version=version)
    return jsonify({
        "status": "success",
        "data": terms_data
    }), 200

@terms_bp.route('/current', methods=['GET'])
def get_current_terms():
    """GET /api/terms/current - Retrieves latest T&C version info."""
    lang = request.args.get('language', 'English')
    version = terms_store.get_current_version()
    
    terms_data = terms_store.get_terms(language=lang, version=version)
    return jsonify({
        "status": "success",
        "version": version,
        "data": terms_data
    }), 200
