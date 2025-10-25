import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from saas.config import GOOGLE_OAUTH_CONFIG

class CalendarService:
    @staticmethod
    def create_meeting(customer_id, meeting_data):
        """Müşteri adına Google Calendar'da toplantı oluştur"""
        from saas.models.oauth import OAuthModel
        
        access_token = OAuthModel.get_valid_google_token(customer_id)
        if not access_token:
            raise Exception("Google Calendar not connected")
        
        try:
            credentials = Credentials(access_token)
            service = build('calendar', 'v3', credentials=credentials)
            
            event = {
                'summary': meeting_data['title'],
                'description': meeting_data['description'],
                'start': {
                    'dateTime': meeting_data['start_time'],
                    'timeZone': 'Europe/Istanbul',
                },
                'end': {
                    'dateTime': meeting_data['end_time'],
                    'timeZone': 'Europe/Istanbul',
                },
                'attendees': meeting_data['attendees'],
                'conferenceData': {
                    'createRequest': {
                        'requestId': meeting_data['session_id'],
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10}
                    ]
                }
            }
            
            event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            return event
            
        except Exception as e:
            raise Exception(f"Calendar event creation failed: {str(e)}")

    @staticmethod
    def refresh_google_token(refresh_token):
        """Google token'ını refresh et"""
        try:
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': GOOGLE_OAUTH_CONFIG['client_id'],
                'client_secret': GOOGLE_OAUTH_CONFIG['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            })
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Token refresh error: {e}")
            return None