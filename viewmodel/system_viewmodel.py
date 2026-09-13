from copy import deepcopy
from pathlib import Path
import json

from model.config_manager import ConfigManager


class SystemViewModel:
    """
    Coordinates application configuration for System View.

    ConfigManager is the single authority for application configuration.
    Theme data remains separate and is persisted independently.
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

        self.config_manager = ConfigManager(
            config_path=self.config_path
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
        self.config_manager.reload()

        canonical = self._get_canonical_config()

        self.saved_config = self._with_legacy_camera_section(
            canonical
        )

        self.working_config = deepcopy(
            self.saved_config
        )

        self.saved_theme = self._load_json(
            self.theme_path,
            {},
        )

        self.working_theme = deepcopy(
            self.saved_theme
        )

        self._normalize_config()

    # ------------------------------------------------------------------
    # Configuration access
    # ------------------------------------------------------------------
    def get_config(self):
        return deepcopy(self.working_config)

    def get_theme(self):
        return deepcopy(self.working_theme)

    def get_value(self, section, key, default=None):
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
        self._sync_canonical_camera_config()
        self._normalize_config()
        self.validate()

        persisted_config = self._build_persisted_config()

        # Refresh ConfigManager from disk, then update only the canonical
        # application configuration keys through its public interface.
        self.config_manager.reload()

        for key, value in persisted_config.items():
            self.config_manager.set(
                key,
                deepcopy(value),
            )

        self.config_manager.save()

        self._save_json(
            self.theme_path,
            self.working_theme,
        )

        self.saved_config = self._with_legacy_camera_section(
            self._get_canonical_config()
        )

        self.working_config = deepcopy(
            self.saved_config
        )

        self.saved_theme = deepcopy(
            self.working_theme
        )

        return True

    def cancel(self):
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
        self._validate_camera_config()
        self._validate_detection_config()
        self._validate_tracking_config()
        self._validate_direction_config()
        self._validate_counter_config()
        self._validate_plc_config()
        self._validate_safety_config()
        self._validate_counting_lines()

    def _validate_camera_config(self):
        cameras = self.working_config.get("cameras", {})

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
            if not isinstance(index, int) or index < 0:
                raise ValueError(
                    "Camera indices must contain non-negative integers."
                )

        width = cameras.get("width")
        height = cameras.get("height")

        if not isinstance(width, int) or width <= 0:
            raise ValueError(
                "Camera width must be a positive integer."
            )

        if not isinstance(height, int) or height <= 0:
            raise ValueError(
                "Camera height must be a positive integer."
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

    def _validate_tracking_config(self):
        tracking = self.working_config.get(
            "tracking",
            {},
        )

        if not isinstance(tracking, dict):
            raise ValueError(
                "Tracking configuration must be an object."
            )

        iou_threshold = tracking.get(
            "iou_threshold",
            0.3,
        )

        if not isinstance(iou_threshold, (int, float)):
            raise ValueError(
                "Tracking IoU threshold must be numeric."
            )

        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError(
                "Tracking IoU threshold must be between 0.0 and 1.0."
            )

        max_missed_frames = tracking.get(
            "max_missed_frames",
            10,
        )

        if (
            not isinstance(max_missed_frames, int)
            or max_missed_frames < 0
        ):
            raise ValueError(
                "Maximum missed frames must be a non-negative integer."
            )

    def _validate_direction_config(self):
        direction = self.working_config.get(
            "direction_defaults",
            {},
        )

        if not isinstance(direction, dict):
            raise ValueError(
                "Direction defaults must be an object."
            )

        minimum_movement = direction.get(
            "minimum_movement",
            5,
        )

        cooldown_frames = direction.get(
            "cooldown_frames",
            10,
        )

        if (
            not isinstance(minimum_movement, (int, float))
            or minimum_movement < 0
        ):
            raise ValueError(
                "Minimum movement must be non-negative."
            )

        if (
            not isinstance(cooldown_frames, int)
            or cooldown_frames < 0
        ):
            raise ValueError(
                "Cooldown frames must be a non-negative integer."
            )

    def _validate_counter_config(self):
        counter = self.working_config.get(
            "counter",
            {},
        )

        if not isinstance(counter, dict):
            raise ValueError(
                "Counter configuration must be an object."
            )

        initial_count = counter.get(
            "initial_count",
            0,
        )

        if (
            not isinstance(initial_count, int)
            or initial_count < 0
        ):
            raise ValueError(
                "Initial count must be a non-negative integer."
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

        if not isinstance(host, str) or not host.strip():
            raise ValueError(
                "PLC host cannot be empty."
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

        timeout = plc.get(
            "timeout",
            5.0,
        )

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(
                "PLC timeout must be greater than zero."
            )

        buffer_size = plc.get(
            "buffer_size",
            4096,
        )

        if not isinstance(buffer_size, int) or buffer_size <= 0:
            raise ValueError(
                "PLC buffer size must be greater than zero."
            )

        encoding = plc.get(
            "encoding",
            "utf-8",
        )

        if not isinstance(encoding, str) or not encoding.strip():
            raise ValueError(
                "PLC encoding cannot be empty."
            )

    def _validate_safety_config(self):
        safety = self.working_config.get(
            "safety",
            {},
        )

        if not isinstance(safety, dict):
            raise ValueError(
                "Safety configuration must be an object."
            )

        threshold = safety.get(
            "occupancy_safety_threshold",
            1,
        )

        if not isinstance(threshold, int) or threshold < 0:
            raise ValueError(
                "Occupancy safety threshold must be a non-negative integer."
            )

    def _validate_counting_lines(self):
        lines = self.working_config.get(
            "counting_lines",
            [],
        )

        if not isinstance(lines, list):
            raise ValueError(
                "Counting lines must be a list."
            )

        for line in lines:
            if line is None:
                continue

            if not isinstance(line, dict):
                raise ValueError(
                    "Each counting line must be an object."
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
    # Defaults
    # ------------------------------------------------------------------
    @staticmethod
    def _default_config():
        return ConfigManager().as_dict()

    @staticmethod
    def _default_theme():
        return {}

    # ------------------------------------------------------------------
    # ConfigManager helpers
    # ------------------------------------------------------------------
    def _get_canonical_config(self):
        config = self.config_manager.as_dict()

        return {
            key: deepcopy(config.get(key))
            for key in ConfigManager.DEFAULT_CONFIG
        }

    @staticmethod
    def _with_legacy_camera_section(config):
        result = deepcopy(config)

        resolution = result.get(
            "camera_resolution",
            [1280, 720],
        )

        result["cameras"] = {
            "count": result.get(
                "camera_count",
                1,
            ),
            "indices": list(
                result.get(
                    "camera_indices",
                    [],
                )
            ),
            "width": resolution[0],
            "height": resolution[1],
        }

        return result

    def _normalize_config(self):
        defaults = ConfigManager().as_dict()

        merged = ConfigManager._deep_merge(
            defaults,
            self.working_config,
        )

        canonical_keys = set(
            ConfigManager.DEFAULT_CONFIG.keys()
        )

        self.working_config = {
            key: deepcopy(merged[key])
            for key in canonical_keys
            if key in merged
        }

        self.working_config = self._with_legacy_camera_section(
            self.working_config
        )

    def _sync_canonical_camera_config(self):
        cameras = self.working_config.get(
            "cameras",
            {},
        )

        if not isinstance(cameras, dict):
            return

        resolution = self.working_config.get(
            "camera_resolution",
            [1280, 720],
        )

        self.working_config["camera_count"] = cameras.get(
            "count",
            self.working_config.get(
                "camera_count",
                self.MIN_CAMERAS,
            ),
        )

        self.working_config["camera_indices"] = list(
            cameras.get(
                "indices",
                self.working_config.get(
                    "camera_indices",
                    [],
                ),
            )
        )

        self.working_config["camera_resolution"] = [
            cameras.get(
                "width",
                resolution[0],
            ),
            cameras.get(
                "height",
                resolution[1],
            ),
        ]

    def _build_persisted_config(self):
        persisted = deepcopy(
            self.working_config
        )

        persisted.pop(
            "cameras",
            None,
        )

        return {
            key: persisted[key]
            for key in ConfigManager.DEFAULT_CONFIG
            if key in persisted
        }

    # ------------------------------------------------------------------
    # Theme/file helpers
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