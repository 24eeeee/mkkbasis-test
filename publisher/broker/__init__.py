from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType

EXCHANGE_NAME = 'payments'
exchange = RabbitExchange(EXCHANGE_NAME, type=ExchangeType.TOPIC, durable=True)

def make_broker(url: str):
    return RabbitBroker(url)
