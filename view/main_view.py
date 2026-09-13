import customtkinter as ctk
import pathlib
from PIL import Image
from datetime import datetime

from view.auto_view import AutoView
from view.teach_view import TeachView
from view.system_view import SystemView

from viewmodel.auto_viewmodel import AutoViewModel
from viewmodel.teach_viewmodel import TeachViewModel
from viewmodel.system_viewmodel import SystemViewModel


def get_logo_path() -> pathlib.Path:
    path = pathlib.Path(__file__).parent.absolute()
    return path.parent / "assets" / "logo.png"


class MainView(ctk.CTk):
    def __init__(self, viewmodel=None):
        super().__init__()

        self.vm = viewmodel

        # ---------------------------------------------------------
        # Application ViewModels
        # ---------------------------------------------------------
        self.auto_viewmodel = (
            self.vm
            if self.vm is not None
            else AutoViewModel()
        )

        self.teach_viewmodel = TeachViewModel(
            camera_count=self.auto_viewmodel.camera_count,
            auto_viewmodel=self.auto_viewmodel,
        )

        self.system_viewmodel = SystemViewModel()

        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()

        self.state("zoomed")
        self.geometry(
            f"{self.width}x{self.height}+0+0"
        )

        self.protocol(
            "WM_DELETE_WINDOW",
            self._close,
        )

        self.title(
            "HUMAN DETECTION & MONITORING"
        )

        # ---------------------------------------------------------
        # Main frame configuration
        # ---------------------------------------------------------
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---------------------------------------------------------
        # Logo
        # ---------------------------------------------------------
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(get_logo_path()),
            dark_image=Image.open(get_logo_path()),
            size=(150, 70),
        )

        ctk.set_appearance_mode("light")

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------
        self.header = ctk.CTkFrame(self)
        self.header.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="new",
        )

        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_columnconfigure(1, weight=2)
        self.header.grid_columnconfigure(2, weight=1)
        self.header.grid_rowconfigure(0, weight=1)

        self.header_logo = ctk.CTkLabel(
            self.header,
            image=self.logo_image,
            text="",
            cursor="hand2",
        )
        self.header_logo.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nw",
        )
        self.header_logo.bind(
            "<Double-1>",
            self._minimize,
        )

        self.header_title = ctk.CTkLabel(
            self.header,
            text="HUMAN DETECTION & MONITORING",
            font=ctk.CTkFont(
                size=36,
                weight="bold",
            ),
        )
        self.header_title.grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="ew",
        )

        self.header_time = ctk.CTkLabel(
            self.header,
            text="TIME",
            font=ctk.CTkFont(size=22),
        )
        self.header_time.grid(
            row=0,
            column=2,
            padx=5,
            pady=5,
            sticky="e",
        )

        self._update_time()

        # ---------------------------------------------------------
        # Footer
        # ---------------------------------------------------------
        self.footer = ctk.CTkFrame(self)
        self.footer.grid(
            row=2,
            column=0,
            padx=5,
            pady=5,
            sticky="sew",
        )

        self.footer.grid_columnconfigure(
            (0, 1, 2, 3, 4),
            weight=1,
        )
        self.footer.grid_rowconfigure(
            0,
            weight=1,
        )

        self.auto_button = FooterButton(
            self.footer,
            text="AUTO",
            command=self._show_auto_view,
        )
        self.auto_button.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.teach_button = FooterButton(
            self.footer,
            text="TEACH",
            command=self._show_teach_view,
        )
        self.teach_button.grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.system_button = FooterButton(
            self.footer,
            text="SYSTEM",
            command=self._show_system_view,
        )
        self.system_button.grid(
            row=0,
            column=2,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.exit_button = FooterButton(
            self.footer,
            text="EXIT",
            command=self._close,
        )
        self.exit_button.grid(
            row=0,
            column=3,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.start_button = FooterButton(
            self.footer,
            text="START",
            command=self._toggle_monitoring,
        )
        self.start_button.grid(
            row=0,
            column=4,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        # ---------------------------------------------------------
        # Content
        # ---------------------------------------------------------
        self.content = ctk.CTkFrame(self)
        self.content.grid(
            row=1,
            column=0,
            padx=5,
            pady=0,
            sticky="nsew",
        )

        self.content.grid_rowconfigure(
            0,
            weight=1,
        )
        self.content.grid_columnconfigure(
            0,
            weight=1,
        )

        self.currentContent = None

        # Both views are created once and share their ViewModels.
        self.auto_view = AutoView(
            self.content,
            viewmodel=self.auto_viewmodel,
        )

        self.teach_view = TeachView(
            self.content,
            viewmodel=self.teach_viewmodel,
            camera_count=self.auto_viewmodel.camera_count,
        )

        self.system_view = SystemView(
            self.content,
            viewmodel=self.system_viewmodel,
        )

        self._show_auto_view()

    # -------------------------------------------------------------
    # View switching
    # -------------------------------------------------------------
    def _hide_current_view(self):
        if self.currentContent is not None:
            self.currentContent.grid_forget()

    def _show_auto_view(self):
        self._hide_current_view()

        self.currentContent = self.auto_view
        self.currentContent.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

    def _show_teach_view(self):
        # Do not leave cameras running while configuring the counting line.
        if self.auto_viewmodel.is_monitoring:
            self.auto_view.stop_monitoring()
            self.start_button.configure(text="START")

        self._hide_current_view()

        self.currentContent = self.teach_view
        self.currentContent.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

        self.teach_view.select_camera(
            self.teach_view.selected_camera
        )

    def _show_system_view(self):
        # System configuration should not be changed while monitoring.
        if self.auto_viewmodel.is_monitoring:
            self.auto_view.stop_monitoring()
            self.start_button.configure(text="START")

        self._hide_current_view()

        self.currentContent = self.system_view
        self.currentContent.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

    # -------------------------------------------------------------
    # Monitoring control
    # -------------------------------------------------------------
    def _toggle_monitoring(self):
        # START is an Auto View operation.
        if self.currentContent is not self.auto_view:
            self._show_auto_view()

        if self.auto_viewmodel.is_monitoring:
            self.auto_view.stop_monitoring()
            self.start_button.configure(text="START")
            return

        started = self.auto_view.start_monitoring()

        if started:
            self.start_button.configure(text="STOP")

    # -------------------------------------------------------------
    # Clock
    # -------------------------------------------------------------
    def _update_time(self):
        current_time = datetime.now().strftime(
            "%I:%M:%S %p"
        )

        self.header_time.configure(
            text=current_time
        )

        self.after(
            1000,
            self._update_time,
        )

    # -------------------------------------------------------------
    # Window controls
    # -------------------------------------------------------------
    def _minimize(self, event=None):
        self.iconify()

    def _close(self):
        try:
            if self.auto_view is not None:
                self.auto_view.stop_monitoring()

            if self.auto_viewmodel is not None:
                self.auto_viewmodel.shutdown()

        finally:
            self.destroy()


class FooterButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        text,
        command=None,
        **kwargs,
    ):
        super().__init__(
            master,
            text=text,
            command=command,
            font=ctk.CTkFont(
                size=22,
                weight="bold",
            ),
            corner_radius=10,
            height=40,
            **kwargs,
        )
