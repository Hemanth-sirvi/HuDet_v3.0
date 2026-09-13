class TeachViewModel:
    """
    Coordinates Teach View configuration.

    This ViewModel keeps camera counting-line configuration in memory and
    applies it to the corresponding DirectionModel when available.

    Persistent storage is intentionally left outside this class for now.
    """

    MIN_CAMERAS = 1
    MAX_CAMERAS = 4

    def __init__(self, camera_count=1, auto_viewmodel=None):
        self.camera_count = self._clamp_camera_count(camera_count)
        self.auto_viewmodel = auto_viewmodel

        self._camera_configurations = [
            self._default_configuration()
            for _ in range(self.camera_count)
        ]

        self._load_from_auto_viewmodel()

    # ------------------------------------------------------------------
    # Camera configuration
    # ------------------------------------------------------------------
    def get_camera_configuration(self, camera_index):
        """Return a copy of one camera's current teaching configuration."""
        self._validate_camera_index(camera_index)

        return self._camera_configurations[camera_index].copy()

    def get_all_configurations(self):
        """Return copies of all camera configurations."""
        return [
            configuration.copy()
            for configuration in self._camera_configurations
        ]

    def save_camera_configuration(
        self,
        camera_index,
        line_start,
        line_end,
        enter_side="negative",
    ):
        """
        Save one camera's counting-line configuration.

        The configuration is also applied to the corresponding
        DirectionModel in AutoViewModel when available.
        """
        self._validate_camera_index(camera_index)

        if line_start is None or line_end is None:
            raise ValueError(
                "Both line_start and line_end are required."
            )

        if tuple(line_start) == tuple(line_end):
            raise ValueError(
                "line_start and line_end cannot be the same point."
            )

        if enter_side not in ("positive", "negative"):
            raise ValueError(
                "enter_side must be 'positive' or 'negative'."
            )

        configuration = {
            "line_start": tuple(line_start),
            "line_end": tuple(line_end),
            "enter_side": enter_side,
        }

        self._camera_configurations[camera_index] = configuration

        self._apply_to_auto_viewmodel(
            camera_index,
            configuration,
        )

    def clear_camera_configuration(self, camera_index):
        """
        Clear the counting-line configuration for one camera.
        """
        self._validate_camera_index(camera_index)

        self._camera_configurations[camera_index] = (
            self._default_configuration()
        )

        if self.auto_viewmodel is not None:
            direction_models = getattr(
                self.auto_viewmodel,
                "direction_models",
                None,
            )

            if (
                isinstance(direction_models, list)
                and camera_index < len(direction_models)
            ):
                direction_models[camera_index].reset()

    # ------------------------------------------------------------------
    # AutoViewModel integration
    # ------------------------------------------------------------------
    def set_auto_viewmodel(self, auto_viewmodel):
        """
        Attach an AutoViewModel and apply all existing configurations.
        """
        self.auto_viewmodel = auto_viewmodel

        if self.auto_viewmodel is None:
            return

        self._load_from_auto_viewmodel()

        for camera_index, configuration in enumerate(
            self._camera_configurations
        ):
            if configuration["line_start"] is not None:
                self._apply_to_auto_viewmodel(
                    camera_index,
                    configuration,
                )

    def _apply_to_auto_viewmodel(
        self,
        camera_index,
        configuration,
    ):
        if self.auto_viewmodel is None:
            return

        set_line = getattr(
            self.auto_viewmodel,
            "set_counting_line",
            None,
        )

        if callable(set_line):
            set_line(
                camera_index,
                configuration["line_start"],
                configuration["line_end"],
                configuration["enter_side"],
            )

    def _load_from_auto_viewmodel(self):
        """
        Pull existing counting-line configurations from AutoViewModel.

        This supports the current in-memory architecture. Later,
        ConfigManager can provide persistent configurations instead.
        """
        if self.auto_viewmodel is None:
            return

        direction_models = getattr(
            self.auto_viewmodel,
            "direction_models",
            None,
        )

        if not isinstance(direction_models, list):
            return

        for camera_index in range(
            min(self.camera_count, len(direction_models))
        ):
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
            enter_side = getattr(
                direction_model,
                "enter_side",
                "negative",
            )

            if line_start is not None and line_end is not None:
                self._camera_configurations[camera_index] = {
                    "line_start": tuple(line_start),
                    "line_end": tuple(line_end),
                    "enter_side": enter_side,
                }

    # ------------------------------------------------------------------
    # Camera count
    # ------------------------------------------------------------------
    def set_camera_count(self, camera_count):
        """
        Change the number of managed cameras while respecting 1-4 limits.
        """
        new_count = self._clamp_camera_count(camera_count)

        if new_count == self.camera_count:
            return

        if new_count > self.camera_count:
            for _ in range(new_count - self.camera_count):
                self._camera_configurations.append(
                    self._default_configuration()
                )

        else:
            self._camera_configurations = (
                self._camera_configurations[:new_count]
            )

        self.camera_count = new_count

    # ------------------------------------------------------------------
    # Persistence placeholders
    # ------------------------------------------------------------------
    def export_configurations(self):
        """
        Return configurations in a JSON-friendly format.

        This method does not write a file. Persistence will be handled
        later by the configuration layer.
        """
        configurations = []

        for configuration in self._camera_configurations:
            configurations.append(
                {
                    "line_start": (
                        list(configuration["line_start"])
                        if configuration["line_start"] is not None
                        else None
                    ),
                    "line_end": (
                        list(configuration["line_end"])
                        if configuration["line_end"] is not None
                        else None
                    ),
                    "enter_side": configuration["enter_side"],
                }
            )

        return configurations

    def import_configurations(self, configurations):
        """
        Load configurations from JSON-friendly data.

        This updates only in-memory configuration and the connected
        AutoViewModel. File I/O remains outside this ViewModel.
        """
        if configurations is None:
            return

        configurations = list(configurations)

        for camera_index in range(
            min(self.camera_count, len(configurations))
        ):
            configuration = configurations[camera_index]

            if not configuration:
                continue

            line_start = configuration.get("line_start")
            line_end = configuration.get("line_end")
            enter_side = configuration.get(
                "enter_side",
                "negative",
            )

            if line_start is None or line_end is None:
                self.clear_camera_configuration(camera_index)
                continue

            self.save_camera_configuration(
                camera_index,
                line_start,
                line_end,
                enter_side,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _clamp_camera_count(cls, camera_count):
        if not isinstance(camera_count, int):
            raise TypeError(
                "camera_count must be an integer."
            )

        return max(
            cls.MIN_CAMERAS,
            min(cls.MAX_CAMERAS, camera_count),
        )

    @staticmethod
    def _default_configuration():
        return {
            "line_start": None,
            "line_end": None,
            "enter_side": "negative",
        }

    def _validate_camera_index(self, camera_index):
        if not isinstance(camera_index, int):
            raise TypeError(
                "camera_index must be an integer."
            )

        if not 0 <= camera_index < self.camera_count:
            raise IndexError(
                f"camera_index must be between 0 and "
                f"{self.camera_count - 1}."
            )
