import os
import json
import time

from web3 import Web3

class Model:
    def __init__(self, callback=None, id=None, provider=None, boost=1, env=None, errorcallback=None, checkfreq=2):
        if id is None: raise Exception("Model ID cannot be None")
        if provider is None: raise Exception("Web3 provider cannot be None")
        if env is None: raise Exception("ENV cannot be None")
        if errorcallback is None: raise Exception("Error callback cannot be None")
        if callback is None: raise Exception("Callback cannot be None")

        self.id = id
        self.boost = boost
        self.callback = callback
        self.checkfreq = checkfreq
        self.errorcallback = errorcallback
        
        if list(str(os.getenv("PROVIDER")))[0].lower() == "h":
            self.provider = Web3(Web3.HTTPProvider(str(os.getenv("PROVIDER"))))
        elif list(str(os.getenv("PROVIDER")))[0].lower() == "w":
            self.provider = Web3(Web3.WebsocketProvider(str(os.getenv("PROVIDER"))))
                
        self.contract_abi = json.loads(open("data/contract_abi.json", "r").read())
        self.contract_address = Web3.to_checksum_address(open("data/contract_address.txt", "r").read())
        
        self.private_key = env["PRIVATE_KEY"]
        self.public_key = Web3.to_checksum_address(env["PUBLIC_KEY"])

    def start(self):
        try:
            contract = self.provider.eth.contract(address=self.contract_address, abi=self.contract_abi)
            listener = contract.events.RequestCreated.create_filter(fromBlock='latest')
            
            while True:
                time.sleep(self.checkfreq)
                for event in listener.get_new_entries():
                    if int(event["args"]["model"]) == self.id:
                        print("------------------------------\n")
                        print("   Request:     " + str(event["args"]["requestId"]))
                        print("   - Origin:         " + str(event["args"]["origin"]))
                        print("   - Confirmations:  " + str(event["args"]["confirmations"]))
                        print("   - Bid:            " + str(event["args"]["bid"]))
                        print("   - Prompt:         " + str(event["args"]["prompt"]))
                        print("   - Model:          " + str(event["args"]["model"]))
                        print("   - Entropy:        " + str(event["args"]["entropy"]))
                        print("------------------------------\n")
                        

                        result = self.callback(self.id, str(event["args"]["prompt"]), int(event["args"]["entropy"]))

                        function = contract.functions.submitResponse(event["args"]["requestId"], event["args"]["model"], str(result))
                        nonce = self.provider.eth.get_transaction_count(self.public_key)

                        gasEstimate = function.estimate_gas({'from': self.public_key})
                        gasPrice = self.provider.eth.generate_gas_price()
                        if gasPrice is None:
                            gasPrice = self.provider.eth.gas_price * 10

                        estimated_gas_cost = gasEstimate * gasPrice
                        balance = self.provider.eth.get_balance(self.public_key)
                        if balance < estimated_gas_cost:
                            raise Exception(f"\n   ERROR: insufficient funds. Have {balance}, need {estimated_gas_cost}")
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
                            print("\n     - TX          : " + str(tx.hex()) + "\n")
        
        except Exception as e:
            self.errorcallback(e)