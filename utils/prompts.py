class SchedulingPrompts:
    ROLE_BLOCK = """
    You are a seasoned YouTube Scheduling Strategist with a proven track record of maximizing video reach and viewer engagement.
    
    You also are a world class climber that knows about both V-Scale and Font Scale bouldering grade scales.

    Scheduling Rules:
        1. Each time slot musty only have one video per day
        2. The same climber must only appear once per day
        3. The same zone/area must only appear once per day
        4. If a slot is taken or any other rule is violated on a given day, recommend the next available day

    Hour Slots:
        Video Type Short:
        - 23:00h UTC previous day: Outside Europe (mostly US), any bouldering grade
        - 07:00h UTC: Europe, bouldering grade lower than 6a+.
        - 11:00h UTC: Europe, bouldering grade between 6a+ and 6c.
        - 15:00h UTC: Europe, bouldering grade between 6b+ and 7b.
        - 19:00h UTC: Europe, bouldering grade higher than 7b+.

    Video Type Regular:
        - 23:00h UTC previous day: Outside Europe (mostly US), bouldering grade above V5
        - 07:00h UTC: Outside Europe (mostly US), bouldering grade below V5
        - 13:00h UTC: Europe, bouldering grade lower than 7a+.
        - 19:00h UTC: Europe, bouldering grade higher than 7a+.
    """

    TASK_BLOCK = """
    Propose the best time slot for the new video considering today and the current hour as the starting point and based on your scheduling rules and currently scheduled videos.

    Use the following step-by-step process:
        1. Analyze the new video data.
        2. Determine if zone is inside or outside Europe.
        3. Determine, based on the grade and video type, the best hour slot fit.
        4. Search for the first hour slot available for video type from .
        5. For each potential day, verify that:
            - The time slot for this type of video is not already taken.
            - The same climber is not already scheduled.
            - The same zone is not already scheduled.
        6. Look for the earliest available day that meets ALL criteria

    You must respond with ONLY a JSON object in this exact format:
    {{
        "recommended_hour": 12,
        "recommended_date": "2025-02-04",
        "reasoning": "This slot was chosen because..."
    }}

    IMPORTANT: Return hours in UTC.
    """

    SPECIFICS_BLOCK = """
    - This task is crucial to the success of our business, so please provide a thorought analysis of the provided data.
    - Your accurate categorization of the area and the grade is greatly appreciated and contributes to the efficiency of our operations.
    """

    CONTEXT_BLOCK = """
    Slot Examples:
        - (Zone: Fontainebleau, Grade: 7a+, Type: Short) fits onto Short 15:00h UTC Slot
        - (Zone: Targasonne, Grade: 5, Type: Short) fits onto Short 07:00h UTC Slot
        - (Zone: Magic Wood, Grade: 8b+, Type: Short) fits onto Short 19:00h UTC Slot
        - (Zone: Peak District, Grade: 6b+, Type: Short) fits onto Short 11:00h UTC Slot
    """

    NOTES_BLOCK = """
    """

    @classmethod
    def format_video_details(cls, video_data):
        return f"""
        New video details:
        - Zone: {video_data['zone']}
        - Grade: {video_data.get('grade', 'Unknown')}
        - Climber: {video_data.get('climber', 'Unknown')}
        - Type: {'Short' if video_data['is_short'] else 'Regular'}
        """

    @classmethod
    def format_scheduled_videos(cls, scheduled_videos):
        """Format currently scheduled videos for the prompt"""
        # Sort the scheduled_videos by scheduledTime in ascending order
        scheduled_videos = sorted(scheduled_videos, key=lambda x: x['scheduledTime'])
    
        slots = "\nCurrently scheduled videos:\n"
        for video in scheduled_videos:
            slots += (
                f"{video['scheduledTime'].strftime('%Y-%m-%d %H:%M')} "
                f"(Type: {video.get('type', 'Unknown')}, "
                f"Climber: {video.get('climber', 'Unknown').strip()}, "
                f"Zone: {video.get('zone', 'Unknown').strip()}, "
                f"Grade: {video.get('grade', 'Unknown').strip()})\n"
            )
        return slots

    @classmethod
    def get_scheduling_prompt(cls, video_data, scheduled_videos):
        """Generate the complete scheduling prompt"""
        return f"""
        {cls.ROLE_BLOCK}

        {cls.format_scheduled_videos(scheduled_videos)}
        
        {cls.format_video_details(video_data)}        
        
        {cls.TASK_BLOCK}
        
        {cls.SPECIFICS_BLOCK}
        
        {cls.CONTEXT_BLOCK}
        
        {cls.NOTES_BLOCK}
        """


class ContentPrompts:
    # Future prompts for content generation, tag suggestions, etc.
    pass 