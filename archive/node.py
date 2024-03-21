
import os
import json
import time

import importlib

from events import EventsHandler

from web3 import Web3

from dotenv import load_dotenv
load_dotenv()

class Node:
    def __init__(self, models=[], boost=1, provider_type="http"):
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

    def infer(self, id, prompt, entropy):
        module = importlib.import_module("models." + str(id))
        return module.infer(id, prompt, entropy)

    def start(self):
        contract = self.provider.eth.contract(address=self.contract_address, abi=self.contract_abi)
        listener = contract.events.RequestCreated.create_filter(fromBlock='latest')

        self.event_handler.update_events()

        while True:
            time.sleep(1)
            for event in listener.get_all_entries():
                if int(event["args"]["modelId"]) in self.models:
                    if self.is_known(event["args"]["requestId"].hex()) == False:
                        start_time = time.time()

                        print("---------------------------------------------------------------------\n")
                        print("   Request")
                        print("      Model:    " + str(event["args"]["modelId"]))
                        print("      Prompt:   " + str(event["args"]["prompt"]))
                        print("\n---------------------------------------------------------------------\n")

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
                        print("---------------------------------------------------------------------\n")
                        print("    Success")
                        print("         TX: " + str(tx.hex()) + "\n")
                        print("---------------------------------------------------------------------\n")

                        self.know(event["args"]["requestId"])

                        print(time.time() - start_time)
    
    def know(self, request_id):
        time.sleep(0.2)
        data = json.loads(open("database/requests.json", "r").read())
        data.append(str(request_id.hex()))
        open("database/requests.json", "w").write(json.dumps(data, indent=4))

    def is_known(self, request_id):
        with open("database/requests.json") as file:
            data = json.load(file)
            for item in data:
                if str(item) == str(request_id):
                    return True
        return False