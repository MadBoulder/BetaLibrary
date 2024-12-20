import utils.database
import pytz
import datetime
from functools import lru_cache
import json
import sys

PROBLEMS_KEY = 'problem_data'
ENCODED_SEPARATOR = '___'
DECODED_SEPARATOR = '/'

def createSlug(areaCode, problemId):
    return areaCode + DECODED_SEPARATOR + problemId

def createEncodedSlug(areaCode, problemId):
    return areaCode + ENCODED_SEPARATOR + problemId

def encodeSlug(key):
    return key.replace(DECODED_SEPARATOR, ENCODED_SEPARATOR)

def decodeSlug(key):
    if key:
        return key.replace(ENCODED_SEPARATOR, DECODED_SEPARATOR)
    else:
        return None

def getSlugData(slug):
    if ENCODED_SEPARATOR in slug:
        parts = slug.split(ENCODED_SEPARATOR)
    elif DECODED_SEPARATOR in slug:
        parts = slug.split(DECODED_SEPARATOR)
    else:
        raise ValueError("Invalid slug format provided.")

    if len(parts) != 2:
        raise ValueError("Slug does not contain exactly one delimiter or has improper format.")

    areaName, problemId = parts[0], parts[1]
    return (areaName, problemId)

@lru_cache(maxsize=10)
def getAllVideoData():
    return utils.database.getValue(f'{PROBLEMS_KEY}/items')

def getVideoDataDate():
    return utils.database.getDate(PROBLEMS_KEY)

def getVideoCount():
    return utils.database.getValue('video_count')

def setVideoData(videoData):
    utils.database.setValue(f'{PROBLEMS_KEY}/items', videoData)

    total_problems = 0
    for area in videoData.values():
        total_problems += len(area)
    utils.database.setValue('video_count', total_problems)

    utils.database.updateDate(PROBLEMS_KEY)
    getAllVideoData.cache_clear()
    
@lru_cache(maxsize=10)
def getSearchData():
    return utils.database.getValue('data_search_optimized')

def setVideoDataSearchOptimized(videoData):
    utils.database.setValue('data_search_optimized', videoData)


def getContributorsCount():
    return utils.database.getValue('contributor_count')

def getContributorsList():
    print("get_contributors_list")
    return utils.database.getValue('contributors')

def setContributorData(contributors):
    utils.database.setValue('contributors', contributors)
    contributor_count = len(contributors)
    utils.database.setValue('contributor_count', contributor_count)

@lru_cache(maxsize=10)
def getPlaylistsData():
    data = utils.database.getValue('playlist_data/items')
    return data;

def getPlaylistData(areaCode):
    data =  utils.database.getValue(f'playlist_data/items/{areaCode}')
    return data;

def setPlaylistData(playlists):
    utils.database.setValue('playlist_data/items', playlists)
    utils.database.updateDate('playlist_data')
    getPlaylistsData.cache_clear()

def getAreasCount():
    return utils.database.getValue('areas_count')

@lru_cache(maxsize=10)
def getAreasData():
    data = utils.database.getValue('area_data')
    return data;

def getAreaKeysFromProblems():
    return utils.database.getValue(f'{PROBLEMS_KEY}/items', shallow=True)

@lru_cache(maxsize=10)
def getAreaData(areaCode):
    data = utils.database.getValue(f'area_data/{areaCode}')
    return data;

def setAreaData(areas):
    utils.database.setValue('area_data', areas)
    areaCount = len(areas)
    utils.database.setValue('areas_count', areaCount)
    getAreasData.cache_clear()
    getAreaData.cache_clear()

def addArea(areaCode, areaData):
    utils.database.updateValue('area_data', {areaCode: areaData})

@lru_cache(maxsize=10)
def getCountriesData():
    data = utils.database.getValue('country_data')
    return data;

def getCountriesKeys():
    return utils.database.getKeys('country_data')

@lru_cache(maxsize=10)
def getCountryData(countryCode):
    data = utils.database.getValue(f'country_data/{countryCode}')
    return data;

def getStateData(countryCode, stateCode):
    return utils.database.getValue(f'country_data/{countryCode}/states/{stateCode}')

def setCountryData(countries):
    utils.database.setValue('country_data', countries)
    getCountriesData.cache_clear()
    getCountryData.cache_clear()

def updateCountry(countryCode, data):
    utils.database.setValue(f'country_data/{countryCode}', data)
    getCountriesData.cache_clear()
    getCountryData.cache_clear()

def updateState(countryCode, stateCode, data):
    utils.database.setValue(f'country_data/{countryCode}/states/{stateCode}', data)
    getCountriesData.cache_clear()
    getCountryData.cache_clear()

def getAllBoulderData():
    data = utils.database.getValue('boulder_data')
    return data;

def getBoulderData(areaCode):
    data = utils.database.getValue(f'boulder_data/{areaCode}')
    return data;

def setBoulderData(boulders):
    utils.database.setValue('boulder_data', boulders)


