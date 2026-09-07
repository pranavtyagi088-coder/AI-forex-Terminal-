from enum import Enum
from typing import Dict, Optional
import re
from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    FOREX_MAJOR = "FOREX_MAJOR"
    FOREX_CROSS = "FOREX_CROSS"
    COMMODITY_METAL = "COMMODITY_METAL"
    INDEX = "INDEX"
    CRYPTO = "CRYPTO"


class InstrumentSpec(BaseModel):
    canonical_symbol: str
    asset_class: AssetClass
    base_currency: str
    quote_currency: str
    contract_size: float
    pip_unit: float           # e.g., 0.0001 for EURUSD, 0.01 for USDJPY, 0.1 for XAUUSD
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01
    max_allowed_spread_pips: float = 3.0
    digits: int = 5


class InstrumentRegistry:
    """Authoritative, fail-closed registry for instrument specs, lot sizing bounds, and symbol normalization."""

    def __init__(self):
        self._registry: Dict[str, InstrumentSpec] = {}
        self._load_default_specifications()

    def _load_default_specifications(self):
        # FX Majors
        for sym, base, quote in [
            ("EURUSD", "EUR", "USD"),
            ("GBPUSD", "GBP", "USD"),
            ("AUDUSD", "AUD", "USD"),
            ("NZDUSD", "NZD", "USD"),
            ("USDCAD", "USD", "CAD"),
            ("USDCHF", "USD", "CHF"),
        ]:
            self._registry[sym] = InstrumentSpec(
                canonical_symbol=sym,
                asset_class=AssetClass.FOREX_MAJOR,
                base_currency=base,
                quote_currency=quote,
                contract_size=100000.0,
                pip_unit=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                max_allowed_spread_pips=2.5,
                digits=5,
            )

        # FX Major JPY
        self._registry["USDJPY"] = InstrumentSpec(
            canonical_symbol="USDJPY",
            asset_class=AssetClass.FOREX_MAJOR,
            base_currency="USD",
            quote_currency="JPY",
            contract_size=100000.0,
            pip_unit=0.01,
            min_lot=0.01,
            max_lot=100.0,
            lot_step=0.01,
            max_allowed_spread_pips=2.5,
            digits=3,
        )

        # FX Crosses
        crosses = [
            ("EURGBP", "EUR", "GBP", 0.0001, 5, 2.5),
            ("EURJPY", "EUR", "JPY", 0.01, 3, 3.0),
            ("GBPJPY", "GBP", "JPY", 0.01, 3, 3.5),
            ("AUDJPY", "AUD", "JPY", 0.01, 3, 3.0),
            ("EURAUD", "EUR", "AUD", 0.0001, 5, 3.0),
            ("GBPAUD", "GBP", "AUD", 0.0001, 5, 3.5),
            ("EURCAD", "EUR", "CAD", 0.0001, 5, 3.0),
            ("NZDJPY", "NZD", "JPY", 0.01, 3, 3.0),
        ]
        for sym, base, quote, unit, digits, spread in crosses:
            self._registry[sym] = InstrumentSpec(
                canonical_symbol=sym,
                asset_class=AssetClass.FOREX_CROSS,
                base_currency=base,
                quote_currency=quote,
                contract_size=100000.0,
                pip_unit=unit,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                max_allowed_spread_pips=spread,
                digits=digits,
            )

        # Metals & Commodities
        self._registry["XAUUSD"] = InstrumentSpec(
            canonical_symbol="XAUUSD",
            asset_class=AssetClass.COMMODITY_METAL,
            base_currency="XAU",
            quote_currency="USD",
            contract_size=100.0,  # 100 oz per lot
            pip_unit=0.1,         # 1 pip = .10,  move = 10 pips
            min_lot=0.01,
            max_lot=50.0,
            lot_step=0.01,
            max_allowed_spread_pips=5.0,
            digits=2,
        )
        self._registry["XAGUSD"] = InstrumentSpec(
            canonical_symbol="XAGUSD",
            asset_class=AssetClass.COMMODITY_METAL,
            base_currency="XAG",
            quote_currency="USD",
            contract_size=5000.0,
            pip_unit=0.01,
            min_lot=0.01,
            max_lot=20.0,
            lot_step=0.01,
            max_allowed_spread_pips=6.0,
            digits=3,
        )

        # Indices
        self._registry["US30"] = InstrumentSpec(
            canonical_symbol="US30",
            asset_class=AssetClass.INDEX,
            base_currency="USD",
            quote_currency="USD",
            contract_size=1.0,
            pip_unit=1.0,         # 1 point move
            min_lot=0.1,
            max_lot=100.0,
            lot_step=0.1,
            max_allowed_spread_pips=5.0,
            digits=1,
        )
        self._registry["NAS100"] = InstrumentSpec(
            canonical_symbol="NAS100",
            asset_class=AssetClass.INDEX,
            base_currency="USD",
            quote_currency="USD",
            contract_size=1.0,
            pip_unit=1.0,
            min_lot=0.1,
            max_lot=100.0,
            lot_step=0.1,
            max_allowed_spread_pips=4.0,
            digits=1,
        )

    def normalize_symbol(self, raw_symbol: str) -> str:
        """Normalizes broker symbols (e.g. 'EURUSD.pro', 'EUR/USD', 'XAUUSDm', 'GOLD') to canonical form."""
        if not raw_symbol or not isinstance(raw_symbol, str):
            raise ValueError("Invalid symbol format.")

        s = raw_symbol.upper().strip()
        s = s.replace("/", "").replace("-", "").replace("_", "")

        # Aliases
        if s in ("GOLD", "XAU"):
            return "XAUUSD"
        if s in ("SILVER", "XAG"):
            return "XAGUSD"
        if s in ("US30USD", "DJ30", "WS30"):
            return "US30"
        if s in ("NAS100USD", "USTEC", "NQ100"):
            return "NAS100"

        # Common broker suffix patterns (.r, .pro, .c, .m, .raw, .i, micro)
        s = re.sub(r"(\.PRO|\.RAW|\.R|\.C|\.M|\.I|\.MICRO|MICRO|RAW|PRO|M)$", "", s)

        return s

    def get_spec(self, raw_symbol: str) -> InstrumentSpec:
        """Retrieve spec for a symbol with fail-closed guarantee."""
        canonical = self.normalize_symbol(raw_symbol)
        if canonical not in self._registry:
            raise KeyError(f"UNSUPPORTED_INSTRUMENT: '{raw_symbol}' (canonical '{canonical}') not in registry.")
        return self._registry[canonical]

    def is_supported(self, raw_symbol: str) -> bool:
        try:
            canonical = self.normalize_symbol(raw_symbol)
            return canonical in self._registry
        except Exception:
            return False
