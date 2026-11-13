import importlib.util

from ...core.tools import registry
from . import auth


def _fmt(items):
    out = []
    for i in items:
        vid = i.get("id", {}).get("videoId", "")
        sn = i["snippet"]
        out.append(f"[{vid}] {sn['title']} — {sn['channelTitle']} ({sn['publishedAt'][:10]})")
    return "\n".join(out) or "No results."


def search_videos(query: str, max_results: int = 5):
    r = auth.service("youtube", "v3").search().list(part="snippet", q=query, type="video", maxResults=max_results).execute()
    return _fmt(r.get("items", []))


def my_subscriptions(max_results: int = 25):
    r = auth.service("youtube", "v3").subscriptions().list(part="snippet", mine=True, maxResults=max_results).execute()
    return "\n".join(f"[{i['snippet']['resourceId']['channelId']}] {i['snippet']['title']}" for i in r.get("items", [])) \
        or "No subscriptions."


def channel_latest(channel_id: str, max_results: int = 5):
    r = auth.service("youtube", "v3").search().list(part="snippet", channelId=channel_id, order="date",
                                                    type="video", maxResults=max_results).execute()
    return _fmt(r.get("items", []))


def get_transcript(video_id: str):
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        text = " ".join(s.text for s in YouTubeTranscriptApi().fetch(video_id))
    except (TypeError, AttributeError):  # older library versions
        text = " ".join(d["text"] for d in YouTubeTranscriptApi.get_transcript(video_id))
    return text[:6000]


def register():
    registry.tool("youtube_search_videos", "Search YouTube videos.", {"type": "object", "properties": {
        "query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}, risk="read")(search_videos)
    registry.tool("youtube_my_subscriptions", "List channels the user is subscribed to.", auth.opt(max_results="integer"),
                  risk="read")(my_subscriptions)
    registry.tool("youtube_channel_latest", "Latest videos from a channel id.", {"type": "object", "properties": {
        "channel_id": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["channel_id"]},
        risk="read")(channel_latest)
    if importlib.util.find_spec("youtube_transcript_api"):
        registry.tool("youtube_get_transcript", "Get the transcript of a video (for summarizing).",
                      auth.obj(video_id="string"), risk="read")(get_transcript)
