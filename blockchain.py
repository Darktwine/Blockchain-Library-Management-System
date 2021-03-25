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
        self.is_miner = False
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

    # creating a new block and clears out all previous requests data
    def new_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'transaction': self.transaction,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.transaction = []
        self.request = []
        self.request_id = []
        self.book = []
        self.book_key = []
        self.is_miner = False
        self.chain.append(block)
        return block

    # proof of work, validates either the request id or the key, depending on the value passed in
    def proof(self, sender_address, receiver_address, value):
        # if value = 1 check id, if true id is valid
        if value == 1:
            confirm = 0
            response = requests.get(f'http://{sender_address}/get_request_id')
            check_this = response.json()['request_id']
            network = self.nodes
            for node in network:
                if node != sender_address and node != receiver_address:
                    response = requests.get(f'http://{node}/get_request_id')
                    compare_this = response.json()['request_id']
                    # compare the id from receiver_address with other nodes in network
                    if check_this == compare_this:
                        confirm += 1
            check = self.consensus(sender_address, receiver_address, confirm)
            if check:
                return True
        # if value = 2 check keys, if true key is valid
        if value == 2:
            confirm = 0
            response = requests.get(f'http://{sender_address}/get_book_key')
            check_this = response.json()['book_key']
            network = self.nodes
            for node in network:
                if node != sender_address and node != receiver_address:
                    response = requests.get(f'http://{node}/get_book_key')
                    compare_this = response.json()['book_key']
                    # compare the key from sender_port with other nodes in network
                    if check_this == compare_this:
                        confirm += 1
            check = self.consensus(sender_address, receiver_address, confirm)
            if check:
                return True

    # check if >50% agrees
    def consensus(self, sender_address, receiver_address, confirm):
        # count all nodes in network but sender and receiver
        # if over 50% of the nodes validate it, consensus is achieved
        counter = 0
        network = self.nodes
        for node in network:
            if node != sender_address and node != receiver_address:
                counter += 1
        if confirm / counter > 0.5:
            return True
        return False

    def set_miner(self):
        self.is_miner = True

    def verify_miner(self):
        if self.is_miner == True:
            return True
        
        return False

    def send_request(self, sender_address, receiver_address, book_id, request_message):
        # create a new request from the sender to the receiver
        network = self.nodes
        for node in network:
            if node == receiver_address:
                requests.post(f'http://{node}/set_request', json={
                    'sender_address': sender_address,
                    'receiver_address': receiver_address,
                    'book_id': book_id,
                    'request_message': request_message
                })

    def set_request(self, sender_address, receiver_address, book_id, request_message):
        self.request.append({
            'sender_address': sender_address,
            'receiver_address': receiver_address,
            'book_id': book_id,
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

    # adds request id into list
    def set_request_ids(self, request_id):
        self.request_id.append({'request_id': request_id})

    # encrypt book and generate the key with Fernet
    # decode to send non bytes through network
    def encrypt_book_and_create_key(self, book_id):
        book_key = Fernet.generate_key()
        ubyte_key = book_key.decode()
        byte_key = Fernet(book_key)
        encrypted_book = byte_key.encrypt(book_id.encode())
        ubyte_encrypted_book = encrypted_book.decode()
        self.book.append({'encrypted_book': ubyte_encrypted_book})
        self.book_key.append({'book_key': ubyte_key})

    def send_book(self, sender_address, receiver_address):
        network = self.nodes
        for node in network:
            if node == receiver_address:
                response = requests.get(f'http://{sender_address}/get_book')
                if response.status_code == 200:
                    requests.post(f'http://{node}/set_book', json={
                        'encrypted_book': response.json()['encrypted_book']
                    })
    
    def send_book_key(self, sender_address, receiver_address):
        network = self.nodes
        for node in network:
            if node != sender_address and node != receiver_address:
                response = requests.get(f'http://{sender_address}/get_book_key')
                if response.status_code == 200:
                    requests.post(f'http://{node}/set_key', json={
                        'book_key': response.json()['book_key']
                    })   

    # adds encrypted book into list
    def set_books(self, encrypted_book):
        self.book.append({'encrypted_book': encrypted_book})

    # adds key into list
    def set_keys(self, book_key):
        self.book_key.append({'book_key': book_key})

    # after sender address gets the encrypted book and other nodes get keys
    # sender address sends receiver address the request id
    def send_request_id_to_receiver(self, sender_address, receiver_address):
        network = self.nodes
        for node in network:
            if node == receiver_address:
                response = requests.get(f'http://{sender_address}/get_request_id')
                if response.status_code == 200:
                    requests.post(f'http://{node}/set_request_id', json={
                        'request_id': response.json()['request_id']
                    })

    def send_book_key_to_receiver(self, sender_address, receiver_address):
        network = self.nodes
        for node in network:
            if node == receiver_address:
                response = requests.get(f'http://{sender_address}/get_book_key')
                if response.status_code == 200:
                    requests.post(f'http://{node}/set_key', json={
                        'book_key': response.json()['book_key']
                    })

    # after key is sent sender node checks if key is valid by decrypting book
    # decrypted book should be book_value requested
    def decrypted_book(self, sender_address, receiver_address, book_id):
        response = requests.get(f'http://{sender_address}/get_book_key')
        key = response.json()['book_key'].encode()
        response2 = requests.get(f'http://{sender_address}/get_book')
        encrypted_book = response2.json()['encrypted_book'].encode()
        f = Fernet(key)
        book = f.decrypt(encrypted_book).decode()
        if book == book_id:
            return True
        return False

    def send_transaction(self, miner_address, request_id, book_key):
        network = self.nodes
        for node in network:
            requests.post(f'http://{node}/set_transaction', json={
                'request_id': request_id,
                'book_key': book_key
            })

    def set_transactions(self, request_id, book_key):
        self.transaction.append({
            'proof': request_id + book_key
        })
        last_block = self.last_block
        previous_hash = self.hash(last_block)
        self.new_block(previous_hash)

    # hashing
    @staticmethod
    def hash(block):
        block_hash = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_hash).hexdigest()

    # get last block
    @property
    def last_block(self):
        return self.chain[-1]



app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

#######################################################
#######################################################
############### Route HTTP Methods ####################
#######################################################
#######################################################

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

# Generate a request
@app.route('/add_request', methods=['POST'])
def add_request():
    # for the node creating a new request, set their miner status to true
    blockchain.set_miner()

    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address', 'book_id', 'request_message']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    # Create and add request id to self
    request_id = uuid4()
    blockchain.create_request_id(request_id)

    # Send the information to the address of the receiver node
    blockchain.send_request(request_info['sender_address'], request_info['receiver_address'], request_info['book_id'], request_info['request_message'])

    # Send request id to all the other nodes except the receiver of the request
    blockchain.send_request_id(request_info['sender_address'], request_info['receiver_address'])

    response = {'message': f"Request for {request_info['receiver_address']} and the request id has been created."}
    return jsonify(response), 201

@app.route('/set_request', methods=['POST'])
def set_request():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address', 'book_id', 'request_message']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    # Send the information to the address of the receiver node
    blockchain.set_request(request_info['sender_address'], request_info['receiver_address'], request_info['book_id'], request_info['request_message'])

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

# generate book by calling generate_book_key method
@app.route('/add_book', methods=['POST'])
def add_book():
    book_info = request.get_json()
    required = ['sender_address', 'receiver_address', 'book_id']
    if not all(keys in book_info for keys in required):
        return 'Missing book information', 400

    blockchain.encrypt_book_and_create_key(book_info['book_id'])

    blockchain.send_book(book_info['sender_address'], book_info['receiver_address'])
    blockchain.send_book_key(book_info['sender_address'], book_info['receiver_address'])

    response = {'message': "The requested book has been encrypted and the book key has been generated."}
    return jsonify(response), 201

# set book
@app.route('/set_book', methods=['POST'])
def set_book():
    book_info = request.get_json()
    required = ['encrypted_book']
    if not all(keys in book_info for keys in required):
        return 'Missing encrypted book', 400

    blockchain.set_books(book_info['encrypted_book'])
    response = {'message': "Encrypted book has been sent."}
    return jsonify(response), 200

# set book key by calling set_keys method
@app.route('/set_key', methods=['POST'])
def set_key():
    book_key_info = request.get_json()
    required = ['book_key']
    if not all(keys in book_key_info for keys in required):
        return 'Missing book key', 400

    blockchain.set_keys(book_key_info['book_key'])
    response = {'message': "The book key has been sent to the other nodes."}
    return jsonify(response), 201

@app.route('/send_request_id_for_validation', methods=['POST'])
def send_request_id_for_validation():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address']
    if not all(keys in request_info for keys in required):
        return 'Missing keys', 400

    blockchain.send_request_id_to_receiver(request_info['sender_address'], request_info['receiver_address'])

    response = {'message': f"Request id has been sent to {request_info['receiver_address']}."}
    return jsonify(response), 201

@app.route('/validate_request_id', methods=['POST'])
def validate_request_id():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address']
    if not all(keys in request_info for keys in required):
        return 'Missing keys', 400

    # validated returns true or false after checking the request id against the other nodes in the network
    validated = blockchain.proof(request_info['sender_address'], request_info['receiver_address'], value = 1)

    if validated:
        response = {'message': "The request id has been validated, achieving over 50 percent consensus."}
    else:
        response = {'message': "The request id has been rejected, failing to recieve over 50 percent consensus."}
    return jsonify(response), 201

@app.route('/send_book_key_for_validation', methods=['POST'])
def send_book_key_for_validation():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address']
    if not all(keys in request_info for keys in required):
        return 'Missing keys', 400

    blockchain.send_book_key_to_receiver(request_info['sender_address'], request_info['receiver_address'])

    response = {'message': f"Book key has been sent to {request_info['receiver_address']}."}
    return jsonify(response), 201

@app.route('/decrypt_book', methods=['POST'])
def decrypt_book():
     # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address', 'book_id']
    if not all(keys in request_info for keys in required):
        return 'Missing keys', 400

    decrypted = blockchain.decrypted_book(request_info['sender_address'], request_info['receiver_address'], request_info['book_id'])

    if decrypted:
        response = {'message': "The book key successfully decrypted the book."}
    else:
        response = {'message': "The book key has failed to decrypt the book."}
    
    return jsonify(response), 201

@app.route('/validate_book_key', methods=['POST'])
def validate_book_key():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['sender_address', 'receiver_address']
    if not all(keys in request_info for keys in required):
        return 'Missing keys', 400

    # validated returns true or false after checking the request id against the other nodes in the network
    validated = blockchain.proof(request_info['sender_address'], request_info['receiver_address'], value = 2)

    if validated:
        response = {'message': "The book key has been validated, achieving over 50 percent consensus."}
    else:
        response = {'message': "The book key has been rejected, failing to recieve over 50 percent consensus."}

    return jsonify(response), 201

# mine the transaction as a block and add it to the blockchain
@app.route('/mine_transaction', methods=['POST'])
def mine_transaction():
    # verify that the miner is the one who originally sent the request
    can_mine = blockchain.verify_miner()

    if can_mine:
        values = request.get_json()
        required = ['miner_address', 'request_id', 'book_key']
        if not all(keys in values for keys in required):
            return 'Missing keys', 400

        blockchain.send_transaction(values['miner_address'], values['request_id'], values['book_key'])

        response = {'message': "Transaction has been mined and added to the blockchain."}
        return jsonify(response), 200

# set the transaction for every node in the network
@app.route('/set_transaction', methods=['POST'])
def set_transaction():
    # convert the POST info into JSON format, and save into requested_info
    request_info = request.get_json()

    # must have these keys for the request to be valid, generate an error if any are missing
    required = ['request_id', 'book_key']
    if not all(keys in request_info for keys in required):
        return 'Missing keys for request', 400

    # Send the information to the address of the receiver node
    blockchain.set_transactions(request_info['request_id'], request_info['book_key'])

    response = {'message': "The transaction has been sent to all nodes."}
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
        'book_id': blockchain.request[0]['book_id'],
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

# get the encrypted book from book list
@app.route('/get_book', methods=['GET'])
def get_book():
    response = {
        'encrypted_book': blockchain.book[0]['encrypted_book']
    }
    return jsonify(response), 200

# get key from key list
@app.route('/get_book_key', methods=['GET'])
def get_book_key():
    response = {
        'book_key': blockchain.book_key[0]['book_key']
    }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
    args = parser.parse_args()
    port = args.port
    app.run(host='127.0.0.1', port=port)