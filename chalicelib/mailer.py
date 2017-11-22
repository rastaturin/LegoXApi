import boto3
from botocore.vendored import requests

CHARSET = "UTF-8"


class MailerInterface:
    def send_message(self, email, subject, html):
        raise NotImplementedError("Should have implemented this")


class SesMailer(MailerInterface):

    def __init__(self, sender):
        self.sender = sender
        self.client = boto3.client('ses', region_name='us-west-2')

    def send_message(self, email, subject, html):
        self.client.send_email(
            Destination={
                'ToAddresses': [
                    email,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': html,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=self.sender,
        )


class MailGun(MailerInterface):
    API = "https://api.mailgun.net/v3/%s/messages"

    def __init__(self, domain, api_key, frm):
        self.domain = domain
        self.key = api_key
        self.frm = frm
        # self.sender = sender

    def send_message(self, email, subject, html):
        return requests.post(
            self.API % self.domain,
            auth=("api", self.key),
            data={
                  "from": self.frm,
                  "to": [email],
                  "subject": subject,
                  "html": html}
        )

