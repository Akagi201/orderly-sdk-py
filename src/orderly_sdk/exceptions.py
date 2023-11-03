"""
Module for Orderly API exceptions
"""


class OrderlyAPIException(Exception):
    """
    Common exception for Orderly API
    """

    def __init__(self, resp_json, status_code):
        self.status_code = status_code
        self.code = resp_json.get("code")
        self.message = resp_json.get("message")

    def __str__(self):
        return f"APIError(code={self.code}: {self.message}"


class OrderlyValueException(Exception):
    """
    Value exception for Orderly API
    """

    def __init__(self, response) -> None:
        self.response = response

    def __str__(self) -> str:
        return f"OrderlyValueException: {self.response.text}"


class OrderlyWebsocketUnableToConnectException(Exception):
    pass
