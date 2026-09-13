import copy
import json
from pathlib import Path


class ConfigManager:
    """
    Loads and saves application configuration to a JSON file on disk.

    ConfigManager only knows about reading/writing JSON-friendly data.
    It has no knowledge of DetectionModel, TrackingModel, DirectionModel,
    PLCModel, or any other application object - callers convert to/from
    the dictionaries this class persists.

    Every constructor parameter across the model layer that has a
    sensible default (DetectionModel, TrackingModel, DirectionModel,
    PLCModel, CounterModel) is represented here, plus the per-camera
    counting line and AutoViewModel-level settings. Anything missing
    from a config file on disk is filled in from DEFAULT_CONFIG via a
    deep merge, so partial/hand-edited config files never crash on a
    missing key - and old config.json files without the newer sections
    (e.g. "tracking", "safety") still load correctly.
    """

    DEFAULT_CONFIG = {
        # ------------------------------------------------------------
        # AutoViewModel / camera fleet
        # ------------------------------------------------------------
        "camera_count": 1,
        "camera_indices": None,
        "camera_resolution": [1280, 720],

        # ------------------------------------------------------------
        # DetectionModel
        # ------------------------------------------------------------
        "detection": {
            "model_path": None,
            "confidence_threshold": 0.5,
            "device": None,
            "image_size": 640,
        },

        # ------------------------------------------------------------
        # TrackingModel - global defaults, one instance per camera.
        # ------------------------------------------------------------
        "tracking": {
            "iou_threshold": 0.3,
            "max_missed_frames": 10,
        },

        # Optional per-camera overrides of the tracking defaults above.
        # Each entry is either null (use the global default) or
        # {"iou_threshold": ..., "max_missed_frames": ...}.
        "tracking_overrides": [],

        # ------------------------------------------------------------
        # DirectionModel - global defaults for minimum_movement /
        # cooldown_frames. line_start/line_end/enter_side always come
        # from "counting_lines" (per camera), which may also override
        # minimum_movement/cooldown_frames per camera.
        # ------------------------------------------------------------
        "direction_defaults": {
            "minimum_movement": 5,
            "cooldown_frames": 10,
        },

        # Per-camera counting line configuration. Each entry is either
        # null (no line configured yet) or:
        # {
        #     "line_start": [x, y],
        #     "line_end": [x, y],
        #     "enter_side": "negative" | "positive",
        #     "minimum_movement": <optional, overrides direction_defaults>,
        #     "cooldown_frames": <optional, overrides direction_defaults>,
        # }
        "counting_lines": [],

        # ------------------------------------------------------------
        # CounterModel
        # ------------------------------------------------------------
        "counter": {
            "initial_count": 0,
        },

        # ------------------------------------------------------------
        # PLCModel
        # ------------------------------------------------------------
        "plc": {
            "host": "127.0.0.1",
            "port": 5000,
            "auto_connect": False,
            "timeout": 5.0,
            "buffer_size": 4096,
            "encoding": "utf-8",
        },

        # ------------------------------------------------------------
        # AutoViewModel safety logic
        # ------------------------------------------------------------
        "safety": {
            "occupancy_safety_threshold": 1,
        },
    }

    def __init__(self, config_path=None):
        if config_path is None:
            base_path = Path(__file__).resolve().parent.parent
            config_path = base_path / "config" / "config.json"

        self.config_path = Path(config_path)
        self._config = self._load_or_create()

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------
    def _load_or_create(self):
        """
        Load configuration from disk, falling back to defaults when the
        file is missing, empty, or contains invalid JSON. Missing keys
        (including nested ones) are filled in from DEFAULT_CONFIG.
        """
        if not self.config_path.exists():
            return self._clone_defaults()

        try:
            raw_text = self.config_path.read_text(encoding="utf-8")
        except OSError:
            return self._clone_defaults()

        if not raw_text.strip():
            return self._clone_defaults()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return self._clone_defaults()

        if not isinstance(data, dict):
            return self._clone_defaults()

        return self._deep_merge(self._clone_defaults(), data)

    def save(self):
        """Persist the current in-memory configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as config_file:
            json.dump(self._config, config_file, indent=4)

    def reload(self):
        """Discard in-memory changes and reload from disk."""
        self._config = self._load_or_create()

    @classmethod
    def _clone_defaults(cls):
        return copy.deepcopy(cls.DEFAULT_CONFIG)

    @classmethod
    def _deep_merge(cls, base, overrides):
        """
        Recursively merge overrides into base, returning base.

        Only dict values are merged recursively; lists and scalars in
        overrides replace the corresponding value in base outright, so
        an explicit [] or null in the file is honored rather than
        silently falling back to the default.
        """
        for key, value in overrides.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                cls._deep_merge(base[key], value)
            else:
                base[key] = value

        return base

    # ------------------------------------------------------------------
    # Generic access
    # ------------------------------------------------------------------
    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    def as_dict(self):
        """Return a deep copy of the full configuration."""
        return copy.deepcopy(self._config)

    # ------------------------------------------------------------------
    # Camera fleet settings
    # ------------------------------------------------------------------
    def get_camera_settings(self):
        return {
            "camera_count": self._config.get("camera_count", 1),
            "camera_indices": self._config.get("camera_indices"),
            "camera_resolution": tuple(
                self._config.get("camera_resolution", [1280, 720])
            ),
        }

    def set_camera_settings(
        self,
        camera_count=None,
        camera_indices=None,
        camera_resolution=None,
    ):
        if camera_count is not None:
            self._config["camera_count"] = camera_count

        if camera_indices is not None:
            self._config["camera_indices"] = list(camera_indices)

        if camera_resolution is not None:
            self._config["camera_resolution"] = list(camera_resolution)

    # ------------------------------------------------------------------
    # DetectionModel settings
    # ------------------------------------------------------------------
    def get_detection_settings(self):
        return dict(self._config.get(
            "detection",
            self.DEFAULT_CONFIG["detection"],
        ))

    def set_detection_settings(
        self,
        model_path=None,
        confidence_threshold=None,
        device=None,
        image_size=None,
    ):
        settings = dict(self.get_detection_settings())

        if model_path is not None:
            settings["model_path"] = str(model_path)

        if confidence_threshold is not None:
            settings["confidence_threshold"] = confidence_threshold

        if device is not None:
            settings["device"] = device

        if image_size is not None:
            settings["image_size"] = image_size

        self._config["detection"] = settings

    # ------------------------------------------------------------------
    # TrackingModel settings (global defaults + per-camera overrides)
    # ------------------------------------------------------------------
    def get_tracking_settings(self):
        return dict(self._config.get(
            "tracking",
            self.DEFAULT_CONFIG["tracking"],
        ))

    def set_tracking_settings(self, iou_threshold=None, max_missed_frames=None):
        settings = dict(self.get_tracking_settings())

        if iou_threshold is not None:
            settings["iou_threshold"] = iou_threshold

        if max_missed_frames is not None:
            settings["max_missed_frames"] = max_missed_frames

        self._config["tracking"] = settings

    def get_tracking_override(self, camera_index):
        """Return the per-camera tracking override, or None if unset."""
        overrides = self._config.get("tracking_overrides", [])

        if 0 <= camera_index < len(overrides):
            return overrides[camera_index]

        return None

    def set_tracking_override(
        self,
        camera_index,
        iou_threshold=None,
        max_missed_frames=None,
    ):
        overrides = list(self._config.get("tracking_overrides", []))
        self._pad_list(overrides, camera_index)

        current = overrides[camera_index] or {}

        if iou_threshold is not None:
            current["iou_threshold"] = iou_threshold

        if max_missed_frames is not None:
            current["max_missed_frames"] = max_missed_frames

        overrides[camera_index] = current
        self._config["tracking_overrides"] = overrides

    # ------------------------------------------------------------------
    # DirectionModel settings (global defaults + per-camera lines)
    # ------------------------------------------------------------------
    def get_direction_defaults(self):
        return dict(self._config.get(
            "direction_defaults",
            self.DEFAULT_CONFIG["direction_defaults"],
        ))

    def set_direction_defaults(self, minimum_movement=None, cooldown_frames=None):
        settings = dict(self.get_direction_defaults())

        if minimum_movement is not None:
            settings["minimum_movement"] = minimum_movement

        if cooldown_frames is not None:
            settings["cooldown_frames"] = cooldown_frames

        self._config["direction_defaults"] = settings

    def get_counting_lines(self):
        return self._config.get("counting_lines", [])

    def set_counting_lines(self, counting_lines):
        self._config["counting_lines"] = counting_lines

    def get_counting_line(self, camera_index):
        """Return one camera's counting-line entry, or None if unset."""
        counting_lines = self._config.get("counting_lines", [])

        if 0 <= camera_index < len(counting_lines):
            return counting_lines[camera_index]

        return None

    def set_counting_line(self, camera_index, line_config):
        """Set/replace one camera's counting-line entry (or None to clear)."""
        counting_lines = list(self._config.get("counting_lines", []))
        self._pad_list(counting_lines, camera_index)

        counting_lines[camera_index] = line_config
        self._config["counting_lines"] = counting_lines

    # ------------------------------------------------------------------
    # CounterModel settings
    # ------------------------------------------------------------------
    def get_counter_settings(self):
        return dict(self._config.get(
            "counter",
            self.DEFAULT_CONFIG["counter"],
        ))

    def set_counter_settings(self, initial_count=None):
        settings = dict(self.get_counter_settings())

        if initial_count is not None:
            settings["initial_count"] = initial_count

        self._config["counter"] = settings

    # ------------------------------------------------------------------
    # PLCModel settings
    # ------------------------------------------------------------------
    def get_plc_settings(self):
        return dict(self._config.get(
            "plc",
            self.DEFAULT_CONFIG["plc"],
        ))

    def set_plc_settings(
        self,
        host=None,
        port=None,
        auto_connect=None,
        timeout=None,
        buffer_size=None,
        encoding=None,
    ):
        settings = dict(self.get_plc_settings())

        if host is not None:
            settings["host"] = host

        if port is not None:
            settings["port"] = port

        if auto_connect is not None:
            settings["auto_connect"] = auto_connect

        if timeout is not None:
            settings["timeout"] = timeout

        if buffer_size is not None:
            settings["buffer_size"] = buffer_size

        if encoding is not None:
            settings["encoding"] = encoding

        self._config["plc"] = settings

    # ------------------------------------------------------------------
    # Safety settings
    # ------------------------------------------------------------------
    def get_safety_settings(self):
        return dict(self._config.get(
            "safety",
            self.DEFAULT_CONFIG["safety"],
        ))

    def set_safety_settings(self, occupancy_safety_threshold=None):
        settings = dict(self.get_safety_settings())

        if occupancy_safety_threshold is not None:
            settings["occupancy_safety_threshold"] = occupancy_safety_threshold

        self._config["safety"] = settings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pad_list(target_list, index):
        """Extend target_list in place with None so index is writable."""
        while len(target_list) <= index:
            target_list.append(None)