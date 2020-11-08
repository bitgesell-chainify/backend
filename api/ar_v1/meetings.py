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


def create_meeting(event, context):
    try:
        body = utils.validate_params(
            event,
            ['body', 'externalMeetingId'])

        client = boto3.client('chime')
        response = client.create_meeting(
            ClientRequestToken=body['externalMeetingId'],
            ExternalMeetingId=body['externalMeetingId'],
            MediaRegion=event['stageVariables']['REGION_NAME']
        )

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=response, status=201)


def get_meeting(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'meetingId'])

        client = boto3.client('chime')
        response = client.get_meeting(
            MeetingId=params['meetingId']
        )

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=response, status=200)


def create_attendee(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'meetingId'])

        body = utils.validate_params(
            event,
            ['body', 'attendeeId'])

        client = boto3.client('chime')
        response = client.create_attendee(
            MeetingId=params['meetingId'],
            ExternalUserId=body['attendeeId']
        )

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=response, status=201)


def get_attendee(event, context):
    try:
        params = utils.validate_params(
            event,
            ['pathParameters', 'meetingId', 'attendeeId'])

        client = boto3.client('chime')
        response = client.get_attendee(
            MeetingId=params['meetingId'],
            AttendeeId=params['attendeeId']
        )

    except Exception as error:
        return utils.bad_request(str(error))

    return utils.json_response(body=response, status=200)
