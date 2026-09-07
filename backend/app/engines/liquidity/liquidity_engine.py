from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FairValueGap:
    type: str
    top: float
    bottom: float
    size_pips: float
    candle_index: int
    mitigated: bool = False

class LiquidityEngine:
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
    def detect_fvg(cls, candles: List[Dict[str, Any]], pip_size: float = 0.0001) -> List[FairValueGap]:
        c = cls._parse_candles(candles)
        if len(c) < 3:
            return []
        fvgs: List[FairValueGap] = []
        for i in range(2, len(c)):
            c1 = c[i - 2]
            c3 = c[i]
            if c3['low'] > c1['high']:
                gap_size = c3['low'] - c1['high']
                if gap_size > (pip_size * 1.0):
                    mitigated = any(c[k]['low'] <= c1['high'] for k in range(i + 1, len(c)))
                    fvgs.append(FairValueGap(
                        type='BULLISH_FVG',
                        top=c3['low'],
                        bottom=c1['high'],
                        size_pips=round(gap_size / pip_size, 1),
                        candle_index=i,
                        mitigated=mitigated
                    ))
            elif c1['low'] > c3['high']:
                gap_size = c1['low'] - c3['high']
                if gap_size > (pip_size * 1.0):
                    mitigated = any(c[k]['high'] >= c1['low'] for k in range(i + 1, len(c)))
                    fvgs.append(FairValueGap(
                        type='BEARISH_FVG',
                        top=c1['low'],
                        bottom=c3['high'],
                        size_pips=round(gap_size / pip_size, 1),
                        candle_index=i,
                        mitigated=mitigated
                    ))
        return fvgs

    @classmethod
    def detect_liquidity_sweep(cls, candles: List[Dict[str, Any]], swing_level: float, direction: str) -> bool:
        c = cls._parse_candles(candles)
        if not c:
            return False
        latest = c[-1]
        if direction.upper() in ['BUY', 'BULLISH']:
            return latest['low'] < swing_level and latest['close'] > swing_level
        else:
            return latest['high'] > swing_level and latest['close'] < swing_level

    @classmethod
    def analyze_liquidity(cls, candles: List[Dict[str, Any]], pip_size: float = 0.0001) -> Dict[str, Any]:
        fvgs = cls.detect_fvg(candles, pip_size)
        unmitigated_fvgs = [f for f in fvgs if not f.mitigated]
        bullish_unmitigated = [f for f in unmitigated_fvgs if f.type == 'BULLISH_FVG']
        bearish_unmitigated = [f for f in unmitigated_fvgs if f.type == 'BEARISH_FVG']
        return {
            'total_fvg_count': len(fvgs),
            'unmitigated_fvg_count': len(unmitigated_fvgs),
            'bullish_fvg_open': len(bullish_unmitigated),
            'bearish_fvg_open': len(bearish_unmitigated),
            'nearest_bullish_fvg': {
                'top': bullish_unmitigated[-1].top,
                'bottom': bullish_unmitigated[-1].bottom,
                'pips': bullish_unmitigated[-1].size_pips
            } if bullish_unmitigated else None,
            'nearest_bearish_fvg': {
                'top': bearish_unmitigated[-1].top,
                'bottom': bearish_unmitigated[-1].bottom,
                'pips': bearish_unmitigated[-1].size_pips
            } if bearish_unmitigated else None
        }
