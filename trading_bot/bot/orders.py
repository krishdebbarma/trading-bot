import time
from decimal import Decimal
from typing import Any, Dict, List

from .client import BinanceFuturesClient
from .logging_config import get_logger
from .validators import (
    validate_order_inputs,
    validate_positive_decimal,
    validate_positive_int,
    validate_side,
    validate_symbol,
)

logger = get_logger(__name__)


def _fmt(d: Decimal) -> str:
    return format(d.normalize(), "f")


def place_order(client: BinanceFuturesClient, symbol: str, side: str,
                order_type: str, quantity, price=None,
                time_in_force: str = "GTC") -> Dict[str, Any]:
    v = validate_order_inputs(symbol, side, order_type, quantity, price)

    params: Dict[str, Any] = {
        "symbol": v["symbol"],
        "side": v["side"],
        "type": v["order_type"],
        "quantity": _fmt(v["quantity"]),
    }
    if v["order_type"] == "LIMIT":
        params["price"] = _fmt(v["price"])
        params["timeInForce"] = time_in_force

    logger.info("Placing %s %s %s qty=%s",
                params["type"], params["side"], params["symbol"], params["quantity"])
    response = client.new_order(**params)
    logger.info("Order accepted orderId=%s status=%s",
                response.get("orderId"), response.get("status"))
    return response


def place_twap_order(client: BinanceFuturesClient, symbol: str, side: str,
                     total_quantity, slices, interval_seconds) -> List[Dict[str, Any]]:
    sym = validate_symbol(symbol)
    s = validate_side(side)
    total = validate_positive_decimal(total_quantity, "Total quantity")
    n = validate_positive_int(slices, "Slices")
    interval = validate_positive_decimal(interval_seconds, "Interval")

    slice_qty = (total / Decimal(n)).quantize(Decimal("0.000001"))
    if slice_qty <= 0:
        from .validators import ValidationError
        raise ValidationError("Slice quantity rounds to 0; reduce slices or increase quantity.")

    logger.info("TWAP start symbol=%s side=%s total=%s slices=%d slice_qty=%s interval=%ss",
                sym, s, total, n, slice_qty, interval)

    results: List[Dict[str, Any]] = []
    for i in range(n):
        logger.info("TWAP slice %d/%d", i + 1, n)
        resp = place_order(client, sym, s, "MARKET", slice_qty)
        results.append(resp)
        if i < n - 1:
            time.sleep(float(interval))

    logger.info("TWAP complete: %d slices placed", len(results))
    return results


def summarize_request(symbol, side, order_type, quantity, price=None) -> Dict[str, Any]:
    summary = {"symbol": symbol, "side": side, "type": order_type, "quantity": str(quantity)}
    if price not in (None, ""):
        summary["price"] = str(price)
    return summary


def summarize_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("orderId", "clientOrderId", "symbol", "status", "type", "side",
            "price", "origQty", "executedQty", "avgPrice", "timeInForce", "updateTime")
    return {k: resp.get(k) for k in keys if k in resp}
