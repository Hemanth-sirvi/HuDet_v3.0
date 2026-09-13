import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
import json
import customtkinter as ctk

from model.theme_manager import ThemeManager


class SystemView(ctk.CTkFrame):
    """
    System View for application and theme configuration.

    The view is responsible for editing values and handing them to the
    SystemViewModel. Persistence and validation remain in the ViewModel.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(self, master, viewmodel=None, **kwargs):
        super().__init__(master, **kwargs)

        self.vm = viewmodel
        self.current_section = None
        self.section_frames = {}

        self.camera_count_var = ctk.StringVar(value="1")
        self.camera_index_vars = []
        self.camera_width_var = ctk.StringVar(value="1280")
        self.camera_height_var = ctk.StringVar(value="720")
        self.application_name_var = ctk.StringVar(
            value="HUMAN DETECTION & MONITORING"
        )

        self.detection_model_path_var = ctk.StringVar()
        self.detection_confidence_var = ctk.StringVar(value="0.5")
        self.detection_image_size_var = ctk.StringVar(value="640")
        self.detection_device_var = ctk.StringVar(value="Auto")

        self.theme_variables = {}
        self.theme_widgets = {}

        self.plc_host_var = ctk.StringVar()
        self.plc_port_var = ctk.StringVar(value="5000")
        self.plc_auto_connect_var = ctk.BooleanVar(value=False)
        self.plc_timeout_var = ctk.StringVar(value="5.0")
        self.plc_buffer_size_var = ctk.StringVar(value="4096")
        self.plc_encoding_var = ctk.StringVar(value="utf-8")

        self._build_layout()
        self._show_section("GENERAL")

    # ------------------------------------------------------------------
    # Main layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)

        # --------------------------------------------------------------
        # Navigation
        # --------------------------------------------------------------
        self.navigation_frame = ctk.CTkFrame(self)
        self.navigation_frame.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.navigation_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.navigation_frame,
            text="SYSTEM",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(
            row=0,
            column=0,
            padx=10,
            pady=(10, 20),
            sticky="ew",
        )

        self.navigation_buttons = {}

        sections = [
            "GENERAL",
            "CAMERAS",
            "DETECTION",
            "PLC",
            "THEME",
        ]

        for row, section in enumerate(sections, start=1):
            button = ctk.CTkButton(
                self.navigation_frame,
                text=section,
                command=lambda name=section: self._show_section(name),
                height=45,
            )
            button.grid(
                row=row,
                column=0,
                padx=10,
                pady=5,
                sticky="ew",
            )
            self.navigation_buttons[section] = button

        self.navigation_frame.grid_rowconfigure(
            len(sections) + 1,
            weight=1,
        )

        # --------------------------------------------------------------
        # Settings workspace
        # --------------------------------------------------------------
        self.workspace_frame = ctk.CTkFrame(self)
        self.workspace_frame.grid(
            row=0,
            column=1,
            padx=(0, 5),
            pady=5,
            sticky="nsew",
        )

        self.workspace_frame.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        self.section_title = ctk.CTkLabel(
            self.workspace_frame,
            text="GENERAL",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.section_title.grid(
            row=0,
            column=0,
            padx=15,
            pady=10,
            sticky="w",
        )

        self.settings_frame = ctk.CTkFrame(self.workspace_frame)
        self.settings_frame.grid(
            row=1,
            column=0,
            padx=10,
            pady=5,
            sticky="nsew",
        )

        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_rowconfigure(0, weight=1)

        # --------------------------------------------------------------
        # Action bar
        # --------------------------------------------------------------
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=5,
            pady=(0, 5),
            sticky="ew",
        )

        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=0)
        self.action_frame.grid_columnconfigure(2, weight=0)

        self.status_label = ctk.CTkLabel(
            self.action_frame,
            text="Ready",
        )
        self.status_label.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="w",
        )

        self.cancel_button = ctk.CTkButton(
            self.action_frame,
            text="CANCEL",
            command=self._cancel,
            width=120,
        )
        self.cancel_button.grid(
            row=0,
            column=1,
            padx=5,
            pady=10,
        )

        self.apply_button = ctk.CTkButton(
            self.action_frame,
            text="APPLY",
            command=self._apply,
            width=120,
        )
        self.apply_button.grid(
            row=0,
            column=2,
            padx=5,
            pady=10,
        )

        self.preview_button = ctk.CTkButton(
            self.action_frame,
            text="PREVIEW",
            command=self._preview_theme,
            width=120,
        )
        self.preview_button.grid(
            row=0,
            column=3,
            padx=(5, 10),
            pady=10,
        )

        self.import_config_button = ctk.CTkButton(
            self.action_frame,
            text="IMPORT CONFIG",
            command=self._import_config,
            width=135,
        )
        self.import_config_button.grid(
            row=0,
            column=4,
            padx=5,
            pady=10,
        )

        self.export_config_button = ctk.CTkButton(
            self.action_frame,
            text="EXPORT CONFIG",
            command=self._export_config,
            width=135,
        )
        self.export_config_button.grid(
            row=0,
            column=5,
            padx=5,
            pady=10,
        )

        self.import_theme_button = ctk.CTkButton(
            self.action_frame,
            text="IMPORT THEME",
            command=self._import_theme,
            width=130,
        )
        self.import_theme_button.grid(
            row=0,
            column=6,
            padx=5,
            pady=10,
        )

        self.export_theme_button = ctk.CTkButton(
            self.action_frame,
            text="EXPORT THEME",
            command=self._export_theme,
            width=130,
        )
        self.export_theme_button.grid(
            row=0,
            column=7,
            padx=(5, 10),
            pady=10,
        )

    # ------------------------------------------------------------------
    # Section navigation
    # ------------------------------------------------------------------
    def _show_section(self, section_name):
        section_name = section_name.upper()

        if section_name not in self.navigation_buttons:
            return

        # Do nothing when the already-selected section is clicked.
        if section_name == self.current_section:
            return

        self.current_section = section_name
        self.section_title.configure(text=section_name)

        for name, button in self.navigation_buttons.items():
            if name == section_name:
                button.configure(fg_color=button.cget("hover_color"))
            else:
                button.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
                )

        self._show_section_frame(section_name)

    def _clear_settings_frame(self):
        # Kept as a compatibility helper. Section frames are persistent and
        # are hidden/shown instead of destroying and recreating them.
        for frame in self.section_frames.values():
            frame.grid_remove()

    def _show_section_frame(self, section_name):
        frame = self._get_or_build_section_frame(section_name)

        for name, section_frame in self.section_frames.items():
            if name == section_name:
                section_frame.grid()
            else:
                section_frame.grid_remove()

    def _get_or_build_section_frame(self, section_name):
        if section_name in self.section_frames:
            return self.section_frames[section_name]

        frame = ctk.CTkFrame(self.settings_frame)
        frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.section_frames[section_name] = frame

        original_settings_frame = self.settings_frame
        self.settings_frame = frame

        try:
            builders = {
                "GENERAL": self._build_general_section,
                "CAMERAS": self._build_cameras_section,
                "DETECTION": self._build_detection_section,
                "PLC": self._build_plc_section,
                "THEME": self._build_theme_section,
            }

            builder = builders.get(section_name)
            if builder is not None:
                builder()
        finally:
            self.settings_frame = original_settings_frame

        return frame

    def _refresh_current_section(self):
        if not self.current_section:
            return

        frame = self.section_frames.get(self.current_section)
        if frame is None:
            return

        for widget in frame.winfo_children():
            widget.destroy()

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        original_settings_frame = self.settings_frame
        self.settings_frame = frame

        try:
            builders = {
                "GENERAL": self._build_general_section,
                "CAMERAS": self._build_cameras_section,
                "DETECTION": self._build_detection_section,
                "PLC": self._build_plc_section,
                "THEME": self._build_theme_section,
            }

            builder = builders.get(self.current_section)
            if builder is not None:
                builder()
        finally:
            self.settings_frame = original_settings_frame

    # ------------------------------------------------------------------
    # Settings sections
    # ------------------------------------------------------------------
    def _build_general_section(self):
        self.settings_frame.grid_columnconfigure(0, weight=0)
        self.settings_frame.grid_columnconfigure(1, weight=1)

        general = self._get_config_section("general")

        application_name = general.get(
            "application_name",
            "HUMAN DETECTION & MONITORING",
        )
        if application_name is None:
            application_name = "HUMAN DETECTION & MONITORING"

        self.application_name_var.set(str(application_name))

        heading = ctk.CTkLabel(
            self.settings_frame,
            text="Application settings",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        heading.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=20,
            pady=(20, 15),
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Application name",
        ).grid(
            row=1,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkEntry(
            self.settings_frame,
            textvariable=self.application_name_var,
            width=360,
        ).grid(
            row=1,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="ew",
        )

        hint = ctk.CTkLabel(
            self.settings_frame,
            text=(
                "The application name is the operator-facing name used "
                "by the application. Leave it unchanged to use the "
                "default name."
            ),
            justify="left",
            wraplength=650,
        )
        hint.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=(8, 20),
            sticky="w",
        )

    def _build_cameras_section(self):
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_columnconfigure(1, weight=1)

        cameras = self._get_config_section("cameras")

        count = cameras.get("count", self.MIN_CAMERAS)
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = self.MIN_CAMERAS

        count = max(self.MIN_CAMERAS, min(self.MAX_CAMERAS, count))

        indices = cameras.get("indices", [])
        if not isinstance(indices, list):
            indices = []

        width = cameras.get("width", 1280)
        height = cameras.get("height", 720)

        self.camera_count_var.set(str(count))
        self.camera_width_var.set(str(width))
        self.camera_height_var.set(str(height))

        heading = ctk.CTkLabel(
            self.settings_frame,
            text="Camera configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        heading.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=20,
            pady=(20, 15),
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Number of cameras",
        ).grid(
            row=1,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        count_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            variable=self.camera_count_var,
            values=[str(value) for value in range(self.MIN_CAMERAS, self.MAX_CAMERAS + 1)],
            command=self._on_camera_count_changed,
            width=160,
        )
        count_menu.grid(
            row=1,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Camera resolution",
        ).grid(
            row=2,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        resolution_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        resolution_frame.grid(
            row=2,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        ctk.CTkLabel(resolution_frame, text="Width").grid(
            row=0,
            column=0,
            padx=(0, 5),
        )
        ctk.CTkEntry(
            resolution_frame,
            textvariable=self.camera_width_var,
            width=100,
        ).grid(
            row=0,
            column=1,
            padx=(0, 15),
        )

        ctk.CTkLabel(resolution_frame, text="Height").grid(
            row=0,
            column=2,
            padx=(0, 5),
        )
        ctk.CTkEntry(
            resolution_frame,
            textvariable=self.camera_height_var,
            width=100,
        ).grid(
            row=0,
            column=3,
        )

        self.camera_indices_frame = ctk.CTkFrame(
            self.settings_frame,
            fg_color="transparent",
        )
        self.camera_indices_frame.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=20,
            pady=(15, 20),
            sticky="ew",
        )
        self.camera_indices_frame.grid_columnconfigure(1, weight=1)

        self._render_camera_index_fields(count, indices)

        hint = ctk.CTkLabel(
            self.settings_frame,
            text=(
                "Camera count must be between 1 and 4. "
                "Indices refer to the camera/device index used by OpenCV."
            ),
            justify="left",
            wraplength=650,
        )
        hint.grid(
            row=4,
            column=0,
            columnspan=2,
            padx=20,
            pady=(0, 20),
            sticky="w",
        )

    def _render_camera_index_fields(self, count, indices):
        for widget in self.camera_indices_frame.winfo_children():
            widget.destroy()

        self.camera_index_vars = []

        title = ctk.CTkLabel(
            self.camera_indices_frame,
            text="Camera devices",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=0,
            pady=(0, 10),
            sticky="w",
        )

        for camera_number in range(count):
            if camera_number < len(indices):
                index = indices[camera_number]
            else:
                index = camera_number

            variable = ctk.StringVar(value=str(index))
            self.camera_index_vars.append(variable)

            ctk.CTkLabel(
                self.camera_indices_frame,
                text=f"Camera {camera_number + 1} index",
            ).grid(
                row=camera_number + 1,
                column=0,
                padx=(0, 15),
                pady=5,
                sticky="w",
            )

            ctk.CTkEntry(
                self.camera_indices_frame,
                textvariable=variable,
                width=140,
            ).grid(
                row=camera_number + 1,
                column=1,
                padx=0,
                pady=5,
                sticky="w",
            )

    def _on_camera_count_changed(self, value):
        try:
            count = int(value)
        except (TypeError, ValueError):
            return

        indices = []
        for variable in self.camera_index_vars:
            try:
                indices.append(int(variable.get()))
            except (TypeError, ValueError):
                indices.append(len(indices))

        self._render_camera_index_fields(count, indices)

    def _build_detection_section(self):
        self.settings_frame.grid_columnconfigure(0, weight=0)
        self.settings_frame.grid_columnconfigure(1, weight=1)

        detection = self._get_config_section("detection")

        model_path = detection.get("model_path")
        confidence = detection.get("confidence_threshold", 0.5)
        image_size = detection.get("image_size", 640)
        device = detection.get("device")

        self.detection_model_path_var.set(
            "" if model_path is None else str(model_path)
        )
        self.detection_confidence_var.set(str(confidence))
        self.detection_image_size_var.set(str(image_size))

        if device is None or str(device).strip() == "":
            self.detection_device_var.set("Auto")
        else:
            self.detection_device_var.set(str(device))

        heading = ctk.CTkLabel(
            self.settings_frame,
            text="Detection configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        heading.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=20,
            pady=(20, 15),
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Model path",
        ).grid(
            row=1,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkEntry(
            self.settings_frame,
            textvariable=self.detection_model_path_var,
            width=420,
        ).grid(
            row=1,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="ew",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Confidence threshold",
        ).grid(
            row=2,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkEntry(
            self.settings_frame,
            textvariable=self.detection_confidence_var,
            width=160,
        ).grid(
            row=2,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Inference image size",
        ).grid(
            row=3,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkEntry(
            self.settings_frame,
            textvariable=self.detection_image_size_var,
            width=160,
        ).grid(
            row=3,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Device",
        ).grid(
            row=4,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkOptionMenu(
            self.settings_frame,
            variable=self.detection_device_var,
            values=["Auto", "CPU", "CUDA"],
            width=160,
        ).grid(
            row=4,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        hint = ctk.CTkLabel(
            self.settings_frame,
            text=(
                "Confidence controls how certain the detector must be before "
                "a person detection is accepted. Higher inference image sizes "
                "can improve detection quality but may reduce performance. "
                "Auto lets the application/model choose the device."
            ),
            justify="left",
            wraplength=700,
        )
        hint.grid(
            row=5,
            column=0,
            columnspan=2,
            padx=20,
            pady=(10, 20),
            sticky="w",
        )

    def _build_plc_section(self):
        self.settings_frame.grid_columnconfigure(0, weight=0)
        self.settings_frame.grid_columnconfigure(1, weight=1)

        plc = self._get_config_section("plc")

        self.plc_host_var.set(
            str(plc.get("host", "127.0.0.1"))
        )
        self.plc_port_var.set(
            str(plc.get("port", 5000))
        )
        self.plc_auto_connect_var.set(
            bool(plc.get("auto_connect", False))
        )
        self.plc_timeout_var.set(
            str(plc.get("timeout", 5.0))
        )
        self.plc_buffer_size_var.set(
            str(plc.get("buffer_size", 4096))
        )
        self.plc_encoding_var.set(
            str(plc.get("encoding", "utf-8"))
        )

        heading = ctk.CTkLabel(
            self.settings_frame,
            text="PLC communication configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        heading.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=20,
            pady=(20, 15),
            sticky="w",
        )

        fields = [
            ("Server host", self.plc_host_var, 1),
            ("Server port", self.plc_port_var, 2),
            ("Connection timeout (seconds)", self.plc_timeout_var, 4),
            ("Receive buffer size (bytes)", self.plc_buffer_size_var, 5),
            ("Encoding", self.plc_encoding_var, 6),
        ]

        for label_text, variable, row in fields:
            ctk.CTkLabel(
                self.settings_frame,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                padx=(20, 10),
                pady=8,
                sticky="w",
            )

            ctk.CTkEntry(
                self.settings_frame,
                textvariable=variable,
                width=300,
            ).grid(
                row=row,
                column=1,
                padx=(10, 20),
                pady=8,
                sticky="w",
            )

        ctk.CTkLabel(
            self.settings_frame,
            text="Auto connect at application start",
        ).grid(
            row=3,
            column=0,
            padx=(20, 10),
            pady=8,
            sticky="w",
        )

        ctk.CTkCheckBox(
            self.settings_frame,
            text="Enabled",
            variable=self.plc_auto_connect_var,
        ).grid(
            row=3,
            column=1,
            padx=(10, 20),
            pady=8,
            sticky="w",
        )

        hint = ctk.CTkLabel(
            self.settings_frame,
            text=(
                "The Python application acts as the TCP/IP client and "
                "communicates with the external C# PLC server. These "
                "settings control the connection; PLC commands and status "
                "handling remain in the PLC communication layer."
            ),
            justify="left",
            wraplength=700,
        )
        hint.grid(
            row=7,
            column=0,
            columnspan=2,
            padx=20,
            pady=(10, 20),
            sticky="w",
        )

    def _build_theme_section(self):
        self.theme_variables = {}
        self.theme_widgets = {}

        theme = self._get_theme()

        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_rowconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(
            self.settings_frame,
        )
        scroll_frame.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="nsew",
        )
        scroll_frame.grid_columnconfigure(1, weight=1)

        self._render_theme_dict(scroll_frame, theme)

        self.restore_default_theme_button = ctk.CTkButton(
            self.settings_frame,
            text="RESTORE DEFAULT THEME",
            command=self._restore_default_theme,
            width=220,
        )
        self.restore_default_theme_button.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 10),
            sticky="w",
        )

        hint = ctk.CTkLabel(
            self.settings_frame,
            text=(
                "Edit the visual properties used by the application. "
                "PREVIEW opens a temporary sample window using the current "
                "values without saving them. RESTORE DEFAULT THEME resets "
                "the working theme only. APPLY saves the edited theme."
            ),
            justify="left",
            wraplength=750,
        )
        hint.grid(
            row=2,
            column=0,
            padx=20,
            pady=(0, 15),
            sticky="w",
        )

    def _get_theme(self):
        if self.vm is None:
            return {}

        get_theme = getattr(self.vm, "get_theme", None)
        if not callable(get_theme):
            return {}

        theme = get_theme()
        return theme if isinstance(theme, dict) else {}

    def _restore_default_theme(self):
        """Reset the working theme to ThemeManager's canonical defaults."""
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        try:
            confirmed = messagebox.askyesno(
                "Restore Default Theme",
                (
                    "Restore all theme settings to their default values?\n\n"
                    "This will replace the current unsaved theme edits. "
                    "You must press APPLY to save the restored theme."
                ),
                parent=self.winfo_toplevel(),
            )
        except tk.TclError:
            return

        if not confirmed:
            return

        self.vm.working_theme = ThemeManager._clone_defaults()
        self.status_label.configure(
            text="Default theme restored. Review, PREVIEW, then APPLY."
        )
        self._refresh_current_section()

    def _render_theme_dict(self, parent, data, path=(), start_row=0):
        row = start_row

        for key, value in data.items():
            current_path = path + (key,)
            label_text = self._theme_label(key)

            if isinstance(value, dict):
                heading = ctk.CTkLabel(
                    parent,
                    text=label_text,
                    font=ctk.CTkFont(size=16, weight="bold"),
                )
                heading.grid(
                    row=row,
                    column=0,
                    columnspan=2,
                    padx=10,
                    pady=(15, 5),
                    sticky="w",
                )
                row += 1

                row = self._render_theme_dict(
                    parent,
                    value,
                    current_path,
                    row,
                )
                continue

            variable = self._make_theme_variable(value)
            self.theme_variables[current_path] = variable

            ctk.CTkLabel(
                parent,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                padx=(10, 15),
                pady=5,
                sticky="w",
            )

            widget = self._make_theme_editor_widget(
                parent,
                variable,
                value,
                current_path,
            )
            widget.grid(
                row=row,
                column=1,
                padx=(0, 10),
                pady=5,
                sticky="ew" if not isinstance(value, bool) else "w",
            )

            self.theme_widgets[current_path] = widget
            row += 1

        return row

    @staticmethod
    def _theme_label(key):
        return key.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _make_theme_variable(value):
        if isinstance(value, bool):
            return ctk.BooleanVar(value=value)
        return ctk.StringVar(value=str(value))

    def _make_theme_editor_widget(self, parent, variable, value, path):
        if isinstance(value, bool):
            return ctk.CTkCheckBox(
                parent,
                text="Enabled",
                variable=variable,
            )

        if self._is_color_value(value, path):
            container = ctk.CTkFrame(parent, fg_color="transparent")
            container.grid_columnconfigure(0, weight=0)
            container.grid_columnconfigure(1, weight=1)
            container.grid_columnconfigure(2, weight=0)

            swatch = ctk.CTkLabel(
                container,
                text="",
                width=36,
                height=28,
                corner_radius=6,
                fg_color=self._safe_hex(
                    value,
                    "#FFFFFF",
                ),
            )
            swatch.grid(
                row=0,
                column=0,
                padx=(0, 8),
                pady=0,
            )

            entry = ctk.CTkEntry(
                container,
                textvariable=variable,
                width=140,
            )
            entry.grid(
                row=0,
                column=1,
                padx=(0, 8),
                sticky="ew",
            )

            select_button = ctk.CTkButton(
                container,
                text="SELECT",
                width=90,
                command=lambda: self._select_theme_color(
                    variable,
                    swatch,
                ),
            )
            select_button.grid(
                row=0,
                column=2,
            )

            variable.trace_add(
                "write",
                lambda *_args, v=variable, s=swatch: self._update_color_swatch(
                    v,
                    s,
                ),
            )

            return container

        if isinstance(value, list):
            return ctk.CTkEntry(
                parent,
                textvariable=variable,
                width=260,
            )

        return ctk.CTkEntry(
            parent,
            textvariable=variable,
            width=360,
        )

    @staticmethod
    def _is_color_value(value, path):
        if not isinstance(value, str):
            return False

        if len(value.strip()) != 7:
            return False

        if not value.strip().startswith("#"):
            return False

        # Theme color sections are explicitly color-oriented, while this
        # also catches future color-valued keys such as *_color.
        color_sections = {"colors"}
        color_keys = {
            "foreground",
            "hover",
            "text",
            "disabled",
            "background",
            "border",
            "counting_line",
            "person_box",
            "person_text",
            "title_text",
            "value_text",
            "running",
            "stopped",
            "connected",
            "disconnected",
            "safe",
            "not_safe",
            "window_background",
            "frame_background",
            "frame_foreground",
            "text_primary",
            "text_secondary",
        }

        return (
            path[0] in color_sections
            or path[-1] in color_keys
            or path[-1].endswith("_color")
        )

    def _update_color_swatch(self, variable, swatch):
        value = variable.get().strip()

        if self._is_valid_hex_color(value):
            swatch.configure(
                fg_color=value,
            )
        else:
            swatch.configure(
                fg_color="#777777",
            )

    def _select_theme_color(self, variable, swatch):
        current = variable.get().strip()

        initial_color = (
            current
            if self._is_valid_hex_color(current)
            else "#FFFFFF"
        )

        try:
            result = colorchooser.askcolor(
                color=initial_color,
                parent=self.winfo_toplevel(),
                title="Select Color",
            )
        except tk.TclError:
            return

        rgb_value, hex_value = result

        if hex_value:
            variable.set(hex_value.upper())
            swatch.configure(
                fg_color=hex_value.upper(),
            )

    @staticmethod
    def _is_valid_hex_color(value):
        if not isinstance(value, str):
            return False

        value = value.strip()

        if len(value) != 7 or not value.startswith("#"):
            return False

        try:
            int(value[1:], 16)
        except ValueError:
            return False

        return True

    def _collect_theme_value(self, original_value, variable):
        if isinstance(original_value, bool):
            return bool(variable.get())

        raw = variable.get()

        if isinstance(original_value, int) and not isinstance(original_value, bool):
            try:
                return int(raw)
            except ValueError as exc:
                raise ValueError(
                    "Theme integer values must contain whole numbers."
                ) from exc

        if isinstance(original_value, float):
            try:
                return float(raw)
            except ValueError as exc:
                raise ValueError(
                    "Theme numeric values must contain valid numbers."
                ) from exc

        if isinstance(original_value, list):
            try:
                import json
                parsed = json.loads(raw)
            except Exception as exc:
                raise ValueError(
                    "Theme list values must be valid JSON arrays."
                ) from exc

            if not isinstance(parsed, list):
                raise ValueError(
                    "Theme list values must be JSON arrays."
                )
            return parsed

        return str(raw)

    def _sync_plc_values_to_vm(self):
        if self.vm is None:
            raise RuntimeError("No SystemViewModel connected.")

        host = self.plc_host_var.get().strip()

        if not host:
            raise ValueError("PLC host cannot be empty.")

        try:
            port = int(self.plc_port_var.get())
        except ValueError as exc:
            raise ValueError(
                "PLC port must be an integer."
            ) from exc

        if not 1 <= port <= 65535:
            raise ValueError(
                "PLC port must be between 1 and 65535."
            )

        try:
            timeout = float(self.plc_timeout_var.get())
        except ValueError as exc:
            raise ValueError(
                "PLC timeout must be a number."
            ) from exc

        if timeout <= 0:
            raise ValueError(
                "PLC timeout must be greater than zero."
            )

        try:
            buffer_size = int(self.plc_buffer_size_var.get())
        except ValueError as exc:
            raise ValueError(
                "PLC buffer size must be an integer."
            ) from exc

        if buffer_size <= 0:
            raise ValueError(
                "PLC buffer size must be greater than zero."
            )

        encoding = self.plc_encoding_var.get().strip()

        if not encoding:
            raise ValueError("PLC encoding cannot be empty.")

        self.vm.set_value("plc", "host", host)
        self.vm.set_value("plc", "port", port)
        self.vm.set_value(
            "plc",
            "auto_connect",
            bool(self.plc_auto_connect_var.get()),
        )
        self.vm.set_value("plc", "timeout", timeout)
        self.vm.set_value("plc", "buffer_size", buffer_size)
        self.vm.set_value("plc", "encoding", encoding)

    def _sync_theme_values_to_vm(self):
        if self.vm is None:
            raise RuntimeError("No SystemViewModel connected.")

        theme = self._get_theme()

        for path, variable in self.theme_variables.items():
            original = theme

            try:
                for key in path:
                    original = original[key]
            except (KeyError, TypeError):
                continue

            value = self._collect_theme_value(
                original,
                variable,
            )

            # Apply the edited leaf value back into the working theme.
            # This supports both nested values such as colors.camera.background
            # and top-level values such as version.
            if len(path) == 1:
                theme[path[0]] = value
                continue

            cursor = theme

            for nested_key in path[:-1]:
                nested = cursor.get(nested_key)

                if not isinstance(nested, dict):
                    nested = {}
                    cursor[nested_key] = nested

                cursor = nested

            cursor[path[-1]] = value

        # Replace the VM's working theme directly with the edited copy.
        self.vm.working_theme = theme

    @staticmethod
    def _safe_hex(value, fallback="#FFFFFF"):
        if not SystemView._is_valid_hex_color(value):
            return fallback
        return value.strip().upper()

    @staticmethod
    def _safe_font(theme, name, fallback=("Arial", 14, "normal")):
        fonts = theme.get("fonts", {})
        font = fonts.get(name, {})
        if not isinstance(font, dict):
            return fallback
        family = str(font.get("family", fallback[0]))
        try:
            size = int(font.get("size", fallback[1]))
        except (TypeError, ValueError):
            size = fallback[1]
        weight = str(font.get("weight", fallback[2]))
        return family, size, weight

    def _preview_theme(self):
        try:
            self._sync_theme_values_to_vm()
            theme = self._get_theme()

            preview = ctk.CTkToplevel(self)
            preview.title(
                theme.get("window", {}).get(
                    "title",
                    "Theme Preview",
                )
            )
            preview.geometry("900x650")
            preview.minsize(760, 520)

            colors = theme.get("colors", {})
            button_colors = colors.get("button", {})
            status_colors = colors.get("status", {})
            camera_colors = colors.get("camera", {})
            log_colors = colors.get("log", {})

            window_bg = self._safe_hex(
                colors.get("window_background"),
                "#F2F2F2",
            )
            frame_bg = self._safe_hex(
                colors.get("frame_background"),
                "#FFFFFF",
            )
            text_primary = self._safe_hex(
                colors.get("text_primary"),
                "#111111",
            )
            text_secondary = self._safe_hex(
                colors.get("text_secondary"),
                "#555555",
            )

            preview.configure(fg_color=window_bg)

            header_font = self._safe_font(
                theme,
                "header_title",
                ("Arial", 28, "bold"),
            )
            normal_font = self._safe_font(
                theme,
                "normal",
                ("Arial", 14, "normal"),
            )
            status_font = self._safe_font(
                theme,
                "status_value",
                ("Arial", 18, "bold"),
            )

            header = ctk.CTkFrame(
                preview,
                fg_color=frame_bg,
            )
            header.pack(
                fill="x",
                padx=10,
                pady=10,
            )

            ctk.CTkLabel(
                header,
                text=theme.get("header", {}).get(
                    "title",
                    "HUMAN DETECTION & MONITORING",
                ),
                text_color=text_primary,
                font=ctk.CTkFont(
                    family=header_font[0],
                    size=header_font[1],
                    weight=header_font[2],
                ),
            ).pack(
                padx=15,
                pady=15,
            )

            body = ctk.CTkFrame(
                preview,
                fg_color=frame_bg,
            )
            body.pack(
                fill="both",
                expand=True,
                padx=10,
                pady=5,
            )
            body.grid_columnconfigure(0, weight=3)
            body.grid_columnconfigure(1, weight=1)
            body.grid_rowconfigure(0, weight=1)

            camera = ctk.CTkFrame(
                body,
                fg_color=self._safe_hex(
                    camera_colors.get("background"),
                    "#111111",
                ),
            )
            camera.grid(
                row=0,
                column=0,
                padx=10,
                pady=10,
                sticky="nsew",
            )

            camera_title = ctk.CTkLabel(
                camera,
                text="Camera 1",
                text_color=self._safe_hex(
                    colors.get("text_primary"),
                    "#FFFFFF",
                ),
                font=ctk.CTkFont(
                    family=normal_font[0],
                    size=normal_font[1],
                    weight=normal_font[2],
                ),
            )
            camera_title.pack(
                anchor="nw",
                padx=10,
                pady=10,
            )

            line_canvas = tk.Canvas(
                camera,
                bg=self._safe_hex(
                    camera_colors.get("background"),
                    "#111111",
                ),
                highlightthickness=0,
            )
            line_canvas.pack(
                fill="both",
                expand=True,
                padx=10,
                pady=10,
            )
            line_canvas.create_line(
                50,
                80,
                330,
                250,
                fill=self._safe_hex(
                    camera_colors.get("counting_line"),
                    "#FF0000",
                ),
                width=3,
            )
            line_canvas.create_rectangle(
                170,
                120,
                300,
                300,
                outline=self._safe_hex(
                    camera_colors.get("person_box"),
                    "#00FF00",
                ),
                width=2,
            )
            line_canvas.create_text(
                235,
                110,
                text="Person 1 96%",
                fill=self._safe_hex(
                    camera_colors.get("person_text"),
                    "#FFFFFF",
                ),
                anchor="s",
            )

            status = ctk.CTkFrame(
                body,
                fg_color=self._safe_hex(
                    status_colors.get("background"),
                    "#FFFFFF",
                ),
            )
            status.grid(
                row=0,
                column=1,
                padx=(0, 10),
                pady=10,
                sticky="nsew",
            )

            for label, value, color_key in [
                ("MONITORING", "RUNNING", "running"),
                ("PLC", "CONNECTED", "connected"),
                ("CURRENT PEOPLE", "1", "value_text"),
                ("EQP STATUS", "SAFE", "safe"),
            ]:
                ctk.CTkLabel(
                    status,
                    text=label,
                    text_color=self._safe_hex(
                        status_colors.get("title_text"),
                        text_secondary,
                    ),
                    font=ctk.CTkFont(
                        family=normal_font[0],
                        size=normal_font[1],
                        weight="bold",
                    ),
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(15, 0),
                )

                ctk.CTkLabel(
                    status,
                    text=value,
                    text_color=self._safe_hex(
                        status_colors.get(color_key),
                        text_primary,
                    ),
                    font=ctk.CTkFont(
                        family=status_font[0],
                        size=status_font[1],
                        weight=status_font[2],
                    ),
                ).pack(
                    anchor="w",
                    padx=15,
                )

            log = ctk.CTkTextbox(
                preview,
                height=90,
                fg_color=self._safe_hex(
                    log_colors.get("background"),
                    "#FFFFFF",
                ),
                text_color=self._safe_hex(
                    log_colors.get("text"),
                    text_primary,
                ),
            )
            log.pack(
                fill="x",
                padx=10,
                pady=10,
            )
            log.insert(
                "end",
                "12:30:01 | Theme preview\n"
                "12:30:02 | Person entered\n"
                "12:30:03 | Current people: 1\n",
            )
            log.configure(state="disabled")

        except Exception as exc:
            self.status_label.configure(
                text=f"Theme preview failed: {exc}"
            )

    def _add_placeholder(self, text):
        label = ctk.CTkLabel(
            self.settings_frame,
            text=text,
            wraplength=600,
            justify="left",
            font=ctk.CTkFont(size=16),
        )
        label.grid(
            row=0,
            column=0,
            padx=20,
            pady=20,
            sticky="nw",
        )

    # ------------------------------------------------------------------
    # ViewModel helpers
    # ------------------------------------------------------------------
    def _get_config_section(self, section):
        if self.vm is None:
            return {}

        get_config = getattr(self.vm, "get_config", None)
        if not callable(get_config):
            return {}

        config = get_config()
        if not isinstance(config, dict):
            return {}

        section_data = config.get(section, {})
        return section_data if isinstance(section_data, dict) else {}

    def _sync_camera_values_to_vm(self):
        if self.vm is None:
            raise RuntimeError("No SystemViewModel connected.")

        try:
            count = int(self.camera_count_var.get())
        except ValueError as exc:
            raise ValueError("Camera count must be an integer.") from exc

        if not self.MIN_CAMERAS <= count <= self.MAX_CAMERAS:
            raise ValueError(
                f"Camera count must be between {self.MIN_CAMERAS} and "
                f"{self.MAX_CAMERAS}."
            )

        try:
            width = int(self.camera_width_var.get())
        except ValueError as exc:
            raise ValueError("Camera width must be an integer.") from exc

        try:
            height = int(self.camera_height_var.get())
        except ValueError as exc:
            raise ValueError("Camera height must be an integer.") from exc

        if width <= 0 or height <= 0:
            raise ValueError("Camera width and height must be positive.")

        indices = []
        for camera_number, variable in enumerate(self.camera_index_vars, start=1):
            try:
                index = int(variable.get())
            except ValueError as exc:
                raise ValueError(
                    f"Camera {camera_number} index must be an integer."
                ) from exc

            if index < 0:
                raise ValueError(
                    f"Camera {camera_number} index cannot be negative."
                )

            indices.append(index)

        if len(indices) != count:
            raise ValueError("Number of camera indices must match camera count.")

        self.vm.set_value("cameras", "count", count)
        self.vm.set_value("cameras", "indices", indices)
        self.vm.set_value("cameras", "width", width)
        self.vm.set_value("cameras", "height", height)

    def _sync_detection_values_to_vm(self):
        if self.vm is None:
            raise RuntimeError("No SystemViewModel connected.")

        model_path = self.detection_model_path_var.get().strip()

        try:
            confidence = float(self.detection_confidence_var.get())
        except ValueError as exc:
            raise ValueError(
                "Detection confidence must be a number."
            ) from exc

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Detection confidence must be between 0.0 and 1.0."
            )

        try:
            image_size = int(self.detection_image_size_var.get())
        except ValueError as exc:
            raise ValueError(
                "Inference image size must be an integer."
            ) from exc

        if image_size <= 0:
            raise ValueError(
                "Inference image size must be positive."
            )

        device = self.detection_device_var.get().strip()

        if device == "Auto":
            device_value = None
        elif device == "CPU":
            device_value = "cpu"
        elif device == "CUDA":
            device_value = "cuda"
        else:
            raise ValueError("Invalid detection device.")

        self.vm.set_value(
            "detection",
            "model_path",
            model_path if model_path else None,
        )
        self.vm.set_value(
            "detection",
            "confidence_threshold",
            confidence,
        )
        self.vm.set_value(
            "detection",
            "image_size",
            image_size,
        )
        self.vm.set_value(
            "detection",
            "device",
            device_value,
        )

    def _sync_general_values_to_vm(self):
        if self.vm is None:
            raise RuntimeError("No SystemViewModel connected.")

        application_name = self.application_name_var.get().strip()

        if not application_name:
            raise ValueError("Application name cannot be empty.")

        self.vm.set_value(
            "general",
            "application_name",
            application_name,
        )

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------
    def _import_config(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import Configuration",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                imported = json.load(file)

            if not isinstance(imported, dict):
                raise ValueError("Configuration file must contain a JSON object.")

            # Import into the working copy only. APPLY is still required
            # before anything is persisted to the application's config file.
            self.vm.working_config = imported
            normalize = getattr(self.vm, "_normalize_config", None)
            if callable(normalize):
                normalize()

            self.status_label.configure(
                text="Configuration imported. Review and APPLY the changes."
            )
            self._refresh_current_section()

        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            self.status_label.configure(
                text=f"Config import failed: {exc}"
            )

    def _export_config(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export Configuration",
            defaultextension=".json",
            initialfile="config.json",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            config = self.vm.get_config()

            with open(path, "w", encoding="utf-8") as file:
                json.dump(
                    config,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )
                file.write("\n")

            self.status_label.configure(
                text="Configuration exported."
            )

        except (OSError, TypeError, ValueError) as exc:
            self.status_label.configure(
                text=f"Config export failed: {exc}"
            )

    def _import_theme(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import Theme",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                imported = json.load(file)

            if not isinstance(imported, dict):
                raise ValueError("Theme file must contain a JSON object.")

            # Keep the import in the working copy so PREVIEW and APPLY
            # operate on it without modifying the saved theme immediately.
            self.vm.working_theme = imported

            self.status_label.configure(
                text="Theme imported. Review, PREVIEW, then APPLY."
            )
            self._refresh_current_section()

        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            self.status_label.configure(
                text=f"Theme import failed: {exc}"
            )

    def _export_theme(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export Theme",
            defaultextension=".json",
            initialfile="theme.json",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            theme = self.vm.get_theme()

            with open(path, "w", encoding="utf-8") as file:
                json.dump(
                    theme,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )
                file.write("\n")

            self.status_label.configure(
                text="Theme exported."
            )

        except (OSError, TypeError, ValueError) as exc:
            self.status_label.configure(
                text=f"Theme export failed: {exc}"
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _apply(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        try:
            if self.current_section == "GENERAL":
                self._sync_general_values_to_vm()
            elif self.current_section == "CAMERAS":
                self._sync_camera_values_to_vm()
            elif self.current_section == "DETECTION":
                self._sync_detection_values_to_vm()
            elif self.current_section == "THEME":
                self._sync_theme_values_to_vm()
            elif self.current_section == "PLC":
                self._sync_plc_values_to_vm()

            apply_method = getattr(self.vm, "apply", None)
            if not callable(apply_method):
                raise RuntimeError("SystemViewModel apply() is not available.")

            apply_method()
            self.status_label.configure(text="Changes applied.")
        except Exception as exc:
            self.status_label.configure(text=f"Apply failed: {exc}")

    def _cancel(self):
        if self.vm is None:
            self.status_label.configure(text="No SystemViewModel connected.")
            return

        try:
            cancel_method = getattr(self.vm, "cancel", None)
            if not callable(cancel_method):
                raise RuntimeError("SystemViewModel cancel() is not available.")

            cancel_method()
            self.status_label.configure(text="Changes cancelled.")
            self._refresh_current_section()

        except Exception as exc:
            self.status_label.configure(text=f"Cancel failed: {exc}")

    # ------------------------------------------------------------------
    # ViewModel
    # ------------------------------------------------------------------
    def set_viewmodel(self, viewmodel):
        """Attach or replace the SystemViewModel."""
        self.vm = viewmodel

        if self.vm is None:
            return

        load_method = getattr(self.vm, "load", None)
        if callable(load_method):
            try:
                load_method()
                self.status_label.configure(text="Configuration loaded.")
            except Exception as exc:
                self.status_label.configure(
                    text=f"Configuration load failed: {exc}"
                )

        if self.current_section == "GENERAL":
            self._clear_settings_frame()
            self._build_general_section()
        elif self.current_section == "CAMERAS":
            self._clear_settings_frame()
            self._build_cameras_section()
        elif self.current_section == "DETECTION":
            self._clear_settings_frame()
            self._build_detection_section()
        elif self.current_section == "THEME":
            self._clear_settings_frame()
            self._build_theme_section()
        elif self.current_section == "PLC":
            self._clear_settings_frame()
            self._build_plc_section()
