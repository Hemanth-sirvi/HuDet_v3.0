class TrackingModel:
    """
    Maintains stable IDs for detected people across video frames.

    This tracker uses bounding-box IoU matching, so it has no additional
    third-party dependency. Direction detection and counting are handled
    by a separate component.
    """

    def __init__(self, iou_threshold=0.3, max_missed_frames=10):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames

        self._next_track_id = 1
        self._tracks = {}

    def update(self, detections):
        """
        Update tracks using the detections from DetectionModel.

        Args:
            detections: list of dictionaries containing at least:
                {
                    "bbox": (x1, y1, x2, y2),
                    "confidence": float,
                    "class_id": int,
                    "class_name": str,
                }

        Returns:
            list of tracked detections:
                {
                    "track_id": int,
                    "bbox": (x1, y1, x2, y2),
                    "confidence": float,
                    "class_id": int,
                    "class_name": str,
                    "centroid": (cx, cy),
                }
        """
        if detections is None:
            detections = []

        person_detections = [
            detection
            for detection in detections
            if detection.get("class_name") == "person"
        ]

        track_ids = list(self._tracks.keys())
        unmatched_tracks = set(track_ids)
        unmatched_detections = set(range(len(person_detections)))
        matches = []

        # Greedy highest-IoU matching.
        candidates = []

        for track_id in track_ids:
            track_bbox = self._tracks[track_id]["bbox"]

            for detection_index, detection in enumerate(person_detections):
                iou = self._calculate_iou(
                    track_bbox,
                    detection["bbox"],
                )

                if iou >= self.iou_threshold:
                    candidates.append(
                        (iou, track_id, detection_index)
                    )

        candidates.sort(reverse=True)

        for _, track_id, detection_index in candidates:
            if track_id not in unmatched_tracks:
                continue

            if detection_index not in unmatched_detections:
                continue

            matches.append((track_id, detection_index))
            unmatched_tracks.remove(track_id)
            unmatched_detections.remove(detection_index)

        tracked_detections = []

        # Update matched tracks.
        for track_id, detection_index in matches:
            detection = person_detections[detection_index]
            bbox = self._normalize_bbox(detection["bbox"])
            centroid = self._get_centroid(bbox)

            track = self._tracks[track_id]
            track["bbox"] = bbox
            track["centroid"] = centroid
            track["confidence"] = detection.get("confidence", 0.0)
            track["class_id"] = detection.get("class_id", 0)
            track["class_name"] = detection.get("class_name", "person")
            track["missed_frames"] = 0
            track["age"] += 1

            tracked_detections.append(
                self._build_tracked_detection(track_id, track)
            )

        # Increase missed-frame count for tracks that were not matched.
        expired_track_ids = []

        for track_id in unmatched_tracks:
            track = self._tracks[track_id]
            track["missed_frames"] += 1
            track["age"] += 1

            if track["missed_frames"] > self.max_missed_frames:
                expired_track_ids.append(track_id)

        for track_id in expired_track_ids:
            del self._tracks[track_id]

        # Create new tracks for unmatched detections.
        for detection_index in unmatched_detections:
            detection = person_detections[detection_index]
            bbox = self._normalize_bbox(detection["bbox"])
            centroid = self._get_centroid(bbox)

            track_id = self._next_track_id
            self._next_track_id += 1

            self._tracks[track_id] = {
                "bbox": bbox,
                "centroid": centroid,
                "confidence": detection.get("confidence", 0.0),
                "class_id": detection.get("class_id", 0),
                "class_name": detection.get("class_name", "person"),
                "missed_frames": 0,
                "age": 1,
            }

            tracked_detections.append(
                self._build_tracked_detection(
                    track_id,
                    self._tracks[track_id],
                )
            )

        return tracked_detections

    def get_active_tracks(self):
        """
        Return currently active tracks.

        Tracks that temporarily missed detections are included until
        max_missed_frames is exceeded. This is what should be fed to
        DirectionModel so that a single dropped detection frame does not
        wipe out a track's crossing state (see update()'s docstring for
        why the raw return value of update() is not sufficient for that
        purpose).
        """
        return [
            self._build_tracked_detection(track_id, track)
            for track_id, track in self._tracks.items()
            if track["missed_frames"] <= self.max_missed_frames
        ]

    def reset(self):
        """Clear all active tracks and restart track IDs from 1."""
        self._tracks.clear()
        self._next_track_id = 1

    def remove_track(self, track_id):
        """Remove a specific track."""
        self._tracks.pop(track_id, None)

    @staticmethod
    def _normalize_bbox(bbox):
        x1, y1, x2, y2 = bbox

        return (
            int(x1),
            int(y1),
            int(x2),
            int(y2),
        )

    @staticmethod
    def _get_centroid(bbox):
        x1, y1, x2, y2 = bbox

        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        return center_x, center_y

    @staticmethod
    def _calculate_iou(bbox_a, bbox_b):
        ax1, ay1, ax2, ay2 = bbox_a
        bx1, by1, bx2, by2 = bbox_b

        intersection_x1 = max(ax1, bx1)
        intersection_y1 = max(ay1, by1)
        intersection_x2 = min(ax2, bx2)
        intersection_y2 = min(ay2, by2)

        intersection_width = max(
            0,
            intersection_x2 - intersection_x1,
        )
        intersection_height = max(
            0,
            intersection_y2 - intersection_y1,
        )

        intersection_area = (
            intersection_width * intersection_height
        )

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

        union_area = area_a + area_b - intersection_area

        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    @staticmethod
    def _build_tracked_detection(track_id, track):
        return {
            "track_id": track_id,
            "bbox": track["bbox"],
            "confidence": track["confidence"],
            "class_id": track["class_id"],
            "class_name": track["class_name"],
            "centroid": track["centroid"],
        }