#Ratings
def getRatings(problem_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/ratings')


def submitRating(problem_id, user_uid, rating):
    encodedProblemId = encodeSlug(problem_id)
    newRating = {user_uid: rating}
    utils.database.updateValue(f'problems/{encodedProblemId}/ratings', newRating)


def deleteRating(problem_id, user_uid):
    encodedProblemId = encodeSlug(problem_id)
    utils.database.delete(f'problems/{encodedProblemId}/ratings/{user_uid}')


#Comments
def getComments(problem_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments')

def getComment(problem_id, comment_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments/{comment_id}')


def submitComment(problem_id, user_uid, comment):
    encodedProblemId = encodeSlug(problem_id)
    utc_now = datetime.datetime.now(pytz.utc).isoformat()
    newComment = {
        'user_uid': user_uid,
        'text': comment,
        'date': utc_now
    }
    newCommentId = utils.database.addChildWithUniqueId(f'problems/{encodedProblemId}/comments', newComment)

    return newCommentId


def deleteComment(problem_id, user_uid, comment_id):
    encodedProblemId = encodeSlug(problem_id)
    comment = getComment(problem_id, comment_id)
    if comment:
        if comment.get('user_uid') == user_uid:
            utils.database.delete(f'problems/{encodedProblemId}/comments/{comment_id}')
        else:
            print("Unauthorized attempt to delete a comment.")
    else:
        print("Comment not found.")

    
#Projects
def getProjects(user_uid):
    return utils.database.getValue(f'users/{user_uid}/projects')

def getProject(user_uid, problem_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'users/{user_uid}/projects/{encodedProblemId}')


def addProject(user_uid, problem_id):
    encodedProblemId = encodeSlug(problem_id)
    newProject = {encodedProblemId: problem_id}
    utils.database.updateValue(f'users/{user_uid}/projects', newProject)


def deleteProject(user_uid, problem_id):
    encodedProblemId = encodeSlug(problem_id)
    utils.database.delete(f'users/{user_uid}/projects/{encodedProblemId}')



def getProblemSlug(area, problem_id):
    problemSlug = createSlug(area, problem_id)
    slugExists = utils.database.checkExists(f'{PROBLEMS_KEY}/items/{problemSlug}')
    if not slugExists:
        problemSlug = getSlugFromUrlMapping(problemSlug)
        if not problemSlug:
            problemSlug = getProblemSlugFromPartialSlug(area, problem_id)

    return decodeSlug(problemSlug)


def getProblemSlugWithSlug(slug):
    areaName, problemId = getSlugData(slug)
    return getProblemSlug(areaName, problemId)


def getSlugFromUrlMapping(slug):
    encodedSlug = encodeSlug(slug)
    newUrl = utils.database.getValue(f'url_mappings/{encodedSlug}')
    if newUrl and not newUrl == '':
        return getProblemSlugWithSlug(newUrl)

    return ""


def getProblemSlugFromPartialSlug(areaName, problem_id):
    all_slugs = utils.database.getKeys(f'{PROBLEMS_KEY}/items/{areaName}')
    possible_matches = [slug for slug in all_slugs if slug.startswith(problem_id)]

    if not possible_matches:
        return None
    best_match = min(possible_matches, key=len)
    
    print(f"Best partial match found: {best_match}")
    
    return createSlug(areaName, best_match)


@lru_cache(maxsize=10)
def getVideoData(area, problemId):
    problemSlug = getProblemSlug(area, problemId)
    if(problemSlug):
        videoData = utils.database.getValue(f'{PROBLEMS_KEY}/items/{area}/{problemId}')
    return videoData


@lru_cache(maxsize=10)
def getVideoDataWithSlug(slug):
    area, problemId = getSlugData(slug)
    return getVideoData(area, problemId)


def getVideoDataWithSlugs(problem_ids):
    decoded_problem_ids = [decodeSlug(problemId) for problemId in problem_ids]
    values = utils.database.getChildsValue(f'{PROBLEMS_KEY}/items', decoded_problem_ids)
    return {encodeSlug(decoded_id): value for decoded_id, value in values.items()}


@lru_cache(maxsize=10)
def getVideoDataFromZone(zone_code):
    return utils.database.getValue(f'{PROBLEMS_KEY}/items/{zone_code}')


@lru_cache(maxsize=10)
def getUrlMappings():
    return utils.database.getValue('url_mappings')


def deleteSlug(slugId):
    return utils.database.delete(f'url_mappings/{slugId}')


def addSlug(slugId, newSlug):
    encodedSlugId = encodeSlug(slugId)
    utils.database.updateValue('url_mappings', {encodedSlugId: newSlug})


def addDisableSlug(oldSlug):
    addSlug(oldSlug, '')


def deprecateSlug(oldSlug, newSlug):
    addSlug(oldSlug, newSlug)
    migrateData(oldSlug, newSlug)


def migrateData(oldSlug, newSlug):
    oldEncodedSlug = encodeSlug(oldSlug)
    newEncodedSlug = encodeSlug(newSlug)
    
    # Migrate ratings
    oldRatings = getRatings(oldEncodedSlug)
    if oldRatings:
        utils.database.setValue(f'problems/{newEncodedSlug}/ratings', oldRatings)
        utils.database.delete(f'problems/{oldEncodedSlug}/ratings')

    # Migrate comments
    oldComments = getComments(oldEncodedSlug)
    if oldComments:
        utils.database.setValue(f'problems/{newEncodedSlug}/comments', oldComments)
        utils.database.delete(f'problems/{oldEncodedSlug}/comments')