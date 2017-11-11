from chalicelib.exceptions import NoToken


class Authorization:
    """ Process the Authorization header """

    TYPE_BEARER = 'BEARER'
    TYPE_BASIC = 'BASIC'

    def __init__(self, headers, body):
        super().__init__()
        if not headers:
            raise NoToken("Header with authorization is expected")
        self.auth_header = headers.get("Authorization", None)
        self.data = body
        if not self.auth_header:
            raise NoToken("Authorization header is expected")

    def bearer_required(self):
        return self._auth_required(self.TYPE_BEARER)

    def basic_required(self):
        return self._auth_required(self.TYPE_BASIC)

    def _auth_required(self, auth_type):
        parts = self.auth_header.split(None, 1)
        if parts[0].lower() != auth_type.lower():
            raise NoToken("Authorization header must start with " + auth_type)
        if len(parts) > 1:
            return parts[1]
        return ""


