import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import threading
from datetime import date
import datetime
import json
import sys


def estimate_data_size(data):
    size_bytes = sys.getsizeof(json.dumps(data))
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    size_mb = size_kb / 1024
    return f"{size_mb:.2f} MB"


firebase_lock = threading.Lock()


def init():
    with firebase_lock:
        if not firebase_admin._apps:
            cred = credentials.Certificate('madboulder.json') 
            firebase_admin.initialize_app(cred, { 
                'databaseURL': 'https://madboulder.firebaseio.com' 
            }) 


def getValue(refPath, shallow=False):
    init()
    value = db.reference(refPath).get(shallow=shallow)
    
    print(f"getValue {refPath}: {estimate_data_size(value)}")

    return value


def getChildsValue(refPath, problem_ids):
    init()

    values = {}
    ref = db.reference(refPath)
    for problem_id in problem_ids:
        values[problem_id] = ref.child(problem_id).get()

    print(f"getChildsValue {refPath}: {estimate_data_size(values)}")
    return values


def getValueByField(referencePath, fieldName, fieldValue):
    init()

    ref = db.reference(referencePath)
    query = ref.order_by_child(fieldName).equal_to(fieldValue)
    results = query.get()
    
    if not results:
        print(f"No data found for {fieldName}: {fieldValue}")
        return []

    print(f"getValueByField {referencePath},{fieldName}: {estimate_data_size(results)}")
    dataList = [data for data in results.values()]
    return dataList


def checkExists(refPath):
    init()
    
    snapshot = db.reference(refPath).get(shallow=True)
    print(f"checkExists {refPath}: {estimate_data_size(snapshot)}")

    return snapshot is not None


def getKeys(refPath):
    init()
    value = db.reference(refPath).get(shallow=True)

    print(f"getKeys {refPath}: {estimate_data_size(value)}")

    return value


def setValue(refPath, value):
    """ Set value for a specific path, overwriting existing data """
    init()
    db.reference(refPath).set(value)


def updateValue(refPath, value):
    """ Update value for a specific path, without overwriting existing data """
    init()
    db.reference(refPath).update(value)


def addChildWithUniqueId(refPath, newData):
    try:
        ref = db.reference(refPath)
        newRef = ref.push(newData)
        return newRef.key
    except Exception as e:
        print(f"Failed to add child at {refPath}: {e}")
        return None


def delete(refPath):
    init()
    return db.reference(refPath).delete()


def getDate(refPath):
    init()
    return db.reference(f'{refPath}/date').get()


def updateDate(refPath):
    init()
    db.reference(refPath).update({'date': datetime.datetime.now().isoformat()})



