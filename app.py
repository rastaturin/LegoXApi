import base64
import configparser
import time
import re

from chalice import Chalice, Response
from functools import wraps

from chalicelib.Authorization import Authorization
from chalicelib.exceptions import MainException, InvalidUsage, NotFoundException
from chalicelib.mailer import MailGun
from chalicelib.repository import UserRepository, AuthcodesRepository, SetsRepository, ThemesRepository, \
    MysetsRepository
from chalicelib.services import UserService

app = Chalice(app_name='legoX')
app.debug = True

config = configparser.ConfigParser()
config.read('./chalicelib/conf.ini')


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


@app.route('/login/{email}/{password}', methods=['GET'], cors=True)
@error_handler
def login(email, password):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise InvalidUsage('Invalid Email')
    result = 0
    message = 'Login successfully.'
    print("Email:", email, '; Password:', password)
    user_repo = UserRepository()
    try:
        user = user_repo.get({'email': email})
        if user['password'] != password:
            result = 2
            email = ''
            message = "Unable to login. The email or password you provided is incorrect."
        else:
            code = AuthcodesRepository().add_code(email)
    except NotFoundException as e:
        print("Unable to login. The email or password you provided is incorrect.")
        result = 1
        email = ''
        message = "Unable to login. The email or password you provided is incorrect."
    return {'status': result, 'message': message, '_code': code, 'email': email}


# Forgot password flow. The user will receive the temp password to login
# and then able to update the password in thge console
@app.route('/reset/{email}/{password}', methods=['GET'], cors=True)
def reset_password(email):
    return {'status': 0}


# Update password feature
@app.route('/profile/update/{email}/password/{password}/nickname/{nickname}/logo/{logo}', methods=['GET'], cors=True)
def update_password(email, password, nickname, logo):
    user_repo = UserRepository()
    try:
        user = user_repo.get({'email': email})
        if password:
            print('update password', password)
            user_repo.update_profile(email, {'attribute': 'password', 'value': password})
        if nickname:
            print('update nickname', nickname)
            user_repo.update_profile(email, {'attribute': 'nickname', 'value': nickname})
        if logo:
            print('update logo', logo)
            user_repo.update_profile(email, {'attribute': 'logo', 'value': logo})
    except NotFoundException as e:
        return {'status': 1, 'message': 'Update failed'}
    return {'status': 0, 'message': 'Update successfully'}


@app.route('/register/{email}/{password}', methods=['GET'], cors=True)
@error_handler
def register(email, password):
    status = 0
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise InvalidUsage('Invalid Email')
    print("Email", email)
    user_repo = UserRepository()
    message = ''
    try:
        user = user_repo.get({'email': email})
        status = 1
        return {'status': status, 'sent': {}, 'message': 'The email has been registered.'}
    except NotFoundException as e:
        user = user_repo.reg_user(email, password)
        code = AuthcodesRepository().add_code(email)

    link = config['web']['login']
    text = "Dear customer,<br>" \
           'Please login with your registered email and password to the LegoExchanger: <a href="%s">login</a>.' % link

    mailer = MailGun(config['mailgun']['domain'], config['mailgun']['key'], 'LegoExchanger <alex@mrecorder.com>')
    try:
        sent = mailer.send_message(email, "Login to LegoExchanger", text)
        result = sent.json()
    except Exception as e:
        result = str(e)
        status = 2
    # return {'_code': code, 'sent': result}
    return {'status': status, 'sent': result, '_code': code, 'email': email}


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


@app.route('/icons', methods=['GET'], cors=True)
def get_icons():
    return {'icons':
        [
            'character.png',
            'emoticon.png',
            'emoticon_1.png',
            'emoticon_2.png',
            'emoticon_3.png',
            'face.png',
            'face_1.png',
            'face_10.png',
            'face_11.png',
            'face_12.png',
            'face_2.png',
            'face_3.png',
            'face_4.png',
            'face_5.png',
            'face_6.png',
            'face_7.png',
            'face_8.png',
            'face_9.png',
            'glasses.png',
            'glasses_2.png',
            'happy.png',
            'happy_1.png',
            'happy_2.png',
            'interface.png',
            'man.png',
            'man_1.png',
            'open.png',
            'people.png',
            'people_1.png',
            'people_2.png',
            'smiley.png',
            'ufo.png'
        ]
    }

