import os
import json
import time
import importlib
import logging

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from dotenv import load_dotenv

from web3 import Web3

from events import EventsHandler

load_dotenv()

class Node:
    def __init__(self, models=[], boost=1, provider_type="http"):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.boost = boost
        self.provider_url = os.environ["PROVIDER"]
        self.provider_type = provider_type

        if provider_type == "http":
            self.provider = Web3(Web3.HTTPProvider(self.provider_url))
        elif provider_type == "websocket":
            self.provider = Web3(Web3.WebsocketProvider(self.provider_url))
        
        self.contract_abi = json.loads(open("info/contract_abi.json", "r").read())
        self.contract_address = Web3.to_checksum_address(open("info/contract_address.txt", "r").read())

        self.private_key = os.environ["PRIVATE_KEY"]
        self.public_key = Web3.to_checksum_address(os.environ["PUBLIC_KEY"])

        self.event_handler = EventsHandler()

        self.models = models

        self.requests_lock = Lock()

    def infer(self, id, prompt, entropy):
        module = importlib.import_module("models." + str(id))
        return module.infer(id, prompt, entropy)
    
    def start(self):
        contract = self.provider.eth.contract(address=self.contract_address, abi=self.contract_abi)
        listener = contract.events.RequestCreated.create_filter(fromBlock='latest')

        self.event_handler.update_events()

        with ThreadPoolExecutor(max_workers=4) as executor:
            while True:
                time.sleep(1)
                events = listener.get_all_entries()
                futures = [executor.submit(self.handle_event, event, contract) for event in events]
                for future in as_completed(futures):
                    pass

    def handle_event(self, event, contract):
        max_retries = 5
        retries = 0

        while retries < max_retries:
            try:
                if int(event["args"]["modelId"]) in self.models:
                    request_id_hex = event["args"]["requestId"].hex()
                    if not self.is_known(request_id_hex):
                        start_time = time.time()

                        logging.info("Handling request - Model: %s, Prompt: %s", event["args"]["modelId"], event["args"]["prompt"])

                        result = self.infer(int(event["args"]["modelId"]), str(event["args"]["prompt"]), int(event["args"]["entropy"]))

                        function = contract.functions.fufillRequest(
                            event["args"]["requestId"],
                            int(event["args"]["modelId"]), 
                            str(result)
                        )
                        nonce = self.provider.eth.get_transaction_count(self.public_key)

                        txn_dict = function.build_transaction({
                            'gas': 2000000,
                            'gasPrice': 500000000,
                            'nonce': nonce,
                            'from': self.public_key
                        })
                        
                        signed_txn = self.provider.eth.account.sign_transaction(txn_dict, private_key=self.private_key)
                        
                        tx = self.provider.eth.send_raw_transaction(signed_txn.rawTransaction)
                        logging.info("Request fulfilled successfully - TX: %s", tx.hex())

                        self.know(event["args"]["requestId"])

                        logging.debug("Processing time: %s seconds", time.time() - start_time)
                
                break
            except Exception as e:
                retries += 1
                logging.error(f"Error handling event: {e}. Retrying {retries}/{max_retries}")
                time.sleep(2)

        if retries == max_retries:
            logging.error("Max retries reached. Failed to handle event.")

    def know(self, request_id_hex):
        with self.requests_lock:
            data = json.loads(open("database/requests.json", "r").read())
            data.append(request_id_hex)
            open("database/requests.json", "w").write(json.dumps(data, indent=4))

    def is_known(self, request_id_hex):
        with self.requests_lock:
            with open("database/requests.json") as file:
                data = json.load(file)
                return request_id_hex in data

node = Node(models=[12, 14, 16])
node.start()