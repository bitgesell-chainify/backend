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


def create_class(event, context):
    try:
        body = utils.validate_params(
            event,
            [
                'body',
                'title',
                'startsAt',
                'duration',
                'capacity',
                'courseRef'
            ])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        class_id = str(uuid.uuid4())
        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        item = {
            'PK': body['courseRef'],
            'SK': 'CLASS#{0}'.format(class_id),
            'title': body['title'],
            'classStartsAt': body['startsAt'],
            'classEndsAt': body['startsAt'] + body['duration'],
            'capacity': body['capacity'],
            'createdAt': utc_time
        }
        classes = [item]

        if 'repeat' in body and 'endRepeat' in body:
            repeat = body['repeat']

            start = datetime.datetime.fromtimestamp(body['startsAt'])
            end = datetime.datetime.fromtimestamp(body['endRepeat'])

            if repeat == 'daily':
                delta = datetime.timedelta(days=1)

            if repeat == 'weekly':
                delta = datetime.timedelta(days=7)

            if repeat == 'monthly':
                delta = datetime.timedelta(months=1)

            if repeat == 'yearly':
                delta = datetime.timedelta(years=1)

            starts_at = start + delta
            while starts_at <= end:
                class_item = item.copy()
                class_item['SK'] = 'CLASS#{}'.format(str(uuid.uuid4()))
                class_starts_at = int(time.mktime(starts_at.timetuple()))
                class_ends_at = class_starts_at + body['duration']
                class_item['classStartsAt'] = class_starts_at
                class_item['classEndsAt'] = class_ends_at
                classes.append(class_item)
                starts_at += delta

        with table.batch_writer() as batch:
            for class_item in classes:
                batch.put_item(Item=class_item)

                if body['participants']:
                    for participant in body['participants']:

                        user_ref = participant['userRef']
                        role = participant['role']
                        participant_item = {
                            'PK': class_item['SK'],
                            'SK': user_ref,
                            'classEndsAt': class_item['classEndsAt'],
                            'role': role,
                            'createdAt': utc_time
                        }
                        batch.put_item(Item=participant_item)

    except Exception as error:
        return utils.bad_request(str(error))

    # class_item['students'] = 0
    return utils.json_response(body=classes, status=201)


def fix(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        course_ref = 'COURSE#6639d714-c75f-430b-935a-de4bfb1b9009'
        classes = table.query(
            KeyConditionExpression=Key('PK').eq(course_ref) &
            Key('SK').begins_with('CLASS')
        )

        # with table.batch_writer() as batch:
        #     for class_item in classes['Items']:
        #         class_starts_at = class_item['classStartsAt'] - 10800
        #         class_ends_at = class_item['classEndsAt'] - 10800

        #         class_item['classStartsAt'] = class_starts_at
        #         class_item['classEndsAt'] = class_ends_at

        #         batch.put_item(Item=class_item)

        #         participants = table.query(
        #             KeyConditionExpression=Key('PK').eq(class_item['SK']) &
        #             Key('SK').begins_with('USER')
        #         )

        #         for participant in participants['Items']:
        #             participant.pop('classStartsAt', None)
        #             participant['classEndsAt'] = class_ends_at
        #             batch.put_item(Item=participant)
        body = []
    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_classes(event, context):
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        response = table.scan(
            FilterExpression=Attr("PK").begins_with('COURSE') &
            Attr("SK").begins_with('CLASS'))
        body = response['Items']

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_class(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'classId'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        class_id_or_alias = params['classId']
        body = get_class_by_id(table, class_id_or_alias)

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)


def get_class_by_id(table, class_id):
    class_ref = f'CLASS#{class_id}'
    response = table.query(
        IndexName='SortByPK',
        KeyConditionExpression=Key('SK').eq(class_ref) &
        Key('PK').begins_with('COURSE')
    )

    body = response['Items'][0] if len(response['Items']) > 0 else None
    return body


def get_course_classes(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'courseIdOrAlias'])

        today = datetime.datetime.utcnow().date()
        utc_time = int(time.mktime(today.timetuple()))

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')
        course_id_or_alias = urllib.parse.unquote(params['courseIdOrAlias'])
        classes = get_classes_by_course_id(
            table,
            course_id_or_alias,
            gte=utc_time)

        for i, el in enumerate(classes):
            class_id = el['SK'].replace('CLASS#', '')
            students = get_class_students(table, class_id)
            classes[i]['students'] = students

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=classes, status=200)


def get_classes_by_course_id(table, course_id, gte):
    course_ref = f'COURSE#{course_id}'
    response = table.query(
        IndexName='ClassStartsAt',
        KeyConditionExpression=Key('PK').eq(course_ref) &
        Key('classStartsAt').gte(gte)
    )
    body = response['Items']
    return body


def join_class(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'classId'])

        body = utils.validate_params(
            event,
            [
                'body',
                'role',
                'userId'
            ])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        utc_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        class_id = event['pathParameters']['classId']
        class_ref = 'CLASS#{}'.format(class_id)
        class_data = get_class_by_id(table, class_id)

        starts_at = int(class_data['classStartsAt'])
        duration = int(class_data['duration'])
        active_unlit = starts_at + duration

        user_ref = 'USER#{}'.format(body['userId'])
        class_item = {
            'PK': class_ref,
            'SK': user_ref,
            'participantRole': body['role'],
            'classActiveUntil': active_unlit,
            'createdAt': utc_time
        }

        students = get_class_students(table, class_id)

        if class_data['capacity'] and len(students) >= class_data['capacity']:
            return utils.bad_request('CLASS_ERROR_CAPACITY_EXCEEDED')

        with table.batch_writer() as batch:
            batch.put_item(Item=class_item)

    except Exception as error:
        return utils.bad_request(str(error))

    class_item['students'] = students.append(class_item)

    return utils.json_response(body=class_item, status=201)


def get_class_students(table, class_id):
    class_ref = f'CLASS#{class_id}'
    response = table.query(
        KeyConditionExpression=Key('PK').eq(class_ref) &
        Key('SK').begins_with('USER'),
        FilterExpression=Attr('participantRole').eq('Student')
    )

    return response['Items']


def is_user_authorized_to_participate(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'classId', 'userId'])

        dynamodb = boto3.resource(
            'dynamodb',
            region_name=event['stageVariables']['REGION_NAME'])
        table = dynamodb.Table('ObraLab')

        class_id = params['classId']
        user_id = params['userId']

        response = table.query(
            KeyConditionExpression=Key('PK').eq(f'CLASS#{class_id}') &
            Key('SK').eq(f'USER#{user_id}')
        )
        body = response['Items']

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=body, status=200)
