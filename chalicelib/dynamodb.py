from typing import Dict
import boto3
from boto3.dynamodb.conditions import Key
import json

from chalicelib.exceptions import NotFoundException, DuplicateItem
from botocore.exceptions import ClientError


class DynamoDb:
    def __init__(self, table):
        self.dynamo_db = boto3.resource('dynamodb', region_name='us-west-2')
        self.table = self.dynamo_db.Table(table)
        pass

    def get_item(self, query: Dict)->Dict:
        response = self.table.get_item(Key=query)

        if 'Item' in response:
            return response['Item']
        raise NotFoundException("Not found " + json.dumps(query))

    def query(self, key, value, index=None, limit=0, key_sort=None, value_sort=None):
        key_condition = Key(key).eq(value)
        if key_sort is not None:
            key_condition &= Key(key_sort).eq(value_sort)
        params = {
            'KeyConditionExpression': key_condition,
            'ScanIndexForward': True
        }
        if index is not None:
            params['IndexName'] = index
        if limit > 0:
            params['Limit'] = limit
        return self.table.query(**params)

    def insert_item(self, item, uniq_attribute=None):
        if uniq_attribute is None:
            self.table.put_item(Item=item)
            return item

        try:
            self.insert_uniq(item, uniq_attribute)
            return item
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise DuplicateItem()
            else:
                raise e

    def insert_uniq(self, item, uniq_attribute):
        expression_attribute_names = {
            "#attribute": uniq_attribute
        }
        return self.table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(#attribute)',
            ExpressionAttributeNames=expression_attribute_names
        )

    def del_item(self, query: Dict):
        self.table.delete_item(Key=query)

    def scan(self):
        return self.table.scan()

    def update_item(self, key_dict, update_dict):
        """
        Update an item.
        PARAMS
        @key_dict: dict containing the key name and val eg. {"uuid": item_uuid}
        @update_dict: dict containing the key name and val of
        attributes to be updated
        eg. {"attribute": "processing_status", "value": "completed"}
        """
        table = self.table
        update_expr = 'SET {} = :val1'.format(update_dict['attribute'])
        response = table.update_item(
            Key=key_dict,
            UpdateExpression=update_expr,
            ExpressionAttributeValues={
                ':val1': update_dict['value']
            }
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            return False
