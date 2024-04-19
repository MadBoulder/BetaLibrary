import utils.database
import pytz
import datetime

def getAllVideoData():
    return utils.database.getValue('video_data/items')

def getVideoDataDate():
    return utils.database.getDate('video_data')

def getVideoCount():
    return utils.database.getValue('video_count')

def setVideoData(videoData):
    utils.database.setValue('video_data/items', videoData)
    utils.database.updateValue('video_count', len(videoData))
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


def getPlaylistsData():
    return utils.database.getValue('playlist_data/items')

def getPlaylistData(areaCode):
    return utils.database.getValue(f'playlist_data/items/{areaCode}')

def setPlaylistData(playlists):
    utils.database.setValue('playlist_data/items', playlists)
    utils.database.updateDate('playlist_data')


def getAreasData():
    return utils.database.getValue('area_data')

def getAreaData(areaCode):
    return utils.database.getValue(f'area_data/{areaCode}')

def setAreaData(areas):
    utils.database.setValue('area_data', areas)

def getCountriesData():
    return utils.database.getValue('country_data')

def getCountryData(countryCode):
    return utils.database.getValue(f'country_data/{countryCode}')

def getStateData(countryCode, stateCode):
    return utils.database.getValue(f'country_data/{countryCode}/states/{stateCode}')

def setCountryData(countries):
    utils.database.setValue('country_data', countries)

def getAllBoulderData():
    return utils.database.getValue('boulder_data')

def getBoulderData(areaCode):
    return utils.database.getValue(f'boulder_data/{areaCode}')

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


def getVideoData(area, name):
    encodedProblemSlug = utils.database.encodeSlug(area + '/' + name)
    return getVideoDataWithSlug(encodedProblemSlug)


def getVideoDataWithSlug(encodedSlug):
    print("encodedProblemSlug", encodedSlug)
    videoData = utils.database.getValue(f'video_data/items/{encodedSlug}')
    if not videoData:
        newUrl = utils.database.getValue(f'url_mappings{encodedSlug}')
        if newUrl and not newUrl == '':
            encodedNewUrl = utils.database.encodeSlug(newUrl)
            videoData = utils.database.getValue(f'video_data/items/{encodedNewUrl}')
    return videoData


def getVideoDataFromZone(zone_code):
    return utils.database.getValueByField('video_data/items', 'zone_code', zone_code)


def getUrlMappings():
    return utils.database.getValue('url_mappings')


def deleteSlug(slugId):
    return utils.database.delete(f'url_mappings/{slugId}')


def updateSlug(slugId, newSlug):
    utils.database.updateValue('url_mappings', {slugId: newSlug})


def disableSlug(oldSlug):
    oldEncodedSlug = utils.database.encodeSlug(oldSlug)
    utils.database.updateValue('url_mappings', {oldEncodedSlug: ''})


def deprecateSlug(oldSlug, newSlug):
    oldEncodedSlug = utils.database.encodeSlug(oldSlug)
    utils.database.updateValue('url_mappings', {oldEncodedSlug: newSlug})

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
        utils.database.setValue(f'problems/{newEncodedSlug}/ratings', oldComments)
        utils.database.delete(f'problems/{oldEncodedSlug}/comments')