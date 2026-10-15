from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

PAYMENTS_EXCHANGE = 'payments'

payments_exchange = RabbitExchange(PAYMENTS_EXCHANGE, type=ExchangeType.TOPIC, durable=True)

main_queue = RabbitQueue('payments.new', durable=True, routing_key='payment.created')

RETRY_DELAYS = [2, 4, 8]

def make_retry_queue(delay_s: int) -> RabbitQueue:
    return RabbitQueue(
        f'payments.retry.{delay_s}s',
        durable=True,
        arguments={
            'x-message-ttl': delay_s * 1000,
            'x-dead-letter-exchange': PAYMENTS_EXCHANGE,
            'x-dead-letter-routing-key': 'payment.created'
        }
    )

retry_queues = [make_retry_queue(d) for d in RETRY_DELAYS]

dlq = RabbitQueue('payments.dlq', durable=True)

def make_broker(url: str) -> RabbitBroker:
    return RabbitBroker(url)
