from datamodel import OrderDepth, UserId, TradingState, Order, ConversionObservation
from typing import List, Dict, Any
import json
import jsonpickle
import numpy as np
import math


class Product:
    AMETHYSTS = "AMETHYSTS"
    STARFRUIT = "STARFRUIT"
    ORCHIDS = "ORCHIDS"
    GIFT_BASKET = "GIFT_BASKET"
    CHOCOLATE = "CHOCOLATE"
    STRAWBERRIES = "STRAWBERRIES"
    ROSES = "ROSES"
    SYNTHETIC = "SYNTHETIC"
    SPREAD = "SPREAD"
    VOLCANIC_ROCK = "VOLCANIC_ROCK"
    VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
    VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
    VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
    VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
    VOLCANIC_ROCK_VOUCHER_10500 = "VOLCANIC_ROCK_VOUCHER_10500"


PARAMS = {
    Product.AMETHYSTS: {
        "fair_value": 10000,
        "take_width": 1,
        "clear_width": 0.5,
        "volume_limit": 0,
    },
    Product.STARFRUIT: {
        "take_width": 1,
        "clear_width": 0,
        "prevent_adverse": True,
        "adverse_volume": 15,
        "reversion_beta": -0.229,
        "starfruit_min_edge": 2,
    },
    Product.ORCHIDS: {
        "make_edge": 2,
        "make_probability": 0.800,
    },
    Product.SPREAD: {
        "default_spread_mean": 379.50439988484239,
        "default_spread_std": 76.07966,
        "spread_std_window": 45,
        "zscore_threshold": 7,
        "target_position": 58,
    },
}

BASKET_WEIGHTS = {
    Product.CHOCOLATE: 4,
    Product.STRAWBERRIES: 6,
    Product.ROSES: 1,
}


