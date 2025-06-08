# IMC Prosperity 2025 - Trading Bot Project

This project contains a set of **automated trading algorithms** and **manual trading tools** developed for the **IMC Prosperity 2025 trading competition**.

The repository is organized to support:
- **Algorithmic Trading Bots** (various strategies)
- **Manual Trading Tools**
- **Data Models and Utilities**

---

## 📂 Project Structure

- manual_trading/ # Manual trading scripts and tools
- Trader.py # Base Trader class and logic
- arbitrage_bot.py # Arbitrage trading bot implementation
- datamodel.py # Data model and utility functions (Fourier bot included)
- james_bot.py # last year bot
- test.py # Testing 
- trader_round1.py # Bot used in round 1
- trader_round2.py # Bot used in round 2
- trader_round3.py # Bot used in round 3
- trader_round4.py # Bot used in round 4



---

## 🤖 Algorithmic Trading

**Goal:** Compete in the IMC Prosperity rounds using fully automated trading bots.

### How It Works
- Algo trading: each round prosperity will give us different commodities and different rules. And we need to build a trading bot within 4 days.
- Manual trading: make a model to predict other player's decision and maximizing our profit.


### Running Algo Bots
- use prosperity3bt from [https://www.piwheels.org/project/prosperity3bt/]
