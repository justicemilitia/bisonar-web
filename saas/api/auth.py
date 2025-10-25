from functools import wraps
from flask import request, jsonify
from saas.models.customer import CustomerModel

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        customer_id = kwargs.get('customer_id')
        
        if not api_key or not customer_id:
            return jsonify({'error': 'API key and customer ID required'}), 401
        
        if not CustomerModel.validate_api_key(customer_id, api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function