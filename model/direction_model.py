class DirectionModel:

    ENTER = "ENTER"
    EXIT = "EXIT"

    def __init__(
        self,
        line_start=None,
        line_end=None,
        enter_side="negative",
        minimum_movement=5,
        cooldown_frames=10,
    ):
        self.line_start = line_start
        self.line_end = line_end
        self.enter_side = enter_side
        self.minimum_movement = minimum_movement
        self.cooldown_frames = cooldown_frames

        self._tracks = {}

        self.frame_count = 0

        self._validate_configuration()

    def _validate_configuration(self):
        if self.enter_side not in ("positive", "negative"):
            raise ValueError(
                "enter_side must be either 'positive' or 'negative'."
            )

        if self.line_start is not None or self.line_end is not None:
            if self.line_start is None or self.line_end is None:
                raise ValueError(
                    "Both line_start and line_end must be provided."
                )

            if self.line_start == self.line_end:
                raise ValueError(
                    "line_start and line_end cannot be the same point."
                )

    def set_line(self, line_start, line_end):
        """Set or update the virtual counting line."""
        if line_start == line_end:
            raise ValueError(
                "line_start and line_end cannot be the same point."
            )

        self.line_start = tuple(line_start)
        self.line_end = tuple(line_end)

        # Existing side states are no longer valid after changing the line.
        self._tracks.clear()

    def set_enter_side(self, enter_side):
        """Set which side of the line represents ENTER."""
        if enter_side not in ("positive", "negative"):
            raise ValueError(
                "enter_side must be either 'positive' or 'negative'."
            )

        self.enter_side = enter_side
        self._tracks.clear()

    def update(self, tracked_detections):
        """
        Process the current frame's tracked people.

        Args:
            tracked_detections:
                List of tracked detection dictionaries from TrackingModel.
                Each item must contain:
                    {
                        "track_id": int,
                        "centroid": (x, y),
                    }

        Returns:
            List of crossing events:
                {
                    "track_id": int,
                    "direction": "ENTER" or "EXIT",
                    "centroid": (x, y),
                }
        """
        if self.line_start is None or self.line_end is None:
            return []

        if tracked_detections is None:
            tracked_detections = []

        self.frame_count += 1
        events = []
        active_track_ids = set()

        for detection in tracked_detections:
            if "track_id" not in detection or "centroid" not in detection:
                continue

            track_id = detection["track_id"]
            centroid = tuple(detection["centroid"])
            active_track_ids.add(track_id)

            current_side = self._get_side(centroid)

            if current_side == 0:
                # The centroid is directly on the line.
                continue

            track = self._tracks.get(track_id)

            if track is None:
                self._tracks[track_id] = {
                    "previous_centroid": centroid,
                    "previous_side": current_side,
                    "last_crossing_frame": None,
                    "last_direction": None,
                }
                continue

            previous_centroid = track["previous_centroid"]
            previous_side = track["previous_side"]

            movement = self._distance(previous_centroid, centroid)

            # Ignore tiny movements/noise.
            if movement < self.minimum_movement:
                track["previous_centroid"] = centroid
                continue

            # A side change means the person crossed the line.
            if (
                previous_side != current_side
                and previous_side != 0
                and current_side != 0
            ):
                if self._is_crossing_allowed(track):
                    direction = self._get_direction(
                        previous_side,
                        current_side,
                    )

                    if direction is not None:
                        events.append(
                            {
                                "track_id": track_id,
                                "direction": direction,
                                "centroid": centroid,
                            }
                        )

                        track["last_crossing_frame"] = self.frame_count
                        track["last_direction"] = direction

            track["previous_centroid"] = centroid
            track["previous_side"] = current_side

        # Remove tracks that are no longer present.
        stale_track_ids = set(self._tracks.keys()) - active_track_ids

        for track_id in stale_track_ids:
            del self._tracks[track_id]

        return events

    def get_track_state(self, track_id):
        """Return internal direction state for a tracked person."""
        track = self._tracks.get(track_id)

        if track is None:
            return None

        return track.copy()

    def reset(self):
        """Clear all tracked direction states."""
        self._tracks.clear()
        self.frame_count = 0

    def _get_direction(self, previous_side, current_side):
        """
        Convert a side transition into ENTER or EXIT.

        If ENTER is the positive side:
            negative -> positive = ENTER
            positive -> negative = EXIT

        If ENTER is the negative side:
            positive -> negative = ENTER
            negative -> positive = EXIT
        """
        if self.enter_side == "positive":
            if previous_side < 0 and current_side > 0:
                return self.ENTER

            if previous_side > 0 and current_side < 0:
                return self.EXIT

        else:
            if previous_side > 0 and current_side < 0:
                return self.ENTER

            if previous_side < 0 and current_side > 0:
                return self.EXIT

        return None

    def _is_crossing_allowed(self, track):
        last_crossing_frame = track["last_crossing_frame"]

        if last_crossing_frame is None:
            return True

        return (
            self.frame_count - last_crossing_frame
            >= self.cooldown_frames
        )

    def _get_side(self, point):
        """
        Return the point's signed side relative to the line.

        Returns:
            positive -> one side of the line
            negative -> the other side
            0        -> point lies on the line
        """
        x1, y1 = self.line_start
        x2, y2 = self.line_end
        px, py = point

        cross_product = (
            (x2 - x1) * (py - y1)
            - (y2 - y1) * (px - x1)
        )

        if cross_product > 0:
            return 1

        if cross_product < 0:
            return -1

        return 0

    @staticmethod
    def _distance(point_a, point_b):
        ax, ay = point_a
        bx, by = point_b

        dx = bx - ax
        dy = by - ay

        return (dx * dx + dy * dy) ** 0.5
