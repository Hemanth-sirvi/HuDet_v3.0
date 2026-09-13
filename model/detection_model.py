
from pathlib import Path

from ultralytics import YOLO


class DetectionModel:
    """
    Handles person detection using an Ultralytics YOLOv5u model.

    DetectionModel is responsible only for loading the model and running
    inference. Tracking, direction detection, and people counting belong
    to higher-level components.
    """

    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_path=None,
        confidence_threshold=0.5,
        device=None,
        image_size=640,
    ):
        base_path = Path(__file__).resolve().parent.parent

        # The current project uses YOLOv5u medium.
        default_model_path = base_path / "assets" / "yolov5mu.pt"

        self.model_path = (
            Path(model_path)
            if model_path is not None
            else default_model_path
        )

        self.confidence_threshold = confidence_threshold
        self.device = device
        self.image_size = image_size

        self.model = None
        self._load_model()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the YOLOv5u model from the assets directory."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Detection model not found: {self.model_path}"
            )

        try:
            self.model = YOLO(str(self.model_path))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load detection model: {self.model_path}"
            ) from exc

    @property
    def is_loaded(self):
        """Return True when the detection model is loaded."""
        return self.model is not None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, frame):
        """
        Run person detection on a single OpenCV BGR frame.

        Returns a list of dictionaries in the form:

            {
                "bbox": (x1, y1, x2, y2),
                "confidence": float,
                "class_id": int,
                "class_name": str,
            }
        """
        if not self.is_loaded:
            raise RuntimeError(
                "Detection model is not loaded."
            )

        if frame is None:
            return []

        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                imgsz=self.image_size,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Detection inference failed: {exc}"
            ) from exc

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes

            for index in range(len(boxes)):
                class_id = int(
                    boxes.cls[index].item()
                )

                # This application only needs people.
                if class_id != self.PERSON_CLASS_ID:
                    continue

                confidence = float(
                    boxes.conf[index].item()
                )

                x1, y1, x2, y2 = (
                    boxes.xyxy[index]
                    .cpu()
                    .tolist()
                )

                class_name = self._get_class_name(
                    class_id
                )

                detections.append(
                    {
                        "bbox": (
                            int(x1),
                            int(y1),
                            int(x2),
                            int(y2),
                        ),
                        "confidence": confidence,
                        "class_id": class_id,
                        "class_name": class_name,
                    }
                )

        return detections

    # ------------------------------------------------------------------
    # Class-name handling
    # ------------------------------------------------------------------

    def _get_class_name(self, class_id):
        """
        Safely resolve a class name from the Ultralytics model.

        Ultralytics may expose ``model.names`` as either a dictionary
        or a list depending on the model/version.
        """
        names = getattr(self.model, "names", None)

        if isinstance(names, dict):
            return str(
                names.get(
                    class_id,
                    "person",
                )
            )

        if isinstance(names, (list, tuple)):
            if 0 <= class_id < len(names):
                return str(names[class_id])

        return "person"

    # ------------------------------------------------------------------
    # Runtime configuration
    # ------------------------------------------------------------------

    def set_confidence_threshold(self, threshold):
        """Update the minimum confidence required for detection."""
        if not isinstance(
            threshold,
            (int, float),
        ):
            raise TypeError(
                "Confidence threshold must be a number."
            )

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Confidence threshold must be between 0.0 and 1.0."
            )

        self.confidence_threshold = float(
            threshold
        )

    def set_image_size(self, image_size):
        """Update the inference image size."""
        if (
            not isinstance(image_size, int)
            or isinstance(image_size, bool)
            or image_size <= 0
        ):
            raise ValueError(
                "image_size must be a positive integer."
            )

        self.image_size = image_size

