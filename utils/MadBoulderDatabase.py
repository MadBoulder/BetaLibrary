import utils.database
import pytz
import datetime
from functools import lru_cache
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

def getAllVideoData():
    return utils.database.getValue('video_data/items')

def getVideoDataDate():
    return utils.database.getDate('video_data')

def getVideoCount():
    return utils.database.getValue('video_count')

def setVideoData(videoData):
    utils.database.setValue('video_data/items', videoData)
    utils.database.setValue('video_count', len(videoData))
    utils.database.updateDate('video_data')
    
def get_video_data_search_optimized():
    return utils.database.getValue('video_data_search_optimized')

def setVideoDataSearchOptimized(videoData):
    utils.database.setValue('video_data_search_optimized', videoData)


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
    data =  utils.database.getValue('playlist_data/items')
    data_size = estimate_data_size(data)
    print(f"Data fetched for 'getPlaylistsData': {data_size} bytes")
    return data;

def getPlaylistData(areaCode):
    data =  utils.database.getValue(f'playlist_data/items/{areaCode}')
    return data;

def setPlaylistData(playlists):
    utils.database.setValue('playlist_data/items', playlists)
    utils.database.updateDate('playlist_data')

def getAreasCount():
    return utils.database.getValue('areas_count')

@lru_cache(maxsize=10)
def getAreasData():
    data = utils.database.getValue('area_data')
    data_size = estimate_data_size(data)
    print(f"Data fetched for 'getAreasData': {data_size} bytes")
    return data;

def getAreaData(areaCode):
    data = utils.database.getValue(f'area_data/{areaCode}')
    return data;

def setAreaData(areas):
    utils.database.setValue('area_data', areas)
    areaCount = len(areas)
    utils.database.setValue('areas_count', areaCount)

@lru_cache(maxsize=10)
def getCountriesData():
    data = utils.database.getValue('country_data')
    data_size = estimate_data_size(data)
    print(f"Data fetched for 'getCountriesData': {data_size} bytes")
    return data;

def getCountryData(countryCode):
    data = utils.database.getValue(f'country_data/{countryCode}')
    return data;

def getStateData(countryCode, stateCode):
    return utils.database.getValue(f'country_data/{countryCode}/states/{stateCode}')

def setCountryData(countries):
    utils.database.setValue('country_data', countries)

def getAllBoulderData():
    data = utils.database.getValue('boulder_data')
    data_size = estimate_data_size(data)
    print(f"Data fetched for 'getAllBoulderData': {data_size} bytes")
    return data;

def getBoulderData(areaCode):
    data = utils.database.getValue(f'boulder_data/{areaCode}')
    return data;

def setBoulderData(boulders):
    utils.database.setValue('boulder_data', boulders)


#Ratings
def getRatings(problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/ratings')


def submitRating(problem_id, user_uid, rating):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    newRating = {user_uid: rating}
    utils.database.updateValue(f'problems/{encodedProblemId}/ratings', newRating)


def deleteRating(problem_id, user_uid):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    utils.database.delete(f'problems/{encodedProblemId}/ratings/{user_uid}')


#Comments
def getComments(problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments')

def getComment(problem_id, comment_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments/{comment_id}')


def submitComment(problem_id, user_uid, comment):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    utc_now = datetime.datetime.now(pytz.utc).isoformat()
    newComment = {
        'user_uid': user_uid,
        'text': comment,
        'date': utc_now
    }
    newCommentId = utils.database.addChildWithUniqueId(f'problems/{encodedProblemId}/comments', newComment)

    return newCommentId


def deleteComment(problem_id, user_uid, comment_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
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
    encodedProblemId = utils.database.encodeSlug(problem_id)
    return utils.database.getValue(f'users/{user_uid}/projects/{encodedProblemId}')


def addProject(user_uid, problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    newProject = {encodedProblemId: problem_id}
    utils.database.updateValue(f'users/{user_uid}/projects', newProject)


def deleteProject(user_uid, problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    utils.database.delete(f'users/{user_uid}/projects/{encodedProblemId}')




def getProblemSlug(area, name):
    encodedProblemSlug = utils.database.encodeSlug(area + '/' + name)
    return utils.database.decodeSlug(getProblemSlugWithSlug(encodedProblemSlug))


def getProblemSlugWithSlug(slug):
    encodedSlug = utils.database.encodeSlug(slug)
    problemSlug = encodedSlug
    slugExists = utils.database.checkExists(encodedSlug)
    if not slugExists:
        problemSlug = getSlugFromUrlMapping(encodedSlug)
        if not problemSlug:
            problemSlug = getProblemSlugFromPartialSlug(encodedSlug)

    return utils.database.decodeSlug(problemSlug)


def getSlugFromUrlMapping(encodedSlug):
    problemSlug = ""

    newUrl = utils.database.getValue(f'url_mappings/{encodedSlug}')
    if newUrl and not newUrl == '':
        encodedNewUrl = utils.database.encodeSlug(newUrl)
        snapshot = utils.database.getValue(f'video_data/items/{encodedNewUrl}', shallow=True)
        if snapshot is not None:
            problemSlug = encodedNewUrl

    return problemSlug


def getProblemSlugFromPartialSlug(partialEncodedSlug):
    all_slugs = utils.database.getKeys('video_data/items')
    possible_matches = [slug for slug in all_slugs if slug.startswith(partialEncodedSlug)]
    
    if not possible_matches:
        return None
    best_match = min(possible_matches, key=len)
    print(f"Best partial match found: {best_match}")
    
    return best_match


@lru_cache(maxsize=10)
def getVideoData(area, name):
    encodedProblemSlug = utils.database.encodeSlug(area + '/' + name)
    return getVideoDataWithSlug(encodedProblemSlug)


@lru_cache(maxsize=10)
def getVideoDataWithSlug(slug):
    problemSlug = getProblemSlugWithSlug(slug)
    if(problemSlug):
        encodedProblemSlug = utils.database.encodeSlug(problemSlug)
        videoData = utils.database.getValue(f'video_data/items/{encodedProblemSlug}')
    return videoData


def getVideoDataFromZone(zone_code):
    return utils.database.getValueByField('video_data/items', 'zone_code', zone_code)


@lru_cache(maxsize=10)
def getUrlMappings():
    return utils.database.getValue('url_mappings')


def deleteSlug(slugId):
    return utils.database.delete(f'url_mappings/{slugId}')


def addSlug(slugId, newSlug):
    encodedSlugId = utils.database.encodeSlug(slugId)
    utils.database.updateValue('url_mappings', {encodedSlugId: newSlug})


def addDisableSlug(oldSlug):
    addSlug(oldSlug, '')


def deprecateSlug(oldSlug, newSlug):
    addSlug(oldSlug, newSlug)
    migrateData(oldSlug, newSlug)


def migrateData(oldSlug, newSlug):
    oldEncodedSlug = utils.database.encodeSlug(oldSlug)
    newEncodedSlug = utils.database.encodeSlug(newSlug)
    
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