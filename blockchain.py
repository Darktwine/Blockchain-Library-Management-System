import binascii
import uuid
from cryptography.fernet import Fernet
import hashlib
import json
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.chain = []
        self.transaction = []
        self.request = []
        self.request_id = []
        self.book = []
        self.book_key = []
        self.nodes = set()

        self.new_block(previous_hash='0')

    # add and register all nodes in a list for a port
    def create_nodes(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid')

    # creation of a new transaction, which will include both the request id and key for validation
    def new_transaction(self, req_id, key):
        self.transaction.append({
            'proof': req_id+key
        })
        last_block = self.last_block
        previous_hash = self.hash(last_block)
        self.new_block(previous_hash)

    # creating a new block and clears out all previous requests data
    def new_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'transaction': self.transaction,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.transaction = []
        self.request = []
        self.book = []
        self.request_id = []
        self.book_key = []
        self.chain.append(block)
        return block

    # proof of work 
    def proof(self, sender_address, receiver_address, value):
        # if value = 1 check id, if true id is valid
        if value == 1:
            confirm = 0
            response = requests.get(f'http://{receiver_address}/get/id')
            check_this = response.json()['id']
            network = self.nodes
            for node in network:
                if node != sender_address and node != receiver_address:
                    response = requests.get(f'http://{node}/get/id')
                    compare_this = response.json()['id']
                    # compare the id from receiver_address with other nodes in network
                    if check_this == compare_this:
                        confirm += 1
            check = self.consensus(sender_address, receiver_address, confirm)
            if check:
                return True
        # if value = 2 check keys, if true key is valid
        if value == 2:
            confirm = 0
            response = requests.get(f'http://{sender_address}/get/key')
            check_this = response.json()['key']
            network = self.nodes
            for node in network:
                if node != sender_address and node != receiver_address:
                    response = requests.get(f'http://{node}/get/key')
                    compare_this = response.json()['key']
                    # compare the key from sender_port with other nodes in network
                    if check_this == compare_this:
                        confirm += 1
            check = self.consensus(sender_address, receiver_address, confirm)
            if check:
                return True

    # check if >50% agrees
    def consensus(self, sender_address, receiver_address, confirm):
        # count all nodes in network but sender and receiver
        # compare if agree is > 50%
        counter = 0
        network = self.nodes
        for node in network:
            if node != sender_address and node != receiver_address:
                counter += 1
        if confirm / counter > 0.5:
            return True
        return False

    # generate book key
    def generate_book_keys(self, book_value):
        # using Fernet to generate keys and encrypt the book
        # decode to send non bytes through network
        key = Fernet.generate_key()
        ubyte_key = key.decode()
        byte_key = Fernet(key)
        encrypted = byte_key.encrypt(book_value.encode())
        ubyte_encrypted = encrypted.decode()
        self.book.append({'encrypted_book': ubyte_encrypted})
        self.book_key.append({'key': ubyte_key})

    # adds request into the list
    def set_requests(self, sender_port, receiver_port, book_value):
        self.request.append({
            'sender_port': sender_port,
            'receiver_port': receiver_port,
            'book_value': book_value
        })

    # adds encrypted book into list
    def set_books(self, encrypted_book):
        self.book.append({'encrypted_book': encrypted_book})

    # adds key into list
    def set_keys(self, book_key):
        self.book_key.append({'key': book_key})

    # adds request id into list
    def set_request_ids(self, request_id):
        self.request_id.append({'request_id': request_id})

    # hashing
    @staticmethod
    def hash(block):
        block_hash = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_hash).hexdigest()

    # get last block
    @property
    def last_block(self):
        return self.chain[-1]


    def send_request(self, sender_address, receiver_address, request_message):
        # create a new request from the sender to the receiver
        network = self.nodes
        for node in network:
            if node == receiver_address:
                requests.post(f'http://{node}/set_request', json={
                    'sender_address': sender_address,
                    'receiver_address': receiver_address,
                    'request_message': request_message
                })



    def set_request(self, sender_address, receiver_address, request_message):
        self.request.append({
            'sender_address': sender_address,
            'receiver_address': receiver_address,
            'request_message': request_message
        })

    def create_request_id(self, request_id):
        self.request_id.append({
            'request_id': request_id
        })

    def send_request_id(self, sender_address, receiver_address):
        network = self.nodes
        for node in network:
            if node != receiver_address and node != sender_address:
                response = requests.get(f'http://{sender_address}/get_request_id')
                if response.status_code == 200:
                    requests.post(f'http://{node}/set_request_id', json={
                        'request_id': response.json()['request_id']
                    })

    # checks if chain is valid
    def validate_chain(self, chain):
        previous_block = chain[0]
        counter = 1
        while counter < len(chain):
            current_block = chain[counter]
            previous_hash = self.hash(previous_block)
            if current_block['previous_hash'] != previous_hash:
                return False
            previous_block = current_block
            counter = counter + 1
        return True



app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()


#######################################################
############### Route HTTP Methods ####################
#######################################################

# create block
@app.route('/add_block', methods=['GET'])
def add_block():
    last_block = blockchain.last_block
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(previous_hash)
    response = {
        'message': "new block",
        'index': block['index'],
        'transaction': block['transaction'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


# Generate a request
@app.route('/add_request', methods=['POST'])
def add_request():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address', 'request_message']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    # Create and add request id to self
    request_id = uuid4()
    blockchain.create_request_id(request_id)

    # Send the information to the address of the receiver node
    blockchain.send_request(request_info['sender_address'], request_info['receiver_address'], request_info['request_message'])

    # Send request id to all the other nodes except the receiver of the request
    blockchain.send_request_id(request_info['sender_address'], request_info['receiver_address'])

    response = {'message': f"Request for {request_info['receiver_address']} and the request id has been created."}
    return jsonify(response), 201

@app.route('/set_request', methods=['POST'])
def set_request():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address', 'request_message']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    # Send the information to the address of the receiver node
    blockchain.set_request(request_info['sender_address'], request_info['receiver_address'], request_info['request_message'])

    response = {'message': f"The request has been sent for {request_info['receiver_address']}."}
    return jsonify(response), 201

@app.route('/set_request_id', methods=['POST'])
def set_request_id():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()
    required = ['request_id']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    blockchain.set_request_ids(request_info['request_id'])
    response = {'message': "The request id has been sent to the other nodes."}
    return jsonify(response), 201

# returns chain
@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

# returns request
@app.route('/get_request', methods=['GET'])
def get_request():
    response = {
        'sender_address': blockchain.request[0]['sender_address'],
        'receiver_address': blockchain.request[0]['receiver_address'],
        'request_message': blockchain.request[0]['request_message']
    }
    return jsonify(response), 200

# returns request id
@app.route('/get_request_id', methods=['GET'])
def get_request_id():
    response = {
        'request_id': blockchain.request_id[0]['request_id']
    }
    return jsonify(response), 200

# add new nodes
@app.route('/new_nodes', methods=['POST'])
def new_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error", 400
    for node in nodes:
        blockchain.create_nodes(node)
    response = {
        'message': "Node created",
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
    args = parser.parse_args()
    port = args.port
    app.run(host='127.0.0.1', port=port)