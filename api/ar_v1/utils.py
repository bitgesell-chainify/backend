import json
import decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o)
        if isinstance(o, set):
            return list(o)
        return super(DecimalEncoder, self).default(o)


def json_response(body, status):
    return {
        'statusCode': status,
        'headers': {
            "Access-Control-Allow-Origin": "*"
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def bad_request(error):
    response = json.dumps({
        'error': 'bad request',
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'message': error
    })
    return {'statusCode': 400, 'body': response}


def validate_params(event, params):
    invalid_params = []
    data_item = params.pop(0)
    if data_item not in event:
        invalid_params.append(data_item)

    if not data_item:
        invalid_params.append(data_item)

    if len(invalid_params) == 0 and data_item:
        while len(params) > 0:
            param = params.pop(0)
            if param not in event[data_item]:
                invalid_params.append(param)

    if len(invalid_params) > 0:
        raise Exception('Error while parsing reauired params: {0}'.format(
            ', '.join(invalid_params)))

    if data_item == 'body':
        body = event['body']
        if isinstance(body, str):
            body = json.loads(body)
        return body

    if data_item == 'pathParameters':
        params = event['pathParameters']
        if isinstance(params, str):
            params = json.loads(params)
        return params

    if data_item == 'queryStringParameters':
        return event['queryStringParameters']


def correct_locale(locale):
    locale = locale.lower()
    conversions = {
        'cz': 'cs',
        'cn': 'zh-CN',
        'jp': 'ja',
        'dk': 'da',
        'gr': 'el',
        'il': 'he',
        'in': 'hi',
        'no': 'nb',
        'br': 'pt-BR',
        'kp': 'ko',
        'kr': 'ko',
        'gb': 'en',
        'us': 'en'
    }

    supported_locales = [
        'af', 'ar', 'ca', 'zh', 'zh-CN', 'zh-HK', 'hr', 'cs', 'da',
        'nl', 'en', 'en-GB', 'fi', 'fr', 'de', 'el', 'he', 'hi', 'hu',
        'id', 'it', 'ja', 'ko', 'ms', 'nb', 'pl', 'pt-BR', 'pt', 'ro',
        'ru', 'es', 'sv', 'tl']

    if locale in conversions:
        locale = conversions[locale]

    if locale not in supported_locales:
        locale = 'en'

    return locale