class Trader:
    def __init__(self, params=None):
        if params is None:
            params = PARAMS
        self.params = params

        self.LIMIT = {
            Product.AMETHYSTS: 20,
            Product.STARFRUIT: 20,
            Product.ORCHIDS: 100,
            Product.GIFT_BASKET: 60,
            Product.CHOCOLATE: 250,
            Product.STRAWBERRIES: 350,
            Product.ROSES: 60,
            Product.VOLCANIC_ROCK: 400,
            Product.VOLCANIC_ROCK_VOUCHER_9500: 200,
            Product.VOLCANIC_ROCK_VOUCHER_9750: 200,
            Product.VOLCANIC_ROCK_VOUCHER_10000: 200,
            Product.VOLCANIC_ROCK_VOUCHER_10250: 200,
            Product.VOLCANIC_ROCK_VOUCHER_10500: 200,
        }

        # Voucher-specific attributes
        self.vouchers = [
            Product.VOLCANIC_ROCK_VOUCHER_9500,
            Product.VOLCANIC_ROCK_VOUCHER_9750,
            Product.VOLCANIC_ROCK_VOUCHER_10000,
            Product.VOLCANIC_ROCK_VOUCHER_10250,
            Product.VOLCANIC_ROCK_VOUCHER_10500
        ]
        self.strikes = [9500, 9750, 10000, 10250, 10500]
        self.threshold = 1  # Trading threshold in SeaShells

    # Cumulative normal distribution function using error function
    def N(self, x):
        return (1 + math.erf(x / math.sqrt(2))) / 2

    # Black-Scholes call option pricing
    def black_scholes_call(self, S, K, T, sigma, r=0):
        if T <= 0 or sigma <= 0 or S <= 0:
            return max(S - K, 0)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        C = S * self.N(d1) - K * math.exp(-r * T) * self.N(d2)
        return C

    # Existing methods from template (unchanged for brevity)
    def take_best_orders(self, product: str, fair_value: int, take_width: float, orders: List[Order], order_depth: OrderDepth, position: int, buy_order_volume: int, sell_order_volume: int, prevent_adverse: bool = False, adverse_volume: int = 0) -> (int, int):
        position_limit = self.LIMIT[product]
        if len(order_depth.sell_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_amount = -1 * order_depth.sell_orders[best_ask]
            if best_ask <= fair_value - take_width:
                quantity = min(best_ask_amount, position_limit - position)
                if quantity > 0:
                    orders.append(Order(product, best_ask, quantity))
                    buy_order_volume += quantity
                    order_depth.sell_orders[best_ask] += quantity
                    if order_depth.sell_orders[best_ask] == 0:
                        del order_depth.sell_orders[best_ask]
        if len(order_depth.buy_orders) != 0:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_amount = order_depth.buy_orders[best_bid]
            if best_bid >= fair_value + take_width:
                quantity = min(best_bid_amount, position_limit + position)
                if quantity > 0:
                    orders.append(Order(product, best_bid, -1 * quantity))
                    sell_order_volume += quantity
                    order_depth.buy_orders[best_bid] -= quantity
                    if order_depth.buy_orders[best_bid] == 0:
                        del order_depth.buy_orders[best_bid]
        return buy_order_volume, sell_order_volume

    def take_best_orders_with_adverse(self, product: str, fair_value: int, take_width: float, orders: List[Order], order_depth: OrderDepth, position: int, buy_order_volume: int, sell_order_volume: int, adverse_volume: int) -> (int, int):
        position_limit = self.LIMIT[product]
        if len(order_depth.sell_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_amount = -1 * order_depth.sell_orders[best_ask]
            if abs(best_ask_amount) <= adverse_volume and best_ask <= fair_value - take_width:
                quantity = min(best_ask_amount, position_limit - position)
                if quantity > 0:
                    orders.append(Order(product, best_ask, quantity))
                    buy_order_volume += quantity
                    order_depth.sell_orders[best_ask] += quantity
                    if order_depth.sell_orders[best_ask] == 0:
                        del order_depth.sell_orders[best_ask]
        if len(order_depth.buy_orders) != 0:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_amount = order_depth.buy_orders[best_bid]
            if abs(best_bid_amount) <= adverse_volume and best_bid >= fair_value + take_width:
                quantity = min(best_bid_amount, position_limit + position)
                if quantity > 0:
                    orders.append(Order(product, best_bid, -1 * quantity))
                    sell_order_volume += quantity
                    order_depth.buy_orders[best_bid] -= quantity
                    if order_depth.buy_orders[best_bid] == 0:
                        del order_depth.buy_orders[best_bid]
        return buy_order_volume, sell_order_volume

    def market_make(self, product: str, orders: List[Order], bid: int, ask: int, position: int, buy_order_volume: int, sell_order_volume: int) -> (int, int):
        buy_quantity = self.LIMIT[product] - (position + buy_order_volume)
        if buy_quantity > 0:
            orders.append(Order(product, round(bid), buy_quantity))
        sell_quantity = self.LIMIT[product] + (position - sell_order_volume)
        if sell_quantity > 0:
            orders.append(Order(product, round(ask), -sell_quantity))
        return buy_order_volume, sell_order_volume

    def clear_position_order(self, product: str, fair_value: float, width: int, orders: List[Order], order_depth: OrderDepth, position: int, buy_order_volume: int, sell_order_volume: int) -> List[Order]:
        position_after_take = position + buy_order_volume - sell_order_volume
        fair_for_bid = round(fair_value - width)
        fair_for_ask = round(fair_value + width)
        buy_quantity = self.LIMIT[product] - (position + buy_order_volume)
        sell_quantity = self.LIMIT[product] + (position - sell_order_volume)
        if position_after_take > 0:
            clear_quantity = sum(volume for price, volume in order_depth.buy_orders.items() if price >= fair_for_ask)
            clear_quantity = min(clear_quantity, position_after_take)
            sent_quantity = min(sell_quantity, clear_quantity)
            if sent_quantity > 0:
                orders.append(Order(product, fair_for_ask, -abs(sent_quantity)))
                sell_order_volume += abs(sent_quantity)
        if position_after_take < 0:
            clear_quantity = sum(abs(volume) for price, volume in order_depth.sell_orders.items() if price <= fair_for_bid)
            clear_quantity = min(clear_quantity, abs(position_after_take))
            sent_quantity = min(buy_quantity, clear_quantity)
            if sent_quantity > 0:
                orders.append(Order(product, fair_for_bid, abs(sent_quantity)))
                buy_order_volume += abs(sent_quantity)
        return buy_order_volume, sell_order_volume

    def starfruit_fair_value(self, order_depth: OrderDepth, traderObject) -> float:
        if len(order_depth.sell_orders) != 0 and len(order_depth.buy_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_bid = max(order_depth.buy_orders.keys())
            filtered_ask = [price for price in order_depth.sell_orders.keys() if abs(order_depth.sell_orders[price]) >= self.params[Product.STARFRUIT]["adverse_volume"]]
            filtered_bid = [price for price in order_depth.buy_orders.keys() if abs(order_depth.buy_orders[price]) >= self.params[Product.STARFRUIT]["adverse_volume"]]
            mm_ask = min(filtered_ask) if len(filtered_ask) > 0 else None
            mm_bid = max(filtered_bid) if len(filtered_bid) > 0 else None
            if mm_ask is None or mm_bid is None:
                if traderObject.get("starfruit_last_price", None) is None:
                    mmmid_price = (best_ask + best_bid) / 2
                else:
                    mmmid_price = traderObject["starfruit_last_price"]
            else:
                mmmid_price = (mm_ask + mm_bid) / 2
            if traderObject.get("starfruit_last_price", None) is not None:
                last_price = traderObject["starfruit_last_price"]
                last_returns = (mmmid_price - last_price) / last_price
                pred_returns = last_returns * self.params[Product.STARFRUIT]["reversion_beta"]
                fair = mmmid_price + (mmmid_price * pred_returns)
            else:
                fair = mmmid_price
            traderObject["starfruit_last_price"] = mmmid_price
            return fair
        return None

    def make_amethyst_orders(self, order_depth: OrderDepth, fair_value: int, position: int, buy_order_volume: int, sell_order_volume: int, volume_limit: int) -> (List[Order], int, int):
        orders: List[Order] = []
        baaf = min([price for price in order_depth.sell_orders.keys() if price > fair_value + 1])
        bbbf = max([price for price in order_depth.buy_orders.keys() if price < fair_value - 1])
        if baaf <= fair_value + 2 and position <= volume_limit:
            baaf = fair_value + 3
        if bbbf >= fair_value - 2 and position >= -volume_limit:
            bbbf = fair_value - 3
        buy_order_volume, sell_order_volume = self.market_make(Product.AMETHYSTS, orders, bbbf + 1, baaf - 1, position, buy_order_volume, sell_order_volume)
        return orders, buy_order_volume, sell_order_volume

    def take_orders(self, product: str, order_depth: OrderDepth, fair_value: float, take_width: float, position: int, prevent_adverse: bool = False, adverse_volume: int = 0) -> (List[Order], int, int):
        orders: List[Order] = []
        buy_order_volume = 0
        sell_order_volume = 0
        if prevent_adverse:
            buy_order_volume, sell_order_volume = self.take_best_orders_with_adverse(product, fair_value, take_width, orders, order_depth, position, buy_order_volume, sell_order_volume, adverse_volume)
        else:
            buy_order_volume, sell_order_volume = self.take_best_orders(product, fair_value, take_width, orders, order_depth, position, buy_order_volume, sell_order_volume)
        return orders, buy_order_volume, sell_order_volume

    def clear_orders(self, product: str, order_depth: OrderDepth, fair_value: float, clear_width: int, position: int, buy_order_volume: int, sell_order_volume: int) -> (List[Order], int, int):
        orders: List[Order] = []
        buy_order_volume, sell_order_volume = self.clear_position_order(product, fair_value, clear_width, orders, order_depth, position, buy_order_volume, sell_order_volume)
        return orders, buy_order_volume, sell_order_volume

    def make_starfruit_orders(self, order_depth: OrderDepth, fair_value: float, min_edge: float, position: int, buy_order_volume: int, sell_order_volume: int) -> (List[Order], int, int):
        orders: List[Order] = []
        aaf = [price for price in order_depth.sell_orders.keys() if price >= round(fair_value + min_edge)]
        bbf = [price for price in order_depth.buy_orders.keys() if price <= round(fair_value - min_edge)]
        baaf = min(aaf) if len(aaf) > 0 else round(fair_value + min_edge)
        bbbf = max(bbf) if len(bbf) > 0 else round(fair_value - min_edge)
        buy_order_volume, sell_order_volume = self.market_make(Product.STARFRUIT, orders, bbbf + 1, baaf - 1, position, buy_order_volume, sell_order_volume)
        return orders, buy_order_volume, sell_order_volume

    def orchids_implied_bid_ask(self, observation: ConversionObservation) -> (float, float):
        return (
            observation.bidPrice - observation.exportTariff - observation.transportFees - 0.1,
            observation.askPrice + observation.importTariff + observation.transportFees
        )

    def orchids_arb_take(self, order_depth: OrderDepth, observation: ConversionObservation, position: int) -> (List[Order], int, int):
        orders: List[Order] = []
        position_limit = self.LIMIT[Product.ORCHIDS]
        buy_order_volume = 0
        sell_order_volume = 0
        implied_bid, implied_ask = self.orchids_implied_bid_ask(observation)
        buy_quantity = position_limit - position
        sell_quantity = position_limit + position
        ask = round(observation.askPrice) - 2
        edge = (ask - implied_ask) * self.params[Product.ORCHIDS]["make_probability"] if ask > implied_ask else 0
        for price in sorted(list(order_depth.sell_orders.keys())):
            if price >= implied_bid - edge:
                break
            quantity = min(abs(order_depth.sell_orders[price]), buy_quantity)
            if quantity > 0:
                orders.append(Order(Product.ORCHIDS, round(price), quantity))
                buy_order_volume += quantity
        for price in sorted(list(order_depth.buy_orders.keys()), reverse=True):
            if price <= implied_ask + edge:
                break
            quantity = min(abs(order_depth.buy_orders[price]), sell_quantity)
            if quantity > 0:
                orders.append(Order(Product.ORCHIDS, round(price), -quantity))
                sell_order_volume += quantity
        return orders, buy_order_volume, sell_order_volume

    def orchids_arb_clear(self, position: int) -> int:
        return -position

    def orchids_arb_make(self, observation: ConversionObservation, position: int, buy_order_volume: int, sell_order_volume: int) -> (List[Order], int, int):
        orders: List[Order] = []
        position_limit = self.LIMIT[Product.ORCHIDS]
        implied_bid, implied_ask = self.orchids_implied_bid_ask(observation)
        aggressive_ask = round(observation.askPrice) - 2
        aggressive_bid = round(observation.bidPrice) + 2
        bid = aggressive_bid if aggressive_bid < implied_bid else implied_bid - 1
        ask = aggressive_ask if aggressive_ask >= implied_ask + 0.5 else (aggressive_ask + 1 if aggressive_ask + 1 >= implied_ask + 0.5 else implied_ask + 2)
        buy_quantity = position_limit - (position + buy_order_volume)
        if buy_quantity > 0:
            orders.append(Order(Product.ORCHIDS, round(bid), buy_quantity))
        sell_quantity = position_limit + (position - sell_order_volume)
        if sell_quantity > 0:
            orders.append(Order(Product.ORCHIDS, round(ask), -sell_quantity))
        return orders, buy_order_volume, sell_order_volume

    def get_swmid(self, order_depth) -> float:
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        best_bid_vol = abs(order_depth.buy_orders[best_bid])
        best_ask_vol = abs(order_depth.sell_orders[best_ask])
        return (best_bid * best_ask_vol + best_ask * best_bid_vol) / (best_bid_vol + best_ask_vol)

    def get_synthetic_basket_order_depth(self, order_depths: Dict[str, OrderDepth]) -> OrderDepth:
        CHOCOLATE_PER_BASKET = BASKET_WEIGHTS[Product.CHOCOLATE]
        STRAWBERRIES_PER_BASKET = BASKET_WEIGHTS[Product.STRAWBERRIES]
        ROSES_PER_BASKET = BASKET_WEIGHTS[Product.ROSES]
        synthetic_order_price = OrderDepth()
        chocolate_best_bid = max(order_depths[Product.CHOCOLATE].buy_orders.keys()) if order_depths[Product.CHOCOLATE].buy_orders else 0
        chocolate_best_ask = min(order_depths[Product.CHOCOLATE].sell_orders.keys()) if order_depths[Product.CHOCOLATE].sell_orders else float("inf")
        strawberries_best_bid = max(order_depths[Product.STRAWBERRIES].buy_orders.keys()) if order_depths[Product.STRAWBERRIES].buy_orders else 0
        strawberries_best_ask = min(order_depths[Product.STRAWBERRIES].sell_orders.keys()) if order_depths[Product.STRAWBERRIES].sell_orders else float("inf")
        roses_best_bid = max(order_depths[Product.ROSES].buy_orders.keys()) if order_depths[Product.ROSES].buy_orders else 0
        roses_best_ask = min(order_depths[Product.ROSES].sell_orders.keys()) if order_depths[Product.ROSES].sell_orders else float("inf")
        implied_bid = chocolate_best_bid * CHOCOLATE_PER_BASKET + strawberries_best_bid * STRAWBERRIES_PER_BASKET + roses_best_bid * ROSES_PER_BASKET
        implied_ask = chocolate_best_ask * CHOCOLATE_PER_BASKET + strawberries_best_ask * STRAWBERRIES_PER_BASKET + roses_best_ask * ROSES_PER_BASKET
        if implied_bid > 0:
            chocolate_bid_volume = order_depths[Product.CHOCOLATE].buy_orders[chocolate_best_bid] // CHOCOLATE_PER_BASKET
            strawberries_bid_volume = order_depths[Product.STRAWBERRIES].buy_orders[strawberries_best_bid] // STRAWBERRIES_PER_BASKET
            roses_bid_volume = order_depths[Product.ROSES].buy_orders[roses_best_bid] // ROSES_PER_BASKET
            implied_bid_volume = min(chocolate_bid_volume, strawberries_bid_volume, roses_bid_volume)
            synthetic_order_price.buy_orders[implied_bid] = implied_bid_volume
        if implied_ask < float("inf"):
            chocolate_ask_volume = -order_depths[Product.CHOCOLATE].sell_orders[chocolate_best_ask] // CHOCOLATE_PER_BASKET
            strawberries_ask_volume = -order_depths[Product.STRAWBERRIES].sell_orders[strawberries_best_ask] // STRAWBERRIES_PER_BASKET
            roses_ask_volume = -order_depths[Product.ROSES].sell_orders[roses_best_ask] // ROSES_PER_BASKET
            implied_ask_volume = min(chocolate_ask_volume, strawberries_ask_volume, roses_ask_volume)
            synthetic_order_price.sell_orders[implied_ask] = -implied_ask_volume
        return synthetic_order_price

    def convert_synthetic_basket_orders(self, synthetic_orders: List[Order], order_depths: Dict[str, OrderDepth]) -> Dict[str, List[Order]]:
        component_orders = {Product.CHOCOLATE: [], Product.STRAWBERRIES: [], Product.ROSES: []}
        synthetic_basket_order_depth = self.get_synthetic_basket_order_depth(order_depths)
        best_bid = max(synthetic_basket_order_depth.buy_orders.keys()) if synthetic_basket_order_depth.buy_orders else 0
        best_ask = min(synthetic_basket_order_depth.sell_orders.keys()) if synthetic_basket_order_depth.sell_orders else float("inf")
        for order in synthetic_orders:
            price = order.price
            quantity = order.quantity
            if quantity > 0 and price >= best_ask:
                chocolate_price = min(order_depths[Product.CHOCOLATE].sell_orders.keys())
                strawberries_price = min(order_depths[Product.STRAWBERRIES].sell_orders.keys())
                roses_price = min(order_depths[Product.ROSES].sell_orders.keys())
            elif quantity < 0 and price <= best_bid:
                chocolate_price = max(order_depths[Product.CHOCOLATE].buy_orders.keys())
                strawberries_price = max(order_depths[Product.STRAWBERRIES].buy_orders.keys())
                roses_price = max(order_depths[Product.ROSES].buy_orders.keys())
            else:
                continue
            component_orders[Product.CHOCOLATE].append(Order(Product.CHOCOLATE, chocolate_price, quantity * BASKET_WEIGHTS[Product.CHOCOLATE]))
            component_orders[Product.STRAWBERRIES].append(Order(Product.STRAWBERRIES, strawberries_price, quantity * BASKET_WEIGHTS[Product.STRAWBERRIES]))
            component_orders[Product.ROSES].append(Order(Product.ROSES, roses_price, quantity * BASKET_WEIGHTS[Product.ROSES]))
        return component_orders

    def execute_spread_orders(self, target_position: int, basket_position: int, order_depths: Dict[str, OrderDepth]):
        if target_position == basket_position:
            return None
        target_quantity = abs(target_position - basket_position)
        basket_order_depth = order_depths[Product.GIFT_BASKET]
        synthetic_order_depth = self.get_synthetic_basket_order_depth(order_depths)
        if target_position > basket_position:
            basket_ask_price = min(basket_order_depth.sell_orders.keys())
            basket_ask_volume = abs(basket_order_depth.sell_orders[basket_ask_price])
            synthetic_bid_price = max(synthetic_order_depth.buy_orders.keys())
            synthetic_bid_volume = abs(synthetic_order_depth.buy_orders[synthetic_bid_price])
            orderbook_volume = min(basket_ask_volume, synthetic_bid_volume)
            execute_volume = min(orderbook_volume, target_quantity)
            basket_orders = [Order(Product.GIFT_BASKET, basket_ask_price, execute_volume)]
            synthetic_orders = [Order(Product.SYNTHETIC, synthetic_bid_price, -execute_volume)]
            aggregate_orders = self.convert_synthetic_basket_orders(synthetic_orders, order_depths)
            aggregate_orders[Product.GIFT_BASKET] = basket_orders
            return aggregate_orders
        else:
            basket_bid_price = max(basket_order_depth.buy_orders.keys())
            basket_bid_volume = abs(basket_order_depth.buy_orders[basket_bid_price])
            synthetic_ask_price = min(synthetic_order_depth.sell_orders.keys())
            synthetic_ask_volume = abs(synthetic_order_depth.sell_orders[synthetic_ask_price])
            orderbook_volume = min(basket_bid_volume, synthetic_ask_volume)
            execute_volume = min(orderbook_volume, target_quantity)
            basket_orders = [Order(Product.GIFT_BASKET, basket_bid_price, -execute_volume)]
            synthetic_orders = [Order(Product.SYNTHETIC, synthetic_ask_price, execute_volume)]
            aggregate_orders = self.convert_synthetic_basket_orders(synthetic_orders, order_depths)
            aggregate_orders[Product.GIFT_BASKET] = basket_orders
            return aggregate_orders

    def spread_orders(self, order_depths: Dict[str, OrderDepth], product: Product, basket_position: int, spread_data: Dict[str, Any]):
        if Product.GIFT_BASKET not in order_depths.keys():
            return None
        basket_order_depth = order_depths[Product.GIFT_BASKET]
        synthetic_order_depth = self.get_synthetic_basket_order_depth(order_depths)
        basket_swmid = self.get_swmid(basket_order_depth)
        synthetic_swmid = self.get_swmid(synthetic_order_depth)
        spread = basket_swmid - synthetic_swmid
        spread_data["spread_history"].append(spread)
        if len(spread_data["spread_history"]) < self.params[Product.SPREAD]["spread_std_window"]:
            return None
        elif len(spread_data["spread_history"]) > self.params[Product.SPREAD]["spread_std_window"]:
            spread_data["spread_history"].pop(0)
        spread_std = np.std(spread_data["spread_history"])
        zscore = (spread - self.params[Product.SPREAD]["default_spread_mean"]) / spread_std
        if zscore >= self.params[Product.SPREAD]["zscore_threshold"] and basket_position != -self.params[Product.SPREAD]["target_position"]:
            return self.execute_spread_orders(-self.params[Product.SPREAD]["target_position"], basket_position, order_depths)
        if zscore <= -self.params[Product.SPREAD]["zscore_threshold"] and basket_position != self.params[Product.SPREAD]["target_position"]:
            return self.execute_spread_orders(self.params[Product.SPREAD]["target_position"], basket_position, order_depths)
        spread_data["prev_zscore"] = zscore
        return None

    def run(self, state: TradingState):
        traderObject = jsonpickle.decode(state.traderData) if state.traderData else {}

        # Initialize traderObject for volcanic rock data
        if "last_price" not in traderObject:
            traderObject["last_price"] = None
            traderObject["log_returns"] = []

        result = {}
        conversions = 0

        # Compute mid-price of VOLCANIC_ROCK
        if Product.VOLCANIC_ROCK in state.order_depths:
            volcanic_rock_depth = state.order_depths[Product.VOLCANIC_ROCK]
            best_bid = max(volcanic_rock_depth.buy_orders.keys()) if volcanic_rock_depth.buy_orders else 0
            best_ask = min(volcanic_rock_depth.sell_orders.keys()) if volcanic_rock_depth.sell_orders else float("inf")
            mid_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask < float("inf") else None

            # Update log returns for volatility estimation
            if mid_price is not None:
                if traderObject["last_price"] is not None and traderObject["last_price"] > 0:
                    r_t = math.log(mid_price / traderObject["last_price"])
                    traderObject["log_returns"].append(r_t)
                    if len(traderObject["log_returns"]) > 100:
                        traderObject["log_returns"].pop(0)
                traderObject["last_price"] = mid_price

            # Estimate volatility
            sigma = np.std(traderObject["log_returns"]) if len(traderObject["log_returns"]) >= 10 else None

            # Time to expiration (expiration at timestamp 69,900)
            n = state.timestamp // 100  # Current time step number (0 to 699)
            if n < 699 and sigma is not None:
                T = 699 - n  # Time steps remaining

                # Trade each voucher
                for voucher, K in zip(self.vouchers, self.strikes):
                    if voucher in state.order_depths:
                        # Calculate fair value
                        C_fair = self.black_scholes_call(mid_price, K, T, sigma)

                        # Market data
                        voucher_depth = state.order_depths[voucher]
                        best_bid = max(voucher_depth.buy_orders.keys()) if voucher_depth.buy_orders else None
                        best_ask = min(voucher_depth.sell_orders.keys()) if voucher_depth.sell_orders else None
                        position = state.position.get(voucher, 0)

                        orders = []
                        # Buy if fair value exceeds ask price plus threshold
                        if best_ask is not None and C_fair > best_ask + self.threshold:
                            quantity = min(voucher_depth.sell_orders[best_ask], self.LIMIT[voucher] - position)
                            if quantity > 0:
                                orders.append(Order(voucher, best_ask, quantity))
                        # Sell if fair value is below bid price minus threshold
                        if best_bid is not None and C_fair < best_bid - self.threshold:
                            quantity = min(voucher_depth.buy_orders[best_bid], self.LIMIT[voucher] + position)
                            if quantity > 0:
                                orders.append(Order(voucher, best_bid, -quantity))
                        if orders:
                            result[voucher] = orders

        # Existing product trading logic (unchanged)
        if Product.AMETHYSTS in self.params and Product.AMETHYSTS in state.order_depths:
            amethyst_position = state.position.get(Product.AMETHYSTS, 0)
            amethyst_take_orders, buy_order_volume, sell_order_volume = self.take_orders(
                Product.AMETHYSTS, state.order_depths[Product.AMETHYSTS], self.params[Product.AMETHYSTS]["fair_value"],
                self.params[Product.AMETHYSTS]["take_width"], amethyst_position
            )
            amethyst_clear_orders, buy_order_volume, sell_order_volume = self.clear_orders(
                Product.AMETHYSTS, state.order_depths[Product.AMETHYSTS], self.params[Product.AMETHYSTS]["fair_value"],
                self.params[Product.AMETHYSTS]["clear_width"], amethyst_position, buy_order_volume, sell_order_volume
            )
            amethyst_make_orders, _, _ = self.make_amethyst_orders(
                state.order_depths[Product.AMETHYSTS], self.params[Product.AMETHYSTS]["fair_value"], amethyst_position,
                buy_order_volume, sell_order_volume, self.params[Product.AMETHYSTS]["volume_limit"]
            )
            result[Product.AMETHYSTS] = amethyst_take_orders + amethyst_clear_orders + amethyst_make_orders

        if Product.STARFRUIT in self.params and Product.STARFRUIT in state.order_depths:
            starfruit_position = state.position.get(Product.STARFRUIT, 0)
            starfruit_fair_value = self.starfruit_fair_value(state.order_depths[Product.STARFRUIT], traderObject)
            starfruit_take_orders, buy_order_volume, sell_order_volume = self.take_orders(
                Product.STARFRUIT, state.order_depths[Product.STARFRUIT], starfruit_fair_value,
                self.params[Product.STARFRUIT]["take_width"], starfruit_position,
                self.params[Product.STARFRUIT]["prevent_adverse"], self.params[Product.STARFRUIT]["adverse_volume"]
            )
            starfruit_clear_orders, buy_order_volume, sell_order_volume = self.clear_orders(
                Product.STARFRUIT, state.order_depths[Product.STARFRUIT], starfruit_fair_value,
                self.params[Product.STARFRUIT]["clear_width"], starfruit_position, buy_order_volume, sell_order_volume
            )
            starfruit_make_orders, _, _ = self.make_starfruit_orders(
                state.order_depths[Product.STARFRUIT], starfruit_fair_value,
                self.params[Product.STARFRUIT]["starfruit_min_edge"], starfruit_position, buy_order_volume, sell_order_volume
            )
            result[Product.STARFRUIT] = starfruit_take_orders + starfruit_clear_orders + starfruit_make_orders

        if Product.ORCHIDS in self.params and Product.ORCHIDS in state.order_depths:
            orchids_position = state.position.get(Product.ORCHIDS, 0)
            conversions = self.orchids_arb_clear(orchids_position)
            orchids_position = 0
            orchids_take_orders, buy_order_volume, sell_order_volume = self.orchids_arb_take(
                state.order_depths[Product.ORCHIDS], state.observations.conversionObservations[Product.ORCHIDS], orchids_position
            )
            orchids_make_orders, _, _ = self.orchids_arb_make(
                state.observations.conversionObservations[Product.ORCHIDS], orchids_position, buy_order_volume, sell_order_volume
            )
            result[Product.ORCHIDS] = orchids_take_orders + orchids_make_orders

        if Product.SPREAD not in traderObject:
            traderObject[Product.SPREAD] = {"spread_history": [], "prev_zscore": 0, "clear_flag": False, "curr_avg": 0}
        basket_position = state.position.get(Product.GIFT_BASKET, 0)
        spread_orders = self.spread_orders(state.order_depths, Product.GIFT_BASKET, basket_position, traderObject[Product.SPREAD])
        if spread_orders is not None:
            result[Product.CHOCOLATE] = spread_orders[Product.CHOCOLATE]
            result[Product.STRAWBERRIES] = spread_orders[Product.STRAWBERRIES]
            result[Product.ROSES] = spread_orders[Product.ROSES]
            result[Product.GIFT_BASKET] = spread_orders[Product.GIFT_BASKET]

        traderData = jsonpickle.encode(traderObject)
        return result, conversions, traderData

