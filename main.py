import os
import subprocess
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Button, Label, Input, ListView, ListItem
from textual.screen import Screen

class YouTubeScreen(Screen):
    """유튜브 재생 화면"""
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("유튜브 영상 URL을 입력하세요:", classes="title"),
            Input(placeholder="https://www.youtube.com/watch?...", id="yt_url"),
            Button("재생", id="play_yt", variant="success"),
            Button("메인으로", id="back", variant="error")
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "play_yt":
            url_input = self.query_one("#yt_url", Input)
            url = url_input.value
            if url:
                self.app.notify(f"영상 재생 시작: {url}")
                # mpv를 사용하여 yt-dlp로 영상을 스트리밍 재생합니다.
                # 참고: 라즈베리파이 콘솔 환경(X11 없음)에서는 --vo=drm 옵션이 유용할 수 있습니다.
                try:
                    subprocess.Popen(['mpv', url])
                except Exception as e:
                    self.app.notify(f"실행 오류: {e}", severity="error")

class GameScreen(Screen):
    """ROM 게임 실행 화면"""
    ROM_DIR = "roms"
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        # ROM 폴더가 없으면 생성
        if not os.path.exists(self.ROM_DIR):
            os.makedirs(self.ROM_DIR)
            
        roms = os.listdir(self.ROM_DIR)
        
        yield Container(
            Label("게임 목록 (roms 폴더 내 파일):", classes="title"),
            ListView(
                *[ListItem(Label(rom), id=f"rom_{i}") for i, rom in enumerate(roms)],
                id="rom_list"
            ),
            Button("메인으로", id="back", variant="error")
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
        
        self.app.notify(f"게임 실행: {selected_rom}")
        try:
            # RetroArch를 이용해 게임을 실행 (라즈베리파이 환경에 맞춰 코어 경로나 명령어 수정 필요)
            subprocess.Popen(['retroarch', rom_path])
        except Exception as e:
            self.app.notify(f"실행 오류: {e}", severity="error")

class MainScreen(Screen):
    """메인 메뉴 화면"""
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_menu"):
            yield Label("라즈베리파이 미디어 & 게임 런처", id="main_title")
            yield Button("1. 유튜브", id="btn_youtube", variant="primary")
            yield Button("2. ROM 게임", id="btn_games", variant="primary")
            yield Button("3. 시스템 종료", id="btn_shutdown", variant="warning")
            yield Button("종료(TUI 닫기)", id="btn_quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_youtube":
            self.app.push_screen(YouTubeScreen())
        elif event.button.id == "btn_games":
            self.app.push_screen(GameScreen())
        elif event.button.id == "btn_shutdown":
            self.app.notify("시스템을 종료합니다...")
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        elif event.button.id == "btn_quit":
            self.app.exit()

class LauncherApp(App):
    """라즈베리파이 TUI 애플리케이션"""
    
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
        ("q", "quit", "프로그램 종료"),
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

if __name__ == "__main__":
    app = LauncherApp()
    app.run()
