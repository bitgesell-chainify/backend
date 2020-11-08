import json
import os
import uuid
import boto3
import datetime
import time
import decimal
import base64
from urllib import request, parse
from boto3.dynamodb.conditions import Key, Attr
import utils


def send_code(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'phone', 'channel', 'locale'])

        phone = body['phone']
        channel = body['channel']
        locale = utils.correct_locale(body['locale'])

        account_sid = os.environ['TwilioAccountSid']
        auth_token = os.environ['TwilioAuthToken']
        verify_sid = os.environ['TwilioVerifySid']
        url = "https://verify.twilio.com/v2/Services/{}/Verifications"
        verify_url = url.format(verify_sid)

        post_params = {"To": phone, "Channel": channel, "Locale": locale}
        data = parse.urlencode(post_params).encode()
        req = request.Request(verify_url)

        authentication = "{}:{}".format(account_sid, auth_token)
        base64string = base64.b64encode(authentication.encode('utf-8'))
        req.add_header(
            "Authorization", "Basic %s" % base64string.decode('ascii'))

        res = None
        with request.urlopen(req, data) as f:
            res = str(f.read().decode('utf-8'))

    except Exception as error:
        return utils.bad_request(str(error))

    body = json.loads(res)
    return utils.json_response(body=body, status=201)


def check_code(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'phone', 'code'])

        phone = body['phone']
        code = body['code']

        account_sid = os.environ['TwilioAccountSid']
        auth_token = os.environ['TwilioAuthToken']
        verify_sid = os.environ['TwilioVerifySid']
        url = "https://verify.twilio.com/v2/Services/{}/VerificationCheck"
        verify_url = url.format(verify_sid)

        post_params = {"To": phone, "Code": code}
        data = parse.urlencode(post_params).encode()
        req = request.Request(verify_url)

        authentication = "{}:{}".format(account_sid, auth_token)
        base64string = base64.b64encode(authentication.encode('utf-8'))
        req.add_header(
            "Authorization", "Basic %s" % base64string.decode('ascii'))

        res = None
        with request.urlopen(req, data) as f:
            res = str(f.read().decode('utf-8'))

    except Exception as error:
        return utils.bad_request(str(error))

    body = json.loads(res) if res else None
    return utils.json_response(body=body, status=201)
