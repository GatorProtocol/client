import threading
import sys
import os
import json

from node import Node
from events import EventsHandler

from errorcallbacks import restart

events_handler = EventsHandler()
events_handler_thread = threading.Thread(target=events_handler.start)
events_handler_thread.start()

node = Node(models=[12, 14, 16])
node.start()