"""
Module for Orderly API exceptions
"""


class OrderlyAPIException(Exception):
    """
    Common exception for Orderly API
    """

    def __init__(self, resp_json, status_code):
        self.status_code = status_code
        try:
            self.code = resp_json.get("code")
            self.message = resp_json.get("message")
        except Exception:
            self.code = None
            self.message = resp_json

    def __str__(self):
        return f"APIError(code={self.code}: {self.message}"


class OrderlyRequestException(Exception):
    """
    Value exception for Orderly API
    """

    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"OrderlyRequestException: {self.message}"
