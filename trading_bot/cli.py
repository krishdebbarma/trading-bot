import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bot.client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from bot.logging_config import get_logger
from bot.orders import (
    place_order,
    place_twap_order,
    summarize_request,
    summarize_response,
)
from bot.validators import ValidationError

console = Console()
logger = get_logger("trading_bot.cli")


def _load_env() -> tuple:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com").strip()
    if not api_key or not api_secret:
        console.print(Panel.fit(
            "[bold red]Missing API credentials[/bold red]\n\n"
            "Create a [cyan].env[/cyan] file (copy [cyan].env.example[/cyan]) with:\n"
            "  BINANCE_API_KEY=...\n  BINANCE_API_SECRET=...\n\n"
            "Get testnet keys at https://testnet.binancefuture.com (API Key tab).",
            title="Setup Required", border_style="red",
        ))
        sys.exit(2)
    return api_key, api_secret, base_url


def _build_client() -> BinanceFuturesClient:
    api_key, api_secret, base_url = _load_env()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
    try:
        client.sync_time()
    except (BinanceNetworkError, BinanceAPIError) as e:
        logger.warning("Time sync failed: %s", e)
    return client


def _print_table(title: str, header_style: str, data: dict) -> None:
    table = Table(title=title, header_style=header_style)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(str(k), str(v))
    console.print(table)


def _handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error("Validation: %s", e)
            console.print(Panel(f"[bold red]Validation error:[/bold red] {e}", border_style="red"))
            return 2
        except BinanceAPIError as e:
            logger.error("API error: %s", e)
            console.print(Panel(
                f"[bold red]API error[/bold red] (HTTP {e.status_code}, code={e.code})\n{e.message}",
                border_style="red",
            ))
            return 3
        except BinanceNetworkError as e:
            logger.error("Network: %s", e)
            console.print(Panel(f"[bold red]Network error:[/bold red] {e}", border_style="red"))
            return 4
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled by user.[/yellow]")
            return 130
        except Exception as e:
            logger.exception("Unexpected: %s", e)
            console.print(Panel(f"[bold red]Unexpected error:[/bold red] {e}", border_style="red"))
            return 1
    return wrapper


@_handle_errors
def cmd_place(args: argparse.Namespace) -> int:
    summary = summarize_request(args.symbol, args.side, args.type, args.quantity, args.price)
    _print_table("Order Request", "bold cyan", summary)

    client = _build_client()
    resp = place_order(
        client=client, symbol=args.symbol, side=args.side, order_type=args.type,
        quantity=args.quantity, price=args.price,
    )
    _print_table("Order Response", "bold green", summarize_response(resp))
    console.print(Panel("[bold green]SUCCESS[/bold green] – order placed on testnet.",
                        border_style="green"))
    return 0


@_handle_errors
def cmd_balance(_: argparse.Namespace) -> int:
    client = _build_client()
    data = client.account()
    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) != 0]
    table = Table(title="Futures Account (non-zero balances)", header_style="bold cyan")
    table.add_column("Asset")
    table.add_column("Wallet")
    table.add_column("Available")
    table.add_column("Unrealized PnL")
    for a in (assets or data.get("assets", [])[:3]):
        table.add_row(
            a.get("asset", ""),
            str(a.get("walletBalance", "0")),
            str(a.get("availableBalance", "0")),
            str(a.get("unrealizedProfit", "0")),
        )
    console.print(table)
    return 0


@_handle_errors
def cmd_twap(args: argparse.Namespace) -> int:
    _print_table("TWAP Request", "bold cyan", {
        "symbol": args.symbol, "side": args.side,
        "totalQuantity": args.quantity, "slices": args.slices,
        "intervalSeconds": args.interval,
    })
    client = _build_client()
    results = place_twap_order(
        client=client, symbol=args.symbol, side=args.side,
        total_quantity=args.quantity, slices=args.slices, interval_seconds=args.interval,
    )
    table = Table(title="TWAP Slices", header_style="bold green")
    table.add_column("#")
    table.add_column("orderId")
    table.add_column("status")
    table.add_column("origQty")
    for i, r in enumerate(results, 1):
        table.add_row(str(i), str(r.get("orderId")), str(r.get("status")), str(r.get("origQty")))
    console.print(table)
    console.print(Panel(
        f"[bold green]SUCCESS[/bold green] – {len(results)} TWAP slice(s) placed.",
        border_style="green",
    ))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trading-bot",
        description="Binance Futures Testnet (USDT-M) trading bot.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("place", help="Place a Market or Limit order")
    pl.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    pl.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    pl.add_argument("--type", required=True, choices=["MARKET", "LIMIT", "market", "limit"])
    pl.add_argument("--quantity", required=True)
    pl.add_argument("--price", help="Required for LIMIT")
    pl.set_defaults(func=cmd_place)

    bal = sub.add_parser("balance", help="Show futures account balances")
    bal.set_defaults(func=cmd_balance)

    tw = sub.add_parser("twap", help="Place a TWAP order (split into N MARKET slices)")
    tw.add_argument("--symbol", required=True)
    tw.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    tw.add_argument("--quantity", required=True, help="Total quantity across all slices")
    tw.add_argument("--slices", required=True, type=int, help="Number of slices")
    tw.add_argument("--interval", required=True, type=float, help="Seconds between slices")
    tw.set_defaults(func=cmd_twap)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
