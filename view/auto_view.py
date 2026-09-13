import customtkinter as ctk
from PIL import Image

import cv2

try:
    from model.theme_manager import ThemeManager
except ImportError:
    ThemeManager = None


class AutoView(ctk.CTkFrame):
    """
    Auto View for live monitoring.

    The view is responsible for displaying data supplied by AutoViewModel.
    It does not perform detection, tracking, direction calculation, or
    people counting itself.

    ThemeManager supplies visual configuration without changing the
    existing Auto View widget placement/layout.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    STATUS_THEME_KEYS = {
        0: "monitoring",
        1: "plc",
        2: "entered",
        3: "exited",
        4: "current_people",
        5: "eqp_status",
    }

    def __init__(
        self,
        master,
        viewmodel=None,
        camera_count=4,
        theme_manager=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.vm = viewmodel

        if theme_manager is not None:
            self.theme_manager = theme_manager
        elif ThemeManager is not None:
            self.theme_manager = ThemeManager()
        else:
            self.theme_manager = None

        self._theme = {}
        self._load_theme()

        # When a ViewModel is available, use its camera count.
        if self.vm is not None and hasattr(self.vm, "camera_count"):
            camera_count = self.vm.camera_count

        self.camera_count = max(
            self.MIN_CAMERAS,
            min(self.MAX_CAMERAS, int(camera_count)),
        )

        self.monitoring_loop_id = None
        self.expanded_camera = None

        self.camera_frames = []
        self.camera_labels = []
        self.camera_images = []
        # Track cameras that failed to open so repeated read failures do
        # not flood the log every monitoring cycle.
        self.camera_open_failed = [False] * self.camera_count
        self.camera_error_messages = [None] * self.camera_count

        # ---------------------------------------------------------
        # Main layout
        # ---------------------------------------------------------
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=9)
        self.grid_columnconfigure(1, weight=1)

        # ---------------------------------------------------------
        # Camera area
        # ---------------------------------------------------------
        self.cameraFrame = ctk.CTkFrame(
            self,
            fg_color=self._theme_get(
                "colors.frame_background",
                "#FFFFFF",
            ),
        )
        self.cameraFrame.grid(
            row=0,
            column=0,
            padx=0,
            pady=0,
            sticky="nsew",
        )

        self._create_camera_layout()

        # ---------------------------------------------------------
        # Status area
        # ---------------------------------------------------------
        self.statusFrame = ctk.CTkFrame(
            self,
            fg_color=self._theme_get(
                "colors.status.background",
                "#FFFFFF",
            ),
        )
        self.statusFrame.grid(
            row=0,
            column=1,
            padx=(5, 0),
            pady=0,
            sticky="nsew",
        )

        self.statusFrame.grid_columnconfigure(0, weight=1)

        self.monitoring_value = self._create_status_item(
            0,
            self._theme_get(
                "auto_view.status.monitoring_label",
                "MONITORING",
            ),
            self._theme_get(
                "auto_view.status.stopped_text",
                "STOPPED",
            ),
        )

        self.plc_value = self._create_status_item(
            1,
            self._theme_get(
                "auto_view.status.plc_label",
                "PLC",
            ),
            self._theme_get(
                "auto_view.status.disconnected_text",
                "DISCONNECTED",
            ),
        )

        self.entered_value = self._create_status_item(
            2,
            self._theme_get(
                "auto_view.status.entered_label",
                "ENTERED",
            ),
            "0",
        )

        self.exited_value = self._create_status_item(
            3,
            self._theme_get(
                "auto_view.status.exited_label",
                "EXITED",
            ),
            "0",
        )

        self.current_value = self._create_status_item(
            4,
            self._theme_get(
                "auto_view.status.current_people_label",
                "CURRENT PEOPLE",
            ),
            "0",
        )

        self.safety_value = self._create_status_item(
            5,
            self._theme_get(
                "auto_view.status.eqp_status_label",
                "EQP STATUS",
            ),
            self._theme_get(
                "auto_view.status.not_safe_text",
                "NOT SAFE",
            ),
        )

        # ---------------------------------------------------------
        # Log area
        # ---------------------------------------------------------
        self.statusFrame.grid_rowconfigure(6, weight=1)

        self.logFrame = ctk.CTkFrame(
            self.statusFrame,
            fg_color=self._theme_get(
                "colors.log.background",
                "#FFFFFF",
            ),
        )
        self.logFrame.grid(
            row=6,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.logFrame.grid_rowconfigure(0, weight=1)
        self.logFrame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(
            self.logFrame,
            fg_color=self._theme_get(
                "colors.log.background",
                "#FFFFFF",
            ),
            text_color=self._theme_get(
                "colors.log.text",
                "#111111",
            ),
            font=self._get_font("auto_view.log.font", "log"),
        )
        self.log_text.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        # Connect the ViewModel callbacks when one is supplied.
        self._connect_viewmodel()

        if self.theme_manager is not None:
            self.theme_manager.add_listener(
                self._on_theme_changed
            )

        self._refresh_status()

    # -------------------------------------------------------------
    # Theme
    # -------------------------------------------------------------
    def _load_theme(self):
        self._theme = (
            self.theme_manager.as_dict()
            if self.theme_manager is not None
            else {}
        )

        self.camera_background = self._theme_get(
            "colors.camera.background",
            "#111111",
        )
        self.camera_border = self._theme_get(
            "colors.camera.border",
            "#808080",
        )
        self.camera_border_width = self._safe_int(
            self._theme_get(
                "dimensions.camera.border_width",
                0,
            ),
            0,
        )
        self.camera_corner_radius = self._safe_int(
            self._theme_get(
                "dimensions.camera.corner_radius",
                0,
            ),
            0,
        )

        self.person_box_color = self._theme_get(
            "colors.camera.person_box",
            "#00FF00",
        )
        self.person_text_color = self._theme_get(
            "colors.camera.person_text",
            "#FFFFFF",
        )
        self.counting_line_color = self._theme_get(
            "colors.camera.counting_line",
            "#FF0000",
        )

        self.person_box_width = self._safe_int(
            self._theme_get(
                "dimensions.camera.person_box_width",
                2,
            ),
            2,
        )
        self.counting_line_width = self._safe_int(
            self._theme_get(
                "dimensions.camera.counting_line_width",
                3,
            ),
            3,
        )
        self.counting_line_endpoint_radius = self._safe_int(
            self._theme_get(
                "dimensions.camera.counting_line_endpoint_radius",
                5,
            ),
            5,
        )

        self.camera_show_name = bool(
            self._theme_get(
                "auto_view.camera_label.show_camera_name",
                True,
            )
        )
        self.camera_name_template = str(
            self._theme_get(
                "auto_view.camera_label.name_template",
                "Camera {index}",
            )
        )

        self.person_overlay_show = bool(
            self._theme_get(
                "auto_view.person_overlay.show",
                True,
            )
        )
        self.person_overlay_track_id = bool(
            self._theme_get(
                "auto_view.person_overlay.show_track_id",
                True,
            )
        )
        self.person_overlay_confidence = bool(
            self._theme_get(
                "auto_view.person_overlay.show_confidence",
                True,
            )
        )
        self.person_overlay_confidence_decimals = self._safe_int(
            self._theme_get(
                "auto_view.person_overlay.confidence_decimals",
                0,
            ),
            0,
        )
        self.person_overlay_label_template = str(
            self._theme_get(
                "auto_view.person_overlay.label_template",
                "Person {track_id} {confidence}%",
            )
        )

        self.counting_line_show = bool(
            self._theme_get(
                "auto_view.counting_line_overlay.show",
                True,
            )
        )
        self.counting_line_show_endpoints = bool(
            self._theme_get(
                "auto_view.counting_line_overlay.show_endpoints",
                True,
            )
        )

        self.monitoring_label = str(
            self._theme_get(
                "auto_view.status.monitoring_label",
                "MONITORING",
            )
        )
        self.plc_label = str(
            self._theme_get(
                "auto_view.status.plc_label",
                "PLC",
            )
        )
        self.entered_label = str(
            self._theme_get(
                "auto_view.status.entered_label",
                "ENTERED",
            )
        )
        self.exited_label = str(
            self._theme_get(
                "auto_view.status.exited_label",
                "EXITED",
            )
        )
        self.current_people_label = str(
            self._theme_get(
                "auto_view.status.current_people_label",
                "CURRENT PEOPLE",
            )
        )
        self.eqp_status_label = str(
            self._theme_get(
                "auto_view.status.eqp_status_label",
                "EQP STATUS",
            )
        )

        self.running_text = str(
            self._theme_get(
                "auto_view.status.running_text",
                "RUNNING",
            )
        )
        self.stopped_text = str(
            self._theme_get(
                "auto_view.status.stopped_text",
                "STOPPED",
            )
        )
        self.connected_text = str(
            self._theme_get(
                "auto_view.status.connected_text",
                "CONNECTED",
            )
        )
        self.disconnected_text = str(
            self._theme_get(
                "auto_view.status.disconnected_text",
                "DISCONNECTED",
            )
        )
        self.safe_text = str(
            self._theme_get(
                "auto_view.status.safe_text",
                "SAFE",
            )
        )
        self.not_safe_text = str(
            self._theme_get(
                "auto_view.status.not_safe_text",
                "NOT SAFE",
            )
        )

        self.status_background = self._theme_get(
            "colors.status.background",
            "#FFFFFF",
        )
        self.status_title_text = self._theme_get(
            "colors.status.title_text",
            "#111111",
        )
        self.status_value_text = self._theme_get(
            "colors.status.value_text",
            "#111111",
        )

        self.status_item_themes = {}
        for key in self.STATUS_THEME_KEYS.values():
            self.status_item_themes[key] = {
                "background": self._theme_get(
                    f"colors.status.items.{key}.background",
                    self.status_background,
                ),
                "text": self._theme_get(
                    f"colors.status.items.{key}.text",
                    self.status_value_text,
                ),
            }

        self.running_color = self._theme_get(
            "colors.status.running",
            "#008000",
        )
        self.stopped_color = self._theme_get(
            "colors.status.stopped",
            "#808080",
        )
        self.connected_color = self._theme_get(
            "colors.status.connected",
            "#008000",
        )
        self.disconnected_color = self._theme_get(
            "colors.status.disconnected",
            "#C00000",
        )
        self.safe_color = self._theme_get(
            "colors.status.safe",
            "#008000",
        )
        self.not_safe_color = self._theme_get(
            "colors.status.not_safe",
            "#C00000",
        )

    def _theme_get(self, path, default=None):
        if self.theme_manager is not None:
            return self.theme_manager.get(path, default)

        current = self._theme
        if not path:
            return current

        for key in str(path).split("."):
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]

        return current

    def _get_font(self, font_path, default_name="normal"):
        definition = self._theme_get(
            f"fonts.{self._theme_get(font_path, default_name)}",
            None,
        )

        if not isinstance(definition, dict):
            definition = self._theme_get(
                f"fonts.{default_name}",
                {
                    "family": "Arial",
                    "size": 14,
                    "weight": "normal",
                },
            )

        family = definition.get("family", "Arial")
        size = self._safe_int(definition.get("size", 14), 14)
        weight = definition.get("weight", "normal")

        if weight not in ("normal", "bold"):
            weight = "normal"

        return ctk.CTkFont(
            family=family,
            size=size,
            weight=weight,
        )

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _hex_to_bgr(value, fallback):
        if not isinstance(value, str):
            value = fallback

        value = value.strip().lstrip("#")
        fallback = fallback.strip().lstrip("#")

        if len(value) != 6:
            value = fallback

        try:
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
            return blue, green, red
        except (TypeError, ValueError):
            return (
                int(fallback[4:6], 16),
                int(fallback[2:4], 16),
                int(fallback[0:2], 16),
            )

    def _on_theme_changed(self, _theme_manager=None):
        """
        Re-apply theme styling without rebuilding or repositioning the
        existing Auto View widgets.
        """
        try:
            self._load_theme()

            self.cameraFrame.configure(
                fg_color=self._theme_get(
                    "colors.frame_background",
                    "#FFFFFF",
                ),
            )

            self.statusFrame.configure(
                fg_color=self.status_background,
            )

            self.logFrame.configure(
                fg_color=self._theme_get(
                    "colors.log.background",
                    "#FFFFFF",
                ),
            )

            self.log_text.configure(
                fg_color=self._theme_get(
                    "colors.log.background",
                    "#FFFFFF",
                ),
                text_color=self._theme_get(
                    "colors.log.text",
                    "#111111",
                ),
                font=self._get_font(
                    "auto_view.log.font",
                    "log",
                ),
            )

            self._apply_camera_theme()
            self._apply_status_theme()

        except Exception as exc:
            self._on_error(
                -1,
                f"Theme update error: {exc}",
            )

    def _apply_camera_theme(self):
        for camera in self.camera_frames:
            camera.configure(
                fg_color=self.camera_background,
                border_color=self.camera_border,
                border_width=self.camera_border_width,
                corner_radius=self.camera_corner_radius,
            )

            camera_label_index = self.camera_frames.index(camera)

            if camera_label_index < len(self.camera_labels):
                label = self.camera_labels[camera_label_index]

                if self.camera_show_name:
                    try:
                        label_text = self.camera_name_template.format(
                            index=camera_label_index + 1,
                        )
                    except (KeyError, IndexError, ValueError):
                        label_text = (
                            f"Camera {camera_label_index + 1}"
                        )
                else:
                    label_text = ""

                label.configure(
                    text=label_text,
                    text_color=self.status_title_text,
                    font=self._get_font(
                        "fonts.camera_label"
                        if False
                        else "auto_view.camera_label.font",
                        "camera_label",
                    ),
                )

    def _apply_status_theme(self):
        if not hasattr(self, "_status_items"):
            return

        labels = {
            0: self.monitoring_label,
            1: self.plc_label,
            2: self.entered_label,
            3: self.exited_label,
            4: self.current_people_label,
            5: self.eqp_status_label,
        }

        for row, item in self._status_items.items():
            status_key = self.STATUS_THEME_KEYS.get(row)
            colors = self.status_item_themes.get(
                status_key,
                {},
            )

            item["frame"].configure(
                fg_color=colors.get(
                    "background",
                    self.status_background,
                ),
            )

            item["title"].configure(
                text=labels.get(row, item["title"].cget("text")),
                text_color=self.status_title_text,
                font=self._get_font(
                    "fonts.status_title"
                    if False
                    else "status.title_font",
                    "status_title",
                ),
            )

            item["value"].configure(
                text_color=colors.get(
                    "text",
                    self.status_value_text,
                ),
                font=self._get_font(
                    "fonts.status_value"
                    if False
                    else "status.value_font",
                    "status_value",
                ),
            )

    def _status_item_color(self, row):
        status_key = self.STATUS_THEME_KEYS.get(row)
        colors = self.status_item_themes.get(
            status_key,
            {},
        )
        return colors.get(
            "text",
            self.status_value_text,
        )

    def _set_status_value(
        self,
        row,
        widget,
        text,
        semantic_color=None,
    ):
        """
        Update a status value while respecting the status item's
        configured text color.

        Semantic state colors remain available as a fallback, but the
        per-item theme text color takes precedence.
        """
        configured_color = self._status_item_color(row)

        widget.configure(
            text=text,
            text_color=semantic_color
            if semantic_color is not None
            else configured_color,
        )

    # -------------------------------------------------------------
    # ViewModel connection
    # -------------------------------------------------------------
    def set_viewmodel(self, viewmodel):
        """Attach an AutoViewModel to the view."""
        self.stop_monitoring()
        self.vm = viewmodel

        if hasattr(self.vm, "camera_count"):
            new_camera_count = max(
                self.MIN_CAMERAS,
                min(self.MAX_CAMERAS, int(self.vm.camera_count)),
            )

            if new_camera_count != self.camera_count:
                self.camera_count = new_camera_count
                self._create_camera_layout()

        self._connect_viewmodel()
        self._refresh_status()

    def _connect_viewmodel(self):
        if self.vm is None:
            return

        if hasattr(self.vm, "set_update_callback"):
            self.vm.set_update_callback(
                self._on_frame_update
            )

        if hasattr(self.vm, "set_event_callback"):
            self.vm.set_event_callback(
                self._on_event
            )

        if hasattr(self.vm, "set_error_callback"):
            self.vm.set_error_callback(
                self._on_error
            )

    # -------------------------------------------------------------
    # Camera layout
    # -------------------------------------------------------------
    def _create_camera_layout(self):
        for frame in self.camera_frames:
            frame.destroy()

        self.camera_frames.clear()
        self.camera_labels.clear()
        self.camera_images.clear()
        self.camera_open_failed = [False] * self.camera_count
        self.camera_error_messages = [None] * self.camera_count
        self.expanded_camera = None

        if self.camera_count == 1:
            rows, columns = 1, 1
        elif self.camera_count == 2:
            rows, columns = 1, 2
        else:
            rows, columns = 2, 2

        for row in range(rows):
            self.cameraFrame.grid_rowconfigure(
                row,
                weight=1,
            )

        for column in range(columns):
            self.cameraFrame.grid_columnconfigure(
                column,
                weight=1,
            )

        for index in range(self.camera_count):
            row = index // columns
            column = index % columns

            camera = ctk.CTkFrame(
                self.cameraFrame,
                fg_color=self.camera_background,
                border_color=self.camera_border,
                border_width=self.camera_border_width,
                corner_radius=self.camera_corner_radius,
            )
            camera.grid(
                row=row,
                column=column,
                padx=5,
                pady=5,
                sticky="nsew",
            )

            if self.camera_show_name:
                try:
                    camera_text = self.camera_name_template.format(
                        index=index + 1,
                    )
                except (KeyError, IndexError, ValueError):
                    camera_text = f"Camera {index + 1}"
            else:
                camera_text = ""

            label = ctk.CTkLabel(
                camera,
                text=camera_text,
                text_color=self.status_title_text,
                font=self._get_font(
                    "auto_view.camera_label.font",
                    "camera_label",
                ),
            )
            label.place(
                relx=0.5,
                rely=0.5,
                anchor="center",
            )

            camera.bind(
                "<Double-Button-1>",
                lambda event, i=index: self._toggle_camera(i),
            )

            label.bind(
                "<Double-Button-1>",
                lambda event, i=index: self._toggle_camera(i),
            )

            self.camera_frames.append(camera)
            self.camera_labels.append(label)
            self.camera_images.append(None)

    # -------------------------------------------------------------
    # Live frame display
    # -------------------------------------------------------------
    def _on_frame_update(
        self,
        camera_index,
        frame,
        tracked_detections,
    ):
        """Receive a processed frame from AutoViewModel."""
        if not 0 <= camera_index < len(self.camera_labels):
            return

        # A successfully received frame means the camera is healthy again.
        self.camera_open_failed[camera_index] = False
        self.camera_error_messages[camera_index] = None

        self._display_frame(
            camera_index,
            frame,
            tracked_detections,
        )

        self._refresh_status()

    def _display_frame(
        self,
        camera_index,
        frame,
        tracked_detections=None,
    ):
        if frame is None:
            return

        try:
            display_frame = frame.copy()

            if self.person_overlay_show and tracked_detections:
                box_color = self._hex_to_bgr(
                    self.person_box_color,
                    "#00FF00",
                )
                text_color = self._hex_to_bgr(
                    self.person_text_color,
                    "#FFFFFF",
                )

                font_definition = self._theme_get(
                    "fonts.camera_label",
                    {
                        "family": "Arial",
                        "size": 14,
                        "weight": "normal",
                    },
                )

                font_size = max(
                    0.3,
                    self._safe_int(
                        font_definition.get("size", 14),
                        14,
                    ) / 25.0,
                )

                thickness = (
                    2
                    if font_definition.get("weight", "normal") == "bold"
                    else 1
                )

                for track in tracked_detections:
                    bbox = track.get("bbox")
                    track_id = track.get("track_id", "?")
                    confidence = track.get("confidence", 0.0)

                    if bbox is None or len(bbox) != 4:
                        continue

                    x1, y1, x2, y2 = map(int, bbox)

                    cv2.rectangle(
                        display_frame,
                        (x1, y1),
                        (x2, y2),
                        box_color,
                        self.person_box_width,
                    )

                    confidence_text = format(
                        confidence * 100,
                        f".{self.person_overlay_confidence_decimals}f",
                    )

                    try:
                        label = self.person_overlay_label_template.format(
                            track_id=track_id
                            if self.person_overlay_track_id
                            else "",
                            confidence=confidence_text
                            if self.person_overlay_confidence
                            else "",
                        )
                    except (KeyError, IndexError, ValueError):
                        parts = []

                        if self.person_overlay_track_id:
                            parts.append(
                                f"Person {track_id}"
                            )

                        if self.person_overlay_confidence:
                            parts.append(
                                f"{confidence_text}%"
                            )

                        label = " ".join(parts)

                    if label:
                        label_y = max(20, y1 - 8)

                        cv2.putText(
                            display_frame,
                            label,
                            (x1, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            font_size,
                            text_color,
                            thickness,
                            cv2.LINE_AA,
                        )

            counting_line = self._get_counting_line(camera_index)

            if self.counting_line_show and counting_line is not None:
                line_start, line_end = counting_line

                line_color = self._hex_to_bgr(
                    self.counting_line_color,
                    "#FF0000",
                )

                cv2.line(
                    display_frame,
                    tuple(map(int, line_start)),
                    tuple(map(int, line_end)),
                    line_color,
                    self.counting_line_width,
                )

                if self.counting_line_show_endpoints:
                    cv2.circle(
                        display_frame,
                        tuple(map(int, line_start)),
                        self.counting_line_endpoint_radius,
                        line_color,
                        -1,
                    )

                    cv2.circle(
                        display_frame,
                        tuple(map(int, line_end)),
                        self.counting_line_endpoint_radius,
                        line_color,
                        -1,
                    )

            rgb_frame = cv2.cvtColor(
                display_frame,
                cv2.COLOR_BGR2RGB,
            )

            image = Image.fromarray(rgb_frame)

            camera = self.camera_frames[camera_index]

            width = camera.winfo_width()
            height = camera.winfo_height()

            if width <= 1 or height <= 1:
                return

            image_ratio = image.width / image.height
            frame_ratio = width / height

            if image_ratio > frame_ratio:
                display_width = width - 10
                display_height = max(1, int(display_width / image_ratio))
            else:
                display_height = height - 10
                display_width = max(1, int(display_height * image_ratio))

            display_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(display_width, display_height),
            )

            label = self.camera_labels[camera_index]
            label.configure(
                image=display_image,
                text="",
            )
            self.camera_images[camera_index] = display_image

        except Exception as exc:
            self._on_error(
                camera_index,
                f"Frame display error: {exc}",
            )

    def _get_counting_line(self, camera_index):
        if self.vm is None:
            return None

        direction_models = getattr(
            self.vm,
            "direction_models",
            None,
        )

        if not isinstance(direction_models, list):
            return None

        if not 0 <= camera_index < len(direction_models):
            return None

        direction_model = direction_models[camera_index]
        line_start = getattr(
            direction_model,
            "line_start",
            None,
        )
        line_end = getattr(
            direction_model,
            "line_end",
            None,
        )

        if line_start is None or line_end is None:
            return None

        return line_start, line_end

    # -------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------
    def start_monitoring(self):
        """Start the ViewModel monitoring process and UI update loop."""
        if self.vm is None:
            self._append_log(
                "Auto ViewModel is not connected."
            )
            return False

        try:
            started = self.vm.start_monitoring()

            if not started:
                self._append_log(
                    "Monitoring could not be started."
                )
                self._refresh_status()
                return False

            self._refresh_status()
            self._schedule_monitoring_update()
            self._append_log(
                "Monitoring started."
            )

            return True

        except Exception as exc:
            self._append_log(
                f"Failed to start monitoring: {exc}"
            )
            self._refresh_status()
            return False

    def stop_monitoring(self):
        """Stop the monitoring loop and release the cameras."""
        if self.monitoring_loop_id is not None:
            try:
                self.after_cancel(
                    self.monitoring_loop_id
                )
            except (ValueError, TypeError):
                pass

            self.monitoring_loop_id = None

        if self.vm is not None:
            try:
                self.vm.stop_monitoring()
            except Exception as exc:
                self._append_log(
                    f"Error stopping monitoring: {exc}"
                )

        self._refresh_status()

    def _schedule_monitoring_update(self):
        if self.monitoring_loop_id is not None:
            return

        self.monitoring_loop_id = self.after(
            30,
            self._run_monitoring_update,
        )

    def _run_monitoring_update(self):
        self.monitoring_loop_id = None

        if self.vm is None:
            return

        if not self.vm.is_monitoring:
            self._refresh_status()
            return

        try:
            self.vm.process_frames()
        except Exception as exc:
            self._append_log(
                f"Monitoring error: {exc}"
            )

        self._refresh_status()

        if self.vm.is_monitoring:
            self._schedule_monitoring_update()

    # -------------------------------------------------------------
    # Status
    # -------------------------------------------------------------
    def _create_status_item(self, row, title, value):
        frame = ctk.CTkFrame(
            self.statusFrame,
            fg_color=self._theme_get(
                f"colors.status.items."
                f"{self.STATUS_THEME_KEYS.get(row, 'monitoring')}.background",
                self.status_background,
            ),
        )
        frame.grid(
            row=row,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(
            (0, 1),
            weight=1,
        )

        title_label = ctk.CTkLabel(
            frame,
            text=title,
            text_color=self.status_title_text,
            font=self._get_font(
                "status.title_font",
                "status_title",
            ),
        )

        title_label.grid(
            row=0,
            column=0,
            padx=5,
            pady=(5, 0),
            sticky="ew",
        )

        value_label = ctk.CTkLabel(
            frame,
            text=value,
            text_color=self._theme_get(
                f"colors.status.items."
                f"{self.STATUS_THEME_KEYS.get(row, 'monitoring')}.text",
                self.status_value_text,
            ),
            font=self._get_font(
                "status.value_font",
                "status_value",
            ),
        )

        value_label.grid(
            row=1,
            column=0,
            padx=5,
            pady=(0, 5),
            sticky="ew",
        )

        if not hasattr(self, "_status_items"):
            self._status_items = {}

        self._status_items[row] = {
            "frame": frame,
            "title": title_label,
            "value": value_label,
        }

        return value_label

    def _refresh_status(self):
        if self.vm is None:
            return

        try:
            monitoring = (
                self.running_text
                if self.vm.is_monitoring
                else self.stopped_text
            )

            self._set_status_value(
                0,
                self.monitoring_value,
                monitoring,
                (
                    self.running_color
                    if self.vm.is_monitoring
                    else self.stopped_color
                ),
            )

            plc_connected = False

            get_plc_status = getattr(
                self.vm,
                "get_plc_status",
                None,
            )

            if callable(get_plc_status):
                plc_status = get_plc_status()

                if isinstance(plc_status, dict):
                    plc_connected = bool(
                        plc_status.get(
                            "connected",
                            False,
                        )
                    )
                else:
                    plc_connected = bool(plc_status)

            self._set_status_value(
                1,
                self.plc_value,
                (
                    self.connected_text
                    if plc_connected
                    else self.disconnected_text
                ),
                (
                    self.connected_color
                    if plc_connected
                    else self.disconnected_color
                ),
            )

            counts = self.vm.get_counts()

            self._set_status_value(
                2,
                self.entered_value,
                str(counts.get("entered", 0)),
            )

            self._set_status_value(
                3,
                self.exited_value,
                str(counts.get("exited", 0)),
            )

            self._set_status_value(
                4,
                self.current_value,
                str(counts.get("current", 0)),
            )

            # Safety state is maintained by AutoViewModel and exposed
            # through get_plc_status() as "SAFE" / "NOT_SAFE".
            # Keep the UI synchronized with that authoritative state.
            safety_text = self.not_safe_text
            safe = False

            get_plc_status = getattr(
                self.vm,
                "get_plc_status",
                None,
            )

            if callable(get_plc_status):
                plc_status_for_safety = get_plc_status()

                if isinstance(plc_status_for_safety, dict):
                    safety_state = str(
                        plc_status_for_safety.get(
                            "safety",
                            "NOT_SAFE",
                        )
                    ).upper()
                    safe = safety_state == "SAFE"

            if safe:
                safety_text = self.safe_text

            self._set_status_value(
                5,
                self.safety_value,
                safety_text,
                self.safe_color if safe else self.not_safe_color,
            )

        except Exception as exc:
            self._on_error(
                -1,
                f"Status update error: {exc}",
            )

    # -------------------------------------------------------------
    # Events and logging
    # -------------------------------------------------------------
    def _on_event(self, camera_index, event, counts):
        direction = event.get(
            "direction",
            "UNKNOWN",
        )
        track_id = event.get(
            "track_id",
            "?",
        )

        self._append_log(
            f"Camera {camera_index + 1}: "
            f"Person {track_id} {direction} | "
            f"Current: {counts.get('current', 0)}"
        )

        self._refresh_status()

    def _on_error(self, camera_index, message):
        if camera_index < 0:
            self._append_log(message)
            return

        if camera_index >= len(self.camera_labels):
            return

        message_text = str(message)

        # Camera.open() reports this once when a device cannot be opened.
        # Keep that state in the camera tile and suppress the follow-up
        # "failed to read" callbacks generated by the monitoring loop.
        if "failed to open camera" in message_text.lower():
            self.camera_open_failed[camera_index] = True
            self.camera_error_messages[camera_index] = "open"

            camera_number = camera_index + 1
            self.camera_labels[camera_index].configure(
                image=None,
                text=f"Camera{camera_number} failed to open",
                text_color=self._theme_get(
                    "colors.status.not_safe",
                    "#C00000",
                ),
                font=self._get_font(
                    "auto_view.camera_label.font",
                    "camera_label",
                ),
            )
            self.camera_images[camera_index] = None

            self._append_log(
                f"Camera {camera_number}: {message_text}"
            )
            return

        if self.camera_open_failed[camera_index]:
            return

        # De-duplicate identical runtime errors from the camera loop.
        if self.camera_error_messages[camera_index] == message_text:
            return

        self.camera_error_messages[camera_index] = message_text
        self._append_log(
            f"Camera {camera_index + 1}: {message_text}"
        )

    def _append_log(self, message):
        self.log_text.insert(
            "end",
            f"{message}\n",
        )
        self.log_text.see("end")

    # -------------------------------------------------------------
    # Camera expand / restore
    # -------------------------------------------------------------
    def _toggle_camera(self, camera_index):
        if self.expanded_camera == camera_index:
            self._restore_cameras()
        else:
            self._expand_camera(camera_index)

    def _expand_camera(self, camera_index):
        if not 0 <= camera_index < len(self.camera_frames):
            return

        self.expanded_camera = camera_index

        for camera in self.camera_frames:
            camera.grid_forget()

        selected_camera = self.camera_frames[camera_index]

        selected_camera.place(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1,
        )

    def _restore_cameras(self):
        if self.expanded_camera is None:
            return

        selected_index = self.expanded_camera
        self.expanded_camera = None

        selected_camera = self.camera_frames[selected_index]
        selected_camera.place_forget()

        if self.camera_count == 1:
            rows, columns = 1, 1
        elif self.camera_count == 2:
            rows, columns = 1, 2
        else:
            rows, columns = 2, 2

        for index, camera in enumerate(self.camera_frames):
            row = index // columns
            column = index % columns

            camera.grid(
                row=row,
                column=column,
                padx=5,
                pady=5,
                sticky="nsew",
            )

    # -------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------
    def destroy(self):
        self.stop_monitoring()

        if self.theme_manager is not None:
            try:
                self.theme_manager.remove_listener(
                    self._on_theme_changed
                )
            except Exception:
                pass

        super().destroy()
