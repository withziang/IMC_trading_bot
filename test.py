from datamodel import Listing, OrderDepth, Trade, TradingState

from chat_bot import Trader

timestamp = 1000

listings = {
    "KELP": Listing(
        symbol="KELP", 
        product="KELP", 
        denomination= "SEASHELLS"
    ),
    "PRODUCT2": Listing(
        symbol="PRODUCT2", 
        product="PRODUCT2", 
        denomination= "SEASHELLS"
    ),
}

order_depths = {
    "KELP": OrderDepth(
        buy_orders={10: 7, 9: 5},
        sell_orders={11: -4, 12: -8}
    ),
    "PRODUCT2": OrderDepth(
        buy_orders={142: 3, 141: 5},
        sell_orders={144: -5, 145: -8}
    ),  
}

own_trades = {
    "KELP": [],
    "PRODUCT2": []
}

market_trades = {
    "KELP": [
        Trade(
            symbol="KELP",
            price=11,
            quantity=4,
            buyer="",
            seller="",
            timestamp=900
        )
    ],
    "PRODUCT2": []
}

position = {
    "KELP": 3,
    "PRODUCT2": -5
}

observations = {}
traderData = ""

state = TradingState(
    traderData,
    timestamp,
    listings,
    order_depths,
    own_trades,
    market_trades,
    position,
    observations
)


trader = Trader()
x,y,z = trader.run(state)

print("result: ")
print(str(x),str(y),str(z))