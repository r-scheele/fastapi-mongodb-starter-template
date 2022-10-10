from fastapi_mail import ConnectionConfig
from common.config import cfg


conf = ConnectionConfig(
    MAIL_USERNAME=cfg.email_username,
    MAIL_FROM=cfg.email_from,
    MAIL_PASSWORD=cfg.email_password,
    MAIL_PORT=cfg.email_port,
    MAIL_SERVER=cfg.email_host,
    MAIL_TLS=True,
    MAIL_SSL=False,
    VALIDATE_CERTS=True,
)
