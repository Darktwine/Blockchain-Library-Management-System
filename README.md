# Smart Library Management System

## This is a library management system using a transactional blockchain.

In a network of nodes, each node can request a book from another node that has it. Each validated transaction (transfer of ownership of a book) is a single block that can be added to the entire blockchain. Transactions are validated with a POW that checks for the request id and the book key, and consensus is achieved if over 50% of the nodes in the network (not including the sender and receiver) validate that transaction.


### Requirements: 
1. Python version 3.6 or later.
2. Install pipenv ($ pip install pipenv)
3. Install requirements ($ pipenv install)

### Instructions for operating the blockchain library
1) To run the servers:
    - python3 blockchain.py
    - python3 blockchain.py -p 5001
    - python3 blockchain.py -p 5002
    - python3 blockchain.py -p 5003

2) Open up an API client (such as Postman or Insomnia).

3) Register a list of all nodes on each port, using the "new_nodes" POST method

    Example: http://localhost:5000/new_nodes
        
    In JSON format:
    
        {
			"nodes": ["127.0.0.1:5000", 
			  	  "127.0.0.1:5001",
			  	  "127.0.0.1:5002",
			  	  "127.0.0.1:5003"]
        }
	
    In this demo, we will treat node 1 as port 5000, node 2 as port 5001, node 3 as port 5002, and node 4 as port 5003.

4) Create a new request from node 1 using the "add_request" POST method. This should contain the necessary keys listed in the method. The sender address is node 1 and the receiver is node 2. A success message should return.

    Example: http://localhost:5000/add_request

    In JSON format:
        
        {
            "sender_address": "127.0.0.1:5000",
            "receiver_address": "127.0.0.1:5001",
	        "book_id": 17,
            "request_message": "I request book b1 from you."
        }
        
        
5) Then with the same request information, call the "set_request" POST method.

6) Call "get_request_id" GET method, and copy the randomly generated id.

7) Call "set_request_id" POST method using the id obtained in the previous step.

8) Now switch to node 2. Call the get_request GET method and we should obtain the request message from node 1. However, get_request_id GET method should not work.

9) Switch to node 3, and call the get_request_id GET method. Should return the request id. However, get_request should not work. This is the same for node 4, and all other nodes in the network that were not the receiver address.

10) Since node 2 now has the request, it can use the book id to encrypt the book. Passing in the sender address, receiver address, and book id, call the add_book POST method. This will send the encrypted book to the receiver (node 1 in this case), and the key to decrypt the book to nodes 3 and 4.

11) Switch to node 1 and call get_book GET method. Should recieve a message with the encrypted book. However, should not be able to access the book key.

12) Switch to node 3 and call get_book_key GET method. Should receive the key to decrypt the book. However, should not be able to access the encrypted book. Same for node 4.
