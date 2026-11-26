import logging

logger = logging.getLogger(__name__)


def sign_in(email: str, password: str, directory) -> bool:
    signed_in = directory.check_password(email, password)
    logger.info("sign-in for %s succeeded: %s", email, signed_in)
    return signed_in


def send_password_reset(email: str, directory) -> None:
    rc = directory.send_reset(email)
    if rc != 0:
        logger.warning("rst rc=%d", rc)
