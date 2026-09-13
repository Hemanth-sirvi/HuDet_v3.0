import customtkinter as ctk


class SystemView(ctk.CTkFrame):
    """
    System View shell for application and theme configuration.

    This first version provides the navigation structure and settings
    workspace. Configuration loading, validation, persistence, and theme
    preview will be handled by SystemViewModel and the configuration layer.
    """

    def __init__(self, master, viewmodel=None, **kwargs):
        super().__init__(master, **kwargs)

        self.vm = viewmodel
        self.current_section = None
        self.section_frames = {}

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

        self.navigation_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        title = ctk.CTkLabel(
            self.navigation_frame,
            text="SYSTEM",
            font=ctk.CTkFont(
                size=24,
                weight="bold",
            ),
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

        self.workspace_frame.grid_rowconfigure(
            1,
            weight=1,
        )
        self.workspace_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        self.section_title = ctk.CTkLabel(
            self.workspace_frame,
            text="GENERAL",
            font=ctk.CTkFont(
                size=22,
                weight="bold",
            ),
        )
        self.section_title.grid(
            row=0,
            column=0,
            padx=15,
            pady=10,
            sticky="w",
        )

        self.settings_frame = ctk.CTkFrame(
            self.workspace_frame
        )
        self.settings_frame.grid(
            row=1,
            column=0,
            padx=10,
            pady=5,
            sticky="nsew",
        )

        self.settings_frame.grid_columnconfigure(
            0,
            weight=1,
        )
        self.settings_frame.grid_rowconfigure(
            0,
            weight=1,
        )

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

        self.action_frame.grid_columnconfigure(
            0,
            weight=1,
        )
        self.action_frame.grid_columnconfigure(
            1,
            weight=0,
        )
        self.action_frame.grid_columnconfigure(
            2,
            weight=0,
        )

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

        self.current_section = section_name
        self.section_title.configure(
            text=section_name
        )

        for name, button in self.navigation_buttons.items():
            if name == section_name:
                button.configure(
                    fg_color=button.cget("hover_color")
                )
            else:
                button.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
                )

        self._clear_settings_frame()

        if section_name == "GENERAL":
            self._build_general_section()
        elif section_name == "CAMERAS":
            self._build_cameras_section()
        elif section_name == "DETECTION":
            self._build_detection_section()
        elif section_name == "PLC":
            self._build_plc_section()
        elif section_name == "THEME":
            self._build_theme_section()

    def _clear_settings_frame(self):
        for widget in self.settings_frame.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # Settings sections
    # ------------------------------------------------------------------
    def _build_general_section(self):
        self._add_placeholder(
            "General application settings will be configured here."
        )

    def _build_cameras_section(self):
        self._add_placeholder(
            "Camera count, camera indices, resolution, and camera "
            "configuration will be configured here."
        )

    def _build_detection_section(self):
        self._add_placeholder(
            "Detection model, confidence, inference size, and related "
            "settings will be configured here."
        )

    def _build_plc_section(self):
        self._add_placeholder(
            "PLC server address, port, connection options, and command "
            "settings will be configured here."
        )

    def _build_theme_section(self):
        self._add_placeholder(
            "Theme editor and temporary preview will be configured here."
        )

    def _add_placeholder(self, text):
        label = ctk.CTkLabel(
            self.settings_frame,
            text=text,
            wraplength=600,
            justify="left",
            font=ctk.CTkFont(
                size=16,
            ),
        )
        label.grid(
            row=0,
            column=0,
            padx=20,
            pady=20,
            sticky="nw",
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _apply(self):
        if self.vm is None:
            self.status_label.configure(
                text="No SystemViewModel connected."
            )
            return

        apply_method = getattr(
            self.vm,
            "apply",
            None,
        )

        if callable(apply_method):
            try:
                apply_method()
                self.status_label.configure(
                    text="Changes applied."
                )
            except Exception as exc:
                self.status_label.configure(
                    text=f"Apply failed: {exc}"
                )
        else:
            self.status_label.configure(
                text="SystemViewModel apply() is not available."
            )

    def _cancel(self):
        if self.vm is None:
            self.status_label.configure(
                text="No SystemViewModel connected."
            )
            return

        cancel_method = getattr(
            self.vm,
            "cancel",
            None,
        )

        if callable(cancel_method):
            try:
                cancel_method()
                self.status_label.configure(
                    text="Changes cancelled."
                )
            except Exception as exc:
                self.status_label.configure(
                    text=f"Cancel failed: {exc}"
                )
        else:
            self.status_label.configure(
                text="SystemViewModel cancel() is not available."
            )

    # ------------------------------------------------------------------
    # ViewModel
    # ------------------------------------------------------------------
    def set_viewmodel(self, viewmodel):
        """Attach or replace the SystemViewModel."""
        self.vm = viewmodel

        if self.vm is not None:
            load_method = getattr(
                self.vm,
                "load",
                None,
            )

            if callable(load_method):
                try:
                    load_method()
                    self.status_label.configure(
                        text="Configuration loaded."
                    )
                except Exception as exc:
                    self.status_label.configure(
                        text=f"Configuration load failed: {exc}"
                    )
