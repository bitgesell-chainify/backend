import json
import os
import uuid
import boto3
import datetime
import time
import decimal
import urllib.parse
from boto3.dynamodb.conditions import Key, Attr
import utils
import users


def validate_stage_variables(func):
    def func_wrapper(event, context):
        print('EVENT', event)
        return utils.validate_params(
            event,
            ['stageVariables', 'REGION_NAME'])
    return func_wrapper


def create_organization(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'name', 'description', 'adminRef', 'alias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        org_id = str(uuid.uuid4())
        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        alias = body['alias']
        org = get_organization_by_alias(table, alias)
        if org:
            return utils.bad_request(
                'Alias in not unique: {}'.format(alias))

        organization_item = {
            'PK': 'ORG#{0}'.format(org_id),
            'SK': '#PROFILE#{0}'.format(org_id),
            'alias': alias,
            'organizationAlias':
                'ALIAS#{}'.format(alias.lower()),
            'name': body['name'],
            'description': body['description'],
            'createdAt': utc_time,
            'introVideoLink': None
        }
        organization_admin = {
            'PK': 'ORG#{0}'.format(org_id),
            'SK': '{}#ROLE#Admin'.format(body['adminRef']),
            'createdAt': utc_time
        }
        with table.batch_writer() as batch:
            batch.put_item(Item=organization_item)
            batch.put_item(Item=organization_admin)

    except Exception as error:
        return utils.bad_request(str(error))

    body = {
        'organization': organization_item,
        'admin': organization_admin
    }

    return utils.json_response(body=body, status=201)


def get_organizations(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        response = table.scan(
            FilterExpression=Attr("PK").begins_with('ORG') &
            Attr("SK").begins_with('#PROFILE'))
        body = response['Items']
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


# @validate_stage_variables
def get_organization(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'orgIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        org_id_or_alias = urllib.parse.unquote(
            event['pathParameters']['orgIdOrAlias'])
        body_by_alias = get_organization_by_alias(table, org_id_or_alias)
        body_by_ref = get_organization_by_ref(table, org_id_or_alias)
        body = body_by_alias or body_by_ref

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_organization_by_alias(table, alias):
    alias = alias.lower()
    response = table.query(
        IndexName='OrganizationAlias',
        KeyConditionExpression=Key('organizationAlias').eq(f'ALIAS#{alias}')
    )

    body = response['Items'][0] if len(response['Items']) > 0 else None
    return body


def get_organization_by_ref(table, org_id):
    response = table.get_item(
        Key={
            'PK': f'ORG#{org_id}',
            'SK': f'#PROFILE#{org_id}'
        }
    )
    body = response['Item'] if 'Item' in response else None
    return body


def create_organization_teacher(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'userRef'])

        params = utils.validate_params(
            event,
            ['pathParameters', 'orgIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        org_ref = event['pathParameters']['orgIdOrAlias']
        org_id_or_alias = urllib.parse.unquote(org_ref)
        org_by_alias = get_organization_by_alias(table, org_id_or_alias)
        org_by_ref = get_organization_by_ref(table, org_id_or_alias)
        org = org_by_alias or org_by_ref

        if not org:
            error = 'Organization not found: {}'.format(org_ref)
            return utils.bad_request(error)

        teacher_item = {
            'PK': org['PK'],
            'SK': '{}#ROLE#Teacher'.format(body['userRef']),
            'createdAt': utc_time
        }
        with table.batch_writer() as batch:
            batch.put_item(Item=teacher_item)

    except Exception as error:
        return utils.bad_request(str(error))

    body = teacher_item
    return utils.json_response(body=body, status=201)


def get_organization_teachers(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'orgIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        org_ref = event['pathParameters']['orgIdOrAlias']
        org_id_or_alias = urllib.parse.unquote(org_ref)
        org_by_alias = get_organization_by_alias(table, org_id_or_alias)
        org_by_ref = get_organization_by_ref(table, org_id_or_alias)
        org = org_by_alias or org_by_ref

        if not org:
            error = 'Organization not found: {}'.format(org_ref)
            return utils.bad_request(error)

        teachers = table.scan(
            FilterExpression=Attr("PK").eq(org['PK'])
            & Attr('SK').contains('#Teacher')
        )
        body = []
        for teacher in teachers['Items']:
            user_id = teacher['SK'] \
                .replace('USER#', '') \
                .replace('#ROLE#Teacher', '')

            user = users.get_user_by_id(table, user_id)
            body.append(user)

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)
