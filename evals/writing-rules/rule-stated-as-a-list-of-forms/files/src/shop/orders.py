import logging

logger = logging.getLogger(__name__)


def charge(order, gateway):
    try:
        gateway.charge(order.total)
    except gateway.Declined:
        pass


def ship(order, carrier):
    try:
        carrier.book(order)
    except carrier.Unavailable as error:
        logger.exception("booking failed")
        raise
