def build_tiktok_init_payload(caption: str, video_url: str, privacy_level: str = 'SELF_ONLY', *, is_aigc: bool = True) -> dict:
    allowed={'PUBLIC_TO_EVERYONE','MUTUAL_FOLLOW_FRIENDS','FOLLOWER_OF_CREATOR','SELF_ONLY'}
    if privacy_level not in allowed:
        raise ValueError('privacy_level must come from TikTok creator_info options')
    return {
        'post_info': {
            'title': caption[:2200],
            'privacy_level': privacy_level,
            'disable_duet': False,
            'disable_comment': False,
            'disable_stitch': False,
            'is_aigc': bool(is_aigc),
        },
        'source_info': {'source':'PULL_FROM_URL','video_url':video_url},
    }
