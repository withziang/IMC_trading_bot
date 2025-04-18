from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Optional
import jsonpickle
import numpy as np
import math

class Product:
    CROISSANTS = "CROISSANTS"
    JAMS = "JAMS"
    DJEMBE = "DJEMBE"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    PICNIC_BASKET2 = "PICNIC_BASKET2"

BASKET_COMPOSITION = {
    Product.PICNIC_BASKET1: {Product.CROISSANTS: 6, Product.JAMS: 3, Product.DJEMBE: 1},
    Product.PICNIC_BASKET2: {Product.CROISSANTS: 4, Product.JAMS: 2}
}

PARAMS = {
    Product.PICNIC_BASKET1: {
        "spread_window": 100,
        "z_threshold": 2.0,
        "position_limit": 60,
        "risk_adjustment": 0.1,
        "base_edge": 3,
        "volatility_window": 20
    },
    Product.PICNIC_BASKET2: {
        "spread_window": 80,
        "z_threshold": 1.8,
        "position_limit": 100,
        "risk_adjustment": 0.15,
        "base_edge": 2,
        "volatility_window": 15
    },
    Product.CROISSANTS: {
        "ema_alpha": 0.2,
        "position_penalty": 0.05,
        "spread_multiplier": 1.5
    },
    Product.JAMS: {
        "ema_alpha": 0.3,
        "position_penalty": 0.03,
        "spread_multiplier": 1.2
    },
    Product.DJEMBE: {
        "ema_alpha": 0.4,
        "position_penalty": 0.08,
        "spread_multiplier": 2.0
    }
}

