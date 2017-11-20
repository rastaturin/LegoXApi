import base64
import configparser
import time
import re

import boto3
from chalice import Chalice, Response
from functools import wraps

from chalicelib.Authorization import Authorization
from chalicelib.exceptions import MainException, InvalidUsage, NotFoundException
from chalicelib.repository import UserRepository, AuthcodesRepository, SetsRepository, ThemesRepository, \
    MysetsRepository
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


@app.route('/sets/{year}/{theme}', methods=['GET'], cors=True)
@app.route('/sets/{year}', methods=['GET'], cors=True)
def get_sets(year, theme=''):
    th_repo = ThemesRepository()
    sets = search_sets(year, theme)
    sets_k = {}
    for set in sets:
        theme = set.get('theme')
        set['theme_name'] = th_repo.get({'key': theme}) if theme > 0 else ''
        set['sales'] = 0
        sets_k[set.get('key')] = set

    for sale in MysetsRepository().scan():
        key = sale.get('key')
        if key in sets_k:
            sets_k[key]['sales'] += 1
            if 'min' in sets_k[key]:
                sets_k[key]['min'] = min(sale['price'], sets_k[key]['min'])
            else:
                sets_k[key]['min'] = sale['price']

    return {'sets': sets}


def search_sets(year, theme):
    if year != '0' and theme != '':
        return SetsRepository().search(int(year), int(theme), 30)
    if year != '0':
        return SetsRepository().search_year(int(year), 30)
    if theme != '':
        return SetsRepository().search_theme(int(theme), 30)
    return seach_sales()


@app.route('/themes', methods=['GET'], cors=True)
def get_sets():
    return {'themes': ThemesRepository().scan()}


@app.route('/mysets', methods=['PUT'], cors=True)
@require_user
def get_sets(user):
    key = str(app.current_request.json_body.get('key', ''))
    price = int(app.current_request.json_body.get('price', 0))
    data = {
        'user': user.get('email'),
        'key': key,
        'price': price
    }
    MysetsRepository().insert(data)
    return {'items': MysetsRepository().query('user', user.get('email'))}


@app.route('/mysets', methods=['GET'], cors=True)
@require_user
def get_sets(user):
    return {'items': MysetsRepository().query('user', user.get('email'))}


@app.route('/set/{key}', methods=['GET'], cors=True)
def get_set(key):
    set = SetsRepository().get({'key': key})
    set['sales'] = MysetsRepository().query('key', key, 'key-index')
    return {'set': set}


@app.route('/sales', methods=['GET'], cors=True)
def get_sets():
    sales = {}
    th_repo = ThemesRepository()
    for sale in MysetsRepository().scan():
        key = sale.get('key')
        if key not in sales:
            sales[key] = SetsRepository().get({'key': key})
            sales[key]['sales'] = 0
            sales[key]['min'] = sale['price']
            theme = sales[key].get('theme')
            sales[key]['theme_name'] = th_repo.get({'key': theme}) if theme > 0 else ''
        sales[key]['sales'] += 1
        sales[key]['min'] = min(sale['price'], sales[key]['min'])
    return {'items': list(sales.values())}


@app.route('/mysets/{key}', methods=['DELETE'], cors=True)
@require_user
def get_sets(key, user):
    MysetsRepository().remove({'user': user.get('email'), 'key': key})
    return {'items': MysetsRepository().query('user', user.get('email'))}


def seach_sales():
    sales = {}
    for sale in MysetsRepository().scan():
        key = sale.get('key')
        if key not in sales:
            sales[key] = SetsRepository().get({'key': key})
    return list(sales.values())
