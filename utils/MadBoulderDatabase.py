import utils.database
import pytz
import datetime

def get_video_data():
    return utils.database.getValue('video_data/items')

def get_video_data_date():
    return utils.database.getValue('video_data/date')

def get_video_count():
    return utils.database.getValue('video_count')

def setVideoData(videoData, reset=False):
        utils.database.updateNodeWithItems('video_data', videoData, reset)
        utils.database.updateNode('video_count', len(videoData))
    
def get_video_data_search_optimized():
    return utils.database.getValue('video_data_search_optimized/items')

def setVideoDataSearchOptimized(videoData):
    utils.database.updateNodeWithItems('video_data_search_optimized', videoData, reset=True)

def get_contributors_count():
    return utils.database.getValue('contributor_count')

def get_contributors_list():
    print("get_contributors_list")
    return utils.database.getValue('contributors/items')

def setContributorData(contributors):
    utils.database.updateNodeWithItems('contributors', contributors, reset=True)
    utils.database.updateNode('contributor_count', len(contributors))


def get_playlist_data():
    return utils.database.getValue('playlist_data/items')

def setPlaylistData(playlists):
    utils.database.updateNodeWithItems('playlist_data', playlists, reset=True)

def get_zone_data():
    return utils.database.getValue('zone_data/items')

def setAreaData(areas):
    utils.database.updateNodeWithItems('zone_data', areas, reset=True)

def get_country_data():
    return utils.database.getValue('country_data/items')

def setCountryData(countries):
    utils.database.updateNodeWithItems('country_data', countries, reset=True)

def get_boulder_data():
    return utils.database.getValue('boulder_data/items')

def setBoulderData(boulders):
    utils.database.updateNodeWithItems('boulder_data', boulders, reset=True)


#Ratings
def getRatings(problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    return utils.database.getValue(f'problems/{encodedProblemId}/ratings')


def submitRating(problem_id, user_uid, rating):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    newRating = {user_uid: rating}
    utils.database.updateChildNode('problems', encodedProblemId, 'ratings', newRating)


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
    newCommentId = utils.database.updateChildNodeWithUniqueId('problems', encodedProblemId, 'comments', newComment)

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
    utils.database.updateChildNode('users', user_uid, 'projects', newProject)
    return


def deleteProject(user_uid, problem_id):
    encodedProblemId = utils.database.encodeSlug(problem_id)
    utils.database.delete(f'users/{user_uid}/projects/{encodedProblemId}')


def getVideoData(area, name):
    encodedProblemSlug = utils.database.encodeSlug(area + '/' + name)
    return getVideoDataWithSlug(encodedProblemSlug)


def getVideoDataWithSlug(encodedSlug):
    print("encodedProblemSlug", encodedSlug)
    videoData = utils.database.getNestedChild('video_data', encodedSlug)
    if not videoData:
        newUrl = utils.database.getNestedChild('url_mappings', encodedSlug)
        if newUrl and not newUrl == '':
            encodedNewUrl = utils.database.encodeSlug(newUrl)
            videoData = utils.database.getNestedChild('video_data', encodedNewUrl)
    return videoData


def getVideoDataFromZone(zone_code):
    return utils.database.getDataByFieldValue('video_data/items', 'zone_code', zone_code)


def disableSlug(oldSlug):
    oldEncodedSlug = utils.database.encodeSlug(oldSlug)
    newMapping = {oldEncodedSlug: ''}
    utils.database.updateNodeWithItems('url_mappings', newMapping)


def deprecateSlug(oldSlug, newSlug):
    newMapping = {utils.database.encodeSlug(oldSlug): newSlug}
    utils.database.updateNodeWithItems('url_mappings', newMapping)

    migrateData(oldSlug, newSlug)


def migrateData(oldSlug, newSlug):
    oldEncodedSlug = utils.database.encodeSlug(oldSlug)
    newEncodedSlug = utils.database.encodeSlug(newSlug)
    
    # Migrate ratings
    oldRatings = getRatings(oldEncodedSlug)
    if oldRatings:
        utils.database.updateChildNode('problems', newEncodedSlug, 'ratings', oldRatings)
        utils.database.delete(f'problems/{oldEncodedSlug}/ratings')

    # Migrate comments
    oldComments = getComments(oldEncodedSlug)
    if oldComments:
        utils.database.updateChildNode('problems', newEncodedSlug, 'comments', oldComments)
        utils.database.delete(f'problems/{oldEncodedSlug}/comments')