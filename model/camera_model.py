import cv2


class CameraModel:
    """
    Handles communication with a local webcam.
    The camera model is responsible only for camera/device operations.
    It does not contain UI or human-detection logic.
    """

    def __init__(self, camera_index=0, width=1280, height=720):
        self.camera_index = camera_index
        self.width = width
        self.height = height

        self._capture = None

    @property
    def is_open(self):
        """Return True when the camera is currently opened."""
        return self._capture is not None and self._capture.isOpened()

    def open(self):
        """Open the webcam and configure its requested resolution."""
        if self.is_open:
            return True

        self._capture = cv2.VideoCapture(self.camera_index)

        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            return False

        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        return True

    def read(self):
        """
        Read one frame from the webcam.

        Returns:
            tuple[bool, frame]:
                success: whether a frame was successfully read
                frame: OpenCV frame when successful, otherwise None
        """
        if not self.is_open:
            return False, None

        success, frame = self._capture.read()

        if not success:
            return False, None

        return True, frame

    def release(self):
        """Release the webcam device."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def set_resolution(self, width, height):
        """Change the requested camera resolution."""
        self.width = width
        self.height = height

        if self.is_open:
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def get_resolution(self):
        """Return the camera's current reported resolution."""
        if not self.is_open:
            return None, None

        actual_width = int(
            self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )
        actual_height = int(
            self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        return actual_width, actual_height

    def __del__(self):
        self.release()
