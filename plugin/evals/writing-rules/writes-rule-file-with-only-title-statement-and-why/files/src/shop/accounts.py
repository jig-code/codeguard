import logging

logger = logging.getLogger(__name__)


def sign_in(email: str, password: str, directory) -> bool:
    signed_in = directory.check_password(email, password)
    logger.info("sign-in for %s succeeded: %s", email, signed_in)
    return signed_in
