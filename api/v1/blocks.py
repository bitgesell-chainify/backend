import json
import os
import uuid
import boto3
import datetime
import time
import decimal
import base64
from urllib import request, parse
import boto3
import utils
from boto3.dynamodb.conditions import Key, Attr


def get_last_saved_block_height(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('BitgesellDB')

        response = table.query(
            IndexName='ByHeight',
            KeyConditionExpression=Key('partition').eq('block')
            & Key('height').gte(1),
            ScanIndexForward=False,
            Limit=1
        )

        height = response['Items'][0]['height'] if len(response['Items']) > 0 else None

        body = {
            "height": height
        }

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def fix_tx_heights(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('BitgesellDB')

        response = table.query(
            IndexName='ByHeight',
            KeyConditionExpression=Key('partition').eq('block')
            & Key('height').gte(1),
            ScanIndexForward=False,
            Limit=4
        )

        blocks = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='ByHeight',
                KeyConditionExpression=Key('partition').eq('block')
                & Key('height').gte(1),
                ScanIndexForward=False,
                ExclusiveStartKey=response['LastEvaluatedKey']

            )

            blocks += response['Items']

        for block in blocks:
            for tx in block['txs']:
                tx_pk = 'TX#{}'.format(tx)
                res_vins = table.query(
                    KeyConditionExpression=Key('PK').eq(tx_pk)
                    & Key('SK').begins_with('VIN#')
                )

                vins = res_vins['Items']

                while 'LastEvaluatedKey' in res_vins:
                    res_vins = table.query(
                        KeyConditionExpression=Key('PK').eq(tx_pk)
                        & Key('SK').begins_with('VIN#'),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )

                    vins += res_vins['Items']

                res_vouts = table.query(
                    KeyConditionExpression=Key('PK').eq(tx_pk)
                    & Key('SK').begins_with('VOUT#')
                )

                vouts = res_vouts['Items']

                while 'LastEvaluatedKey' in res_vouts:
                    res_vouts = table.query(
                        KeyConditionExpression=Key('PK').eq(tx_pk)
                        & Key('SK').begins_with('VOUT#'),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )

                    vouts += res_vouts['Items']

                asd = []
                els = vins + vouts
                for el in els:
                    el['height'] = block['height']
                    # print(el)
                    asd.append(el)
                    # table.put_item(Item=el)

            blocks += response['Items']

        body = {
            "txs": asd
        }

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)
