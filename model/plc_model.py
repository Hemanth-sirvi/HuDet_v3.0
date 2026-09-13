
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

        # Protect socket state and send operations from concurrent access
        # by the UI/application thread and the receive thread.
        self._socket_lock = threading.RLock()

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
        with self._socket_lock:
            if self.is_connected:
                return True

            self._stop_event.clear()
            self._receive_buffer = ""

            # Clean up any stale socket from a previous connection attempt.
            self._close_socket_locked()

            try:
                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )

                sock.settimeout(self.timeout)

                sock.connect(
                    (self.host, self.port)
                )

                self._socket = sock
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
                self._close_socket_locked()

                self._report_error(
                    f"Failed to connect to PLC server: {exc}"
                )

                return False

    def disconnect(self):
        """
        Close the TCP connection.

        The receive thread will terminate naturally after the socket
        is closed or its next receive operation fails.
        """
        with self._socket_lock:
            was_connected = self._connected

            self._stop_event.set()
            self._connected = False

            self._close_socket_locked()

        if was_connected:
            self._notify_connection(False)

    @property
    def is_connected(self):
        """Return True when the PLC server connection is active."""
        with self._socket_lock:
            return (
                self._connected
                and self._socket is not None
            )

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
        if not command_name:
            raise ValueError(
                "command_name cannot be empty."
            )

        if not isinstance(command_name, str):
            raise TypeError(
                "command_name must be a string."
            )

        message = self._build_command_message(
            command_name,
            value,
        )

        with self._socket_lock:
            if not self._connected or self._socket is None:
                self._report_error(
                    "Cannot send command: PLC is not connected."
                )
                return False

            sock = self._socket

            try:
                sock.sendall(
                    (message + "\n").encode(
                        self.encoding
                    )
                )

                return True

            except (OSError, socket.error) as exc:
                self._report_error(
                    f"Failed to send PLC command: {exc}"
                )

                self._mark_disconnected_locked()

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
        """
        Receive newline-delimited status messages.

        This method runs on a dedicated daemon thread and must never
        directly manipulate UI objects.
        """
        while not self._stop_event.is_set():
            with self._socket_lock:
                if not self._connected or self._socket is None:
                    break

                sock = self._socket

            try:
                data = sock.recv(
                    self.buffer_size
                )

                if not data:
                    self._handle_remote_disconnect()
                    break

                try:
                    decoded = data.decode(
                        self.encoding,
                        errors="replace",
                    )
                except (LookupError, UnicodeError) as exc:
                    self._report_error(
                        f"PLC decode error: {exc}"
                    )
                    continue

                with self._socket_lock:
                    self._receive_buffer += decoded

                self._process_receive_buffer()

            except socket.timeout:
                # A timeout is expected because the socket has a finite
                # timeout. Continue checking the stop event.
                continue

            except (OSError, socket.error) as exc:
                if not self._stop_event.is_set():
                    self._report_error(
                        f"PLC receive error: {exc}"
                    )

                self._mark_disconnected()

                break

        self._receive_thread = None

    def _process_receive_buffer(self):
        """
        Process newline-delimited messages.

        Multiple messages can arrive in one TCP packet, while one message
        can arrive across multiple packets. The receive buffer therefore
        persists until complete lines are available.
        """
        while True:
            with self._socket_lock:
                separator_index = self._receive_buffer.find(
                    "\n"
                )

                if separator_index < 0:
                    return

                message = self._receive_buffer[
                    :separator_index
                ]

                self._receive_buffer = (
                    self._receive_buffer[
                        separator_index + 1:
                    ]
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
            try:
                self._status_callback(
                    status_name,
                    value,
                )
            except Exception as exc:
                self._report_error(
                    f"PLC status callback error: {exc}"
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

    def _handle_remote_disconnect(self):
        """
        Handle a clean remote shutdown where recv() returns b"".
        """
        if self._stop_event.is_set():
            return

        self._mark_disconnected()

    def _mark_disconnected(self):
        """
        Mark the connection as disconnected and close the socket.

        The connection callback is fired exactly once for an active
        connection transitioning to disconnected.
        """
        with self._socket_lock:
            was_connected = self._connected

            self._connected = False
            self._stop_event.set()

            self._close_socket_locked()

        if was_connected:
            self._notify_connection(False)

    def _mark_disconnected_locked(self):
        """
        Locked version of _mark_disconnected().

        Caller must already hold _socket_lock.
        """
        was_connected = self._connected

        self._connected = False
        self._stop_event.set()

        self._close_socket_locked()

        if was_connected:
            self._notify_connection(False)

    def _close_socket_locked(self):
        """
        Close and clear the current socket.

        Caller must hold _socket_lock.
        """
        sock = self._socket
        self._socket = None

        if sock is None:
            return

        try:
            sock.shutdown(
                socket.SHUT_RDWR
            )
        except OSError:
            pass

        try:
            sock.close()
        except OSError:
            pass

    def _notify_connection(self, connected):
        if callable(self._connection_callback):
            try:
                self._connection_callback(
                    connected
                )
            except Exception as exc:
                self._report_error(
                    f"PLC connection callback error: {exc}"
                )

    def _report_error(self, message):
        if callable(self._error_callback):
            try:
                self._error_callback(message)
            except Exception:
                # Error callbacks must never be allowed to crash
                # the PLC receive thread.
                pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def __del__(self):
        try:
            self.disconnect()
        except Exception:
            pass

