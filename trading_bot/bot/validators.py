import re
from decimal import Decimal, InvalidOperation

ALLOWED_SIDES = {"BUY", "SELL"}
ALLOWED_TYPES = {"MARKET", "LIMIT"}
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    pass


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    s = symbol.strip().upper()
    if not SYMBOL_RE.match(s):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected 5-20 uppercase alphanumerics."
        )
    return s


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    s = side.strip().upper()
    if s not in ALLOWED_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be BUY or SELL.")
    return s


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required.")
    t = order_type.strip().upper()
    if t not in ALLOWED_TYPES:
        raise ValidationError(f"Invalid order type '{order_type}'. Must be MARKET or LIMIT.")
    return t


def validate_positive_decimal(value, field_name: str) -> Decimal:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required.")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"{field_name} must be a number, got '{value}'.")
    if d <= 0:
        raise ValidationError(f"{field_name} must be > 0, got {d}.")
    return d


def validate_positive_int(value, field_name: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be an integer, got '{value}'.")
    if n <= 0:
        raise ValidationError(f"{field_name} must be > 0, got {n}.")
    return n


def validate_order_inputs(symbol, side, order_type, quantity, price=None) -> dict:
    payload = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_positive_decimal(quantity, "Quantity"),
    }
    if payload["order_type"] == "LIMIT":
        payload["price"] = validate_positive_decimal(price, "Price")
    return payload
