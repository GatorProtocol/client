import threading
import sys
import os
import json

from node import Node

from errorcallbacks import restart, stop

tasks = json.loads(open("tasks.json", "r").read())
for task in tasks:
    if task["errorcallback"] == "restart":
        errorcallback = restart
    else:
        errorcallback = stop

    node = Node(
        id=int(task["id"]),
        provider=task["provider"],
        boost=float(task["boost"]),
        errorcallback=errorcallback,
        env=os.environ
    )
    threading.Thread(target=node.start).start()
