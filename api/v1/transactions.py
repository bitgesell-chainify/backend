import json
import os
import re
import uuid
import boto3
import datetime
import time
import decimal
import base64
from urllib import request, parse
import boto3
import utils
import requests
from boto3.dynamodb.conditions import Key, Attr
from requests.auth import HTTPBasicAuth


def send_raw_transaction(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'hexstring'])

        hexstring = body['hexstring']

        params = {
            'jsonrpc': '1.0',
            'id': 'curltext',
            'method': 'sendrawtransaction',
            'params': [hexstring]
        }
        response = requests.post(
            'http://161.35.123.34:8332',
            json=params,
            auth=HTTPBasicAuth('bgl_user', '12345678')
        )

        # print('response', response, response.content, response.status_code)

        data = response.json()

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=data, status=200)


def get_vouts(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('BitgesellDB')

        body = utils.validate_params(event, ['body', 'LastEvaluatedKey', 'limit'])

        LastEvaluatedKey = body['LastEvaluatedKey']

        if LastEvaluatedKey:
            response = table.scan(
                FilterExpression=Attr("PK").begins_with('TX#') &
                Attr("SK").begins_with('VOUT#'),
                Limit=body['limit'],
                ExclusiveStartKey=LastEvaluatedKey
            )
        else:
            response = table.scan(
                FilterExpression=Attr("PK").begins_with('TX#') &
                Attr("SK").begins_with('VOUT#'),
                Limit=body['limit']
            )

        vouts = response['Items']

        # while 'LastEvaluatedKey' in response:
        #     response = table.scan(
        #         FilterExpression=Attr("PK").begins_with('TX#') &
        #         Attr("SK").begins_with('VOUT#'),
        #         ExclusiveStartKey=response['LastEvaluatedKey']
        #     )

        #     vouts += response['Items']

        body = {'vouts': response['Items']}

        if 'LastEvaluatedKey' in response:
            body['LastEvaluatedKey'] = response['LastEvaluatedKey']

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_transactions_by_address(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('BitgesellDB')

        params = utils.validate_params(event, ['pathParameters', 'address'])

        response = table.query(
            IndexName='ByAddress',
            KeyConditionExpression=Key('address').eq(params['address'])
            & Key('timestamp').gt(1),
            ScanIndexForward=False
        )

        txs = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='ByAddress',
                KeyConditionExpression=Key('address').eq(params['address'])
                & Key('timestamp').gt(1),
                ScanIndexForward=False,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )

            txs += response['Items']

        balance = 0
        for tx in txs:
            # if tx['address'] == params['address']:
            #     continue

            if re.match(r"^VIN", tx['SK']):
                balance += tx['value']

            if re.match(r"^VOUT", tx['SK']):
                balance -= tx['value']

        body = {
            'txs': txs,
            'balance': abs(balance)
        }

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)
