from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class PriceLevelVolume:
    price: float
    volume: float
    pct_of_total: float
    is_poc: bool = False
    in_value_area: bool = False


@dataclass
class VolumeProfileResult:
    poc_price: float
    vah_price: float
    val_price: float
    total_volume: float
    value_area_volume: float
    value_area_pct: float
    high_volume_nodes: List[float]
    low_volume_nodes: List[float]
    provenance_tag: str = "TICK_VOLUME_PROXY"
    price_levels: List[PriceLevelVolume] = field(default_factory=list)


class VolumeProfileEngine:
    """
    Institutional Volume Profile & Value Area Engine (P2-#31 & #32).
    Computes Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL).
    Strictly marked with TICK_VOLUME_PROXY provenance tag to avoid false DOM claims.
    """

    DEFAULT_VALUE_AREA_PCT = 0.70  # Standard 70% Institutional Value Area

    @classmethod
    def compute_profile(
        cls,
        candles: List[Dict[str, Any]],
        n_bins: int = 30,
        value_area_pct: float = DEFAULT_VALUE_AREA_PCT,
    ) -> VolumeProfileResult:
        if not candles or len(candles) < 5:
            return VolumeProfileResult(
                poc_price=0.0,
                vah_price=0.0,
                val_price=0.0,
                total_volume=0.0,
                value_area_volume=0.0,
                value_area_pct=value_area_pct,
                high_volume_nodes=[],
                low_volume_nodes=[],
            )

        highs = [float(c.get("high", c.get("close", 0))) for c in candles]
        lows = [float(c.get("low", c.get("close", 0))) for c in candles]
        closes = [float(c.get("close", 0)) for c in candles]
        volumes = [float(c.get("volume", 100.0)) for c in candles]

        min_price = min(lows)
        max_price = max(highs)

        if math.isclose(min_price, max_price, abs_tol=1e-8):
            return VolumeProfileResult(
                poc_price=closes[-1],
                vah_price=closes[-1],
                val_price=closes[-1],
                total_volume=sum(volumes),
                value_area_volume=sum(volumes),
                value_area_pct=value_area_pct,
                high_volume_nodes=[closes[-1]],
                low_volume_nodes=[],
            )

        bin_edges = np.linspace(min_price, max_price, n_bins + 1)
        bin_volumes = np.zeros(n_bins)

        # Distribute bar volume across its high-low price range
        for h, l, v in zip(highs, lows, volumes):
            bar_vol = max(1.0, v)
            if math.isclose(h, l, abs_tol=1e-8):
                idx = min(n_bins - 1, int((h - min_price) / (max_price - min_price) * n_bins))
                bin_volumes[idx] += bar_vol
            else:
                overlapping_bins = [
                    i for i in range(n_bins)
                    if not (bin_edges[i+1] < l or bin_edges[i] > h)
                ]
                if overlapping_bins:
                    allocated_vol = bar_vol / len(overlapping_bins)
                    for b_idx in overlapping_bins:
                        bin_volumes[b_idx] += allocated_vol

        total_vol = float(np.sum(bin_volumes))
        if total_vol <= 0:
            total_vol = 1.0

        bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2.0 for i in range(n_bins)]
        poc_idx = int(np.argmax(bin_volumes))
        poc_price = round(bin_centers[poc_idx], 5)

        # ── 70% Value Area Expansion Algorithm ──
        target_va_vol = total_vol * value_area_pct
        accumulated_vol = bin_volumes[poc_idx]
        va_bin_indices = {poc_idx}

        up_ptr = poc_idx + 1
        down_ptr = poc_idx - 1

        while accumulated_vol < target_va_vol and (up_ptr < n_bins or down_ptr >= 0):
            vol_up = bin_volumes[up_ptr] if up_ptr < n_bins else -1.0
            vol_down = bin_volumes[down_ptr] if down_ptr >= 0 else -1.0

            if vol_up >= vol_down and up_ptr < n_bins:
                accumulated_vol += vol_up
                va_bin_indices.add(up_ptr)
                up_ptr += 1
            elif down_ptr >= 0:
                accumulated_vol += vol_down
                va_bin_indices.add(down_ptr)
                down_ptr -= 1
            elif up_ptr < n_bins:
                accumulated_vol += vol_up
                va_bin_indices.add(up_ptr)
                up_ptr += 1
            else:
                break

        va_prices = [bin_centers[idx] for idx in va_bin_indices]
        vah_price = round(max(va_prices), 5)
        val_price = round(min(va_prices), 5)

        # ── High/Low Volume Nodes (HVN / LVN) ──
        vol_mean = float(np.mean(bin_volumes))
        vol_std = float(np.std(bin_volumes)) if len(bin_volumes) > 1 else 0.0

        hvns = [round(bin_centers[i], 5) for i in range(n_bins) if bin_volumes[i] >= (vol_mean + 0.8 * vol_std)]
        lvns = [round(bin_centers[i], 5) for i in range(n_bins) if bin_volumes[i] <= (vol_mean - 0.8 * vol_std)]

        price_levels = []
        for i in range(n_bins):
            price_levels.append(PriceLevelVolume(
                price=round(bin_centers[i], 5),
                volume=round(float(bin_volumes[i]), 2),
                pct_of_total=round(float(bin_volumes[i] / total_vol) * 100.0, 2),
                is_poc=(i == poc_idx),
                in_value_area=(i in va_bin_indices),
            ))

        return VolumeProfileResult(
            poc_price=poc_price,
            vah_price=vah_price,
            val_price=val_price,
            total_volume=round(total_vol, 2),
            value_area_volume=round(accumulated_vol, 2),
            value_area_pct=value_area_pct,
            high_volume_nodes=hvns,
            low_volume_nodes=lvns,
            provenance_tag="TICK_VOLUME_PROXY",
            price_levels=price_levels,
        )
