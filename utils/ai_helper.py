import os
import json
from datetime import datetime
import google.generativeai as genai
from utils.prompts import SchedulingPrompts

class GenerativeAI:
    def __init__(self):
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def get_schedule_recommendation(self, video_data, scheduled_videos):
        """
        Single entry point that first gets the optimal hour slot,
        then determines the earliest available day for that slot.
        """
        slot_recommendation = self._get_slot_recommendation(video_data)
        if not slot_recommendation:
            return None

        day_recommendation = self._get_day_recommendation(video_data, scheduled_videos, slot_recommendation)
        if not day_recommendation:
            return None

        merged_recommendation = {
            "recommended_hour": slot_recommendation["recommended_hour"],
            "recommended_date": day_recommendation["recommended_date"],
            "reasoning": f"{slot_recommendation.get('reasoning', '')} {day_recommendation.get('reasoning', '')}".strip()
        }

        # Validate the final output format
        self._validate_schedule_recommendation(merged_recommendation)

        return merged_recommendation

    def _get_slot_recommendation(self, video_data):
        """Get the optimal hour slot for the video."""
        try:
            prompt = SchedulingPrompts.get_slot_prompt(video_data)
            print(prompt)
            generation_config = {"temperature": 0}
            response = self.model.generate_content(prompt, generation_config=generation_config)
            print(response)
            cleaned_response = self._clean_response(response.text)
            slot_recommendation = json.loads(cleaned_response)
            self._validate_slot_recommendation(slot_recommendation)
            return slot_recommendation
        except Exception as e:
            print(f"Error in slot recommendation: {e}")
            return None

    def _get_day_recommendation(self, video_data, scheduled_videos, slot_recommendation):
        """Get the earliest available day for the determined slot."""
        try:
            prompt = SchedulingPrompts.get_day_prompt(video_data, scheduled_videos, slot_recommendation)
            print(prompt)
            generation_config = {"temperature": 0}
            response = self.model.generate_content(prompt, generation_config=generation_config)
            print(response)
            cleaned_response = self._clean_response(response.text)
            day_recommendation = json.loads(cleaned_response)
            self._validate_day_recommendation(day_recommendation)
            return day_recommendation
        except Exception as e:
            print(f"Error in day recommendation: {e}")
            return None

    def _clean_response(self, text):
        cleaned_response = text.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:-3]  # Remove ```json and ```
        if cleaned_response.startswith('{{') and cleaned_response.endswith('}}'):
            cleaned_response = cleaned_response[1:-1]
        return cleaned_response

    def _validate_slot_recommendation(self, recommendation):
        if 'recommended_hour' not in recommendation:
            raise ValueError("Missing recommended_hour in slot recommendation")
        if not isinstance(recommendation['recommended_hour'], int):
            raise ValueError("recommended_hour must be an integer")

    def _validate_day_recommendation(self, recommendation):
        required_keys = ['recommended_date', 'reasoning']
        if not all(key in recommendation for key in required_keys):
            raise ValueError("Missing required keys in day recommendation")
        datetime.strptime(recommendation['recommended_date'], '%Y-%m-%d')

    def _validate_schedule_recommendation(self, recommendation):
        required_keys = ['recommended_hour', 'recommended_date', 'reasoning']
        if not all(key in recommendation for key in required_keys):
            raise ValueError("Missing required keys in final recommendation")
        if not isinstance(recommendation['recommended_hour'], int):
            raise ValueError("recommended_hour must be an integer")
        datetime.strptime(recommendation['recommended_date'], '%Y-%m-%d')