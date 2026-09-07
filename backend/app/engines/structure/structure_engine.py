from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class SwingPoint:
    index: int
    price: float
    type: str  # HIGH or LOW
    time: Optional[str] = None

class MarketStructureEngine:
    @staticmethod
    def _parse_candles(candles: List[Dict[str, Any]]) -> List[Dict[str, float]]:
        parsed = []
        for c in candles:
            try:
                parsed.append({
                    'open': float(c.get('open', 0)),
                    'high': float(c.get('high', 0)),
                    'low': float(c.get('low', 0)),
                    'close': float(c.get('close', 0)),
                    'datetime': str(c.get('datetime', ''))
                })
            except (ValueError, TypeError):
                continue
        return parsed

    @classmethod
    def find_swing_points(cls, candles: List[Dict[str, Any]], window: int = 2) -> List[SwingPoint]:
        c = cls._parse_candles(candles)
        if len(c) < (window * 2 + 1):
            return []
        swings: List[SwingPoint] = []
        for i in range(window, len(c) - window):
            high_i = c[i]['high']
            low_i = c[i]['low']
            is_swing_high = all(high_i > c[j]['high'] for j in range(i - window, i + window + 1) if j != i)
            is_swing_low = all(low_i < c[j]['low'] for j in range(i - window, i + window + 1) if j != i)
            if is_swing_high:
                swings.append(SwingPoint(index=i, price=high_i, type='HIGH', time=c[i]['datetime']))
            elif is_swing_low:
                swings.append(SwingPoint(index=i, price=low_i, type='LOW', time=c[i]['datetime']))
        return swings

    @classmethod
    def analyze_structure(cls, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        c = cls._parse_candles(candles)
        if len(c) < 10:
            return {
                'structure_bias': 'NEUTRAL',
                'last_event': 'INSUFFICIENT_DATA',
                'swing_highs': [],
                'swing_lows': [],
                'bos_count': 0,
                'choch_detected': False
            }
        swings = cls.find_swing_points(c, window=2)
        swing_highs = [s for s in swings if s.type == 'HIGH']
        swing_lows = [s for s in swings if s.type == 'LOW']
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {
                'structure_bias': 'NEUTRAL',
                'last_event': 'CONSOLIDATION',
                'swing_highs': [s.price for s in swing_highs],
                'swing_lows': [s.price for s in swing_lows],
                'bos_count': 0,
                'choch_detected': False
            }
        last_high = swing_highs[-1].price
        prev_high = swing_highs[-2].price
        last_low = swing_lows[-1].price
        prev_low = swing_lows[-2].price
        current_close = c[-1]['close']
        structure_bias = 'NEUTRAL'
        last_event = 'NONE'
        choch_detected = False
        bos_detected = False

        if last_high > prev_high and last_low > prev_low:
            structure_bias = 'BULLISH'
            if current_close > last_high:
                last_event = 'BULLISH_BOS'
                bos_detected = True
            else:
                last_event = 'HIGHER_HIGH_STRUCTURE'
        elif last_low < prev_low and last_high < prev_high:
            structure_bias = 'BEARISH'
            if current_close < last_low:
                last_event = 'BEARISH_BOS'
                bos_detected = True
            else:
                last_event = 'LOWER_LOW_STRUCTURE'
        elif last_high > prev_high and last_low < prev_low:
            if current_close > prev_high:
                structure_bias = 'BULLISH_REVERSAL'
                last_event = 'BULLISH_CHOCH'
                choch_detected = True
            else:
                structure_bias = 'EXPANDING_RANGE'
                last_event = 'VOLATILITY_EXPANSION'
        elif last_low < prev_low and last_high > prev_high:
            if current_close < prev_low:
                structure_bias = 'BEARISH_REVERSAL'
                last_event = 'BEARISH_CHOCH'
                choch_detected = True
            else:
                structure_bias = 'EXPANDING_RANGE'

        return {
            'structure_bias': structure_bias,
            'last_event': last_event,
            'last_swing_high': last_high,
            'last_swing_low': last_low,
            'swing_highs_count': len(swing_highs),
            'swing_lows_count': len(swing_lows),
            'bos_detected': bos_detected,
            'choch_detected': choch_detected
        }
