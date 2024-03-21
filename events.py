
from web3 import Web3

from web3.datastructures import AttributeDict

import json
import os
import time


class EventsHandler:
    def __init__(self, checkfreq=1):
        if list(str(os.getenv("PROVIDER")))[0].lower() == "h":
            self.provider = Web3(Web3.HTTPProvider(str(os.getenv("PROVIDER"))))
        elif list(str(os.getenv("PROVIDER")))[0].lower() == "w":
            self.provider = Web3(Web3.WebsocketProvider(str(os.getenv("PROVIDER"))))
        
        self.contract_abi = json.loads(open("info/contract_abi.json", "r").read())
        self.contract_address = Web3.to_checksum_address(open("info/contract_address.txt", "r").read())

        self.contract = self.provider.eth.contract(address=self.contract_address, abi=self.contract_abi)
        self.listener = self.contract.events.RequestCreated.create_filter(fromBlock='latest')

        self.events = []

        self.checkfreq = checkfreq

        self.update_events()

    def get_events(self):
        return self.events

    def update_events(self):
        new = []
        for event in self.listener.get_all_entries():
            self.events.append(event)
    
    def start(self):
        while True:
            self.update_events()
            time.sleep(2)