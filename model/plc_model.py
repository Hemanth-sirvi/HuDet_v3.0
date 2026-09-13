import socket
import threading


class PLCModel:
    """
    TCP/IP client for communicating with the external C# PLC server.

    Outgoing messages:
        CMD|command_name|value

    Incoming messages:
        STATUS|status_name|value

    This class only handles communication. Application-level decisions
    about when monitoring should start or stop belong to higher layers.
    """

    MESSAGE_SEPARATOR = "|"
    COMMAND_PREFIX = "CMD"
    STATUS_PREFIX = "STATUS"

    def __init__(
        self,
        host="127.0.0.1",
        port=5000,
        timeout=5.0,
        buffer_size=4096,
        encoding="utf-8",
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.encoding = encoding

        self._socket = None
        self._connected = False
        self._receive_thread = None
        self._stop_event = threading.Event()
        self._receive_buffer = ""

        self._status_callback = None
        self._connection_callback = None
        self._error_callback = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self):
        """
        Connect to the C# PLC server.

        Returns:
            True if connected, otherwise False.
        """
        if self.is_connected:
            return True

        self._stop_event.clear()
        self._receive_buffer = ""

        try:
            self._socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))

            self._connected = True

            self._notify_connection(True)

            self._receive_thread = threading.Thread(
                target=self._receive_loop,
                name="PLCReceiveThread",
                daemon=True,
            )
            self._receive_thread.start()

            return True

        except (OSError, socket.error) as exc:
            self._connected = False

            if self._socket is not None:
                try:
                    self._socket.close()
                except OSError:
                    pass

                self._socket = None

            self._report_error(
                f"Failed to connect to PLC server: {exc}"
            )

            return False

    def disconnect(self):
        """Close the TCP connection."""
        self._stop_event.set()
        self._set_disconnected()

    @property
    def is_connected(self):
        """Return True when the PLC server connection is active."""
        return self._connected and self._socket is not None

    # ------------------------------------------------------------------
    # Sending commands
    # ------------------------------------------------------------------
    def send_command(self, command_name, value=""):
        """
        Send a command to the C# server.

        Format:
            CMD|command_name|value

        Returns:
            True if the message was sent successfully.
        """
        if not self.is_connected:
            self._report_error(
                "Cannot send command: PLC is not connected."
            )
            return False

        if not command_name:
            raise ValueError("command_name cannot be empty.")

        message = self._build_command_message(
            command_name,
            value,
        )

        try:
            self._socket.sendall(
                (message + "\n").encode(self.encoding)
            )
            return True

        except (OSError, socket.error) as exc:
            self._report_error(
                f"Failed to send PLC command: {exc}"
            )
            self._set_disconnected()
            return False

    def _build_command_message(self, command_name, value):
        return (
            f"{self.COMMAND_PREFIX}"
            f"{self.MESSAGE_SEPARATOR}"
            f"{command_name}"
            f"{self.MESSAGE_SEPARATOR}"
            f"{value}"
        )

    # ------------------------------------------------------------------
    # Receiving status messages
    # ------------------------------------------------------------------
    def _receive_loop(self):
        while not self._stop_event.is_set():
            if not self.is_connected:
                break

            try:
                data = self._socket.recv(self.buffer_size)

                if not data:
                    self._set_disconnected()
                    break

                self._receive_buffer += data.decode(
                    self.encoding,
                    errors="replace",
                )

                self._process_receive_buffer()

            except socket.timeout:
                continue

            except (OSError, socket.error) as exc:
                if not self._stop_event.is_set():
                    self._report_error(
                        f"PLC receive error: {exc}"
                    )

                self._set_disconnected()
                break

    def _process_receive_buffer(self):
        """
        Process newline-delimited messages.

        Multiple messages can arrive in a single TCP packet, and a single
        message can arrive across multiple packets, so the buffer is kept
        until a complete line is available.
        """
        while "\n" in self._receive_buffer:
            message, self._receive_buffer = (
                self._receive_buffer.split("\n", 1)
            )

            message = message.strip()

            if message:
                self._handle_message(message)

    def _handle_message(self, message):
        parsed = self.parse_status_message(message)

        if parsed is None:
            return

        status_name, value = parsed

        if callable(self._status_callback):
            self._status_callback(
                status_name,
                value,
            )

    @classmethod
    def parse_status_message(cls, message):
        """
        Parse:
            STATUS|status_name|value

        Returns:
            (status_name, value) or None for invalid/non-status messages.
        """
        if not isinstance(message, str):
            return None

        parts = message.strip().split(
            cls.MESSAGE_SEPARATOR,
            2,
        )

        if len(parts) != 3:
            return None

        prefix, status_name, value = parts

        if prefix != cls.STATUS_PREFIX:
            return None

        if not status_name:
            return None

        return status_name, value

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def set_status_callback(self, callback):
        """
        Register a callback for incoming PLC status messages.

        Callback:
            callback(status_name, value)
        """
        self._status_callback = callback

    def set_connection_callback(self, callback):
        """
        Register a callback for connection state changes.

        Callback:
            callback(is_connected)
        """
        self._connection_callback = callback

    def set_error_callback(self, callback):
        """
        Register a callback for communication errors.

        Callback:
            callback(message)
        """
        self._error_callback = callback

    # ------------------------------------------------------------------
    # Connection state helpers
    # ------------------------------------------------------------------
    def _set_disconnected(self):
        was_connected = self._connected

        self._connected = False

        sock = self._socket
        self._socket = None

        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass

        if was_connected:
            self._notify_connection(False)

    def _notify_connection(self, connected):
        if callable(self._connection_callback):
            self._connection_callback(connected)

    def _report_error(self, message):
        if callable(self._error_callback):
            self._error_callback(message)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def __del__(self):
        try:
            self.disconnect()
        except Exception:
            pass
