
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
            cred = credentials.Certificate('madboulder-development.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://madboulder-development-default-rtdb.europe-west1.firebasedatabase.app/'
            })


def getValue(refPath, shallow=False):
    init()
    return db.reference(refPath).get(shallow=shallow)


def getValueByField(referencePath, fieldName, fieldValue):
    init()

    ref = db.reference(referencePath)
    query = ref.order_by_child(fieldName).equal_to(fieldValue)
    results = query.get()
    
    if not results:
        print(f"No data found for {fieldName}: {fieldValue}")
        return []

    dataList = [data for data in results.values()]
    return dataList


def checkExists(refPath):
    init()
    
    snapshot = db.reference(refPath).get(shallow=True)
    return snapshot is not None


def getKeys(refPath):
    init()
    return db.reference(refPath).get(shallow=True)


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



