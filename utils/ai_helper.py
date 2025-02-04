import os
import json
from datetime import datetime
import google.generativeai as genai
from utils.prompts import SchedulingPrompts

class GenerativeAI:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        self.model = genai.GenerativeModel('gemini-pro')

    def get_schedule_recommendation(self, video_data, scheduled_videos):
        """Get scheduling recommendation for a video"""
        try:
            # Get the complete prompt from SchedulingPrompts
            prompt = SchedulingPrompts.get_scheduling_prompt(video_data, scheduled_videos)
            
            # Get response from AI
            response = self.model.generate_content(prompt)
            
            # Clean and parse the response
            cleaned_response = response.text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:-3]  # Remove ```json and ```
            # Remove an extra outer pair of curly braces if present
            if cleaned_response.startswith('{{') and cleaned_response.endswith('}}'):
                cleaned_response = cleaned_response[1:-1]
            
            recommendation = json.loads(cleaned_response)
            
            # Validate the response format
            self._validate_schedule_recommendation(recommendation)
            
            return recommendation
            
        except Exception as e:
            print(f"Error getting AI recommendation: {e}")
            print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return None

    def _validate_schedule_recommendation(self, recommendation):
        """Validate the schedule recommendation format"""
        required_keys = ['recommended_hour', 'recommended_date', 'reasoning']
        if not all(key in recommendation for key in required_keys):
            raise ValueError("Missing required keys in recommendation")
            
        if not isinstance(recommendation['recommended_hour'], int):
            raise ValueError("recommended_hour must be an integer")
            
        # Validate date format
        datetime.strptime(recommendation['recommended_date'], '%Y-%m-%d') 