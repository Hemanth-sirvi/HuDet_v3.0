from model.camera_model import CameraModel
from model.config_manager import ConfigManager
from model.counter_model import CounterModel
from model.detection_model import DetectionModel
from model.direction_model import DirectionModel
from model.plc_model import PLCModel
from model.tracking_model import TrackingModel


class AutoViewModel:
    """
    Coordinates camera capture, detection, tracking, direction detection,
    people counting, and PLC communication for Auto View.

    The ViewModel does not directly manipulate CustomTkinter widgets.

    Every tunable parameter across the model layer (DetectionModel,
    TrackingModel, DirectionModel, CounterModel, PLCModel) as well as
    the camera fleet and safety-threshold settings is sourced from
    ConfigManager. Explicit constructor arguments always take priority
    over whatever is stored on disk - this keeps existing direct-
    instantiation call sites (and tests) working unchanged, while a
    plain AutoViewModel() picks up everything from config/config.json.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    # Sent to the PLC as CMD|SAFETY|<value>.
    SAFETY_SAFE = "SAFE"
    SAFETY_NOT_SAFE = "NOT_SAFE"

    def __init__(
        self,
        camera_count=None,
        camera_indices=None,
        camera_resolution=None,
        model_path=None,
        confidence_threshold=None,
        device=None,
        image_size=None,
        iou_threshold=None,
        max_missed_frames=None,
        minimum_movement=None,
        cooldown_frames=None,
        counting_lines=None,
        initial_count=None,
        plc_host=None,
        plc_port=None,
        plc_auto_connect=None,
        plc_timeout=None,
        plc_buffer_size=None,
        plc_encoding=None,
        occupancy_safety_threshold=None,
        config_manager=None,
    ):
        # ------------------------------------------------------------
        # Configuration
        #
        # config_manager is the single source of truth for defaults.
        # Any explicit argument above overrides the corresponding
        # config value for this instance only; the resolved value is
        # what later gets written back out via save_full_config().
        # ------------------------------------------------------------
        self.config_manager = (
            config_manager
            if config_manager is not None
            else ConfigManager()
        )

        camera_settings = self.config_manager.get_camera_settings()
        detection_settings = self.config_manager.get_detection_settings()
        tracking_settings = self.config_manager.get_tracking_settings()
        direction_defaults = self.config_manager.get_direction_defaults()
        counter_settings = self.config_manager.get_counter_settings()
        plc_settings = self.config_manager.get_plc_settings()
        safety_settings = self.config_manager.get_safety_settings()

        self.camera_count = self._clamp_camera_count(
            camera_count
            if camera_count is not None
            else camera_settings["camera_count"]
        )

        self.camera_indices = self._build_camera_indices(
            camera_indices
            if camera_indices is not None
            else camera_settings["camera_indices"]
        )

        self.camera_resolution = (
            tuple(camera_resolution)
            if camera_resolution is not None
            else camera_settings["camera_resolution"]
        )

        # --- DetectionModel settings ---------------------------------
        self.detection_settings = {
            "model_path": (
                model_path
                if model_path is not None
                else detection_settings["model_path"]
            ),
            "confidence_threshold": (
                confidence_threshold
                if confidence_threshold is not None
                else detection_settings["confidence_threshold"]
            ),
            "device": (
                device if device is not None else detection_settings["device"]
            ),
            "image_size": (
                image_size
                if image_size is not None
                else detection_settings["image_size"]
            ),
        }

        # --- TrackingModel global defaults ---------------------------
        self.tracking_settings = {
            "iou_threshold": (
                iou_threshold
                if iou_threshold is not None
                else tracking_settings["iou_threshold"]
            ),
            "max_missed_frames": (
                max_missed_frames
                if max_missed_frames is not None
                else tracking_settings["max_missed_frames"]
            ),
        }

        # --- DirectionModel global defaults ---------------------------
        self.direction_defaults = {
            "minimum_movement": (
                minimum_movement
                if minimum_movement is not None
                else direction_defaults["minimum_movement"]
            ),
            "cooldown_frames": (
                cooldown_frames
                if cooldown_frames is not None
                else direction_defaults["cooldown_frames"]
            ),
        }

        if counting_lines is None:
            counting_lines = self.config_manager.get_counting_lines()

        # --- CounterModel settings ------------------------------------
        resolved_initial_count = (
            initial_count
            if initial_count is not None
            else counter_settings["initial_count"]
        )

        # --- PLCModel settings ------------------------------------------
        self.plc_settings = {
            "host": plc_host if plc_host is not None else plc_settings["host"],
            "port": plc_port if plc_port is not None else plc_settings["port"],
            "timeout": (
                plc_timeout
                if plc_timeout is not None
                else plc_settings["timeout"]
            ),
            "buffer_size": (
                plc_buffer_size
                if plc_buffer_size is not None
                else plc_settings["buffer_size"]
            ),
            "encoding": (
                plc_encoding
                if plc_encoding is not None
                else plc_settings["encoding"]
            ),
        }

        self.plc_auto_connect = (
            plc_auto_connect
            if plc_auto_connect is not None
            else plc_settings["auto_connect"]
        )

        self.occupancy_safety_threshold = (
            occupancy_safety_threshold
            if occupancy_safety_threshold is not None
            else safety_settings["occupancy_safety_threshold"]
        )

        # ------------------------------------------------------------
        # Model construction
        # ------------------------------------------------------------
        self.detection_model = DetectionModel(
            model_path=self.detection_settings["model_path"],
            confidence_threshold=self.detection_settings["confidence_threshold"],
            device=self.detection_settings["device"],
            image_size=self.detection_settings["image_size"],
        )

        self.cameras = []
        self.trackers = []
        self.direction_models = []

        self.counter = CounterModel(initial_count=resolved_initial_count)

        self.frames = [None] * self.camera_count
        self.latest_detections = [[] for _ in range(self.camera_count)]
        self.latest_tracks = [[] for _ in range(self.camera_count)]
        self.latest_events = [[] for _ in range(self.camera_count)]

        self.monitoring = False
        self._update_callback = None
        self._event_callback = None
        self._error_callback = None
        self._plc_connection_callback = None

        self._create_camera_models(counting_lines)

        # ------------------------------------------------------------
        # PLC
        # ------------------------------------------------------------
        self.plc_model = PLCModel(
            host=self.plc_settings["host"],
            port=self.plc_settings["port"],
            timeout=self.plc_settings["timeout"],
            buffer_size=self.plc_settings["buffer_size"],
            encoding=self.plc_settings["encoding"],
        )

        self._plc_connected = False
        self._plc_status = {}
        self._safety_status = self.SAFETY_SAFE

        self.plc_model.set_connection_callback(
            self._handle_plc_connection_change
        )
        self.plc_model.set_status_callback(self._handle_plc_status)
        self.plc_model.set_error_callback(self._handle_plc_error)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _create_camera_models(self, counting_lines):
        if counting_lines is None:
            counting_lines = [None] * self.camera_count

        if len(counting_lines) < self.camera_count:
            counting_lines = list(counting_lines) + [
                None
                for _ in range(
                    self.camera_count - len(counting_lines)
                )
            ]

        for index in range(self.camera_count):
            camera = CameraModel(
                camera_index=self.camera_indices[index],
                width=self.camera_resolution[0],
                height=self.camera_resolution[1],
            )

            tracker = TrackingModel(
                **self._resolve_tracking_settings(index)
            )

            direction_model = self._build_direction_model(
                counting_lines[index]
            )

            self.cameras.append(camera)
            self.trackers.append(tracker)
            self.direction_models.append(direction_model)

    def _resolve_tracking_settings(self, camera_index):
        """
        Merge the global tracking defaults with any per-camera override
        stored in ConfigManager for this camera index.
        """
        settings = dict(self.tracking_settings)
        override = self.config_manager.get_tracking_override(camera_index)

        if override:
            settings.update(
                {
                    key: value
                    for key, value in override.items()
                    if value is not None
                }
            )

        return settings

    def _build_direction_model(self, direction_config):
        """
        Build one camera's DirectionModel, applying direction_defaults
        for any field the per-camera counting-line entry does not
        override.
        """
        if not direction_config:
            return DirectionModel(
                minimum_movement=self.direction_defaults["minimum_movement"],
                cooldown_frames=self.direction_defaults["cooldown_frames"],
            )

        return DirectionModel(
            line_start=direction_config["line_start"],
            line_end=direction_config["line_end"],
            enter_side=direction_config.get("enter_side", "negative"),
            minimum_movement=direction_config.get(
                "minimum_movement",
                self.direction_defaults["minimum_movement"],
            ),
            cooldown_frames=direction_config.get(
                "cooldown_frames",
                self.direction_defaults["cooldown_frames"],
            ),
        )

    @classmethod
    def _clamp_camera_count(cls, camera_count):
        if not isinstance(camera_count, int):
            raise TypeError("camera_count must be an integer.")

        return max(
            cls.MIN_CAMERAS,
            min(cls.MAX_CAMERAS, camera_count),
        )

    def _build_camera_indices(self, camera_indices):
        if camera_indices is None:
            return list(range(self.camera_count))

        indices = list(camera_indices)

        if len(indices) < self.camera_count:
            start_index = indices[-1] + 1 if indices else 0

            while len(indices) < self.camera_count:
                indices.append(start_index)
                start_index += 1

        return indices[:self.camera_count]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def set_update_callback(self, callback):
        """
        Register a callback invoked after each processed camera frame.

        Callback receives:
            camera_index
            frame
            tracked_detections
        """
        self._update_callback = callback

    def set_event_callback(self, callback):
        """
        Register a callback invoked when ENTER / EXIT events occur.

        Callback receives:
            camera_index
            event
            counts
        """
        self._event_callback = callback

    def set_error_callback(self, callback):
        """Register a callback for camera/model processing errors."""
        self._error_callback = callback

    def set_plc_connection_callback(self, callback):
        """
        Register a callback invoked when the PLC connection state
        changes.

        Callback receives:
            is_connected
        """
        self._plc_connection_callback = callback

    # ------------------------------------------------------------------
    # Monitoring control
    # ------------------------------------------------------------------
    def start_monitoring(self):
        """
        Open all configured cameras, connect to the PLC, and start
        monitoring.

        Returns:
            True when at least one configured camera opens successfully.
        """
        if self.monitoring:
            return True

        opened_cameras = []

        for index, camera in enumerate(self.cameras):
            try:
                if camera.open():
                    opened_cameras.append(index)
                else:
                    self._report_error(
                        index,
                        f"Failed to open camera {self.camera_indices[index]}",
                    )
            except Exception as exc:
                self._report_error(index, str(exc))

        # Do not claim monitoring is running when no camera is available.
        if not opened_cameras:
            self.monitoring = False
            return False

        self.monitoring = True

        # PLC connectivity is independent from camera monitoring: a
        # camera-only setup should still be able to run even if the PLC
        # is offline. Failures are surfaced through the error callback
        # rather than blocking start_monitoring().
        if self.plc_auto_connect and not self.plc_model.is_connected:
            self.plc_model.connect()

        self._publish_safety_status(self.counter.get_counts())

        return True

    def stop_monitoring(self):
        """Stop monitoring, release every camera, and disconnect the PLC."""
        self.monitoring = False

        for camera in self.cameras:
            camera.release()

        for tracker in self.trackers:
            tracker.reset()

        for direction_model in self.direction_models:
            direction_model.reset()

        self.frames = [None] * self.camera_count
        self.latest_detections = [[] for _ in range(self.camera_count)]
        self.latest_tracks = [[] for _ in range(self.camera_count)]
        self.latest_events = [[] for _ in range(self.camera_count)]

        if self.plc_model.is_connected:
            self.plc_model.disconnect()

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def process_frames(self):
        """
        Capture and process one frame from every available camera.

        This method is intentionally non-blocking with respect to the
        monitoring loop: the caller decides when to call it, which makes
        it suitable for a Tkinter `after()` loop later.
        """
        if not self.monitoring:
            return

        for index, camera in enumerate(self.cameras):
            try:
                success, frame = camera.read()

                if not success:
                    self._report_error(
                        index,
                        f"Failed to read camera {self.camera_indices[index]}",
                    )
                    continue

                detections = self.detection_model.detect(frame)

                tracked_detections = self.trackers[index].update(
                    detections
                )

                # IMPORTANT: DirectionModel is fed the tracker's full set
                # of currently active tracks (get_active_tracks()), not
                # just tracked_detections.
                #
                # tracked_detections only contains tracks matched or
                # created THIS frame. TrackingModel keeps a track alive
                # internally for up to max_missed_frames after a missed
                # detection, but that grace period is invisible to
                # DirectionModel unless we pass it get_active_tracks()
                # as well - otherwise a single dropped YOLO detection
                # (occlusion, motion blur, etc.) causes DirectionModel
                # to drop the track's previous_side/previous_centroid
                # state, and a crossing that straddles that dropped
                # frame can go uncounted or be double-counted once the
                # track is "rediscovered" as if it were brand new.
                active_tracks = self.trackers[index].get_active_tracks()

                events = self.direction_models[index].update(
                    active_tracks
                )

                counts = self.counter.process_events(events)

                self.frames[index] = frame
                self.latest_detections[index] = detections
                self.latest_tracks[index] = tracked_detections
                self.latest_events[index] = events

                if callable(self._update_callback):
                    self._update_callback(
                        index,
                        frame,
                        tracked_detections,
                    )

                if events and callable(self._event_callback):
                    for event in events:
                        self._event_callback(index,event,counts.copy(),)

                if events:
                    self._publish_safety_status(counts)

            except Exception as exc:
                self._report_error(index, str(exc))

    # ------------------------------------------------------------------
    # Direction configuration
    # ------------------------------------------------------------------
    def set_counting_line(
        self,
        camera_index,
        line_start,
        line_end,
        enter_side="negative",
    ):
        """Configure the counting line for one camera."""
        self._validate_camera_index(camera_index)

        self.direction_models[camera_index].set_line(
            line_start,
            line_end,
        )
        self.direction_models[camera_index].set_enter_side(
            enter_side
        )

        # Reset the associated tracker because the movement state is
        # no longer valid after changing the counting line.
        self.trackers[camera_index].reset()

    def save_counting_lines_to_config(self):
        """
        Persist all cameras' current counting-line configuration through
        ConfigManager.

        This reads directly from each DirectionModel, so it reflects the
        latest state regardless of whether it was set via TeachViewModel
        or directly through set_counting_line().
        """
        counting_lines = []

        for direction_model in self.direction_models:
            if direction_model.line_start is None:
                counting_lines.append(None)
                continue

            counting_lines.append(
                {
                    "line_start": list(direction_model.line_start),
                    "line_end": list(direction_model.line_end),
                    "enter_side": direction_model.enter_side,
                    "minimum_movement": direction_model.minimum_movement,
                    "cooldown_frames": direction_model.cooldown_frames,
                }
            )

        self.config_manager.set_counting_lines(counting_lines)
        self.config_manager.save()

    def save_full_config(self):
        """
        Persist every currently-active parameter this ViewModel knows
        about back to ConfigManager/disk in one shot: camera fleet,
        detection, tracking (+ overrides), direction defaults, counting
        lines, counter, PLC, and safety settings.

        Use this after changing any runtime setting (e.g. via
        detection_model.set_confidence_threshold()) to make the change
        durable across restarts.
        """
        self.config_manager.set_camera_settings(
            camera_count=self.camera_count,
            camera_indices=self.camera_indices,
            camera_resolution=self.camera_resolution,
        )

        self.config_manager.set_detection_settings(
            model_path=self.detection_model.model_path,
            confidence_threshold=self.detection_model.confidence_threshold,
            device=self.detection_model.device,
            image_size=self.detection_model.image_size,
        )

        self.config_manager.set_tracking_settings(
            iou_threshold=self.tracking_settings["iou_threshold"],
            max_missed_frames=self.tracking_settings["max_missed_frames"],
        )

        for index, tracker in enumerate(self.trackers):
            self.config_manager.set_tracking_override(
                index,
                iou_threshold=tracker.iou_threshold,
                max_missed_frames=tracker.max_missed_frames,
            )

        self.config_manager.set_direction_defaults(
            minimum_movement=self.direction_defaults["minimum_movement"],
            cooldown_frames=self.direction_defaults["cooldown_frames"],
        )

        self.config_manager.set_counter_settings(
            initial_count=self.counter.current
        )

        self.config_manager.set_plc_settings(
            host=self.plc_model.host,
            port=self.plc_model.port,
            auto_connect=self.plc_auto_connect,
            timeout=self.plc_model.timeout,
            buffer_size=self.plc_model.buffer_size,
            encoding=self.plc_model.encoding,
        )

        self.config_manager.set_safety_settings(
            occupancy_safety_threshold=self.occupancy_safety_threshold
        )

        # Counting lines are derived straight from DirectionModel state.
        self.save_counting_lines_to_config()

    # ------------------------------------------------------------------
    # PLC
    # ------------------------------------------------------------------
    def connect_plc(self):
        """Manually connect to the PLC server."""
        return self.plc_model.connect()

    def disconnect_plc(self):
        """Manually disconnect from the PLC server."""
        self.plc_model.disconnect()

    @property
    def is_plc_connected(self):
        return self.plc_model.is_connected

    def get_plc_status(self):
        """
        Return the PLC connection/safety state for display.

        {
            "connected": bool,
            "safety": "SAFE" | "NOT_SAFE",
            "status": dict of the last-seen STATUS|name|value messages,
        }
        """
        return {
            "connected": self._plc_connected,
            "safety": self._safety_status,
            "status": dict(self._plc_status),
        }

    def set_occupancy_safety_threshold(self, threshold):
        """Update the occupancy count at/above which the room is NOT_SAFE."""
        self.occupancy_safety_threshold = threshold
        self._publish_safety_status(self.counter.get_counts())

    def _publish_safety_status(self, counts):
        """
        Derive a SAFE / NOT_SAFE state from the current occupancy count
        and send it to the PLC.

        The room is considered unsafe whenever the current occupancy is
        at or above occupancy_safety_threshold (default: 1, i.e. any
        person present).
        """
        current = counts.get("current", 0)

        safety_status = (
            self.SAFETY_NOT_SAFE
            if current >= self.occupancy_safety_threshold
            else self.SAFETY_SAFE
        )

        status_changed = safety_status != self._safety_status
        self._safety_status = safety_status

        if status_changed and self.plc_model.is_connected:
            self.plc_model.send_command("SAFETY", safety_status)
            self.plc_model.send_command("OCCUPANCY", str(current))

    def _handle_plc_connection_change(self, is_connected):
        self._plc_connected = is_connected

        if callable(self._plc_connection_callback):
            self._plc_connection_callback(is_connected)

    def _handle_plc_status(self, status_name, value):
        self._plc_status[status_name] = value

    def _handle_plc_error(self, message):
        self._report_error(-1, f"PLC: {message}")

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------
    def get_counts(self):
        """Return global people counts."""
        return self.counter.get_counts()

    def get_camera_frame(self, camera_index):
        """Return the latest frame for a camera."""
        self._validate_camera_index(camera_index)
        return self.frames[camera_index]

    def get_camera_tracks(self, camera_index):
        """Return the latest tracked detections for a camera."""
        self._validate_camera_index(camera_index)
        return self.latest_tracks[camera_index]

    def get_camera_events(self, camera_index):
        """Return the latest ENTER / EXIT events for a camera."""
        self._validate_camera_index(camera_index)
        return self.latest_events[camera_index]

    @property
    def is_monitoring(self):
        return self.monitoring

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def reset_counts(self):
        """Reset the global people counter."""
        self.counter.reset()
        self._publish_safety_status(self.counter.get_counts())

    def shutdown(self):
        """Release all resources owned by the ViewModel."""
        self.stop_monitoring()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_camera_index(self, camera_index):
        if not isinstance(camera_index, int):
            raise TypeError("camera_index must be an integer.")

        if not 0 <= camera_index < self.camera_count:
            raise IndexError(
                f"camera_index must be between 0 and "
                f"{self.camera_count - 1}."
            )

    def _report_error(self, camera_index, message):
        if callable(self._error_callback):
            self._error_callback(camera_index, message)