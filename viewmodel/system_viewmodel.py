from copy import deepcopy
from pathlib import Path
import json

from model.config_manager import ConfigManager


class SystemViewModel:
    """
    Coordinates application configuration for System View.

    The ViewModel keeps two copies of the configuration:

        saved_config   -> last accepted configuration
        working_config -> changes currently being edited

    This makes APPLY / CANCEL straightforward.

    JSON persistence is handled here for the current development stage.
    A dedicated ConfigManager / ThemeManager can later replace these
    private file helpers without changing SystemView.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(
        self,
        config_path=None,
        theme_path=None,
    ):
        base_path = Path(__file__).resolve().parent.parent

        self.config_path = (
            Path(config_path)
            if config_path is not None
            else base_path / "config" / "config.json"
        )

        self.theme_path = (
            Path(theme_path)
            if theme_path is not None
            else base_path / "config" / "theme.json"
        )

        self.saved_config = {}
        self.working_config = {}

        self.saved_theme = {}
        self.working_theme = {}

        self.load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self):
        """
        Load config.json and theme.json.

        Missing or invalid files are replaced with development defaults.
        """
        self.saved_config = self._load_json(
            self.config_path,
            self._default_config(),
        )

        self.saved_theme = self._load_json(
            self.theme_path,
            self._default_theme(),
        )

        self.working_config = deepcopy(
            self.saved_config
        )

        self.working_theme = deepcopy(
            self.saved_theme
        )

        self._normalize_config()

    # ------------------------------------------------------------------
    # Configuration access
    # ------------------------------------------------------------------
    def get_config(self):
        """Return a copy of the current working application config."""
        return deepcopy(self.working_config)

    def get_theme(self):
        """Return a copy of the current working theme config."""
        return deepcopy(self.working_theme)

    def get_value(self, section, key, default=None):
        """Return one working configuration value."""
        section_data = self.working_config.get(
            section,
            {},
        )

        if not isinstance(section_data, dict):
            return default

        return section_data.get(
            key,
            default,
        )

    def get_theme_value(self, section, key, default=None):
        """Return one working theme value."""
        section_data = self.working_theme.get(
            section,
            {},
        )

        if not isinstance(section_data, dict):
            return default

        return section_data.get(
            key,
            default,
        )

    # ------------------------------------------------------------------
    # Configuration editing
    # ------------------------------------------------------------------
    def set_value(self, section, key, value):
        """Change one working application configuration value."""
        if not section:
            raise ValueError("section cannot be empty.")

        if not key:
            raise ValueError("key cannot be empty.")

        if section not in self.working_config:
            self.working_config[section] = {}

        if not isinstance(
            self.working_config[section],
            dict,
        ):
            self.working_config[section] = {}

        self.working_config[section][key] = value

    def set_theme_value(self, section, key, value):
        """Change one working theme value."""
        if not section:
            raise ValueError("section cannot be empty.")

        if not key:
            raise ValueError("key cannot be empty.")

        if section not in self.working_theme:
            self.working_theme[section] = {}

        if not isinstance(
            self.working_theme[section],
            dict,
        ):
            self.working_theme[section] = {}

        self.working_theme[section][key] = value

    # ------------------------------------------------------------------
    # Apply / Cancel
    # ------------------------------------------------------------------
    def apply(self):
        """
        Validate and save current working configuration and theme.

        Returns:
            True when successfully applied.
        """
        self._sync_canonical_camera_config()
        self.validate()

        self._save_json(
            self.config_path,
            self._build_persisted_config(),
        )

        self._save_json(
            self.theme_path,
            self.working_theme,
        )

        self.saved_config = deepcopy(
            self.working_config
        )

        self.saved_theme = deepcopy(
            self.working_theme
        )

        return True

    def cancel(self):
        """Discard all unsaved changes."""
        self.working_config = deepcopy(
            self.saved_config
        )

        self.working_theme = deepcopy(
            self.saved_theme
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self):
        """Validate all configuration values currently being edited."""
        self._validate_camera_config()
        self._validate_detection_config()
        self._validate_plc_config()

    def _validate_camera_config(self):
        cameras = self.working_config.get(
            "cameras",
            {},
        )

        if not isinstance(cameras, dict):
            raise ValueError(
                "Camera configuration must be an object."
            )

        count = cameras.get(
            "count",
            self.MIN_CAMERAS,
        )

        if not isinstance(count, int):
            raise ValueError(
                "Camera count must be an integer."
            )

        if not self.MIN_CAMERAS <= count <= self.MAX_CAMERAS:
            raise ValueError(
                "Camera count must be between "
                f"{self.MIN_CAMERAS} and {self.MAX_CAMERAS}."
            )

        indices = cameras.get(
            "indices",
            [],
        )

        if not isinstance(indices, list):
            raise ValueError(
                "Camera indices must be a list."
            )

        if len(indices) != count:
            raise ValueError(
                "Number of camera indices must match camera count."
            )

        for index in indices:
            if not isinstance(index, int):
                raise ValueError(
                    "Camera indices must contain integers."
                )

    def _validate_detection_config(self):
        detection = self.working_config.get(
            "detection",
            {},
        )

        if not isinstance(detection, dict):
            raise ValueError(
                "Detection configuration must be an object."
            )

        confidence = detection.get(
            "confidence_threshold",
            0.5,
        )

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise ValueError(
                "Detection confidence must be numeric."
            )

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Detection confidence must be between 0.0 and 1.0."
            )

        image_size = detection.get(
            "image_size",
            640,
        )

        if not isinstance(image_size, int) or image_size <= 0:
            raise ValueError(
                "Detection image size must be a positive integer."
            )

    def _validate_plc_config(self):
        plc = self.working_config.get(
            "plc",
            {},
        )

        if not isinstance(plc, dict):
            raise ValueError(
                "PLC configuration must be an object."
            )

        host = plc.get(
            "host",
            "",
        )

        if not isinstance(host, str):
            raise ValueError(
                "PLC host must be a string."
            )

        port = plc.get(
            "port",
            5000,
        )

        if not isinstance(port, int):
            raise ValueError(
                "PLC port must be an integer."
            )

        if not 1 <= port <= 65535:
            raise ValueError(
                "PLC port must be between 1 and 65535."
            )

    # ------------------------------------------------------------------
    # Change-state helpers
    # ------------------------------------------------------------------
    @property
    def has_unsaved_changes(self):
        return (
            self.working_config != self.saved_config
            or self.working_theme != self.saved_theme
        )

    # ------------------------------------------------------------------
    # Development defaults
    # ------------------------------------------------------------------
    @staticmethod
    def _default_config():
        return {
            "general": {
                "application_name":
                    "HUMAN DETECTION & MONITORING"
            },
            "camera_count": 1,
            "camera_indices": [0],
            "camera_resolution": [1280, 720],
            "detection": {
                "model_path": "assets/yolov5mu.pt",
                "confidence_threshold": 0.5,
                "image_size": 640,
                "device": None,
            },
            "plc": {
                "host": "127.0.0.1",
                "port": 5000,
                "timeout": 5.0,
                "buffer_size": 4096,
            },
        }

    @staticmethod
    def _default_theme():
        return {}

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_json(path, default):
        try:
            if not path.exists():
                return deepcopy(default)

            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return deepcopy(default)

            return data

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return deepcopy(default)

    @staticmethod
    def _save_json(path, data):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )
            file.write("\n")

        temporary_path.replace(path)

    def _normalize_config(self):
        """Normalize saved config for both System View and AutoViewModel."""
        if not isinstance(self.working_config, dict):
            self.working_config = {}

        merged = ConfigManager._deep_merge(
            ConfigManager._clone_defaults(),
            self.working_config,
        )
        self.working_config = merged

        camera_count = self.working_config.get("camera_count", self.MIN_CAMERAS)
        camera_indices = self.working_config.get("camera_indices")
        resolution = self.working_config.get("camera_resolution", [1280, 720])

        # Accept the older System View camera section when present.
        legacy = self.working_config.get("cameras")
        if isinstance(legacy, dict):
            camera_count = legacy.get("count", camera_count)
            camera_indices = legacy.get("indices", camera_indices)
            width = legacy.get("width")
            height = legacy.get("height")
            if width is not None and height is not None:
                resolution = [width, height]

        if not isinstance(camera_count, int):
            camera_count = self.MIN_CAMERAS
        camera_count = max(self.MIN_CAMERAS, min(self.MAX_CAMERAS, camera_count))

        if not isinstance(camera_indices, list):
            camera_indices = []
        camera_indices = [i for i in camera_indices if isinstance(i, int)]
        next_index = max(camera_indices) + 1 if camera_indices else 0
        while len(camera_indices) < camera_count:
            camera_indices.append(next_index)
            next_index += 1
        camera_indices = camera_indices[:camera_count]

        if (not isinstance(resolution, list) or len(resolution) != 2
                or not all(isinstance(v, int) and v > 0 for v in resolution)):
            resolution = [1280, 720]

        self.working_config["camera_count"] = camera_count
        self.working_config["camera_indices"] = camera_indices
        self.working_config["camera_resolution"] = resolution
        self.working_config["cameras"] = {
            "count": camera_count,
            "indices": list(camera_indices),
            "width": resolution[0],
            "height": resolution[1],
        }

    def _sync_canonical_camera_config(self):
        """Copy System View's camera edits into AutoViewModel's schema."""
        cameras = self.working_config.get("cameras", {})
        if not isinstance(cameras, dict):
            return

        current_resolution = self.working_config.get("camera_resolution", [1280, 720])
        self.working_config["camera_count"] = cameras.get(
            "count", self.working_config.get("camera_count", self.MIN_CAMERAS)
        )
        self.working_config["camera_indices"] = list(cameras.get(
            "indices", self.working_config.get("camera_indices", [])
        ))
        self.working_config["camera_resolution"] = [
            cameras.get("width", current_resolution[0]),
            cameras.get("height", current_resolution[1]),
        ]

    def _build_persisted_config(self):
        """Return the canonical config that AutoViewModel consumes."""
        persisted = deepcopy(self.working_config)
        persisted.pop("cameras", None)
        return persisted
