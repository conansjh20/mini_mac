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
        self.app.call_from_thread(self.app.notify, f"재생 준비 중: {title}")
        
        # 이전 재생 중인 영상이 있으면 종료
        self.stop_current_video()

        volume = os.getenv("VOLUME", "100")
        rotate = os.getenv("VIDEO_ROTATE", "270")
        
        mpv_cmd = [
            'mpv',
            '--no-video-rotate',
            f'--video-rotate={rotate}',
            '--ytdl-format=best[height<=240]/bestvideo[height<=240]+bestaudio/best',
            '--cache=yes',
            '--demuxer-max-bytes=20M',
            '--demuxer-readahead-secs=10',
            '--audio-buffer=0.2',
            f'--volume={volume}',
            '--volume-max=200',
        ]
        
        audio_device = os.getenv("AUDIO_DEVICE")
        if audio_device:
            mpv_cmd.append(f'--audio-device={audio_device}')

        mpv_cmd.append(url)
        
        try:
            self.app.call_from_thread(self.app.notify, f"240p 재생 시작: {title}")
            self.current_process = subprocess.Popen(mpv_cmd)
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

class LocalVideoScreen(Screen):
    """Local Video Player Screen for files in ./videos directory"""
    VIDEOS_DIR = "videos"
    VALID_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.ts', '.3gp')

    def __init__(self):
        super().__init__()
        self.video_files = []
        self.current_process = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("로컬 비디오 목록 (videos 폴더):", classes="title"),
            Label("비디오 파일 검색 중...", id="local_status"),
            ListView(id="local_list"),
            Button("새로고침", id="btn_refresh", variant="primary"),
            Button("Back to Main", id="back", variant="error")
        )
        yield Footer()

    def on_mount(self) -> None:
        self.load_videos()

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

    def load_videos(self) -> None:
        if not os.path.exists(self.VIDEOS_DIR):
            try:
                os.makedirs(self.VIDEOS_DIR)
            except Exception:
                pass

        if os.path.exists(self.VIDEOS_DIR):
            files = os.listdir(self.VIDEOS_DIR)
            self.video_files = [f for f in files if f.lower().endswith(self.VALID_EXTENSIONS)]
            self.video_files.sort()
        else:
            self.video_files = []

        list_view = self.query_one("#local_list", ListView)
        list_view.clear()

        for i, f_name in enumerate(self.video_files):
            list_view.append(ListItem(Label(f"{i+1}. {f_name}"), id=f"localitem_{i}"))

        status_label = self.query_one("#local_status", Label)
        if self.video_files:
            status_label.update(f"총 {len(self.video_files)}개의 비디오 파일이 발견되었습니다.")
            list_view.focus()
        else:
            status_label.update("videos 폴더에 비디오 파일이 없습니다.")

    def play_video(self, file_path: str, file_name: str) -> None:
        self.stop_current_video()

        volume = os.getenv("VOLUME", "100")
        rotate = os.getenv("VIDEO_ROTATE", "270")
        
        mpv_cmd = [
            'mpv',
            '--no-video-rotate',
            f'--video-rotate={rotate}',
            '--cache=yes',
            '--demuxer-max-bytes=20M',
            '--demuxer-readahead-secs=10',
            '--audio-buffer=0.2',
            f'--volume={volume}',
            '--volume-max=200',
        ]
        
        audio_device = os.getenv("AUDIO_DEVICE")
        if audio_device:
            mpv_cmd.append(f'--audio-device={audio_device}')

        mpv_cmd.append(file_path)

        try:
            self.app.notify(f"비디오 재생 시작: {file_name}")
            self.current_process = subprocess.Popen(mpv_cmd)
        except Exception as e:
            self.app.notify(f"재생 오류: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.stop_current_video()
            self.app.pop_screen()
        elif event.button.id == "btn_refresh":
            self.load_videos()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id and event.item.id.startswith("localitem_"):
            index = int(event.item.id.split("_")[1])
            if index < len(self.video_files):
                f_name = self.video_files[index]
                full_path = os.path.join(self.VIDEOS_DIR, f_name)
                self.play_video(full_path, f_name)

class MainScreen(Screen):
    """Main Menu Screen"""
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_menu"):
            yield Label("Raspberry Pi Media Launcher", id="main_title")
            yield Button("1. YouTube", id="btn_youtube", variant="primary")
            yield Button("2. Local Videos (videos/)", id="btn_local_videos", variant="primary")
            yield Button("3. Shutdown System", id="btn_shutdown", variant="warning")
            yield Button("Quit TUI", id="btn_quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#btn_youtube", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_youtube":
            self.app.push_screen(YouTubeScreen())
        elif event.button.id == "btn_local_videos":
            self.app.push_screen(LocalVideoScreen())
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

