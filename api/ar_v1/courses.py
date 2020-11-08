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


def create_course(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'name', 'description', 'authorRef'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        course_id = str(uuid.uuid4())
        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        alias = body['name'].replace(' ', '-').lower()
        course_alias = 'ALIAS#{0}'.format(alias)

        course = get_course_by_alias(table, course_alias)
        if course:
            return utils.bad_request(
                'Alias in not unique: {}'.format(alias))

        course_item = {
            'PK': body['authorRef'],
            'SK': 'COURSE#{0}'.format(course_id),
            'name': body['name'],
            'description': body['description'],
            'isActive': False,
            'alias': alias,
            'courseAlias': course_alias,
            'introVideoLink': None,
            'createdAt': utc_time
        }
        with table.batch_writer() as batch:
            batch.put_item(Item=course_item)

    except Exception as error:
        return utils.bad_request(str(error))

    body = course_item
    return utils.json_response(body=body, status=201)


def get_courses(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        response = table.scan(
            FilterExpression=Attr("PK").begins_with('ORG') &
            Attr("SK").begins_with('COURSE'))
        body = response['Items']
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_course(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'courseIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        course_id_or_alias = urllib.parse.unquote(params['courseIdOrAlias'])
        body_by_alias = get_course_by_alias(table, course_id_or_alias)
        body_by_course_id = get_course_by_id(table, course_id_or_alias)
        body = body_by_alias or body_by_course_id

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_course_by_alias(table, alias):
    alias = f'ALIAS#{alias}'
    response = table.query(
        IndexName='CourseAlias',
        KeyConditionExpression=Key('courseAlias').eq(alias)
    )

    body = response['Items'][0] if len(response['Items']) > 0 else None
    return body


def get_course_by_id(table, course_id):
    course_ref = 'COURSE#{0}'.format(course_id)
    response = table.query(
        IndexName='SortByPK',
        KeyConditionExpression=Key('SK').eq(course_ref)
        & Key('PK').begins_with('ORG')
    )

    body = response['Items'][0] if len(response['Items']) > 0 else None
    return body


def get_organization_courses(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'orgIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        org_id_or_alias = urllib.parse.unquote(params['orgIdOrAlias'])
        body = get_courses_by_org_id(table, org_id_or_alias)

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_courses_by_org_id(table, org_id):
    org_ref = 'ORG#{}'.format(org_id)
    response = table.query(
        KeyConditionExpression=Key('PK').eq(org_ref) &
        Key('SK').begins_with('COURSE')
    )
    body = response['Items']
    return body


def create_course_teacher(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'userRef'])

        params = utils.validate_params(
            event,
            ['pathParameters', 'courseIdOrAlias'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        course_ref = event['pathParameters']['courseIdOrAlias']
        course_ref = urllib.parse.unquote(course_ref)
        course_by_alias = get_course_by_alias(table, course_ref)
        course_by_id = get_course_by_id(table, course_ref)
        course = course_by_alias or course_by_id

        if not course:
            return utils.bad_request('Course not found')

        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        teacher_item = {
            'PK': course['SK'],
            'SK': '{}#ROLE#Teacher'.format(body['userRef']),
            'createdAt': utc_time,
            'courseTeacher': body['userRef']
        }
        with table.batch_writer() as batch:
            batch.put_item(Item=teacher_item)

    except Exception as error:
        return utils.bad_request(str(error))

    body = teacher_item
    return utils.json_response(body=body, status=201)
