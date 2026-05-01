import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.validators import (
    ValidationError,
    validate_order_inputs,
    validate_order_type,
    validate_positive_decimal,
    validate_positive_int,
    validate_side,
    validate_symbol,
)


class TestValidators(unittest.TestCase):
    def test_symbol_ok(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")
        self.assertEqual(validate_symbol("ETHUSDT"), "ETHUSDT")

    def test_symbol_bad(self):
        for bad in ["", "BT", "bt-usdt", "a" * 21, "BTC USDT"]:
            with self.assertRaises(ValidationError):
                validate_symbol(bad)

    def test_side(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")
        for bad in ["", "hold", "long"]:
            with self.assertRaises(ValidationError):
                validate_side(bad)

    def test_type(self):
        self.assertEqual(validate_order_type("market"), "MARKET")
        self.assertEqual(validate_order_type("LIMIT"), "LIMIT")
        for bad in ["", "stop", "trailing"]:
            with self.assertRaises(ValidationError):
                validate_order_type(bad)

    def test_positive_decimal(self):
        self.assertEqual(float(validate_positive_decimal("1.5", "q")), 1.5)
        for bad in [None, "", "-1", "0", "abc"]:
            with self.assertRaises(ValidationError):
                validate_positive_decimal(bad, "q")

    def test_positive_int(self):
        self.assertEqual(validate_positive_int("5", "n"), 5)
        for bad in [None, "", "0", "-3", "abc", "1.5"]:
            with self.assertRaises(ValidationError):
                validate_positive_int(bad, "n")

    def test_market_payload(self):
        p = validate_order_inputs("btcusdt", "buy", "market", "0.01")
        self.assertEqual(p["order_type"], "MARKET")
        self.assertNotIn("price", p)

    def test_limit_payload(self):
        p = validate_order_inputs("btcusdt", "sell", "limit", "0.01", price="65000")
        self.assertEqual(p["order_type"], "LIMIT")
        self.assertEqual(float(p["price"]), 65000)

    def test_limit_requires_price(self):
        with self.assertRaises(ValidationError):
            validate_order_inputs("BTCUSDT", "BUY", "LIMIT", "0.01")


if __name__ == "__main__":
    unittest.main()
