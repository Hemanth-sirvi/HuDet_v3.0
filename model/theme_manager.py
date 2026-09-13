import copy
import json
from pathlib import Path


class ThemeManager:
    """
    Loads, accesses, modifies, and saves the application theme.

    ThemeManager is intentionally independent of Tkinter/CustomTkinter.
    It only manages theme data stored in config/theme.json so views and
    view models can consume the same theme without knowing how it is
    persisted.

    Supported access style:

        theme.get("colors.camera.person_box")
        theme.set("colors.camera.person_box", "#FFFF00")

    Missing values are filled from DEFAULT_THEME through a deep merge.
    """

    DEFAULT_THEME = {
        "appearance": {
            "mode": "dark",
        },
        "window": {
            "title": "HUMAN DETECTION & MONITORING",
            "maximized": True,
            "fullscreen": False,
            "header_content_footer_ratio": [1, 10, 1],
        },
        "colors": {
            "window_background": "#F2F2F2",
            "frame_background": "#FFFFFF",
            "frame_foreground": "#FFFFFF",
            "text_primary": "#111111",
            "text_secondary": "#555555",
            "button": {
                "foreground": "#1F6AA5",
                "hover": "#144870",
                "text": "#FFFFFF",
                "disabled": "#A0A0A0",
            },
            "camera": {
                "background": "#111111",
                "border": "#808080",
                "counting_line": "#FF0000",
                "person_box": "#00FF00",
                "person_text": "#FFFFFF",
            },
            "status": {
                "background": "#FFFFFF",
                "title_text": "#111111",
                "value_text": "#111111",

                # Per-status-item appearance. These allow each status
                # card (MONITORING, PLC, ENTERED, etc.) to have its own
                # background and text color.
                "items": {
                    "monitoring": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                    "plc": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                    "entered": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                    "exited": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                    "current_people": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                    "eqp_status": {
                        "background": "#FFFFFF",
                        "text": "#111111",
                    },
                },

                # Semantic state colors. AutoView uses these when a
                # status value is RUNNING/STOPPED, CONNECTED/DISCONNECTED,
                # or SAFE/NOT SAFE.
                "running": "#008000",
                "stopped": "#808080",
                "connected": "#008000",
                "disconnected": "#C00000",
                "safe": "#008000",
                "not_safe": "#C00000",
            },
            "log": {
                "background": "#FFFFFF",
                "text": "#111111",
            },
        },
        "fonts": {
            "header_title": {
                "family": "Arial",
                "size": 36,
                "weight": "bold",
            },
            "header_time": {
                "family": "Arial",
                "size": 22,
                "weight": "normal",
            },
            "footer_button": {
                "family": "Arial",
                "size": 22,
                "weight": "bold",
            },
            "view_title": {
                "family": "Arial",
                "size": 24,
                "weight": "bold",
            },
            "section_title": {
                "family": "Arial",
                "size": 16,
                "weight": "bold",
            },
            "status_title": {
                "family": "Arial",
                "size": 16,
                "weight": "bold",
            },
            "status_value": {
                "family": "Arial",
                "size": 20,
                "weight": "bold",
            },
            "normal": {
                "family": "Arial",
                "size": 14,
                "weight": "normal",
            },
            "camera_label": {
                "family": "Arial",
                "size": 14,
                "weight": "normal",
            },
            "log": {
                "family": "Consolas",
                "size": 12,
                "weight": "normal",
            },
        },
        "dimensions": {
            "header": {
                "padding_x": 5,
                "padding_y": 5,
                "logo_width": 150,
                "logo_height": 70,
            },
            "footer": {
                "padding_x": 5,
                "padding_y": 5,
                "button_height": 40,
                "button_corner_radius": 10,
            },
            "content": {
                "padding_x": 5,
                "padding_y": 0,
            },
            "camera": {
                "outer_padding": 5,
                "border_width": 0,
                "corner_radius": 0,
                "counting_line_width": 3,
                "counting_line_endpoint_radius": 5,
                "person_box_width": 2,
            },
            "status": {
                "outer_padding_x": 5,
                "outer_padding_y": 5,
                "item_padding_x": 5,
                "item_padding_y": 5,
            },
            "log": {
                "padding_x": 5,
                "padding_y": 5,
            },
        },
        "header": {
            "title": "HUMAN DETECTION & MONITORING",
            "logo_size": [150, 70],
            "title_alignment": "center",
            "time_alignment": "right",
        },
        "footer": {
            "buttons": {
                "AUTO": {
                    "text": "AUTO",
                    "visible": True,
                    "enabled": True,
                },
                "TEACH": {
                    "text": "TEACH",
                    "visible": True,
                    "enabled": True,
                },
                "SYSTEM": {
                    "text": "SYSTEM",
                    "visible": True,
                    "enabled": True,
                },
                "EXIT": {
                    "text": "EXIT",
                    "visible": True,
                    "enabled": True,
                },
                "START": {
                    "text": "START",
                    "stop_text": "STOP",
                    "visible": True,
                    "enabled": True,
                },
            },
        },
        "auto_view": {
            "camera_area_ratio": 9,
            "status_area_ratio": 1,
            "camera_grid_gap": 5,
            "camera_label": {
                "show_camera_name": True,
                "name_template": "Camera {index}",
            },
            "person_overlay": {
                "show": True,
                "show_track_id": True,
                "show_confidence": True,
                "confidence_decimals": 0,
                "label_template": "Person {track_id} {confidence}%",
            },
            "counting_line_overlay": {
                "show": True,
                "show_endpoints": True,
            },
            "status": {
                "monitoring_label": "MONITORING",
                "plc_label": "PLC",
                "entered_label": "ENTERED",
                "exited_label": "EXITED",
                "current_people_label": "CURRENT PEOPLE",
                "eqp_status_label": "EQP STATUS",
                "running_text": "RUNNING",
                "stopped_text": "STOPPED",
                "connected_text": "CONNECTED",
                "disconnected_text": "DISCONNECTED",
                "safe_text": "SAFE",
                "not_safe_text": "NOT SAFE",
            },
            "log": {
                "font": "log",
                "show_scrollbar": True,
                "start_at_bottom": True,
            },
        },
        "teach_view": {
            "control_area_ratio": 1,
            "preview_area_ratio": 3,
            "title": "TEACH",
            "camera_selector_title": "SELECT CAMERA",
            "direction_title": "ENTER DIRECTION",
            "instruction": (
                "Click and drag on the camera image to draw the counting line."
            ),
            "clear_button_text": "CLEAR LINE",
            "save_button_text": "SAVE",
            "status_no_line": "No counting line set.",
            "status_save_success_template": (
                "Camera {index} configuration saved."
            ),
            "status_save_missing_line": "Draw a counting line before saving.",
            "show_counting_line_endpoints": True,
            "line_width": 5,
        },
        "interaction": {
            "auto_view": {
                "camera_double_click_expand": True,
                "camera_double_click_restore": True,
            },
            "teach_view": {
                "line_draw_button": "left",
            },
        },
        "version": 0,
    }

    def __init__(self, theme_path=None):
        if theme_path is None:
            base_path = Path(__file__).resolve().parent.parent
            theme_path = base_path / "config" / "theme.json"

        self.theme_path = Path(theme_path)
        self._theme = self._load_or_create()
        self._listeners = []

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------
    def _load_or_create(self):
        """
        Load theme.json and deep-merge it with DEFAULT_THEME.

        Missing keys are filled from the defaults. Lists and scalar values
        replace their defaults completely.
        """
        if not self.theme_path.exists():
            return self._clone_defaults()

        try:
            raw_text = self.theme_path.read_text(encoding="utf-8")
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

    def save(self, notify=True):
        """Persist the current in-memory theme to theme.json."""
        self.theme_path.parent.mkdir(parents=True, exist_ok=True)

        with self.theme_path.open("w", encoding="utf-8") as theme_file:
            json.dump(self._theme, theme_file, indent=4)

        if notify:
            self._notify_listeners()

    def reload(self, notify=True):
        """Discard in-memory changes and reload the theme from disk."""
        self._theme = self._load_or_create()

        if notify:
            self._notify_listeners()

    # ------------------------------------------------------------------
    # Generic access
    # ------------------------------------------------------------------
    def get(self, path, default=None):
        """
        Return a theme value using dot-separated paths.

        Example:
            get("colors.camera.person_box")
        """
        if not path:
            return copy.deepcopy(self._theme)

        current = self._theme

        for key in str(path).split("."):
            if not isinstance(current, dict) or key not in current:
                return copy.deepcopy(default)

            current = current[key]

        return copy.deepcopy(current)

    def set(self, path, value, notify=False):
        """
        Set a theme value using a dot-separated path.

        Example:
            set("colors.camera.person_box", "#FFFF00")
        """
        keys = str(path).split(".")

        if not keys or any(not key for key in keys):
            raise ValueError("Theme path must not be empty.")

        current = self._theme

        for key in keys[:-1]:
            child = current.get(key)

            if not isinstance(child, dict):
                child = {}
                current[key] = child

            current = child

        current[keys[-1]] = copy.deepcopy(value)

        if notify:
            self._notify_listeners()

    def update(self, values, notify=False):
        """
        Deep-merge a dictionary into the current theme.

        Useful when SystemViewModel applies a group of theme changes at once.
        """
        if not isinstance(values, dict):
            raise TypeError("Theme update must be a dictionary.")

        self._deep_merge(self._theme, values)

        if notify:
            self._notify_listeners()

    def as_dict(self):
        """Return a deep copy of the complete in-memory theme."""
        return copy.deepcopy(self._theme)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def get_section(self, section, default=None):
        """Return a complete top-level theme section."""
        return self.get(section, default)

    def get_font(self, name, default=None):
        """
        Return a font definition such as:
        {"family": "Arial", "size": 14, "weight": "normal"}.
        """
        return self.get(f"fonts.{name}", default)

    def get_color(self, path, default=None):
        """Return a color from the colors section."""
        if not str(path).startswith("colors."):
            path = f"colors.{path}"

        return self.get(path, default)

    def get_dimension(self, path, default=None):
        """Return a dimension from the dimensions section."""
        if not str(path).startswith("dimensions."):
            path = f"dimensions.{path}"

        return self.get(path, default)

    # ------------------------------------------------------------------
    # Change listeners
    # ------------------------------------------------------------------
    def add_listener(self, callback):
        """
        Register a callback invoked after save/reload/update/set when
        notification is requested.

        The callback receives this ThemeManager instance.
        """
        if not callable(callback):
            raise TypeError("Theme listener must be callable.")

        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        """Remove a previously registered theme listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        """Notify registered listeners without allowing one failure to stop others."""
        for callback in tuple(self._listeners):
            try:
                callback(self)
            except Exception:
                # A bad listener must not break configuration persistence.
                continue

    # ------------------------------------------------------------------
    # Reset / utility
    # ------------------------------------------------------------------
    def reset_to_defaults(self, notify=False):
        """Replace the in-memory theme with a fresh copy of DEFAULT_THEME."""
        self._theme = self._clone_defaults()

        if notify:
            self._notify_listeners()

    @classmethod
    def _clone_defaults(cls):
        return copy.deepcopy(cls.DEFAULT_THEME)

    @classmethod
    def _deep_merge(cls, base, overrides):
        """
        Recursively merge overrides into base.

        Dictionaries are merged recursively. Lists and scalar values replace
        the existing value completely.
        """
        for key, value in overrides.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                cls._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

        return base
