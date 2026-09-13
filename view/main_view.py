import pathlib
from datetime import datetime

import customtkinter as ctk
from PIL import Image
import ctypes
from tkinter import messagebox
from model.theme_manager import ThemeManager
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

    # Password required before opening configuration pages.
    # Change this value to the required operator password.
    ACCESS_PASSWORD = "1111"

    def __init__(self, viewmodel=None):
        super().__init__()

        self.vm = viewmodel
        self.theme_manager = ThemeManager()

        self.title("")
        self._remove_windows_titlebar(self)

        # Keep the main application hidden until the complete interface has
        # been initialized. Startup work is scheduled through Tk's event
        # loop so the loading dialog can actually paint and update.
        self._set_theme_appearance_mode()

        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()

        self.withdraw()
        self.geometry(f"{self.width}x{self.height}+0+0")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.title(
            self.theme_manager.get(
                "window.title",
                "HUMAN DETECTION & MONITORING",
            )
        )
        self.configure(
            fg_color=self._theme_color(
                "colors.window_background",
                "#111111",
            )
        )

        self.auto_viewmodel = None
        self.teach_viewmodel = None
        self.system_viewmodel = None
        self.header = None
        self.footer = None
        self.content = None
        self.auto_view = None
        self.teach_view = None
        self.system_view = None
        self.currentContent = None

        self._create_startup_dialog()
        self._startup_progress(0, "Starting application...")

        # Initialization is deliberately deferred until the Tk event loop is
        # running.  This is the important difference from the previous
        # implementation: the splash is painted before expensive model/view
        # construction begins.
        self.after(50, self._startup_step_models)

    # -------------------------------------------------------------
    # Startup loading overlay
    # -------------------------------------------------------------
    def _create_startup_dialog(self):
        """Create a standalone themed startup dialog before building the UI."""
        frame_bg = self._theme_color(
            "colors.frame_background",
            "#1B1B1B",
        )
        text_primary = self._theme_color(
            "colors.text_primary",
            "#F2F2F2",
        )
        text_secondary = self._theme_color(
            "colors.text_secondary",
            "#B8B8B8",
        )
        window_bg = self._theme_color(
            "colors.window_background",
            "#111111",
        )
        button_color = self._theme_color(
            "colors.button.foreground",
            "#2D6A4F",
        )
        border_color = self._theme_color(
            "colors.frame_foreground",
            "#252525",
        )

        self.startup_dialog = ctk.CTkToplevel(self)
        self.startup_dialog.title("")
        self._remove_windows_titlebar(self.startup_dialog)
        self.startup_dialog.resizable(False, False)
        self.startup_dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: None,
        )

        dialog_width = 520
        dialog_height = 190

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - dialog_width) // 2)
        y = max(0, (screen_height - dialog_height) // 2)

        self.startup_dialog.geometry(
            f"{dialog_width}x{dialog_height}+{x}+{y}"
        )
        self.startup_dialog.configure(fg_color=window_bg)

        # Keep the startup dialog above other windows while the main
        # application is intentionally withdrawn.
        try:
            self.startup_dialog.attributes("-topmost", True)
        except Exception:
            pass

        self.startup_dialog.grab_set()

        dialog = ctk.CTkFrame(
            self.startup_dialog,
            fg_color=frame_bg,
            corner_radius=12,
            border_width=1,
            border_color=border_color,
        )
        dialog.pack(
            fill="both",
            expand=True,
            padx=1,
            pady=1,
        )

        title = ctk.CTkLabel(
            dialog,
            text=self.theme_manager.get(
                "window.title",
                "HUMAN DETECTION & MONITORING",
            ),
            text_color=text_primary,
            font=self._theme_font(
                "view_title",
                fallback_size=22,
                fallback_weight="bold",
            ),
        )
        title.pack(padx=20, pady=(20, 5))

        self.startup_status = ctk.CTkLabel(
            dialog,
            text="Starting application...",
            text_color=text_secondary,
            font=self._theme_font(
                "normal",
                fallback_size=14,
            ),
        )
        self.startup_status.pack(padx=20, pady=(0, 12))

        self.startup_progress_bar = ctk.CTkProgressBar(
            dialog,
            width=440,
            height=16,
            fg_color=window_bg,
            progress_color=button_color,
        )
        self.startup_progress_bar.pack(padx=20, pady=(0, 8))
        self.startup_progress_bar.set(0.0)

        self.startup_percent = ctk.CTkLabel(
            dialog,
            text="0%",
            text_color=text_secondary,
            font=self._theme_font(
                "normal",
                fallback_size=12,
            ),
        )
        self.startup_percent.pack(padx=20, pady=(0, 12))

        # Force the splash to paint while the root is still hidden.
        self.startup_dialog.update_idletasks()
        self.startup_dialog.update()

    def _startup_progress(self, value, message):
        """Update and render startup progress on the standalone splash."""
        progress = getattr(self, "startup_progress_bar", None)
        dialog = getattr(self, "startup_dialog", None)

        if progress is None or dialog is None:
            return

        value = max(0, min(100, int(value)))
        self.startup_status.configure(text=str(message))
        progress.set(value / 100.0)
        self.startup_percent.configure(text=f"{value}%")

        try:
            dialog.update_idletasks()
            dialog.update()
        except Exception:
            pass

    def _close_startup_dialog(self):
        dialog = getattr(self, "startup_dialog", None)
        if dialog is None:
            return

        try:
            if dialog.grab_current() == str(dialog):
                dialog.grab_release()
        except Exception:
            pass

        try:
            dialog.destroy()
        except Exception:
            pass

        self.startup_dialog = None
        self.startup_progress_bar = None
        self.startup_status = None
        self.startup_percent = None

    # -------------------------------------------------------------
    # Startup initialization steps
    # -------------------------------------------------------------
    def _startup_step_models(self):
        self._startup_progress(10, "Loading AI detection system...")

        self.auto_viewmodel = (
            self.vm
            if self.vm is not None
            else AutoViewModel()
        )

        self._startup_progress(45, "AI detection system loaded.")
        self.after(10, self._startup_step_viewmodels)

    def _startup_step_viewmodels(self):
        self._startup_progress(50, "Loading configuration panels...")

        self.teach_viewmodel = TeachViewModel(
            camera_count=self.auto_viewmodel.camera_count,
            auto_viewmodel=self.auto_viewmodel,
        )

        self.system_viewmodel = SystemViewModel()
        self._startup_progress(60, "Configuration panels loaded.")
        self.after(10, self._startup_step_layout)

    def _startup_step_layout(self):
        self._startup_progress(65, "Building application interface...")
        self._build_layout()
        self._startup_progress(85, "Application interface built.")
        self.after(10, self._startup_step_theme)

    def _startup_step_theme(self):
        self._startup_progress(90, "Applying theme...")
        self._apply_shell_theme()
        self.after(10, self._startup_step_ready)

    def _startup_step_ready(self):
        self._show_auto_view()
        self._startup_progress(100, "Ready")

        # Give the final UI one event-loop pass to finish geometry and theme
        # redraws before revealing it.
        self.after_idle(self._finish_startup)

    def _finish_startup(self):
        self._close_startup_dialog()

        # Reveal the fully constructed application first.
        self.deiconify()

        try:
            self.state("zoomed")
        except Exception:
            pass

        self.update_idletasks()

        # Now that the main window is visible and the camera widgets have
        # real dimensions, capture one preview frame for each camera.
        if self.auto_view is not None:
            self.auto_view.capture_initial_preview()

    # -------------------------------------------------------------
    # Theme
    # -------------------------------------------------------------
    def _set_theme_appearance_mode(self):
        mode = self.theme_manager.get(
            "appearance.mode",
            "dark",
        )

        if str(mode).lower() == "system":
            ctk.set_appearance_mode("System")
        elif str(mode).lower() == "light":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def _theme_color(self, path, fallback):
        value = self.theme_manager.get(path, fallback)
        return value if isinstance(value, str) else fallback

    def _theme_font(self, name, fallback_family="Arial", fallback_size=14,
                    fallback_weight="normal"):
        font = self.theme_manager.get(f"fonts.{name}", {})
        if not isinstance(font, dict):
            font = {}

        family = str(font.get("family", fallback_family))
        try:
            size = int(font.get("size", fallback_size))
        except (TypeError, ValueError):
            size = fallback_size

        weight = str(font.get("weight", fallback_weight))

        return ctk.CTkFont(
            family=family,
            size=size,
            weight=weight,
        )

    def _apply_shell_theme(self):
        colors = {
            "window": self._theme_color(
                "colors.window_background",
                "#F2F2F2",
            ),
            "frame": self._theme_color(
                "colors.frame_background",
                "#FFFFFF",
            ),
            "button": self._theme_color(
                "colors.button.foreground",
                "#1F6AA5",
            ),
            "button_hover": self._theme_color(
                "colors.button.hover",
                "#144870",
            ),
            "button_text": self._theme_color(
                "colors.button.text",
                "#FFFFFF",
            ),
            "button_disabled": self._theme_color(
                "colors.button.disabled",
                "#A0A0A0",
            ),
            "text_primary": self._theme_color(
                "colors.text_primary",
                "#111111",
            ),
            "text_secondary": self._theme_color(
                "colors.text_secondary",
                "#555555",
            ),
        }

        if hasattr(self, "header"):
            self.configure(fg_color=colors["window"])
            self.header.configure(fg_color=colors["frame"])
            self.footer.configure(fg_color=colors["frame"])
            self.content.configure(fg_color=colors["frame"])

        header_title_font = self._theme_font(
            "header_title",
            fallback_size=36,
            fallback_weight="bold",
        )
        header_time_font = self._theme_font(
            "header_time",
            fallback_size=22,
        )
        footer_font = self._theme_font(
            "footer_button",
            fallback_size=22,
            fallback_weight="bold",
        )

        if hasattr(self, "header_title"):
            self.header_title.configure(
                text=self.theme_manager.get(
                    "header.title",
                    self.theme_manager.get(
                        "window.title",
                        "HUMAN DETECTION & MONITORING",
                    ),
                ),
                text_color=colors["text_primary"],
                font=header_title_font,
            )

        if hasattr(self, "header_time"):
            self.header_time.configure(
                text_color=colors["text_secondary"],
                font=header_time_font,
            )

        if hasattr(self, "auto_button"):
            self._apply_footer_button_theme(
                self.auto_button,
                "AUTO",
                footer_font,
                colors,
            )
            self._apply_footer_button_theme(
                self.teach_button,
                "TEACH",
                footer_font,
                colors,
            )
            self._apply_footer_button_theme(
                self.system_button,
                "SYSTEM",
                footer_font,
                colors,
            )
            self._apply_footer_button_theme(
                self.exit_button,
                "EXIT",
                footer_font,
                colors,
            )
            self._apply_footer_button_theme(
                self.start_button,
                "START",
                footer_font,
                colors,
            )

        title = self.theme_manager.get(
            "window.title",
            "HUMAN DETECTION & MONITORING",
        )
        self.title(title)

    def _apply_footer_button_theme(self, button, key, font, colors):
        settings = self.theme_manager.get(
            f"footer.buttons.{key}",
            {},
        )
        if not isinstance(settings, dict):
            settings = {}

        text = settings.get("text", key)
        if key == "START":
            text = (
                settings.get("stop_text", "STOP")
                if getattr(self.auto_viewmodel, "is_monitoring", False)
                else settings.get("text", "START")
            )

        button.configure(
            text=text,
            font=font,
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["button_text"],
            height=self.theme_manager.get(
                "dimensions.footer.button_height",
                40,
            ),
            corner_radius=self.theme_manager.get(
                "dimensions.footer.button_corner_radius",
                10,
            ),
            state=("normal" if settings.get("enabled", True) else "disabled"),
        )

        if not settings.get("visible", True):
            button.grid_remove()
        else:
            button.grid()

    def reload_theme(self):
        """
        Reload the saved theme.json and apply it to the application shell.

        Child views can be rebuilt by MainView when their runtime
        configuration changes; this method deliberately limits itself
        to the shell so header/footer placement and behavior remain
        unchanged.
        """
        self.theme_manager.reload(notify=False)
        self._set_theme_appearance_mode()
        self._apply_shell_theme()

    # -------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---------------------------------------------------------
        # Logo
        # ---------------------------------------------------------
        logo_size = self.theme_manager.get(
            "header.logo_size",
            [150, 70],
        )
        if not isinstance(logo_size, (list, tuple)) or len(logo_size) != 2:
            logo_size = [150, 70]

        try:
            logo_size = (int(logo_size[0]), int(logo_size[1]))
        except (TypeError, ValueError):
            logo_size = (150, 70)

        logo_path = get_logo_path()
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path),
            dark_image=Image.open(logo_path),
            size=logo_size,
        )

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------
        self.header = ctk.CTkFrame(self)
        self.header.grid(
            row=0,
            column=0,
            padx=self.theme_manager.get("dimensions.header.padding_x", 5),
            pady=self.theme_manager.get("dimensions.header.padding_y", 5),
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
        self.header_logo.bind("<Double-1>", self._minimize)

        self.header_title = ctk.CTkLabel(
            self.header,
            text="",
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
            padx=self.theme_manager.get("dimensions.footer.padding_x", 5),
            pady=self.theme_manager.get("dimensions.footer.padding_y", 5),
            sticky="sew",
        )

        self.footer.grid_columnconfigure(
            (0, 1, 2, 3, 4),
            weight=1,
        )
        self.footer.grid_rowconfigure(0, weight=1)

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
            command=self._request_teach_access,
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
            command=self._request_system_access,
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
            command=self._confirm_exit,
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
            padx=self.theme_manager.get("dimensions.content.padding_x", 5),
            pady=self.theme_manager.get("dimensions.content.padding_y", 0),
            sticky="nsew",
        )

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

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

    # -------------------------------------------------------------
    # View switching
    # -------------------------------------------------------------
    def _hide_current_view(self):
        if self.currentContent is not None:
            self.currentContent.grid_forget()

    def _show_auto_view(self):
        if (
            self.currentContent is self.system_view
            and not self.auto_viewmodel.is_monitoring
        ):
            self._reload_operational_configuration()

        self._hide_current_view()

        self.currentContent = self.auto_view
        self.currentContent.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

        self._apply_footer_button_theme(
            self.start_button,
            "START",
            self._theme_font(
                "footer_button",
                fallback_size=22,
                fallback_weight="bold",
            ),
            {
                "button": self._theme_color(
                    "colors.button.foreground",
                    "#1F6AA5",
                ),
                "button_hover": self._theme_color(
                    "colors.button.hover",
                    "#144870",
                ),
                "button_text": self._theme_color(
                    "colors.button.text",
                    "#FFFFFF",
                ),
                "button_disabled": self._theme_color(
                    "colors.button.disabled",
                    "#A0A0A0",
                ),
            },
        )

    def _show_teach_view(self):
        if self.auto_viewmodel.is_monitoring:
            return

        if self.currentContent is self.system_view:
            self._reload_operational_configuration()

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

        if self.auto_viewmodel.is_monitoring:
            return


        self._hide_current_view()

        self.currentContent = self.system_view
        self.currentContent.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

    def _reload_operational_configuration(self):
        old_auto_viewmodel = self.auto_viewmodel

        if old_auto_viewmodel is not None:
            try:
                old_auto_viewmodel.shutdown()
            except Exception:
                pass

        self.auto_viewmodel = AutoViewModel()

        self.teach_viewmodel = TeachViewModel(
            camera_count=self.auto_viewmodel.camera_count,
            auto_viewmodel=self.auto_viewmodel,
        )

        if self.auto_view is not None:
            self.auto_view.destroy()

        if self.teach_view is not None:
            self.teach_view.destroy()

        self.auto_view = AutoView(
            self.content,
            viewmodel=self.auto_viewmodel,
        )

        self.teach_view = TeachView(
            self.content,
            viewmodel=self.teach_viewmodel,
            camera_count=self.auto_viewmodel.camera_count,
        )

        self.reload_theme()

        self.start_button.configure(
            text=self.theme_manager.get(
                "footer.buttons.START.text",
                "START",
            )
        )

    # -------------------------------------------------------------
    # Monitoring control
    # -------------------------------------------------------------
    def _toggle_monitoring(self):
        if self.currentContent is not self.auto_view:
            self._show_auto_view()

        if self.auto_viewmodel.is_monitoring:
            self.auto_view.stop_monitoring()

            self._set_monitoring_navigation_state(
                False
            )

            self._update_start_button_text()
            return

        started = self.auto_view.start_monitoring()

        if started:
            self._set_monitoring_navigation_state(
                True
            )

            self._update_start_button_text()
    def _update_start_button_text(self):
        if self.auto_viewmodel.is_monitoring:
            text = self.theme_manager.get(
                "footer.buttons.START.stop_text",
                "STOP",
            )
        else:
            text = self.theme_manager.get(
                "footer.buttons.START.text",
                "START",
            )

        self.start_button.configure(text=text)

    # -------------------------------------------------------------
    # Clock
    # -------------------------------------------------------------
    def _update_time(self):
        current_time = datetime.now().strftime("%I:%M:%S %p")
        self.header_time.configure(text=current_time)

        self.after(1000, self._update_time)

    # -------------------------------------------------------------
    # Window controls
    # -------------------------------------------------------------
    def _minimize(self, event=None):
        from ctypes import wintypes

        try:
            hwnd = wintypes.HWND(self.winfo_id())

            # Get the real top-level window handle.
            root_hwnd = ctypes.windll.user32.GetAncestor(
                hwnd,
                2,  # GA_ROOT
            )

            if root_hwnd:
                ctypes.windll.user32.ShowWindow(
                    root_hwnd,
                    6,  # SW_MINIMIZE
                )

        except Exception:
            pass
    def _close(self):
        try:
            if self.auto_view is not None:
                self.auto_view.stop_monitoring()

            if self.auto_viewmodel is not None:
                self.auto_viewmodel.shutdown()

        finally:
            self.destroy()

    def _remove_windows_titlebar(self, window):
        import ctypes

        window.update_idletasks()

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        if not hwnd:
            hwnd = window.winfo_id()

        GWL_STYLE = -16
        WS_CAPTION = 0x00C00000

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32 = ctypes.windll.user32

        if hasattr(user32, "GetWindowLongPtrW"):
            style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
            user32.SetWindowLongPtrW(
                hwnd,
                GWL_STYLE,
                style & ~WS_CAPTION,
            )
        else:
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(
                hwnd,
                GWL_STYLE,
                style & ~WS_CAPTION,
            )

        user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE
            | SWP_NOSIZE
            | SWP_NOZORDER
            | SWP_NOACTIVATE
            | SWP_FRAMECHANGED,
        )
    # -------------------------------------------------------------
    # Protected page access
    # -------------------------------------------------------------

    def _request_teach_access(self):
        if self.auto_viewmodel.is_monitoring:
            return

        if self._request_password("TEACH"):
            self._show_teach_view()

    def _request_system_access(self):
        if self.auto_viewmodel.is_monitoring:
            return

        if self._request_password("SYSTEM"):
            self._show_system_view()

    def _request_password(self, page_name):
        """
        Ask for the operator password before opening a protected page.

        Returns:
            True when the supplied password is correct.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        self._remove_windows_titlebar(dialog)

        dialog_width = 420
        dialog_height = 220

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max(
            0,
            (screen_width - dialog_width) // 2,
        )
        y = max(
            0,
            (screen_height - dialog_height) // 2,
        )

        dialog.geometry(
            f"{dialog_width}x{dialog_height}+{x}+{y}"
        )
        dialog.resizable(False, False)

        window_bg = self._theme_color(
            "colors.window_background",
            "#111111",
        )
        frame_bg = self._theme_color(
            "colors.frame_background",
            "#1B1B1B",
        )
        border_color = self._theme_color(
            "colors.frame_foreground",
            "#252525",
        )
        text_primary = self._theme_color(
            "colors.text_primary",
            "#F2F2F2",
        )
        text_secondary = self._theme_color(
            "colors.text_secondary",
            "#B8B8B8",
        )
        button_color = self._theme_color(
            "colors.button.foreground",
            "#2D6A4F",
        )
        button_hover = self._theme_color(
            "colors.button.hover",
            "#22543D",
        )
        button_text = self._theme_color(
            "colors.button.text",
            "#FFFFFF",
        )

        dialog.configure(
            fg_color=window_bg
        )

        container = ctk.CTkFrame(
            dialog,
            fg_color=frame_bg,
            corner_radius=12,
            border_width=1,
            border_color=border_color,
        )
        container.pack(
            fill="both",
            expand=True,
            padx=1,
            pady=1,
        )

        title = ctk.CTkLabel(
            container,
            text=f"{page_name} ACCESS",
            text_color=text_primary,
            font=self._theme_font(
                "view_title",
                fallback_size=22,
                fallback_weight="bold",
            ),
        )
        title.pack(
            padx=20,
            pady=(22, 5),
        )

        instruction = ctk.CTkLabel(
            container,
            text="Enter operator password",
            text_color=text_secondary,
            font=self._theme_font(
                "normal",
                fallback_size=14,
            ),
        )
        instruction.pack(
            padx=20,
            pady=(0, 12),
        )

        password_entry = ctk.CTkEntry(
            container,
            width=280,
            show="*",
            font=self._theme_font(
                "normal",
                fallback_size=14,
            ),
        )
        password_entry.pack(
            padx=20,
            pady=(0, 15),
        )

        result = {
            "authenticated": False,
        }

        def submit():
            password = password_entry.get()

            if password == self.ACCESS_PASSWORD:
                result["authenticated"] = True
                dialog.destroy()
                return

            error_label.configure(
                text="Incorrect password."
            )

            password_entry.delete(
                0,
                "end",
            )
            password_entry.focus_set()

        def cancel():
            dialog.destroy()

        button_frame = ctk.CTkFrame(
            container,
            fg_color="transparent",
        )
        button_frame.pack(
            padx=20,
            pady=(0, 15),
        )

        ctk.CTkButton(
            button_frame,
            text="CANCEL",
            command=cancel,
            width=120,
            fg_color=border_color,
            hover_color=button_hover,
            text_color=button_text,
        ).grid(
            row=0,
            column=0,
            padx=5,
        )

        ctk.CTkButton(
            button_frame,
            text="ENTER",
            command=submit,
            width=120,
            fg_color=button_color,
            hover_color=button_hover,
            text_color=button_text,
        ).grid(
            row=0,
            column=1,
            padx=5,
        )

        error_label = ctk.CTkLabel(
            container,
            text="",
            text_color="#D9534F",
            font=self._theme_font(
                "normal",
                fallback_size=12,
            ),
        )
        error_label.pack(
            padx=20,
            pady=(0, 5),
        )

        password_entry.bind(
            "<Return>",
            lambda event: submit(),
        )
        password_entry.bind(
            "<Escape>",
            lambda event: cancel(),
        )

        dialog.protocol(
            "WM_DELETE_WINDOW",
            cancel,
        )

        try:
            dialog.grab_set()
        except Exception:
            pass

        password_entry.focus_set()

        self.wait_window(dialog)

        return result["authenticated"]

    # -------------------------------------------------------------
    # Exit confirmation
    # -------------------------------------------------------------

    def _confirm_exit(self):
        """
        Ask for confirmation before shutting down the application.
        """
        confirmed = messagebox.askyesno(
            "Exit Application",
            "Are you sure you want to exit?",
            parent=self,
        )

        if confirmed:
            self._close()

    def _set_monitoring_navigation_state(self, monitoring):
        """
        Disable configuration/navigation actions while detection is running.
        """
        state = "disabled" if monitoring else "normal"

        self.teach_button.configure(
            state=state
        )

        self.system_button.configure(
            state=state
        )

        self.exit_button.configure(
            state=state
        )


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
            **kwargs,
        )

