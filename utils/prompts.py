class SchedulingPrompts:
    RULES = """
    Scheduling Rules:

    Time Slots:
    Video Type Short:
    - 23:00h UTC previous day: Outside Europe (mostly US), any grade
    - 07:00h UTC: Europe, low grade (3-6a)
    - 11:00h UTC: Europe, mid grade (6a-6c)
    - 15:00h UTC: Europe, advanced grade (6c+-7b)
    - 19:00h UTC: Europe, elite grade (>7b+)
    
    Video Type Regular:
    - 23:00h UTC previous day: Outside Europe (mostly US), grade above V5
    - 07:00h UTC: Outside Europe (mostly US), grade below V5
    - 13:00h UTC: Europe, low-mid grade
    - 19:00h UTC: Europe, advanced-elite grade

    Additional Rules:
    1. Each time slot should only have one video per day
    2. The same climber should not appear multiple times on the same day
    3. The same zone/area should not appear multiple times on the same day
    4. Try to space out videos from the same zone across different days
    5. If a slot is taken or any rule is violated on a given day, recommend the next available day

    IMPORTANT: Return hours in UTC.
    """

    SCHEDULE_REQUEST = """
    Based on these scheduling rules and currently scheduled videos, what is the best time slot for this new video? 
    Consider the video type, grade, location, and scheduling constraints.
    
    Analyze the schedule to:
    1. Find the appropriate hour based on video type and characteristics
    2. Check which days have that hour slot available for video type
    3. For each potential day, verify that:
       - The time slot for this type of video is not already taken
       - The same climber is not already scheduled
       - The same zone is not already scheduled
    4. Look for the earliest available day that meets ALL criteria
    
    You must respond with ONLY a JSON object in this exact format:
    {{
        "recommended_hour": 12,
        "recommended_date": "2025-02-04",
        "reasoning": "This slot was chosen because..."
    }}

    """

    @classmethod
    def format_video_details(cls, video_data):
        return f"""
        New video details:
        - Title: {video_data['title']}
        - Zone: {video_data['zone']}
        - Grade: {video_data['grade']}
        - Climber: {video_data.get('climber', 'Unknown')}
        - Type: {'Short' if video_data['is_short'] else 'Regular'}
        """

    @classmethod
    def format_scheduled_videos(cls, scheduled_videos):
        """Format currently scheduled videos for the prompt"""
        slots = "\nCurrently scheduled videos:\n"
        for video in scheduled_videos:
            slots += (
                f"- {video['title']} "
                f"(Climber: {video['climber']}, "
                f"Zone: {video['zone']}, "
                f"Grade: {video['grade']}) "
                f"at {video['scheduledTime'].strftime('%Y-%m-%d %H:%M')}\n"
            )
        return slots

    @classmethod
    def get_scheduling_prompt(cls, video_data, scheduled_videos):
        """Generate the complete scheduling prompt"""
        return f"""
        {cls.RULES}
        
        {cls.format_video_details(video_data)}
        
        {cls.format_scheduled_videos(scheduled_videos)}
        
        {cls.SCHEDULE_REQUEST}
        """


class ContentPrompts:
    # Future prompts for content generation, tag suggestions, etc.
    pass 