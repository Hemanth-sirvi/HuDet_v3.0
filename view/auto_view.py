import customtkinter as ctk
from PIL import Image

import cv2


class AutoView(ctk.CTkFrame):
    """
    Auto View for live monitoring.

    The view is responsible for displaying data supplied by AutoViewModel.
    It does not perform detection, tracking, direction calculation, or
    people counting itself.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(self, master, viewmodel=None, camera_count=4, **kwargs):
        super().__init__(master, **kwargs)

        self.vm = viewmodel

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

        # ---------------------------------------------------------
        # Main layout
        # ---------------------------------------------------------
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=9)
        self.grid_columnconfigure(1, weight=1)

        # ---------------------------------------------------------
        # Camera area
        # ---------------------------------------------------------
        self.cameraFrame = ctk.CTkFrame(self)
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
        self.statusFrame = ctk.CTkFrame(self)
        self.statusFrame.grid(
            row=0,
            column=1,
            padx=(5, 0),
            pady=0,
            sticky="nsew",
        )

        self.statusFrame.grid_columnconfigure(0, weight=1)

        self.monitoring_value = self._create_status_item(0,"MONITORING","STOPPED",)

        self.plc_value = self._create_status_item(1,"PLC","DISCONNECTED",)

        self.entered_value = self._create_status_item(2,"ENTERED","0",)

        self.exited_value = self._create_status_item(3,"EXITED","0",)

        self.current_value = self._create_status_item(4,"CURRENT PEOPLE","0",)

        self.safety_value = self._create_status_item(5,"EQP STATUS","NOT SAFE",)

        # ---------------------------------------------------------
        # Log area
        # ---------------------------------------------------------
        self.statusFrame.grid_rowconfigure(6, weight=1)

        self.logFrame = ctk.CTkFrame(self.statusFrame)
        self.logFrame.grid(row=6,column=0,padx=5,pady=5,sticky="nsew",)

        self.logFrame.grid_rowconfigure(0, weight=1)
        self.logFrame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(self.logFrame)
        self.log_text.grid(row=0,column=0,padx=5,pady=5,sticky="nsew",)

        # Connect the ViewModel callbacks when one is supplied.
        self._connect_viewmodel()

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

        if hasattr(self.vm, "set_plc_connection_callback"):
            self.vm.set_plc_connection_callback(
                self._on_plc_connection_change
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

            camera = ctk.CTkFrame(self.cameraFrame)
            camera.grid(
                row=row,
                column=column,
                padx=5,
                pady=5,
                sticky="nsew",
            )

            label = ctk.CTkLabel(
                camera,
                text=f"Camera {index + 1}",
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

        self._display_frame(camera_index, frame)

        self._refresh_status()

    def _display_frame(self, camera_index, frame):
        if frame is None:
            return

        try:
            rgb_frame = cv2.cvtColor(
                frame,
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
                display_height = max(
                    1,
                    int(display_width / image_ratio),
                )
            else:
                display_height = height - 10
                display_width = max(
                    1,
                    int(display_height * image_ratio),
                )

            display_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(
                    display_width,
                    display_height,
                ),
            )

            label = self.camera_labels[camera_index]
            label.configure(
                image=display_image,
                text="",
            )

            # Keep a reference so Tkinter does not garbage-collect it.
            self.camera_images[camera_index] = display_image

        except Exception as exc:
            self._on_error(
                camera_index,
                f"Frame display error: {exc}",
            )

    # -------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------
    def start_monitoring(self):
        """Start the ViewModel monitoring process and UI update loop."""
        if self.vm is None:
            self._append_log("Auto ViewModel is not connected.")
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
            self._append_log("Monitoring started.")

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
                self.after_cancel(self.monitoring_loop_id)
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
    def _refresh_status(self):
        if self.vm is None:
            return

        try:
            monitoring = (
                "RUNNING"
                if self.vm.is_monitoring
                else "STOPPED"
            )

            counts = self.vm.get_counts()

            self.monitoring_value.configure(
                text=monitoring
            )

            self.entered_value.configure(
                text=str(counts["entered"])
            )

            self.exited_value.configure(
                text=str(counts["exited"])
            )

            self.current_value.configure(
                text=str(counts["current"])
            )

            self._refresh_plc_status()

        except Exception as exc:
            self._on_error(
                -1,
                f"Status update error: {exc}",
            )

    def _refresh_plc_status(self):
        """
        Pull PLC connection/safety state from AutoViewModel, when it
        exposes get_plc_status(). Falls back to the original static
        labels if the ViewModel does not support PLC status (e.g. an
        older or test ViewModel), so this stays backwards compatible.
        """
        get_plc_status = getattr(self.vm, "get_plc_status", None)

        if not callable(get_plc_status):
            return

        plc_status = get_plc_status()

        self.plc_value.configure(
            text="CONNECTED" if plc_status.get("connected") else "DISCONNECTED"
        )

        safety = plc_status.get("safety", "NOT_SAFE")
        safety_display = "SAFE" if safety == "SAFE" else "NOT SAFE"

        self.safety_value.configure(text=safety_display)

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

    def _on_plc_connection_change(self, is_connected):
        self._append_log(
            "PLC connected." if is_connected else "PLC disconnected."
        )
        self._refresh_status()

    def _on_error(self, camera_index, message):
        if camera_index >= 0:
            self._append_log(
                f"Camera {camera_index + 1}: {message}"
            )
        else:
            self._append_log(message)

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
    # Status item
    # -------------------------------------------------------------
    def _create_status_item(self, row, title, value):
        frame = ctk.CTkFrame(self.statusFrame)
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
            font=ctk.CTkFont(
                size=16,
                weight="bold",
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
            font=ctk.CTkFont(
                size=20,
                weight="bold",
            ),
        )

        value_label.grid(
            row=1,
            column=0,
            padx=5,
            pady=(0, 5),
            sticky="ew",
        )

        return value_label

    # -------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------
    def destroy(self):
        self.stop_monitoring()
        super().destroy()