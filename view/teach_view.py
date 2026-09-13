import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk
import cv2


class TeachView(ctk.CTkFrame):
    """
    Teach View for configuring the counting line for each camera.

    The view provides:
        - Dynamic camera selection (1-4 cameras)
        - Live camera preview when a frame is supplied
        - Mouse-drawn counting line
        - ENTER-side selection
        - Save / clear controls

    Persistence and application configuration are intentionally left to
    TeachViewModel.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(
        self,
        master,
        viewmodel=None,
        camera_count=1,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.vm = viewmodel

        if self.vm is not None and hasattr(self.vm, "camera_count"):
            camera_count = self.vm.camera_count

        self.camera_count = max(
            self.MIN_CAMERAS,
            min(self.MAX_CAMERAS, int(camera_count)),
        )

        self.selected_camera = 0
        self.enter_side = "negative"

        self.line_start = None
        self.line_end = None

        self._display_image = None
        self._source_frame_size = None
        self._display_geometry = None

        # Created lazily in _ensure_overlay_canvas().
        self._overlay_canvas = None

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)

        # --------------------------------------------------------------
        # Camera selection / settings panel
        # --------------------------------------------------------------
        self.controlFrame = ctk.CTkFrame(self)
        self.controlFrame.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.controlFrame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.controlFrame,
            text="TEACH",
            font=ctk.CTkFont(
                size=24,
                weight="bold",
            ),
        )
        title.grid(
            row=0,
            column=0,
            padx=10,
            pady=(10, 15),
            sticky="ew",
        )

        camera_title = ctk.CTkLabel(
            self.controlFrame,
            text="SELECT CAMERA",
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
        )
        camera_title.grid(
            row=1,
            column=0,
            padx=10,
            pady=(0, 5),
            sticky="w",
        )

        self.camera_buttons_frame = ctk.CTkFrame(
            self.controlFrame
        )
        self.camera_buttons_frame.grid(
            row=2,
            column=0,
            padx=10,
            pady=5,
            sticky="ew",
        )

        self.camera_buttons = []
        self._create_camera_buttons()

        direction_title = ctk.CTkLabel(
            self.controlFrame,
            text="ENTER DIRECTION",
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
        )
        direction_title.grid(
            row=3,
            column=0,
            padx=10,
            pady=(20, 5),
            sticky="w",
        )

        self.enter_side_variable = ctk.StringVar(
            value="negative"
        )

        self.enter_negative = ctk.CTkRadioButton(
            self.controlFrame,
            text="Negative side",
            variable=self.enter_side_variable,
            value="negative",
            command=self._direction_changed,
        )
        self.enter_negative.grid(
            row=4,
            column=0,
            padx=15,
            pady=5,
            sticky="w",
        )

        self.enter_positive = ctk.CTkRadioButton(
            self.controlFrame,
            text="Positive side",
            variable=self.enter_side_variable,
            value="positive",
            command=self._direction_changed,
        )
        self.enter_positive.grid(
            row=5,
            column=0,
            padx=15,
            pady=5,
            sticky="w",
        )

        self.instruction_label = ctk.CTkLabel(
            self.controlFrame,
            text=(
                "Click and drag on the camera image "
                "to draw the counting line."
            ),
            wraplength=220,
            justify="left",
        )
        self.instruction_label.grid(
            row=6,
            column=0,
            padx=10,
            pady=(20, 10),
            sticky="ew",
        )

        self.clear_button = ctk.CTkButton(
            self.controlFrame,
            text="CLEAR LINE",
            command=self.clear_line,
        )
        self.clear_button.grid(
            row=7,
            column=0,
            padx=10,
            pady=5,
            sticky="ew",
        )

        self.save_button = ctk.CTkButton(
            self.controlFrame,
            text="SAVE",
            command=self._save,
        )
        self.save_button.grid(
            row=8,
            column=0,
            padx=10,
            pady=5,
            sticky="ew",
        )

        self.status_label = ctk.CTkLabel(
            self.controlFrame,
            text="No counting line set.",
            wraplength=220,
        )
        self.status_label.grid(
            row=9,
            column=0,
            padx=10,
            pady=10,
            sticky="ew",
        )

        self.controlFrame.grid_rowconfigure(
            10,
            weight=1,
        )

        # --------------------------------------------------------------
        # Camera preview
        # --------------------------------------------------------------
        self.previewFrame = ctk.CTkFrame(self)
        self.previewFrame.grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self.previewFrame.grid_rowconfigure(1, weight=1)
        self.previewFrame.grid_columnconfigure(0, weight=1)

        self.preview_title_label = ctk.CTkLabel(
            self.previewFrame,
            text="Camera 1",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.preview_title_label.grid(
            row=0,
            column=0,
            padx=5,
            pady=(5, 0),
            sticky="w",
        )

        # The canvas itself is created lazily in _ensure_overlay_canvas,
        # once we know the CTk color theme, and only once.
        self._overlay_canvas = None
        self._ensure_overlay_canvas()

        self._update_camera_selection()

    def _ensure_overlay_canvas(self):
        """
        Create the drawing surface used for the camera preview and the
        counting-line overlay, if it does not already exist.

        A plain tkinter.Canvas is used (rather than a CTkLabel) because
        it supports independently addressable, layered items
        ("camera_image" and "counting_line") via tags, which is what
        set_camera_frame()/_draw_line() rely on.
        """
        if self._overlay_canvas is not None:
            return

        # Match the canvas background to the current CTk theme so it
        # doesn't show up as a plain white/gray tkinter rectangle.
        try:
            bg_color = self.previewFrame.cget("fg_color")
            if isinstance(bg_color, (list, tuple)):
                bg_color = bg_color[1 if ctk.get_appearance_mode() == "Dark" else 0]
        except Exception:
            bg_color = None

        self._overlay_canvas = tk.Canvas(
            self.previewFrame,
            highlightthickness=0,
            bd=0,
            bg=bg_color if bg_color else "black",
        )
        self._overlay_canvas.grid(
            row=1,
            column=0,
            padx=5,
            pady=5,
            sticky="nsew",
        )

        self._overlay_canvas.bind(
            "<ButtonPress-1>",
            self._line_start_event,
        )
        self._overlay_canvas.bind(
            "<B1-Motion>",
            self._line_draw_event,
        )
        self._overlay_canvas.bind(
            "<ButtonRelease-1>",
            self._line_end_event,
        )

        # Redraw whenever the canvas is resized so the image/line stay
        # correctly scaled and centered.
        self._overlay_canvas.bind(
            "<Configure>",
            self._on_canvas_resize,
        )

    def _on_canvas_resize(self, event):
        # Re-run the same sizing/centering logic against the last raw
        # frame dimensions we know about. We don't keep the original
        # cv2 frame around, so we just rescale the existing PIL-derived
        # PhotoImage's source size via _source_frame_size and redraw
        # the line; the image itself will refresh next time a new
        # frame is pushed in (e.g. on camera reselect).
        if self._source_frame_size is None:
            return

        self._draw_line()

    # ------------------------------------------------------------------
    # Camera selection
    # ------------------------------------------------------------------
    def _create_camera_buttons(self):
        for button in self.camera_buttons:
            button.destroy()

        self.camera_buttons.clear()

        for index in range(self.camera_count):
            button = ctk.CTkButton(
                self.camera_buttons_frame,
                text=f"CAM {index + 1}",
                command=lambda i=index: self.select_camera(i),
            )

            column_count = 2

            button.grid(
                row=index // column_count,
                column=index % column_count,
                padx=3,
                pady=3,
                sticky="ew",
            )

            self.camera_buttons_frame.grid_columnconfigure(
                index % column_count,
                weight=1,
            )

            self.camera_buttons.append(button)

    def select_camera(self, camera_index):
        if not 0 <= camera_index < self.camera_count:
            return

        self.selected_camera = camera_index

        if hasattr(self, "preview_title_label"):
            self.preview_title_label.configure(
                text=f"Camera {camera_index + 1}"
            )

        self._load_camera_configuration()
        self._update_camera_selection()

        # Teach View only needs one preview frame from the selected
        # camera. Monitoring is normally stopped while teaching, so the
        # AutoViewModel does not have a continuously updated frame.
        frame = self._capture_preview_frame(camera_index)

        if frame is not None:
            self.set_camera_frame(frame)

    def _update_camera_selection(self):
        for index, button in enumerate(self.camera_buttons):
            if index == self.selected_camera:
                button.configure(
                    fg_color=button.cget("hover_color"),
                )
            else:
                button.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                )

    def _capture_preview_frame(self, camera_index):
        """
        Capture one frame from the selected camera for Teach View.

        The camera is opened only for the preview capture and then
        released immediately. This keeps Teach View independent from
        the Auto monitoring loop.
        """
        if self.vm is None:
            return None

        auto_viewmodel = getattr(
            self.vm,
            "auto_viewmodel",
            None,
        )

        if auto_viewmodel is None:
            return None

        cameras = getattr(
            auto_viewmodel,
            "cameras",
            None,
        )

        if not isinstance(cameras, list):
            return None

        if not 0 <= camera_index < len(cameras):
            return None

        camera = cameras[camera_index]

        try:
            if not camera.open():
                self.status_label.configure(
                    text=(
                        f"Camera {camera_index + 1} "
                        "could not be opened."
                    )
                )
                return None

            success, frame = camera.read()

            if not success:
                self.status_label.configure(
                    text=(
                        f"Camera {camera_index + 1} "
                        "frame could not be read."
                    )
                )
                return None

            return frame

        except Exception as exc:
            self.status_label.configure(
                text=(
                    f"Camera {camera_index + 1} "
                    f"preview error: {exc}"
                )
            )
            return None

        finally:
            camera.release()

    # ------------------------------------------------------------------
    # Camera frame
    # ------------------------------------------------------------------
    def set_camera_frame(self, frame):
        """
        Display a single OpenCV BGR frame on the preview canvas.

        The canvas is the only drawing surface. The camera image is placed
        as the background item and the counting line is placed above it.
        """
        if frame is None:
            return

        height, width = frame.shape[:2]

        if width <= 0 or height <= 0:
            return

        self._source_frame_size = (width, height)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        self._ensure_overlay_canvas()

        # Wait until the canvas has a usable size.
        self.update_idletasks()

        canvas_width = max(
            1,
            self._overlay_canvas.winfo_width(),
        )
        canvas_height = max(
            1,
            self._overlay_canvas.winfo_height(),
        )

        display_width, display_height = (
            self._calculate_display_size(
                width,
                height,
                canvas_width,
                canvas_height,
            )
        )

        image = image.resize(
            (display_width, display_height),
            Image.Resampling.LANCZOS,
        )

        self._display_image = ImageTk.PhotoImage(image)

        # Remove only the previous camera image and line.
        self._overlay_canvas.delete("camera_image")
        self._overlay_canvas.delete("counting_line")

        self._display_geometry = {
            "width": display_width,
            "height": display_height,
            "x": (canvas_width - display_width) / 2,
            "y": (canvas_height - display_height) / 2,
        }

        self._overlay_canvas.create_image(
            canvas_width / 2,
            canvas_height / 2,
            image=self._display_image,
            anchor="center",
            tags=("camera_image",),
        )

        # Keep a strong reference to the image.
        self._overlay_canvas.image = self._display_image

        # Restore an existing line, if there is one.
        self._draw_line()

    @staticmethod
    def _calculate_display_size(
        source_width,
        source_height,
        canvas_width,
        canvas_height,
    ):
        source_ratio = source_width / source_height
        canvas_ratio = canvas_width / canvas_height

        if source_ratio > canvas_ratio:
            display_width = canvas_width
            display_height = max(
                1,
                int(display_width / source_ratio),
            )
        else:
            display_height = canvas_height
            display_width = max(
                1,
                int(display_height * source_ratio),
            )

        return display_width, display_height

    # ------------------------------------------------------------------
    # Counting-line drawing
    # ------------------------------------------------------------------
    def _line_start_event(self, event):
        if self._display_geometry is None:
            # No frame has been loaded yet; nothing sensible to draw on.
            return

        self.line_start = self._event_to_source_coordinates(
            event.x,
            event.y,
        )
        self.line_end = self.line_start
        self._draw_line()

    def _line_draw_event(self, event):
        if self.line_start is None or self._display_geometry is None:
            return

        self.line_end = self._event_to_source_coordinates(
            event.x,
            event.y,
        )

        self._draw_line()

    def _line_end_event(self, event):
        if self.line_start is None or self._display_geometry is None:
            return

        self.line_end = self._event_to_source_coordinates(
            event.x,
            event.y,
        )

        self._draw_line()
        self._update_line_status()

    def _event_to_source_coordinates(self, x, y):
        if self._source_frame_size is None or self._display_geometry is None:
            return x, y

        source_width, source_height = self._source_frame_size
        geometry = self._display_geometry

        source_x = int(
            (x - geometry["x"])
            * source_width
            / geometry["width"]
        )

        source_y = int(
            (y - geometry["y"])
            * source_height
            / geometry["height"]
        )

        source_x = max(
            0,
            min(source_width - 1, source_x),
        )

        source_y = max(
            0,
            min(source_height - 1, source_y),
        )

        return source_x, source_y

    def _source_to_preview_coordinates(self, point):
        if self._source_frame_size is None or self._display_geometry is None:
            return point

        source_width, source_height = self._source_frame_size
        geometry = self._display_geometry

        preview_x = geometry["x"] + (
            point[0] * geometry["width"] / source_width
        )
        preview_y = geometry["y"] + (
            point[1] * geometry["height"] / source_height
        )

        return preview_x, preview_y

    def _draw_line(self):
        if self.line_start is None or self.line_end is None:
            return

        if self._overlay_canvas is None or self._display_geometry is None:
            return

        # Only delete the line. The camera image is never touched while
        # the operator is dragging.
        self._overlay_canvas.delete("counting_line")

        start = self._source_to_preview_coordinates(
            self.line_start
        )
        end = self._source_to_preview_coordinates(
            self.line_end
        )

        self._overlay_canvas.create_line(
            start[0],
            start[1],
            end[0],
            end[1],
            fill="red",
            width=5,
            tags=("counting_line",),
        )

        # This is the final operation, guaranteeing that the line is
        # above the camera image.
        self._overlay_canvas.tag_raise(
            "counting_line"
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _direction_changed(self):
        self.enter_side = self.enter_side_variable.get()

    def _load_camera_configuration(self):
        self.line_start = None
        self.line_end = None

        if self.vm is None:
            self.enter_side = "negative"
            self.enter_side_variable.set("negative")
            self._update_line_status()
            return

        get_config = getattr(
            self.vm,
            "get_camera_configuration",
            None,
        )

        if not callable(get_config):
            self._update_line_status()
            return

        config = get_config(self.selected_camera)

        if not config:
            self.enter_side = "negative"
            self.enter_side_variable.set("negative")
            self._update_line_status()
            return

        self.line_start = config.get("line_start")
        self.line_end = config.get("line_end")

        self.enter_side = config.get(
            "enter_side",
            "negative",
        )

        self.enter_side_variable.set(
            self.enter_side
        )

        self.after_idle(self._draw_line)
        self._update_line_status()

    def clear_line(self):
        self.line_start = None
        self.line_end = None

        if self._overlay_canvas is not None:
            self._overlay_canvas.delete(
                "counting_line"
            )

        self._update_line_status()

    def _update_line_status(self):
        if self.line_start is None or self.line_end is None:
            self.status_label.configure(
                text="No counting line set."
            )
            return

        self.status_label.configure(
            text=(
                f"Camera {self.selected_camera + 1}\n"
                f"Line: {self.line_start} → {self.line_end}\n"
                f"ENTER side: {self.enter_side}"
            )
        )

    def _save(self):
        if self.line_start is None or self.line_end is None:
            self.status_label.configure(
                text="Draw a counting line before saving."
            )
            return

        if self.vm is not None:
            save_config = getattr(
                self.vm,
                "save_camera_configuration",
                None,
            )

            if callable(save_config):
                save_config(
                    self.selected_camera,
                    self.line_start,
                    self.line_end,
                    self.enter_side,
                )

        self.status_label.configure(
            text=(
                f"Camera {self.selected_camera + 1} "
                "configuration saved."
            )
        )

    # ------------------------------------------------------------------
    # ViewModel
    # ------------------------------------------------------------------
    def set_viewmodel(self, viewmodel):
        self.vm = viewmodel

        if self.vm is not None and hasattr(
            self.vm,
            "camera_count",
        ):
            new_count = max(
                self.MIN_CAMERAS,
                min(
                    self.MAX_CAMERAS,
                    int(self.vm.camera_count),
                ),
            )

            if new_count != self.camera_count:
                self.camera_count = new_count
                self._create_camera_buttons()

        self.select_camera(
            min(
                self.selected_camera,
                self.camera_count - 1,
            )
        )