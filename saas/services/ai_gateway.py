import requests
import os
from saas.config import OPENAI_CONFIG

class AIGateway:
    @staticmethod
    def generate_response(customer_id, message, conversation_history):
        """AI yanıtı oluştur - SİZİN OpenAI key'inizle"""
        from saas.models.customer import CustomerModel
        
        customer = CustomerModel.get_customer_by_id(customer_id)
        if not customer:
            raise Exception("Customer not found")
        
        model = customer.get('ai_model') or 'gpt-3.5-turbo'
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f"Bearer {OPENAI_CONFIG['api_key']}",
                    'Content-Type': 'application/json'
                },
                json={
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': customer.get('custom_prompt', 'You are a helpful assistant.')},
                        *conversation_history,
                        {'role': 'user', 'content': message}
                    ],
                    'max_tokens': customer.get('max_tokens', 200),
                    'temperature': customer.get('temperature', 0.7)
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get('usage', {})
                
                # Token kullanımını kaydet
                from saas.models.usage import UsageModel
                cost = AIGateway.calculate_cost(usage, model)
                UsageModel.record_openai_usage(customer_id, 'session_id', usage, model, cost)
                
                return {
                    'response': result['choices'][0]['message']['content'],
                    'usage': usage
                }
            else:
                raise Exception(f"OpenAI API error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"AI service error: {str(e)}")
    
    @staticmethod
    def calculate_cost(usage, model):
        """Token maliyetini hesapla"""
        rates = {
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.0020},
            'gpt-4-turbo': {'input': 0.0100, 'output': 0.0300}
        }
        
        model_rates = rates.get(model, rates['gpt-3.5-turbo'])
        cost = (usage.get('prompt_tokens', 0) * model_rates['input'] + 
                usage.get('completion_tokens', 0) * model_rates['output']) / 1000
        
        return cost