from chalice import ChaliceViewError


class MainException(ChaliceViewError):
    STATUS_CODE = 500
    ERROR_CODE = 'ERROR'
    ERROR_MESSAGE = ""

    def __init__(self, msg=None, code=None):
        super(Exception, self).__init__(msg or self.ERROR_MESSAGE)
        self.code = code or self.ERROR_CODE


class NotFoundException(MainException):
    STATUS_CODE = 404
    ERROR_CODE = 'NOT_FOUND'


class AlreadyExists(MainException):
    STATUS_CODE = 409
    ERROR_CODE = 'ALREADY_EXISTS'


class DuplicateItem(MainException):
    STATUS_CODE = 409
    ERROR_CODE = 'DUPLICATE_ITEM'


class AuthFailed(MainException):
    STATUS_CODE = 401
    ERROR_CODE = 'AUTH_FAILED'


class TokenExpired(AuthFailed):
    ERROR_CODE = 'TOKEN_EXPIRED'


class BadRequest(MainException):
    STATUS_CODE = 400
    ERROR_CODE = 'BAD_REQUEST'


class NoToken(AuthFailed):
    ERROR_CODE = 'NO_TOKEN'


class NotAcceptableCode(BadRequest):
    ERROR_CODE = 'NOT_ACCEPTABLE_CODE'


class AlreadyUsed(NotAcceptableCode):
    ERROR_CODE = 'ALREADY_USED'


class InvalidUsage(BadRequest):
    ERROR_CODE = 'INVALID_USAGE'


class InvalidLogin(AuthFailed):
    ERROR_CODE = 'LOGIN_FAILED'

    def __init__(self):
        super().__init__("Invalid login")


class InsufficientBalance(BaseException):
    pass

