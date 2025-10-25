from flask import Blueprint, request, jsonify
from saas.api.auth import require_api_key
from saas.services.n8n_coordinator import N8nCoordinator
from saas.models.customer import CustomerModel

api_bp = Blueprint('saas_api', __name__)
n8n_coordinator = N8nCoordinator()

@api_bp.route('/chat/<customer_id>', methods=['POST'])
@require_api_key
def chat_endpoint(customer_id):
    """Ana chat endpoint - n8n'e yönlendirir"""
    try:
        data = request.get_json()
        
        # Kullanım kotasını kontrol et
        quota = CustomerModel.check_usage_quota(customer_id)
        if not quota['allowed']:
            return jsonify({
                'error': 'Monthly message limit exceeded',
                'upgrade_url': '/upgrade'
            }), 429
        
        # n8n'e gönder
        n8n_response = n8n_coordinator.send_to_n8n(customer_id, data)
        
        return jsonify({
            'success': True,
            'response': n8n_response.get('response'),
            'quickReplies': n8n_response.get('quickReplies', []),
            'session': n8n_response.get('session', {}),
            'usage': quota
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'fallback_response': 'Üzgünüm, şu anda teknik bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin.'
        }), 500

@api_bp.route('/oauth/google/connect/<customer_id>')
@require_api_key
def google_connect(customer_id):
    """Google OAuth bağlantısı"""
    from saas.config import GOOGLE_OAUTH_CONFIG
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?\
client_id={GOOGLE_OAUTH_CONFIG['client_id']}\
&redirect_uri={GOOGLE_OAUTH_CONFIG['redirect_uri']}\
&response_type=code\
&scope=https://www.googleapis.com/auth/calendar.events\
&access_type=offline\
&state={customer_id}"
    
    return jsonify({'auth_url': auth_url})