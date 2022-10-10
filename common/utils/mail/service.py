import datetime as dt
from re import template
from injector import singleton, inject
from fastapi_mail import MessageSchema, FastMail

from common.utils.mail.schema import MailCreate
from common.concurrency import cpu_bound_task
from common.config import cfg

from common.utils.mail.config import conf


from jinja2 import Environment, select_autoescape, PackageLoader

env = Environment(
    loader=PackageLoader("common.utils.mail", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


@singleton
class MailService:
    @inject
    def __init__(self):
        self._fastapi_mail = FastMail(conf)

    async def send_email(self, mail: MailCreate, values: dict):

        template = env.get_template(f"{mail.template_name}.html")

        email_body = template.render(**values)

        message = MessageSchema(
            subject=mail.subject,
            recipients=mail.recipients,
            body=email_body,
            subtype="html",
        )

        await self._fastapi_mail.send_message(message)

    async def send_verification_code(self, email: str, code: str):
        values = {
            "url": f"{cfg.domain_name}/verify/{code}",
            "first_name": "Habeeb",
        }

        await self.send_email(
            MailCreate(
                subject="Verification Code",
                recipients=[email],
                template_name="verification",
            ),
            values,
        )
