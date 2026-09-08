# 🏛️ AI Forex Terminal

### The World's First Deterministic, Risk-First Forex Decision Engine
### Where Safety Is Not a Feature — It's the Architecture.

---

## ⚠️ The Problem Every Trader Faces

You've been there. You see a perfect setup. You enter the trade. Then:

- The spread widens to 8 pips during NFP and your stop gets hunted.
- Your broker's feed freezes for 3 seconds — you get filled 12 pips late.
- You're already down 4.8% for the day, one more loss and your prop firm account is gone.
- You're long EUR/USD, long GBP/USD, and long AUD/USD — you think you have 3 trades, but you actually have ONE giant short-USD bet.
- Your "AI trading bot" hallucinates a bullish signal on a chart that's clearly bearish.

**Retail trading platforms let you make these mistakes. We don't.**

---

## 🛡️ What Is AI Forex Terminal?

AI Forex Terminal is an **institutional-grade decision and execution engine** built for serious Forex traders, prop firm challengers, and quantitative trading desks.

It is **NOT** a signal generator. It is **NOT** an AI bot that trades for you.

It is a **safety-first command center** that sits between you (or your strategy) and the market — and it **refuses to let you make catastrophic mistakes.**

Think of it as the **risk officer at a hedge fund**, but automated, deterministic, and running 24/5.

---

## 🧠 How It Works (In Plain English)

### The 5-Step Safety Pipeline

Every single trade you want to take goes through this pipeline. No exceptions.

---

## 🔒 The 9 Safety Gates (Explained for Traders)

| Gate | What It Checks | Why It Matters |
|------|---------------|----------------|
| **0. Data Freshness** | Is your account data from the last 60 seconds? | Stale data = wrong lot size = blown account |
| **1. Instrument Validation** | Is this a real, supported trading pair? | Prevents fat-finger errors on fake symbols |
| **2. Spread Guard** | Is the current spread within normal limits? | Trading during 15-pip spreads is suicide |
| **3. Circuit Breaker** | Are you on a losing streak? | After 5 consecutive losses, the system pauses you |
| **4. Drawdown Limits** | Have you hit your daily or total loss limit? | Prop firm compliance — breach this and you lose your funded account |
| **5. News Blackout** | Is NFP, CPI, or FOMC in the next 30 min? | News spikes destroy technical setups |
| **6. Strategy Health** | Is your strategy performing well lately? | If a strategy's win rate drops below 32%, it gets auto-suspended |
| **7. Stop Loss Geometry** | Is your SL on the correct side of entry? | BUY with SL above entry = instant loss |
| **8. Portfolio Correlation** | Are all your trades secretly the same bet? | Long EUR/USD + Long GBP/USD + Long AUD/USD = 3x USD risk |

---

## 📉 Strategy Lifecycle Intelligence

Most traders keep using a strategy long after it stops working. Our **Decay Detection Engine** monitors your strategies in real-time:

**This happens automatically.** You don't need to manually track your strategy performance. The engine does it for you every time a trade closes.

---

## 🔐 Cryptographic Decision Audit Trail

Every decision (approved OR rejected) generates an **immutable SHA-256 receipt**:

- **Decision ID:** DEC-A3F8B2C1D4
- **Timestamp:** Exact microsecond
- **Market Snapshot:** Price, spread, volatility at the moment of decision
- **Risk Snapshot:** Lot size, risk USD, pip distance
- **Compliance Snapshot:** Which gates passed, which failed
- **Data Provenance:** Where each data point came from (broker feed, user input, simulated)
- **Integrity Hash:** 7f3b2c1... (if anyone tampers with this record, the hash breaks)

**Why does this matter?**
- Prop firm audits: Prove you followed rules
- Trade journaling: Know exactly WHY a trade was blocked
- AI verification: Detect if your AI advisor hallucinated a signal
- Legal compliance: Institutional-grade record keeping

---

## 🧮 Mathematical Precision (The Details Nerds Love)

