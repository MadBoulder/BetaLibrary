
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import threading
from datetime import date
import datetime
    

def encodeSlug(key):
    return key.replace('/', '___')

def decodeSlug(key):
    return key.replace('___', '/')


firebase_lock = threading.Lock()


def init():
    with firebase_lock:
        if not firebase_admin._apps:
            cred = credentials.Certificate('madboulder.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://madboulder.firebaseio.com'
            })


def getValue(element_name):
    init()
    return db.reference(element_name).get()


def getNestedChild(elementName, childKey):
    init()
    return db.reference(f"{elementName}/items/{childKey}").get()


def updateNode(elementName, data):
    init()
    nodeRef = db.reference(elementName)
    nodeRef.set(data)


def updateNodeWithItems(nodeName, data, reset=False):
    init()
    root = db.reference()
    nodePath = root.child(nodeName)
    
    if nodePath.get() is None:
        print(f"No existing data found for {nodeName}. Creating new node...")
        nodePath.set({
            'items': data,
            'date': datetime.datetime.now().strftime("%Y-%m-%d")
        })
    else:
        print(f"Updating existing data for {nodeName}.")

        update_dict = {'items': data}
        update_dict['date'] = datetime.datetime.now().strftime("%Y-%m-%d")

        if reset:
            nodePath.set(update_dict)
        else:
            nodePath.update(update_dict)


def updateNestedChildNode(elementName, childKey, subChildKey, newData):
    init()
    root = db.reference()
    nestedChildRef = root.child(f"{elementName}/items/{childKey}/{subChildKey}")
    nestedChildRef.update(newData)


def updateChildNode(elementName, childKey, subChildKey, newData):
    init()
    root = db.reference()
    ref = root.child(f'{elementName}/{childKey}/{subChildKey}')
    ref.update(newData)


def setChildNode(elementName, childKey, subChildKey, newData):
    init()
    ref = db.reference(f'{elementName}/{childKey}/{subChildKey}')
    ref.set(newData)


def updateChildNodeWithUniqueId(elementName, childKey, subChildKey, newData):
    init()
    ref = db.reference(f'{elementName}/{childKey}/{subChildKey}')
    newRef = ref.push(newData)
    return newRef.key


def updateNestedChild(elementName, childKey, newData):
    init()
    root = db.reference()
    nestedChildRef = root.child(f"{elementName}/items/{childKey}")
    nestedChildRef.update(newData)


def updateChild(elementName, childKey, newData):
    init()
    root = db.reference()
    nestedChildRef = root.child(f"{elementName}/{childKey}")
    nestedChildRef.update(newData)


def updateNodeNestedChildNode(parentNode, childNode, nestedChildNode, newData):
    init()
    nestedChildRef = db.reference(f"{parentNode}/{childNode}/{nestedChildNode}")
    print(f"Updating nested child {nestedChildNode} for {childNode} under {parentNode}.")
    nestedChildRef.update(newData)

    
def delete(element_name):
    init()
    return db.reference(element_name).delete()


def getVideoDataFromZone(zone_code):
    init()

    ref = db.reference('video_data/items')
    query = ref.order_by_child('zone_code').equal_to(zone_code)
    results = query.get()
    
    if not results:
        print("No problems found for zone:", zone_code)
        return []

    problems = [data for data in results.values()]
    return problems