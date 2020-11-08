import json
import os
import re
import uuid
import boto3
import datetime
import time
import decimal
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import classes
import utils


def create_user(event, context):
    try:
        body = utils.validate_params(event, [
            'body',
            'firstName',
            'lastName',
            'defaultPhone'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        user = get_user_by_default_phone(table, body['defaultPhone'])
        if user:
            return utils.bad_request('User is not unique: {}'.format(body['defaultPhone']))

        user_id = str(uuid.uuid4())
        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        user_item = {
            'PK': 'USER#{0}'.format(user_id),
            'SK': '#PROFILE#{0}'.format(user_id),
            'firstName': body['firstName'],
            'lastName': body['lastName'],
            'middleName': body['middleName'],
            'createdAt': utc_time,
            'defaultPhone': body['defaultPhone']
        }
        table.put_item(Item=user_item)
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=user_item, status=201)


def get_user(event, context):
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=event['stageVariables']['REGION_NAME'])
    table = dynamodb.Table('ObraLab')
    params = utils.validate_params(event, ['pathParameters', 'userRef'])

    try:
        user_ref = params['userRef']
        user_by_phone = get_user_by_default_phone(table, user_ref)
        user_by_user_id = get_user_by_id(table, user_ref)
        user = user_by_phone or user_by_user_id

        if user:
            user_ref = '{}#ROLE#Admin'.format(user['PK'])
            orgs = table.query(
                IndexName='SortByPK',
                KeyConditionExpression=Key('SK').eq(user_ref)
                & Key('PK').begins_with('ORG#')
            )

            admin_at = []
            for org in orgs['Items']:
                res = table.get_item(
                    Key={
                        'PK': org['PK'],
                        'SK': org['PK'].replace('ORG#', "#PROFILE#")
                    }
                )
                if res['Item']:
                    admin_at.append(res['Item'])

            user['adminAt'] = admin_at

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=user, status=200)


def get_user_by_id(table, user_id):
    user = table.get_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'#PROFILE#{user_id}'
        }
    )
    body = user['Item'] if 'Item' in user else None
    return body


def get_user_by_default_phone(table, default_phone):
    response = table.query(
        IndexName='UserByDefaultPhone',
        KeyConditionExpression=Key('defaultPhone').eq(default_phone)
    )
    body = response['Items'][0] if len(response['Items']) > 0 else None
    return body


def get_active_classes(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'userRef'])

        query_params = utils.validate_params(
            event,
            ['queryStringParameters', 'gte', 'lte'])

        now = datetime.datetime.utcnow()
        utc_time = int(time.mktime(now.timetuple()))

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        gte = int(query_params['gte']) if 'gte'in query_params else 1
        lte = int(query_params['lte']) if 'lte'in query_params else 9999999999

        user_ref = params['userRef']
        classes = query_active_classes(
            table,
            user_ref=f'USER#{user_ref}',
            gte=gte,
            lte=lte)

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=classes, status=200)


def query_active_classes(table, user_ref, gte, lte):
    query = table.query(
        IndexName='ClassEndsAt',
        KeyConditionExpression=Key('SK').eq(user_ref)
        & Key('classEndsAt').between(gte, lte)
    )

    body = []
    for item in query['Items']:
        class_id = item['PK'].replace('CLASS#', '')
        user_class = classes.get_class_by_id(table, class_id)

        participants = table.query(
            KeyConditionExpression=Key('PK').eq(item['PK']) &
            Key('SK').begins_with('USER')
        )

        teachers = []
        for participant in participants['Items']:
            if participant['role'] == 'Teacher':
                user_id = participant['SK'].replace('USER#', '')
                user = get_user_by_id(table, user_id)
                teachers.append(user)

        user_class['teachers'] = teachers
        user_class['role'] = item['role']
        body.append(user_class)

    return body


def update_user(event, context):
    try:
        body = utils.validate_params(event, [
            'body',
            'data'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        user = get_user_by_default_phone(table, body['data']['defaultPhone'])
        if not user:
            return utils.bad_request('User is not found: {}'.format(body['data']['defaultPhone']))

        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        user_item = body['data']
        table.put_item(Item=user_item)
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=user_item, status=201)


def update_user_login(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'userRef'])

        body = utils.validate_params(event, [
            'body',
            'geoData'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        user_id = params['userRef'].replace('USER#', '')
        user = get_user_by_id(table, user_id)
        if not user:
            return utils.bad_request('User is not found: {}'.format(user_id))

        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        geo_data = user['geoData'] or []
        geo_data.append(body['geoData'])
        user['geoData'] = geo_data
        table.put_item(Item=user)
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=user_item, status=201)
