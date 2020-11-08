import os
import sys
from sanic import Blueprint
from sanic.response import json
from sanic.log import logger
import asyncio
import aiohttp
import requests
from requests.auth import HTTPBasicAuth
import json as pjson
import hashlib
from datetime import datetime
from time import time
from .errors import bad_request
import configparser
import uuid
import signal
import base58
from termcolor import colored
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal


config = configparser.ConfigParser()
config.read('config.ini')

parser = Blueprint('parser_v1', url_prefix='/parser')


class Parser:
    def __init__(self):

        node_url = '{}:{}'.format(
            os.environ['NODE_URL'],
            os.environ['NODE_PORT'])
        node_auth = HTTPBasicAuth(
            os.environ['NODE_USER'],
            os.environ['NODE_PASSWORD'])
        self.node_url = node_url
        self.node_auth = node_auth

        self.height = 1
        self.last_block = None
        self.step = 5
        self.blocks_to_check = 20

        self.batch_blocks = []
        self.batch_transactions = []
        self.vouts = {}

        self.vouts_last_key = None
        self.vouts_collected = False

    async def emergency_stop_loop(self, title, error):
        logger.info('Emergency loop stop request')
        logger.info('Reason: {}'.format(error))
        logger.info('Closing tasks')
        for task in asyncio.Task.all_tasks():
            task.cancel()

        logger.info('Stopping loop')
        loop = asyncio.get_running_loop()
        loop.stop()
        return bad_request(error)

    async def get_block_hashes(self, height, session):
        try:
            async with session.post(
                self.node_url,
                json={
                    'jsonrpc': '1.0',
                    'id': 'curltext',
                    'method': 'getblockhash',
                    'params': [height]
                },
                auth=aiohttp.BasicAuth(
                    os.environ['NODE_USER'],
                    os.environ['NODE_PASSWORD'])
                    ) as response:
                data = await response.json()
                block_hash = data['result']

            await self.get_block_data(height, block_hash, session)

        except asyncio.CancelledError:
            logger.info('Parser has been stopped')
            raise
        except Exception as error:
            logger.error('Fetching data error: {}'.format(error))

    async def get_block_data(self, height, block_hash, session):
        try:
            async with session.post(
                self.node_url,
                json={
                    'jsonrpc': '1.0',
                    'id': 'curltext',
                    'method': 'getblock',
                    'params': [block_hash, 2]
                },
                auth=aiohttp.BasicAuth(
                    os.environ['NODE_USER'],
                    os.environ['NODE_PASSWORD'])
                    ) as response:
                data = await response.json()
                block_data = data['result']
                block_txs = []
                for tx in block_data['tx']:
                    tx['time'] = block_data['time']
                    tx['height'] = block_data['height']
                    block_txs.append(tx['txid'])
                    self.batch_transactions.append(tx)

                block_data['tx'] = block_txs
                self.batch_blocks.append(block_data)

        except asyncio.CancelledError:
            logger.info('Parser has been stopped')
            raise
        except Exception as error:
            logger.error('Fetching data error: {}'.format(error))

    async def get_vout(self, tx_id, vout):
        url = 'https://bitgesell.amrbz.org/v1/tx/{}/vout/{}'.format(
            tx_id,
            vout
        )
        res = requests.get(
            url,
            headers={"x-api-key": "Ty1HRTEuG57HVWFta94j37FCO8X9D43A2ftOoG4y"}
        )
        return True

    async def save_data(self):
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name='eu-central-1')
            table = dynamodb.Table('BitgesellDB')

            batch_blocks_items = []
            batch_transactions_vins = []
            batch_transactions_vouts = []

            for block in self.batch_blocks:
                item = {
                    'PK': 'BLOCK#{}'.format(block['hash']),
                    'SK': '#PROFILE#{}'.format(block['hash']),
                    'height': int(block['height']),
                    # 'raw': pjson.dumps(block),
                    'txs': block['tx'],
                    'partition': 'block'
                }

                batch_blocks_items.append(item)

            for tx in self.batch_transactions:
                for vout in tx['vout']:
                    script_pub_key = vout['scriptPubKey']
                    address = None
                    if 'addresses' in script_pub_key:
                        address = script_pub_key['addresses'][0]

                    if address:
                        vout_id = 'TX#{}#VOUT#{}'.format(
                            tx['txid'],
                            vout['n'])

                        # value = str(round(vout['value'], 8))
                        value = int(round(vout['value'] * 100000000, 0))

                        self.vouts[vout_id] = {
                            'address': address,
                            'value': value
                        }

                        batch_transactions_vouts.append({
                            'PK': 'TX#{}'.format(tx['txid']),
                            'SK': 'VOUT#{}'.format(vout['n']),
                            'value': value,
                            'address': address,
                            'timestamp': tx['time'],
                            'height': tx['height'],
                            'partition': 'transaction'
                        })

            for tx in self.batch_transactions:
                for vin in tx['vin']:
                    if 'coinbase' in vin:
                        batch_transactions_vins.append({
                            'PK': 'TX#{}'.format(tx['txid']),
                            'SK': 'VIN#COINBASE',
                            'height': tx['height']
                        })
                    else:
                        vout_id = 'TX#{}#VOUT#{}'.format(
                            vin['txid'],
                            vin['vout'])

                        vout = self.vouts[vout_id]

                        batch_transactions_vins.append({
                            'PK': 'TX#{}'.format(tx['txid']),
                            'SK': 'VIN#TX#{}#VOUT#{}'.format(
                                vin['txid'],
                                vin['vout']),
                            'address': vout['address'],
                            'value': vout['value'],
                            'timestamp': tx['time'],
                            'height': tx['height'],
                            'partition': 'transaction'
                        })

            with table.batch_writer() as batch:
                for item in batch_blocks_items:
                    batch.put_item(Item=item)

                for item in batch_transactions_vins:
                    batch.put_item(Item=item)

                for item in batch_transactions_vouts:
                    batch.put_item(Item=item)

        except asyncio.CancelledError:
            logger.info('Parser has been stopped')
            raise
        except Exception as error:
            logger.info('Height: {}'.format(self.height))
            logger.error('Batch insert error: {}'.format(error))
            await self.emergency_stop_loop('Batch insert error', error)
        finally:
            self.batch_blocks = []
            self.batch_transactions = []

    async def get_blockchain_height(self):
        try:
            req = requests.post(
                self.node_url,
                json={
                    'jsonrpc': '1.0',
                    'id': 'curltext',
                    'method': 'getblockcount',
                    'params': []
                },
                auth=self.node_auth)

            data = req.json()
            height = int(data['result'])
        except Exception as error:
            logger.error('Blockchain height request error: {}'.format(error))
            raise

        return height

    async def get_last_saved_block_height(self):
        try:
            res = requests.get(
                'https://bitgesell.amrbz.org/v1/utils/last-saved-block-height',
                headers={
                    'x-api-key': 'Ty1HRTEuG57HVWFta94j37FCO8X9D43A2ftOoG4y'
                })
            last_block = res.json()
            height = last_block['height'] if last_block else None

        except Exception as error:
            logger.error('Blockchain height request error: {}'.format(error))
            raise

        return height

    async def collect_vouts(self):
        logger.info('Clollectiong vouts....')
        data = await self.get_vouts(last_key=None)

        await self.save_vouts(data['vouts'])

        while 'LastEvaluatedKey' in data:
            data = await self.get_vouts(last_key=data['LastEvaluatedKey'])
            if 'vouts' in data:
                await self.save_vouts(data['vouts'])
            else:
                print('ERR', data)
            # ERR {'error': 'bad request', 'headers': {'Access-Control-Allow-Origin': '*'}, 'message': "'LastEvaluatedKey'"}
        self.vouts_collected = True
        logger.info('Vouts successfully collected!')

    async def get_vouts(self, last_key):
        try:
            res = requests.get(
                'https://bitgesell.amrbz.org/v1/utils/vouts',
                json={
                    'LastEvaluatedKey': last_key,
                    'limit': 50000
                },
                headers={
                    'x-api-key': 'Ty1HRTEuG57HVWFta94j37FCO8X9D43A2ftOoG4y'
                })
            data = res.json()
        except Exception as error:
            logger.error('Blockchain height request error: {}'.format(error))
            raise

        return data

    async def save_vouts(self, vouts):
        # logger.info('Saving vouts: {}'.format(len(vouts)))

        for vout in vouts:
            vout_id = '{}#{}'.format(vout['PK'], vout['SK'])
            self.vouts[vout_id] = {
                'address': vout['address'],
                'value': vout['value']
            }
        logger.info('Saved vouts batch: {} of {}'.format(
            len(vouts),
            len(self.vouts.keys())
        ))

    async def start(self):
        # logger.info('Fetching cache data...')
        blockchain_height = await self.get_blockchain_height()
        last_saved_block_height = await self.get_last_saved_block_height()

        while not self.vouts_collected:
            await asyncio.sleep(2)

        if blockchain_height:
            self.height = max(1, blockchain_height - self.blocks_to_check)

        start_height = int(os.environ['START_HEIGHT'])

        if self.height > start_height:
            self.height = start_height

        if last_saved_block_height:
            self.height = max(
                1,
                last_saved_block_height - self.blocks_to_check)

        logger.info('START HIGHT: {}'.format(self.height))

        while True:
            try:
                last_block = await self.get_blockchain_height()
                self.last_block = last_block

        #         if self.height > self.last_block:
        #             # DELETE TRANSACTI~ONS AND BLOCKS FROM DB
        #             pass
        # #         with conn:
        # #             with conn.cursor() as cur:
        # #                 if self.height > self.last_block:
        # #                     cur.execute("""
        # #                         DELETE FROM transactions WHERE height > '{height}'
        # #                     """.format(
        # #                         height=self.last_block
        # #                     ))
        # #                     self.height = self.last_block
        # #                     conn.commit()

            except Exception as error:
                await self.emergency_stop_loop('Loop error:', error)

            logger.info('Parsing range: {} - {}'.format(
                self.height,
                self.last_block))
            logger.info('-' * 40)
            try:

                logger.info('PARSING DATA')
                async with aiohttp.ClientSession() as session:
                    try:
                        while self.height < self.last_block:
                            t0 = time()
                            batch = self.height + self.step
                            if self.height + self.step >= self.last_block:
                                batch = self.last_block + 1

                            batch_range = (self.height, batch)
                            tasks = []
                            for h in range(batch_range[0], batch_range[1]):
                                task = asyncio.create_task(self.get_block_hashes(
                                    h,
                                    session))
                                tasks.append(task)
                                self.height += 1
                            logger.info('Height range {0} - {1}'.format(
                                batch_range[0],
                                batch_range[1] - 1))
                            await asyncio.gather(*tasks)
                            await self.save_data()
                            logger.info('Parsing time: {0} sec'.format(
                                time() - t0))
                            logger.info('-' * 40)

                    except asyncio.CancelledError:
                        logger.info('Parser stopping...')
                        raise
                    except Exception as error:
                        logger.error('HEIGHT: {} Parsing error: {}: '.format(
                            self.height,
                            error))
                        await self.emergency_stop_loop('Parsing error', error)

            except asyncio.CancelledError:
                logger.info('Parser has been stopped')
                raise
            except Exception as error:
                await self.emergency_stop_loop('Request blocks cycle', error)
            finally:
                self.height = max(1, self.height - self.blocks_to_check)
                await asyncio.sleep(60)


controls = Parser()


@parser.listener('after_server_start')
def autostart(app, loop):
    loop.create_task(controls.collect_vouts())
    loop.create_task(controls.start())
    logger.info('Autostart Success!')
    # logger.info('CDM Version: {0}'.format(os.environ['CDM_VERSION']))


@parser.listener('after_server_stop')
def gentle_exit(app, loop):
    logger.info('Killing the process')
    os.kill(os.getpid(), signal.SIGKILL)


@parser.route('/healthcheck', methods=['GET'])
def container_healthcheck(request):
    return json({"action": "healthcheck", "status": "OK"})
