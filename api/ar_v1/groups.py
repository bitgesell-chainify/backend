import json
import os
import uuid
import boto3
import datetime
import time
import decimal
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import utils


def create_group(event, context):
    try:
        body = utils.validate_params(event, [
            'body',
            'name',
            'members',
            'orgRef'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        group_id = str(uuid.uuid4())
        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        org_item = {
            'PK': body['orgRef'],
            'SK': 'GROUP#{0}'.format(group_id),
            'name': body['name']
        }

        with table.batch_writer() as batch:
            batch.put_item(Item=org_item)
            for member in body['members']:
                member_item = {
                    'PK': 'GROUP#{0}'.format(group_id),
                    'SK': member,
                    'role': 'Student'
                }
                batch.put_item(Item=member_item)

        res = {
            'PK': body['orgRef'],
            'SK': 'GROUP#{0}'.format(group_id),
            'name': body['name'],
            'members': body['members']
        }

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=res, status=201)


def get_group(event, context):
    try:
        params = utils.validate_params(event, ['pathParameters', 'groupId'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        group_id = params['groupId']
        group = get_group_by_id(table, group_id)
        if group:
            members = get_group_members(table, group_id)
            group['members'] = members

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=group, status=200)


def get_group_by_id(table, group_id):
    group_ref = 'GROUP#{}'.format(group_id)
    group = table.query(
        IndexName='SortByPK',
        KeyConditionExpression=Key('SK').eq(group_ref)
        & Key('PK').begins_with('ORG')
    )
    body = group['Items'][0] if len(group['Items']) else None
    return body


def get_group_members(table, group_id):
    group_ref = 'GROUP#{}'.format(group_id)
    members = table.query(
        KeyConditionExpression=Key('PK').eq(group_ref)
        & Key('SK').begins_with('USER')
    )

    return members['Items']
