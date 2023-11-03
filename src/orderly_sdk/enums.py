"""
Module for enums in Orderly SDK
"""

from enum import Enum

SYMBOL_TYPE_SPOT = "SPOT"


class OrderType(Enum):
    """
    Order type enum
    https://docs-api.orderly.network/#restful-api-private-create-order
    """

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"
    ASK = "ASK"
    BID = "BID"


class OrderSide(Enum):
    """
    Order side enum
    https://docs-api.orderly.network/#restful-api-private-create-order
    """

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """
    Order status enum
    https://docs-api.orderly.network/#restful-api-private-get-order
    """

    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    INCOMPLETE = "INCOMPLETE"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


class KlineIntervals(Enum):
    """
    Kline intervals enum
    https://docs-api.orderly.network/#restful-api-private-get-kline
    """

    INTERVAL_1MINUTE = "1m"
    INTERVAL_5MINUTE = "5m"
    INTERVAL_15MINUTE = "15m"
    INTERVAL_30MINUTE = "30m"
    INTERVAL_1HOUR = "1h"
    INTERVAL_4HOUR = "4h"
    INTERVAL_12HOUR = "12h"
    INTERVAL_1DAY = "1d"
    INTERVAL_1WEEK = "1w"
    INTERVAL_1MONTH = "1mon"
    INTERVAL_1YEAR = "1y"
