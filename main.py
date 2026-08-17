import os
import json
import subprocess
import urllib.request
import urllib.parse
import html
import yt_dlp
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Button, Label, Input, ListView, ListItem
from textual.screen import Screen

def load_dotenv(dotenv_path=".env"):
    """Simple .env loader without external dependencies"""
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

load_dotenv()

CHANNEL_HANDLE = "Quorum_Sensing"
CHANNEL_ID = "UCQK1Iq7dAuh82nthwH8E0GQ"

class YouTubeScreen(Screen):
    """YouTube Playback Screen with Playlist Support"""
    def __init__(self):
        super().__init__()
        self.videos = []
        self.current_process = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label(f"@{CHANNEL_HANDLE} 인기 동영상 (240p Mode):", classes="title"),
            Label("인기 동영상 목록을 불러오는 중입니다...", id="yt_status"),
            ListView(id="yt_list"),
            Button("Back to Main", id="back", variant="error")
        )
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_playlist()

    def on_unmount(self) -> None:
        self.stop_current_video()

    def stop_current_video(self) -> None:
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=1)
            except Exception:
                self.current_process.kill()
            self.current_process = None

    @work(thread=True)
    def fetch_playlist(self) -> None:
        api_key = os.getenv("YOUTUBE_API_KEY")
        videos_data = []

        # 1. Try Official YouTube Data API
        if api_key:
            try:
                search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=viewCount&type=video&maxResults=25&key={api_key}"
                s_req = urllib.request.Request(search_url)
                with urllib.request.urlopen(s_req) as s_res:
                    res_data = json.loads(s_res.read().decode('utf-8'))
                    v_items = res_data.get('items', [])

                    for item in v_items:
                        raw_title = item['snippet']['title']
                        clean_title = html.unescape(raw_title)
                        video_id = item['id']['videoId']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        videos_data.append((clean_title, video_url))
            except Exception:
                videos_data = []

        # 2. Fallback to yt-dlp if API fails or quota exceeded
        if not videos_data:
            try:
                ydl_opts = {
                    'extract_flat': 'in_playlist',
                    'playlistend': 25,
                    'quiet': True,
                    'no_warnings': True,
                }
                popular_url = f"https://www.youtube.com/@{CHANNEL_HANDLE}/videos?view=0&sort=p"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(popular_url, download=False)
                    entries = info.get('entries', [])
                    for entry in entries:
                        title = html.unescape(entry.get('title', 'Untitled'))
                        url = entry.get('url')
                        if not url and entry.get('id'):
                            url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                        if url:
                            videos_data.append((title, url))
            except Exception as e:
                self.app.call_from_thread(self.app.notify, f"목록 불러오기 실패: {e}", severity="error")
                self.app.call_from_thread(self.update_status, f"로딩 실패: {e}")
                return

        if videos_data:
            self.app.call_from_thread(self.populate_playlist, videos_data)
        else:
            self.app.call_from_thread(self.update_status, "재생목록 항목이 없습니다.")

    def update_status(self, msg: str) -> None:
        self.query_one("#yt_status", Label).update(msg)

    def populate_playlist(self, videos_data: list) -> None:
        self.videos = [{"title": t, "url": u} for t, u in videos_data]
        list_view = self.query_one("#yt_list", ListView)
        list_view.clear()

        for i, (title, _) in enumerate(videos_data):
            list_view.append(ListItem(Label(f"{i+1}. {title}"), id=f"ytitem_{i}"))

        if videos_data:
            self.update_status(f"총 {len(videos_data)}개의 노래를 불러왔습니다. 목록에서 곡을 선택하세요.")
            list_view.focus()
        else:
            self.update_status("재생목록 항목이 없습니다.")

    def play_video(self, url: str, title: str = "") -> None:
        if url:
            display_title = title if title else url
            self.play_video_async(url, display_title)

    @work(thread=True)
    def play_video_async(self, url: str, title: str) -> None:
        self.app.call_from_thread(self.app.notify, f"스트림 분석 중: {title}")
        
        # 이전 재생 중인 영상이 있으면 종료
        self.stop_current_video()

        ydl_opts = {
            'format': 'best[height<=240]/bestvideo[height<=240]+bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                video_url = None
                audio_url = None
                
                # 1. 분리된 비디오/오디오 포맷(DASH)인지 체크
                requested_formats = info.get('requested_formats')
                if requested_formats and len(requested_formats) >= 2:
                    for f in requested_formats:
                        vcodec = f.get('vcodec')
                        acodec = f.get('acodec')
                        if vcodec and vcodec != 'none' and not video_url:
                            video_url = f.get('url')
                        if acodec and acodec != 'none' and not audio_url:
                            audio_url = f.get('url')
                
                # 2. 단일 통합 스트림일 경우
                if not video_url:
                    video_url = info.get('url')

                if video_url:
                    mpv_cmd = ['mpv', '--video-rotate=270']
                    if audio_url:
                        mpv_cmd.append(f'--audio-file={audio_url}')
                    mpv_cmd.append(video_url)

                    self.app.call_from_thread(self.app.notify, f"240p (음성 포함) 재생 시작: {title}")
                    self.current_process = subprocess.Popen(mpv_cmd)
                else:
                    self.app.call_from_thread(self.app.notify, "스트림 주소를 찾을 수 없습니다.", severity="error")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"재생 오류: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.stop_current_video()
            self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id and event.item.id.startswith("ytitem_"):
            index = int(event.item.id.split("_")[1])
            if index < len(self.videos):
                video = self.videos[index]
                self.play_video(video["url"], video["title"])

class MainScreen(Screen):
    """Main Menu Screen"""
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_menu"):
            yield Label("Raspberry Pi Media Launcher", id="main_title")
            yield Button("1. YouTube", id="btn_youtube", variant="primary")
            yield Button("2. Shutdown System", id="btn_shutdown", variant="warning")
            yield Button("Quit TUI", id="btn_quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#btn_youtube", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_youtube":
            self.app.push_screen(YouTubeScreen())
        elif event.button.id == "btn_shutdown":
            self.app.notify("Shutting down...")
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        elif event.button.id == "btn_quit":
            self.app.exit()

class LauncherApp(App):
    """Raspberry Pi TUI Application"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    #main_menu {
        width: 50;
        height: auto;
        border: solid green;
        padding: 2;
        align: center middle;
    }
    #main_title {
        text-style: bold;
        padding-bottom: 2;
        content-align: center middle;
        width: 100%;
    }
    Button {
        width: 100%;
        margin-bottom: 1;
    }
    .title {
        text-style: bold;
        margin-bottom: 1;
    }
    ListView {
        height: 10;
        border: solid blue;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit Application"),
        Binding("down", "focus_next", "Focus Next", show=False),
        Binding("up", "focus_previous", "Focus Previous", show=False),
        Binding("right", "focus_next", "Focus Next", show=False),
        Binding("left", "focus_previous", "Focus Previous", show=False),
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

if __name__ == "__main__":
    app = LauncherApp()
    app.run()

