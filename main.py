import os
import subprocess
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Button, Label, Input, ListView, ListItem
from textual.screen import Screen

class YouTubeScreen(Screen):
    """YouTube Playback Screen"""
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Enter YouTube Video URL:", classes="title"),
            Input(placeholder="https://www.youtube.com/watch?...", id="yt_url"),
            Button("Play", id="play_yt", variant="success"),
            Button("Back to Main", id="back", variant="error")
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "play_yt":
            url_input = self.query_one("#yt_url", Input)
            url = url_input.value
            if url:
                self.app.notify(f"Starting playback: {url}")
                # Use mpv to stream the video
                # Note: On RPi console (no X11), --vo=drm might be useful.
                try:
                    subprocess.Popen(['mpv', url])
                except Exception as e:
                    self.app.notify(f"Error: {e}", severity="error")

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
        
        self.app.notify(f"Launching game: {selected_rom}")
        try:
            # Launch game using RetroArch
            subprocess.Popen(['retroarch', rom_path])
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