class Trader:
    def __init__(self):
        self.position_limits = {
            Product.CROISSANTS: 250,
            Product.JAMS: 350,
            Product.DJEMBE: 60,
            Product.PICNIC_BASKET1: 60,
            Product.PICNIC_BASKET2: 100
        }
        self.spread_history = {basket: [] for basket in BASKET_COMPOSITION}
        self.volatility = {basket: 0 for basket in BASKET_COMPOSITION}
        self.component_emas = {comp: None for comp in [Product.CROISSANTS, Product.JAMS, Product.DJEMBE]}

    def update_ema(self, new_value: float, current_ema: Optional[float], alpha: float) -> float:
        if current_ema is None:
            return new_value
        return alpha * new_value + (1 - alpha) * current_ema

    def calculate_component_mids(self, state: TradingState) -> Dict[str, Optional[float]]:
        mids = {}
        for product in [Product.CROISSANTS, Product.JAMS, Product.DJEMBE]:
            depth = state.order_depths.get(product)
            current_mid = None
            
            # Get current market mid if available
            if depth and depth.sell_orders and depth.buy_orders:
                best_ask = min(depth.sell_orders.keys())
                best_bid = max(depth.buy_orders.keys())
                current_mid = (best_ask + best_bid) / 2
            
            # Update EMA with current mid or maintain previous value
            self.component_emas[product] = current_mid if current_mid else self.component_emas[product]
            
            # Only use EMA if we have valid data
            mids[product] = self.component_emas[product] if self.component_emas[product] is not None else current_mid
            
        return mids

    def calculate_basket_fair_value(self, basket: str, component_mids: Dict[str, Optional[float]]) -> Optional[float]:
        try:
            total = 0
            for product, qty in BASKET_COMPOSITION[basket].items():
                if component_mids.get(product) is None:
                    return None
                total += qty * component_mids[product]
            return total
        except KeyError:
            return None

    def calculate_spread_zscore(self, basket: str, spread: float, traderData: Dict) -> float:
        history = traderData.get(f"{basket}_spreads", [])
        history.append(spread)
        history = history[-PARAMS[basket]["spread_window"]:]
        traderData[f"{basket}_spreads"] = history
        
        if len(history) < 2:
            return 0
            
        spread_mean = np.mean(history)
        spread_std = np.std(history)
        return (spread - spread_mean) / spread_std if spread_std != 0 else 0

    def calculate_volatility(self, basket: str, traderData: Dict) -> float:
        spreads = traderData.get(f"{basket}_spreads", [])
        if len(spreads) < 2:
            return 0
        return np.std(spreads[-PARAMS[basket]["volatility_window"]:])

    def generate_basket_orders(self, basket: str, state: TradingState, traderData: Dict) -> List[Order]:
        params = PARAMS[basket]
        depth = state.order_depths[basket]
        position = state.position.get(basket, 0)
        
        # Calculate fair value and spread
        component_mids = self.calculate_component_mids(state)
        fair_value = self.calculate_basket_fair_value(basket, component_mids)
        if fair_value is None:
            return []

        best_bid = max(depth.buy_orders.keys(), default=fair_value - params["base_edge"])
        best_ask = min(depth.sell_orders.keys(), default=fair_value + params["base_edge"])
        market_mid = (best_ask + best_bid) / 2
        spread = market_mid - fair_value
        
        # Statistical calculations
        zscore = self.calculate_spread_zscore(basket, spread, traderData)
        volatility = self.calculate_volatility(basket, traderData)
        
        # Dynamic pricing
        edge_adjustment = params["base_edge"] * (1 + abs(zscore) + volatility * 2)
        edge = max(params["base_edge"], edge_adjustment)
        position_ratio = abs(position) / self.position_limits[basket]
        edge *= (1 + position_ratio * params["risk_adjustment"])
        
        # Integer price conversion
        bid_price = int(round(fair_value - edge))
        ask_price = int(round(fair_value + edge))
        
        orders = []
        
        # Liquidity taking with integer prices
        if zscore < -params["z_threshold"]:
            ask_volume = sum(v for p,v in depth.sell_orders.items() if p <= fair_value)
            if ask_volume > 0:
                orders.append(Order(basket, int(fair_value), ask_volume))
                    
        elif zscore > params["z_threshold"]:
            bid_volume = sum(v for p,v in depth.buy_orders.items() if p >= fair_value)
            if bid_volume > 0:
                orders.append(Order(basket, int(fair_value), -bid_volume))
        
        # Market making orders
        remaining_buy = self.position_limits[basket] - position
        if remaining_buy > 0:
            orders.append(Order(basket, bid_price, remaining_buy))
                
        remaining_sell = self.position_limits[basket] + position
        if remaining_sell > 0:
            orders.append(Order(basket, ask_price, -remaining_sell))
                
        return orders

    def generate_component_orders(self, product: str, state: TradingState) -> List[Order]:
        params = PARAMS[product]
        depth = state.order_depths[product]
        position = state.position.get(product, 0)
        
        if not depth.sell_orders or not depth.buy_orders:
            return []
            
        best_ask = min(depth.sell_orders.keys())
        best_bid = max(depth.buy_orders.keys())
        mid_price = (best_ask + best_bid) / 2
        
        # Spread calculation with integer conversion
        position_penalty = params["position_penalty"] * abs(position)
        spread = params["spread_multiplier"] * (best_ask - best_bid) * (1 + position_penalty)
        bid_price = int(round(mid_price - spread/2))
        ask_price = int(round(mid_price + spread/2))
        
        orders = []
        buy_capacity = self.position_limits[product] - position
        if buy_capacity > 0:
            orders.append(Order(product, bid_price, buy_capacity))
            
        sell_capacity = self.position_limits[product] + position
        if sell_capacity > 0:
            orders.append(Order(product, ask_price, -sell_capacity))
            
        return orders

    def run(self, state: TradingState) -> (Dict[str, List[Order]], int, str):
        traderData = jsonpickle.decode(state.traderData) if state.traderData else {}
        
        result = {}
        
        # Process baskets
        for basket in BASKET_COMPOSITION:
            if basket in state.order_depths:
                result[basket] = self.generate_basket_orders(basket, state, traderData)
        
        # Process components
        for product in [Product.CROISSANTS, Product.JAMS, Product.DJEMBE]:
            if product in state.order_depths:
                result[product] = self.generate_component_orders(product, state)
        
        # Serialize trader data
        traderData = jsonpickle.encode(traderData)
        return result, 0, traderData