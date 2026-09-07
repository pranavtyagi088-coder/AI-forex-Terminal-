import pytest
from app.engines.risk.instruments import InstrumentRegistry, AssetClass


class TestInstrumentRegistryAndNormalization:
    def test_symbol_normalization_variations(self):
        reg = InstrumentRegistry()
        assert reg.normalize_symbol("EUR/USD") == "EURUSD"
        assert reg.normalize_symbol("EURUSD.pro") == "EURUSD"
        assert reg.normalize_symbol("EURUSDm") == "EURUSD"
        assert reg.normalize_symbol("EURUSD.raw") == "EURUSD"
        assert reg.normalize_symbol("GOLD") == "XAUUSD"
        assert reg.normalize_symbol("XAU/USD") == "XAUUSD"
        assert reg.normalize_symbol("US30USD") == "US30"
        assert reg.normalize_symbol("USTEC") == "NAS100"

    def test_get_spec_forex_major(self):
        reg = InstrumentRegistry()
        spec = reg.get_spec("EURUSD.r")
        assert spec.canonical_symbol == "EURUSD"
        assert spec.asset_class == AssetClass.FOREX_MAJOR
        assert spec.contract_size == 100000.0
        assert spec.pip_unit == 0.0001
        assert spec.min_lot == 0.01
        assert spec.lot_step == 0.01

    def test_get_spec_gold_contract_size(self):
        reg = InstrumentRegistry()
        spec = reg.get_spec("GOLD")
        assert spec.canonical_symbol == "XAUUSD"
        assert spec.asset_class == AssetClass.COMMODITY_METAL
        assert spec.contract_size == 100.0  # 100 oz
        assert spec.pip_unit == 0.1

    def test_get_spec_jpy_pip_unit(self):
        reg = InstrumentRegistry()
        spec = reg.get_spec("USDJPY.pro")
        assert spec.pip_unit == 0.01
        assert spec.digits == 3

    def test_unsupported_instrument_fails_closed(self):
        reg = InstrumentRegistry()
        assert reg.is_supported("UNKNOWNCOIN") is False
        with pytest.raises(KeyError) as exc_info:
            reg.get_spec("UNKNOWNCOIN")
        assert "UNSUPPORTED_INSTRUMENT" in str(exc_info.value)
