import requests
from saas.models.customer import CustomerModel

class N8nCoordinator:
    def __init__(self):
        self.n8n_webhook_url = "https://g30rnaqf.rpcld.co/webhook/f3dc844f-ae75-45d3-b96e-8ade4a9f07bf"
    
    def send_to_n8n(self, customer_id, message_data):
        """n8n'e müşteri konfigürasyonu ile birlikte data gönder"""
        try:
            # Müşteri konfigürasyonunu getir
            customer_config = CustomerModel.get_customer_by_id(customer_id)
            if not customer_config:
                raise Exception("Customer configuration not found")
            
            print(f"🎯 Sending to n8n - Customer: {customer_config.get('name')}")
            
            # n8n'e gönderilecek payload
            payload = {
                'message': message_data.get('message', ''),
                'sessionId': message_data.get('sessionId', ''),
                'userId': message_data.get('userId', ''),
                'customer_config': {
                    'customer_id': customer_id,
                    'business_name': customer_config.get('business_name'),
                    'business_type': customer_config.get('business_type'),
                    'services': customer_config.get('services', []),
                    'custom_prompt': customer_config.get('custom_prompt', ''),
                    'telegram_enabled': customer_config.get('receive_notifications', True),
                    'calendar_enabled': customer_config.get('auto_create_events', True),
                }
            }
            
            print(f"📡 Payload to n8n: {payload}")
            
            # Kullanımı kaydet
            CustomerModel.increment_usage(customer_id, message_count=1)
            
            # n8n'e gönder
            response = requests.post(
                self.n8n_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"📡 n8n response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ n8n response type: {type(result)}")
                print(f"✅ n8n response: {result}")
                
                # ✅ FIX: n8n array döndürüyorsa ilk elemanı al
                if isinstance(result, list) and len(result) > 0:
                    print("🎯 Taking first item from n8n array response")
                    result = result[0]
                
                # ✅ FIX: Response'dan gerekli field'ları al
                if isinstance(result, dict):
                    return {
                        'response': result.get('response', 'Üzgünüm, yanıt oluşturulamadı.'),
                        'quickReplies': result.get('quickReplies', ['Daha Fazla Bilgi', 'Danışmanlık İste', 'Fiyat Teklifi Al']),
                        'session': result.get('session', {})
                    }
                else:
                    raise Exception(f"Unexpected n8n response format: {type(result)}")
                    
            else:
                print(f"❌ n8n error: {response.status_code} - {response.text}")
                raise Exception(f"n8n error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ n8n coordinator error: {e}")
            raise