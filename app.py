import base64
import configparser
import time
import re

import boto3
from chalice import Chalice, Response
from functools import wraps

from chalicelib.Authorization import Authorization
from chalicelib.exceptions import MainException, InvalidUsage, NotFoundException
from chalicelib.repository import UserRepository, AuthcodesRepository
from chalicelib.services import UserService

app = Chalice(app_name='legoX')
app.debug = True

config = configparser.ConfigParser()
config.read('config.ini')


@app.route('/')
def test():
    return {'info': 'This is an API for LegoExchanger Project.'}


def error_handler(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except MainException as e:
            return Response(body={'Message': str(e), 'Code': e.code}, status_code=e.STATUS_CODE)
        except Exception as e:
            return Response(body={'Message': str(e), 'Code': 'INTERNAL_ERROR'}, status_code=500)

    return decorated


def require_user(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        authcode = Authorization(app.current_request.headers, app.current_request.raw_body).bearer_required()
        user_service = UserService(AuthcodesRepository(), UserRepository())
        user = user_service.auth_user(authcode)
        return f(*args, **kwargs, user=user)

    return decorated


@app.route('/login/{email}', methods=['GET'], cors=True)
def sessionkey(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise InvalidUsage('Invalid Email')

    user_repo = UserRepository()
    try:
        user = user_repo.get({'email': email})
    except NotFoundException as e:
        user = user_repo.reg_user(email)
    code = AuthcodesRepository().add_code(email)

    return {'user': user, 'code': code}


