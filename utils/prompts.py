import json

class SchedulingPrompts:
    ROLE_SLOT_BLOCK = """
    You are a world class climber that knows deeply about both V-Scale and Font Scale bouldering grade scales.
    """

    ROLE_DAY_BLOCK = """
    You are a seasoned YouTube Scheduling Strategist with a proven track record of maximizing video reach and viewer engagement.
    
    You also are a world class climber that knows about both V-Scale and Font Scale bouldering grade scales and all the bouldering areas in the world.
    """

    SHORT_SLOTS = """
    Hour Slots:
        - 23:00h UTC previous day: Outside Europe (mostly US), any bouldering grade.
        - 07:00h UTC: Europe, bouldering grade lower than 6a+.
        - 11:00h UTC: Europe, bouldering grade between 6a+ and 6c.
        - 15:00h UTC: Europe, bouldering grade between 6b+ and 7b.
        - 19:00h UTC: Europe, bouldering grade 7b+ and above.
    """

    REGULAR_SLOTS = """
    Hour Slots:
        - 23:00h UTC previous day: Outside Europe (mostly US), bouldering grade V5 and above.
        - 07:00h UTC: Outside Europe (mostly US), bouldering grade below V5.
        - 13:00h UTC: Europe, bouldering grade lower than 7a+.
        - 19:00h UTC: Europe, bouldering grade 7a+ and above.
    """

    TASK_SLOT_BLOCK = """
    TASK: Determine the optimal hour slot for this video based solely on its details and the available hour slots.
    First, analyze the bouldering area to decide if it is located in Europe or outside Europe.
    Then compare the bouldering grade with the bouldering grade in the slots.
    Then, based on this categorization and the available hour slots, choose the best hour slot.
    Respond in JSON with keys:
    - "recommended_hour": The chosen hour (as an integer HH, representing UTC hour).
    - "reasoning": A brief explanation for your choice.
    """

    TASK_DAY_BLOCK = """
    TASK: Determine the earliest available date for this video, which must be scheduled at {assigned_hour} UTC. Consider the following constraints:
        - Identify the first available date where **the {assigned_hour} UTC time slot** is unoccupied.
        - Ensure that no other time slots on that day contain the same climber or bouldering area.
    Respond ONLY in JSON with keys:
        - "recommended_date": The chosen date in YYYY-MM-DD format.
        - "reasoning": A brief explanation for your choice.

    IMPORTANT: Return hours in UTC.
    """

    SPECIFICS_BLOCK = """
    - This task is crucial to the success of our business, so please provide a thorought analysis of the provided data.
    - Your accurate categorization of the area and the grade is greatly appreciated and contributes to the efficiency of our operations.
    """

    CONTEXT_SLOT_SHORTS_BLOCK = """
    Slot Examples:
        - (Bouldering Crag: Fontainebleau, Grade: 7a+) fits onto 15:00h UTC Slot
        - (Bouldering Crag: Targasonne, Grade: 5) fits onto 07:00h UTC Slot
        - (Bouldering Crag: Magic Wood, Grade: 8b+) fits onto 19:00h UTC Slot
        - (Bouldering Crag: Peak District, Grade: 6b+) fits onto 11:00h UTC Slot
        - (Bouldering Crag: Magic Wood, Grade: 7c+) fits onto 19:00h UTC Slot
        - (Bouldering Crag: Red Rocks, Grade: V8) fits onto 23:00h UTC Slot
    """

    CONTEXT_SLOT_BLOCK = """
    Slot Examples:
        - (Bouldering Crag: Fontainebleau, Grade: 7a+) fits onto 13:00h UTC Slot
        - (Bouldering Crag: Targasonne, Grade: 5) fits onto 13:00h UTC Slot
        - (Bouldering Crag: Magic Wood, Grade: 8b+) fits onto 19:00h UTC Slot
        - (Bouldering Crag: Peak District, Grade: 7b+) fits onto 19:00h UTC Slot
        - (Bouldering Crag: Red Rocks, Grade: V8) fits onto 23:00h UTC Slot
        - (Bouldering Crag: Stonefort, Grade: V2) fits onto 07:00h UTC Slot
    """

    CONTEXT_DAY_BLOCK = """
    """

    NOTES_SLOT_BLOCK = """
    """

    NOTES_DAY_BLOCK = """
    Before returning a response, re-evaluate whether your chosen time slot is actually free and does not conflict with any existing schedules.
    """

    @classmethod
    def format_video_details(cls, video_data):
        return f"""
        New video details:
        - Bouldering Crag: {video_data['zone']}
        - Grade: {video_data.get('grade', 'Unknown')}
        - Climber: {video_data.get('climber', 'Unknown')}
        """

    @classmethod
    def format_scheduled_videos(cls, scheduled_videos, is_short):
        """
        Filters the scheduled videos based on video type and returns the formatted string.
        Only scheduled videos with the same format (short/regular) are included.
        """
        filtered_videos = [
            video for video in scheduled_videos
            if video.get('isShort', False) == is_short
        ]
        filtered_videos  = sorted(filtered_videos , key=lambda x: x['scheduledTime'])
    
        formatted_videos = []
        for video in filtered_videos:
            formatted_videos.append({
                "date": video['scheduledTime'].strftime('%Y-%m-%d'),
                "hour slot": video['scheduledTime'].hour,
                "climber": video.get('climber', 'Unknown').strip(),
                "crag": video.get('zone', 'Unknown').strip()
            })
        
        return {"scheduled_videos": formatted_videos}

    @classmethod
    def get_slot_prompt(cls, video_data):
        slots = cls.SHORT_SLOTS if video_data['is_short'] else cls.REGULAR_SLOTS
        examples = cls.CONTEXT_SLOT_SHORTS_BLOCK if video_data['is_short'] else cls.CONTEXT_SLOT_BLOCK

        return f"""
        {cls.ROLE_SLOT_BLOCK}

        {cls.SPECIFICS_BLOCK}
        
        {cls.TASK_SLOT_BLOCK}
        
        {cls.format_video_details(video_data)}
        
        {slots}
        
        {examples}
        
        {cls.NOTES_SLOT_BLOCK}
        """

    @classmethod
    def get_day_prompt(cls, video_data, scheduled_videos, slot_recommendation):
        """Generate the complete scheduling prompt"""
        scheduled_videos_json = json.dumps(
            cls.format_scheduled_videos(scheduled_videos, video_data['is_short']), 
            indent=4
        )
        task_day_block = cls.TASK_DAY_BLOCK.format(assigned_hour=slot_recommendation['recommended_hour'])  # Format dynamically
        return f"""
        {cls.ROLE_DAY_BLOCK}

        {cls.SPECIFICS_BLOCK}

        {task_day_block}

        Currently scheduled videos (JSON format for clarity):
        ```json
        {scheduled_videos_json}
        ```        
        {cls.format_video_details(video_data)}
        
        
        {cls.CONTEXT_DAY_BLOCK}
        
        {cls.NOTES_DAY_BLOCK}
        """


class ContentPrompts:
    # Future prompts for content generation, tag suggestions, etc.
    pass 