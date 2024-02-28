import os
import json
import time

import importlib

from web3 import Web3

class Node:
    def __init__(self, id, provider, boost, env, errorcallback):
        self.id = id
        self.boost = boost
        
        if list(str(os.getenv("PROVIDER")))[0].lower() == "h":
            self.provider = Web3(Web3.HTTPProvider(str(os.getenv("PROVIDER"))))
        elif list(str(os.getenv("PROVIDER")))[0].lower() == "w":
            self.provider = Web3(Web3.WebsocketProvider(str(os.getenv("PROVIDER"))))
                
        self.contract_abi = json.loads(open("data/contract_abi.json", "r").read())
        self.contract_address = Web3.to_checksum_address(open("data/contract_address.txt", "r").read())
        
        self.private_key = env["PRIVATE_KEY"]
        self.public_key = Web3.to_checksum_address(env["PUBLIC_KEY"])

    def infer(self, id, prompt, entropy):
        module = importlib.import_module("models." + str(id))
        return module.infer(prompt, entropy)

    def start(self):
        contract = self.provider.eth.contract(address=self.contract_address, abi=self.contract_abi)
        listener = contract.events.RequestCreated.create_filter(fromBlock='latest')
        
        while True:
            time.sleep(0.1)
            for event in listener.get_new_entries():
                if int(event["args"]["model"]) == self.id:
                    print("------------------------------\n")
                    print("   - Request ID:     " + str(event["args"]["requestId"]))
                    print("   - Origin:         " + str(event["args"]["origin"]))
                    print("   - Confirmations:  " + str(event["args"]["confirmations"]))
                    print("   - Bid:            " + str(event["args"]["bid"]))
                    print("   - Prompt:         " + str(event["args"]["prompt"]))
                    print("   - Model:          " + str(event["args"]["model"]))
                    print("   - Entropy:        " + str(event["args"]["entropy"]))
                    print("------------------------------\n")
                    

                    result = self.infer(self.id, str(event["args"]["prompt"]), int(event["args"]["entropy"]))

                    function = contract.functions.submitResponse(event["args"]["requestId"], event["args"]["model"], str(result))
                    nonce = self.provider.eth.get_transaction_count(self.public_key)

                    gasEstimate = function.estimate_gas({'from': self.public_key})
                    gasPrice = self.provider.eth.generate_gas_price()  # Using the generate_gas_price() method for a more current gas price estimate
                    if gasPrice is None:  # In case the network does not provide a gas price, fall back to the previous strategy
                        gasPrice = self.provider.eth.gas_price * 10

                    estimated_gas_cost = gasEstimate * gasPrice
                    balance = self.provider.eth.get_balance(self.public_key)
                    if balance < estimated_gas_cost:
                        print(f"Insufficient funds: Have {balance}, need {estimated_gas_cost}")
                    else:
                        txn_dict = function.build_transaction({
                            'gas': int(gasEstimate * 5 * self.boost),
                            'gasPrice': int(gasPrice * self.boost),
                            'nonce': nonce,
							'from': self.public_key
                        })
                        
                        signed_txn = self.provider.eth.account.sign_transaction(txn_dict, private_key=self.private_key)
                        
                        tx = self.provider.eth.send_raw_transaction(signed_txn.rawTransaction)
                        print("\n    Success")
                        print("\n     - Request ID  : " + str(event["args"]["requestId"]))
                        print("\n     - TX          : " + str(tx.hex()))