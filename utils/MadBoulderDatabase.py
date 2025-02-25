import utils.database
import pytz
from datetime import datetime
from functools import lru_cache
import json
import sys
import utils.zone_helpers

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

def setPlaylistItem(zone_code, data):
    utils.database.setValue(f'playlist_data/items/{zone_code}', data)
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


def getUserRatings(uid):
    return []


def submitRating(problem_id, user_uid, rating):
    encodedProblemId = encodeSlug(problem_id)
    newRating = {user_uid: rating}
    utils.database.updateValue(f'problems/{encodedProblemId}/ratings', newRating)


def deleteRating(problem_id, user_uid):
    encodedProblemId = encodeSlug(problem_id)
    utils.database.delete(f'problems/{encodedProblemId}/ratings/{user_uid}')


#Comments
def getAllProblems():
    return utils.database.getValue('problems')


def getAllComments():
    problems = getAllProblems()

    comments = []
    for problemId, problem in problems.items():
        problemComments = problem.get('comments', {})
        for commentId, comment in problemComments.items():
            videoData = getVideoDataWithSlug(problemId)
            userData = getUserBasicData(comment.get('user_uid'))
            userDisplay = userData['displayName'] if userData['displayName'] else userData['email']
            comments.append({
                'problem_id': problemId,
                'comment_id': commentId,
                'text': comment.get('text'),
                'date': comment.get('date'),
                'user_uid': comment.get('user_uid'),
                'user_display': userDisplay,
                'videoData': videoData
            })

    return comments


def getComments(problem_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments')

def getComment(problem_id, comment_id):
    encodedProblemId = encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/comments/{comment_id}')

def getUserComments(uid):
    problems = getAllProblems()

    userComments = []
    for problemId, problem in problems.items():
        comments = problem.get('comments', {})
        for commentId, comment in comments.items():
            if comment.get('user_uid') == uid:
                videoData = getVideoDataWithSlug(problemId)
                userComments.append({
                    'problem_id': problemId,
                    'comment_id': commentId,
                    'text': comment.get('text'),
                    'date': comment.get('date'),
                    'videoData': videoData
                })

    return userComments


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
def getProjects(uid):
    projectsList = []
    if uid:
        projectIds = utils.database.getValue(f'users/{uid}/projects')
        if projectIds:
            for problemId in projectIds:
                videoData = getVideoDataWithSlug(problemId)
                if videoData:
                    projectsList.append(videoData)
                else:
                    print(f"Data for problem ID {problemId} not found.")

    return projectsList


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

@lru_cache(maxsize=1)
def getContributorNames():
    """Retrieve a list of contributor names from the database with caching."""
    print("get_contributor_names")
    
    # Retrieve all contributors at once
    contributors = utils.database.getValue('contributors')  # Retrieves all contributors
    
    if not contributors:
        print("No contributors found.")
        return []
    
    # Extract names from the retrieved data
    contributor_names = [contributor['name'] for contributor in contributors.values() if 'name' in contributor]
    return contributor_names


def getAllUsers():
    users_list = []
    admins_list = []

    allUsers = utils.database.getAllUsers()
    for user in allUsers:
        uid = user.uid
        userDetails = utils.database.getUserDetails(uid)

        userInfo = buildUserInfo(user, userDetails)
        users_list.append(userInfo)

        if checkAdminPrivileges(uid):
            admins_list.append(userInfo)

    return users_list, admins_list


def buildUserInfo(user, userDetails=None):
    """Helper function to build user info dictionary."""
    user_info = {
        'uid': user.uid,
        'email': user.email,
        'displayName': user.display_name,
        'contributor_status': 'N/A',  # Default value
        'climber_id': 'N/A',  # Default value
        'profile_completed': False # Default value
    }

    if userDetails:
        user_info['contributor_status'] = userDetails.get('contributor_status', 'N/A')
        user_info['climber_id'] = userDetails.get('climber_id', 'N/A')
        user_info['profile_completed'] = True

    return user_info


def checkAdminPrivileges(uid):
    user_record = utils.database.getUserRecord(uid)
    if user_record.custom_claims:
        return user_record.custom_claims.get('admin', False)
    else:
        return False
    

def getUserUid(id_token):
    decoded_token = utils.database.verifyToken(id_token)
    uid = decoded_token['uid']
    return uid


def getUserBasicData(uid):
    user_data = {}
    if uid:
        user_record = utils.database.getUserRecord(uid)
        user_data['uid'] = uid
        user_data['displayName'] = user_record.display_name
        user_data['email'] = user_record.email

    return user_data


def getUserData(uid):
    user_data = {}
    if uid:
        user_data = getUserBasicData(uid)

        user_details = utils.database.getUserDetails(uid)
        if(user_details):
            user_data.update(user_details)

    return user_data


def getUserStats(uid):
    user_data = {}
    if uid:
        user_data = getUserData(uid)

        account_creation_timestamp = getUserCreationTimestamp(uid)
        account_creation_date = datetime.fromtimestamp(account_creation_timestamp)
        user_data['dateCreated'] = account_creation_date.strftime('%Y-%m-%d')

        time_since_creation = datetime.now() - account_creation_date
        user_data['timeSinceCreation'] = str(time_since_creation.days) + " days"

        contributor_stats = utils.zone_helpers.calculate_contributor_stats(user_data['climber_id'])
        user_data['contributor_stats'] = contributor_stats
        user_data['total_contributors'] = getContributorsCount()

    return user_data


def getUserEmail(uid):
    user_record = utils.database.getUserRecord(uid)
    return user_record.email


def getUserDisplayName(uid):
    user_record = utils.database.getUserRecord(uid)
    return user_record.display_name


def getUserCreationTimestamp(uid):
    if uid:
        user_metadata = utils.database.getUserMetadata(uid)
        return user_metadata.creation_timestamp / 1000 # Convert from milliseconds to seconds


def updateUserDisplayName(uid, display_name):
    return utils.database.updateUserDisplayName(uid, display_name)


def updateUserContributorStatus(uid, contributor_status):
    return utils.database.updateUserDetails(uid, 'contributor_status', contributor_status)


def updateUserClimberId(uid, climberId):
    return utils.database.updateUserDetails(uid, 'climber_id', climberId)


def updateUserAdminRole(uid, admin=False):
    return utils.database.updateUserAdminRole(uid, admin)


def deleteUser(uid):
    return utils.database.deleteUser(uid)


def removeUser(uid):
    return utils.database.removeUser(uid)