- **Floating-point precision shield:** Lot sizes are rounded to 7 decimal places before quantization to prevent the classic 1.9999999 → 1.99 truncation bug
- **Golden test vectors:** 60+ mathematically verified input-output pairs ensure pip valuations are correct to the 4th decimal place across EUR/USD, USD/JPY, XAU/USD, NAS100, and more
- **Cross-instrument parity:** Verified that 50-pip SL on EUR/USD and 50-pip SL on XAU/USD produce identical lot sizes (both pip_val = 10.0)
- **Drawdown cliff-edge precision:** 4.999% daily loss = allowed. 5.000% = blocked. No rounding ambiguity.

---

## 🏗️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Python 3.14 |
| Data Validation | Pydantic v2 (strict mode) |
| Database | SQLAlchemy 2.0 (async) |
| Frontend | React + TypeScript |
| Testing | pytest (242 tests, 100% pass rate) |
| Event System | Custom Pub/Sub with ring buffer |
| Audit Trail | SHA-256 cryptographic hashing |
| Authentication | Bearer token (API key) |

---

## 📊 By The Numbers

| Metric | Value |
|--------|-------|
| Safety Gates | 9 deterministic checks |
| Test Coverage | 242 automated tests |
| Supported Instruments | 20+ (Majors, Crosses, Gold, Silver, Indices) |
| No-Trade Reason Categories | 17 structured taxonomy |
| Strategy Lifecycle States | 4 (Active → Caution → Degraded → Retired) |
| Decision Receipt Fields | 12 immutable data points |
| Event Types Monitored | 10 real-time categories |
| Fail-Closed Guarantees | 100% (any crash = trade blocked) |

---

## 🚫 What This Is NOT

- ❌ **Not a signal provider.** We don't tell you what to trade.
- ❌ **Not an AI trading bot.** AI is a sidecar advisor, never the decision-maker.
- ❌ **Not a backtesting platform.** (That's coming, but safety comes first.)
- ❌ **Not a broker.** We connect to your broker; we don't replace them.
- ❌ **Not a get-rich-quick tool.** This is a risk management system. It protects capital.

---

## 📜 The 8 Golden Rules

These rules are hardcoded into the architecture. They cannot be overridden by any user, AI, or configuration:

1. **Deterministic Evidence > AI Interpretation**
2. **Risk & Compliance > Signal Quality**
3. **NO_TRADE > Bad Trade** (when in doubt, do nothing)
4. **Real Data > Assumptions** (never assume live data)
5. **Audit > Guess** (every decision is cryptographically recorded)
6. **Outcome > Backtest Story** (live results matter more than historical curves)
7. **Safety > Automation** (if the system crashes, trades stop — not continue)
8. **AI is a Sidecar, Not Authority** (AI cannot override risk gates, kill switches, or execute trades)

---

## 🗺️ Development Status

### ✅ Completed & Production-Ready
- [x] 9-Gate Pre-Flight Risk Gatekeeper
- [x] Order Staging & Slippage Drift Guard
- [x] Currency Correlation & Cluster Exposure Engine
- [x] Persistent Circuit Breaker (Kill Switch)
- [x] 20+ Instrument Registry with Broker Normalization
- [x] Golden Risk Test-Vector Suite (60+ vectors)
- [x] Fail-Closed Framework (NaN/Inf/Crash Protection)
- [x] Strategy Lifecycle Decay Engine (Auto Close Sync)
- [x] Cryptographic Decision Audit Trail (SHA-256)
- [x] Field-Level Data Provenance Tracking

### 🔨 In Progress
- [ ] Same-Code-Path Backtester
- [ ] Walk-Forward & Out-of-Sample Validation
- [ ] Volume Profile & Market Regime Detection
- [ ] Multi-Timeframe Evidence Matrix
- [ ] Live MT5/cTrader Broker Bridge
- [ ] Real-Time WebSocket Telemetry Dashboard

---

## 🤝 Who Is This For?

- **Prop Firm Traders** who need to stay within strict drawdown limits
- **Quantitative Desks** who need deterministic, auditable risk controls
- **Serious Retail Traders** who are tired of blowing accounts due to emotional mistakes
- **AI/ML Trading Teams** who need a safety layer between their models and live execution
- **Trading Educators** who want to teach proper risk management with real infrastructure

---

## 📄 License

Private & Proprietary. All rights reserved.

---

> *"The goal is not to make more trades. The goal is to survive long enough to let your edge play out."*

**Built with obsessive attention to safety, precision, and institutional-grade architecture.**
