import os
import json
import subprocess
import urllib.request
import urllib.parse
import zipfile
from textual import work
from textual.app import App, ComposeResult
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

PLAYLIST_ID = "RDBDsb_w3hHVU"

class YouTubeScreen(Screen):
    """YouTube Playback Screen with Playlist Support"""
    def __init__(self):
        super().__init__()
        self.videos = []
        self.current_process = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("YouTube Playlist (240p Mode):", classes="title"),
            Label("재생목록을 불러오는 중입니다...", id="yt_status"),
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
        if not api_key:
            self.app.call_from_thread(self.app.notify, "YOUTUBE_API_KEY not found in .env", severity="error")
            self.app.call_from_thread(self.update_status, "API 키가 .env에 없습니다.")
            return

        url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={PLAYLIST_ID}&maxResults=25&key={api_key}"
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                items = res_data.get('items', [])
                
                videos_data = []
                for i, item in enumerate(items):
                    title = item['snippet']['title']
                    video_id = item['snippet']['resourceId']['videoId']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    videos_data.append((title, video_url))

                self.app.call_from_thread(self.populate_playlist, videos_data)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"API Error: {e}", severity="error")
            self.app.call_from_thread(self.update_status, f"로딩 실패: {e}")

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
        else:
            self.update_status("재생목록 항목이 없습니다.")

    def play_video(self, url: str, title: str = "") -> None:
        if url:
            display_title = title if title else url
            self.app.notify(f"240p 재생 시작: {display_title}")
            
            # 이전 재생 중인 영상이 있으면 종료
            self.stop_current_video()

            try:
                # Force 240p playback using mpv ytdl-format option and rotate counter-clockwise (270 degrees)
                self.current_process = subprocess.Popen([
                    'mpv',
                    '--ytdl-format=bestvideo[height<=240]+bestaudio/best[height<=240]',
                    '--video-rotate=270',
                    url
                ])
            except Exception as e:
                self.app.notify(f"재생 오류: {e}", severity="error")

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

CORE_MAP = {
    ".nes": ["fceumm", "nestopia", "quicknes"],
    ".sfc": ["snes9x", "snes9x2010", "bsnes"],
    ".smc": ["snes9x", "snes9x2010", "bsnes"],
    ".gba": ["mgba", "vba_next", "vbam"],
    ".gb": ["gambatte", "mgba", "sameboy"],
    ".gbc": ["gambatte", "mgba", "sameboy"],
    ".md": ["genesis_plus_gx", "picodrive"],
    ".gen": ["genesis_plus_gx", "picodrive"],
    ".smd": ["genesis_plus_gx", "picodrive"],
    ".gg": ["genesis_plus_gx", "gearsystem"],
    ".sms": ["genesis_plus_gx", "gearsystem"],
    ".n64": ["mupen64plus_next", "parallel_n64"],
    ".z64": ["mupen64plus_next", "parallel_n64"],
    ".v64": ["mupen64plus_next", "parallel_n64"],
    ".pce": ["beetle_pce_fast", "mednafen_pce_fast"],
}

CORE_SEARCH_DIRS = [
    "/usr/lib/aarch64-linux-gnu/libretro",
    "/usr/lib/arm-linux-gnueabihf/libretro",
    "/usr/lib/libretro",
    os.path.expanduser("~/.config/retroarch/cores")
]

def find_libretro_core(rom_path: str) -> str | None:
    ext = os.path.splitext(rom_path)[1].lower()
    
    # zip 파일인 경우 압축 내부 파일의 확장자 확인
    if ext == ".zip" and zipfile.is_zipfile(rom_path):
        try:
            with zipfile.ZipFile(rom_path, 'r') as z:
                for filename in z.namelist():
                    inner_ext = os.path.splitext(filename)[1].lower()
                    if inner_ext in CORE_MAP:
                        ext = inner_ext
                        break
        except Exception:
            pass

    candidates = CORE_MAP.get(ext, [])
    if not candidates:
        return None

    found_cores = []
    for search_dir in CORE_SEARCH_DIRS:
        if os.path.exists(search_dir):
            for file_name in os.listdir(search_dir):
                if file_name.endswith("_libretro.so"):
                    full_path = os.path.join(search_dir, file_name)
                    if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                        found_cores.append(full_path)
    
    # 확장자 기반 매칭 탐색
    for core_path in found_cores:
        core_name = os.path.basename(core_path).lower()
        for cand in candidates:
            if cand in core_name:
                return core_path

    # 매칭되는 적절한 코어가 없으면 None 반환 (잘못된 코어 강제 전달 방지)
    return None

class GameScreen(Screen):
    """ROM Game Execution Screen"""
    ROM_DIR = "roms"
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        # Create ROM folder if it doesn't exist
        if not os.path.exists(self.ROM_DIR):
            os.makedirs(self.ROM_DIR)
            
        roms = os.listdir(self.ROM_DIR)
        
        yield Container(
            Label("Game List (files in roms folder):", classes="title"),
            ListView(
                *[ListItem(Label(rom), id=f"rom_{i}") for i, rom in enumerate(roms)],
                id="rom_list"
            ),
            Button("Back to Main", id="back", variant="error")
        )
        yield Footer()
        
        self.rom_files = roms

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = int(event.item.id.split("_")[1])
        selected_rom = self.rom_files[index]
        rom_path = os.path.join(self.ROM_DIR, selected_rom)
        
        core_path = find_libretro_core(rom_path)
        cmd = ['retroarch']
        if core_path:
            cmd.extend(['-L', core_path])
            self.app.notify(f"Launching game: {selected_rom} ({os.path.basename(core_path)})")
        else:
            self.app.notify(f"Launching game: {selected_rom} (No matching core found)")

        cmd.append(rom_path)

        try:
            # Launch game using RetroArch with detected core
            subprocess.Popen(cmd)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

class MainScreen(Screen):
    """Main Menu Screen"""
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_menu"):
            yield Label("Raspberry Pi Media & Game Launcher", id="main_title")
            yield Button("1. YouTube", id="btn_youtube", variant="primary")
            yield Button("2. ROM Games", id="btn_games", variant="primary")
            yield Button("3. Shutdown System", id="btn_shutdown", variant="warning")
            yield Button("Quit TUI", id="btn_quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_youtube":
            self.app.push_screen(YouTubeScreen())
        elif event.button.id == "btn_games":
            self.app.push_screen(GameScreen())
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
        ("q", "quit", "Quit Application"),
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

if __name__ == "__main__":
    app = LauncherApp()
    app.run()

