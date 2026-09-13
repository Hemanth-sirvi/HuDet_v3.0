from model.camera_model import CameraModel
from model.counter_model import CounterModel
from model.detection_model import DetectionModel
from model.direction_model import DirectionModel
from model.tracking_model import TrackingModel


class AutoViewModel:
    """
    Coordinates camera capture, detection, tracking, direction detection,
    and global people counting for Auto View.

    The ViewModel does not directly manipulate CustomTkinter widgets.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(
        self,
        camera_count=1,
        camera_indices=None,
        model_path=None,
        confidence_threshold=0.5,
        camera_resolution=(1280, 720),
        counting_lines=None,
    ):
        self.camera_count = self._clamp_camera_count(camera_count)

        self.camera_indices = self._build_camera_indices(
            camera_indices
        )

        self.camera_resolution = camera_resolution

        self.detection_model = DetectionModel(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
        )

        self.cameras = []
        self.trackers = []
        self.direction_models = []

        self.counter = CounterModel()

        self.frames = [None] * self.camera_count
        self.latest_detections = [[] for _ in range(self.camera_count)]
        self.latest_tracks = [[] for _ in range(self.camera_count)]
        self.latest_events = [[] for _ in range(self.camera_count)]

        self.monitoring = False
        self._update_callback = None
        self._event_callback = None
        self._error_callback = None

        self._create_camera_models(counting_lines)

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

            tracker = TrackingModel()

            direction_config = counting_lines[index]

            if direction_config is None:
                direction_model = DirectionModel()
            else:
                direction_model = DirectionModel(
                    line_start=direction_config["line_start"],
                    line_end=direction_config["line_end"],
                    enter_side=direction_config.get(
                        "enter_side",
                        "negative",
                    ),
                    minimum_movement=direction_config.get(
                        "minimum_movement",
                        5,
                    ),
                    cooldown_frames=direction_config.get(
                        "cooldown_frames",
                        10,
                    ),
                )

            self.cameras.append(camera)
            self.trackers.append(tracker)
            self.direction_models.append(direction_model)

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

    # ------------------------------------------------------------------
    # Monitoring control
    # ------------------------------------------------------------------
    def start_monitoring(self):
        """
        Open all configured cameras and start monitoring.

        Returns:
            True when at least all configured cameras open successfully.
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
        return True

    def stop_monitoring(self):
        """Stop monitoring and release every camera."""
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

                events = self.direction_models[index].update(
                    tracked_detections
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
