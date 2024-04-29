import utils.MadBoulderDatabase
import time
import threading

NAME = 'name'

class SearchManager:
    def __init__(self):
        self.tasks = {}
        self.results = {}
        self.cancellation_events = {}
        self.lock = threading.Lock()
        self.session_active = {}


    def search(self, session_id, query, max_score):
        print(f"{threading.current_thread().name}: New search for ({query}) requested")
        with self.lock:
            self.stop_all_searches(session_id)
            print(f"{threading.current_thread().name}: Start search for ({query})")
            self.session_active[session_id] = True
            event = threading.Event()
            self.cancellation_events[session_id] = event
            self.results[session_id] = {"areas": None, "problems": None}

        if event.is_set():
            print(f"{threading.current_thread().name}: Cancel search ({query})")
            self.cleanup(session_id)
            return
        
        print(f"{threading.current_thread().name}: Fetch Search Data ({query})")
        searchData = utils.MadBoulderDatabase.getSearchData()
        
        if event.is_set():
            print(f"{threading.current_thread().name}: Cancel search ({query})")
            self.cleanup(session_id)
            return

        print(f"{threading.current_thread().name}: Create threads ({query})")
        zone_thread = threading.Thread(target=self.search_zone, args=(session_id, query, searchData, max_score, event))
        problem_thread = threading.Thread(target=self.search_problem, args=(session_id, query, searchData, max_score, event))
        
        if event.is_set():
            print(f"{threading.current_thread().name}: Cancel search ({query})")
            self.cleanup(session_id)
            return
        
        self.tasks[session_id] = [zone_thread, problem_thread]
        print(f"{threading.current_thread().name}: Start threads ({query})")
        for thread in self.tasks[session_id]:
            thread.start()

        for thread in self.tasks[session_id]:
            thread.join()

        if event.is_set():
            print(f"{threading.current_thread().name}: Cancel search ({query})")
            self.cleanup(session_id)
            return

        print(f"{threading.current_thread().name}: Search ({query}) completed")
        results = self.results.get(session_id, {})
        self.cleanup(session_id)
        print(f"{threading.current_thread().name}: Return ({query}) results")
        return results


    def search_zone(self, session_id, query, searchData, max_score, cancel_event):
        if cancel_event.is_set():
            print(f"{threading.current_thread().name}: Zone ({query}) search cancelled.")
            return
        
        start_time = time.time()
        self.results[session_id]['areas'] = search(query, searchData['areas'], cancel_event, max_score)
        elapsed_time = time.time() - start_time
        print(f"{threading.current_thread().name}: Search Zone ({query}) execution time: {elapsed_time} seconds")


    def search_problem(self, session_id, query, searchData, max_score, cancel_event):
        if cancel_event.is_set():
            print(f"{threading.current_thread().name}: Problem ({query}) search cancelled.")
            return
        
        start_time = time.time()
        problem_results = search(query, searchData['problems'], cancel_event, max_score)
        elapsed_time = time.time() - start_time
        print(f"{threading.current_thread().name}: Search Problem ({query}) execution time: {elapsed_time} seconds")

        if cancel_event.is_set():
            print(f"{threading.current_thread().name}: Problem ({query}) search cancelled.")
            return
        
        updated_problems = []
        if problem_results:
            problem_ids = [problemId for problemId, _ in problem_results]
            problem_details = utils.MadBoulderDatabase.getVideoDataWithSlugs(problem_ids)
            for problemId, problem in problem_results:
                problemData = problem_details.get(problemId, {})
                problem.update({
                    'secure_slug': problemData.get('secure_slug', 'N/A'),
                    'grade': problemData.get('grade', 'N/A'),
                    'zone': problemData.get('zone', 'N/A')
                })
                updated_problems.append((problemId, problem))
            
        self.results[session_id]['problems'] = updated_problems


    def stop_all_searches(self, session_id):
        if self.session_active.get(session_id, False):
            print(f"{threading.current_thread().name}:  stop_all_searches")
            if session_id in self.cancellation_events:
                print(f"{threading.current_thread().name}:  set cancel event")
                self.cancellation_events[session_id].set()

            if session_id in self.tasks:
                for thread in self.tasks[session_id]:
                    if thread.is_alive():
                        print(f"{threading.current_thread().name}:  thread active, wait to finish.")
                        thread.join()
            
            print(f"{threading.current_thread().name}:  Wait for session {session_id} to complete")
            while True:
                if not self.session_active.get(session_id, False):
                    print(f"{threading.current_thread().name}: Session {session_id} completed.")
                    break
                time.sleep(0.1)


    def cleanup(self, session_id):
        print(f"{threading.current_thread().name}:  Perform cleanup")
        if session_id in self.tasks:
            del self.tasks[session_id]
        if session_id in self.results:
            del self.results[session_id]
        if session_id in self.cancellation_events:
            del self.cancellation_events[session_id]
        self.session_active[session_id] = False
        

class bidict(dict):
    """
    Bidirectional dictionary. Given a normal Python dict it enables to retrieve values by
    key and keys by value
    """
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)


def iterative_levenshtein(s, t, costs=(1, 1, 3)):
    """ 
    iterative_levenshtein(s, t) -> ldist
    ldist is the Levenshtein distance between the strings 
    s and t.
    For all i and j, dist[i,j] will contain the Levenshtein 
    distance between the first i characters of s and the 
    first j characters of t

    costs: a tuple or a list with three integers (d, i, s)
           where d defines the costs for a deletion
                 i defines the costs for an insertion and
                 s defines the costs for a substitution

    Source: https://www.python-course.eu/levenshtein_distance.php
    """
    rows = len(s)+1
    cols = len(t)+1
    deletes, inserts, substitutes = costs

    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings
    # by deletions:
    for row in range(1, rows):
        dist[row][0] = row * deletes
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for col in range(1, cols):
        dist[0][col] = col * inserts

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row-1][col] + deletes,
                                 dist[row][col-1] + inserts,
                                 dist[row-1][col-1] + cost)  # substitution
    #  for r in range(rows):
    #      print(dist[r])
    return dist[row][col]


def lcw(u, v):
    """
    Return length of an LCW of strings u and v and its starting indexes.

    (l, i, j) is returned where l is the length of an LCW of the strings u, v
    where the LCW starts at index i in u and index j in v.

    Source: https://www.sanfoundry.com/python-program-find-longest-common-substring-using-dynamic-programming-bottom-up-approach/
    """
    # c[i][j] will contain the length of the LCW at the start of u[i:] and
    # v[j:].
    c = [[-1]*(len(v) + 1) for _ in range(len(u) + 1)]

    for i in range(len(u) + 1):
        c[i][len(v)] = 0
    for j in range(len(v)):
        c[len(u)][j] = 0

    lcw_i = lcw_j = -1
    length_lcw = 0
    for i in range(len(u) - 1, -1, -1):
        for j in range(len(v)):
            if u[i] != v[j]:
                c[i][j] = 0
            else:
                c[i][j] = 1 + c[i + 1][j + 1]
                if length_lcw < c[i][j]:
                    length_lcw = c[i][j]
                    lcw_i = i
                    lcw_j = j

    return length_lcw, lcw_i, lcw_j


def measure_similarity(query, zone):
    """
    Measure both levenshtein distance and lowest common string between
    the search query and the name of bouldering zone and return both values.
    This can be later used to determine search matches.
    """
    levenshtein = iterative_levenshtein(query, zone)
    longest_sub, _, _ = lcw(query.lower(), zone.lower())
    return levenshtein, longest_sub

    
def simple_search(query, items, max_score=0):
    results = []
    
    if not query:
        return []
    
    for item in items:
        name = item.get("name", "").lower()
        if query.lower() in name:
            results.append(item)

    return results
    

def search(query, items, cancel_event , max_score=0):
    """
    From an input search query, return all matches with a score of 0 or lower than max_score.

    The score is computed as:
        - 0 if perfect match
        - levenshtein / (longest substring ^ 4 + 1) otherwise
    """

    if not query:
        return []
    
    for item in items.values():
        if cancel_event.is_set():
            print(f"{threading.current_thread().name}: Search ({query}) cancelled.")
            return []
        
        lev, long_sub = measure_similarity(query, item[NAME])
        score = lev / (long_sub ** 4 + 1)
        item['score'] = score
        # If the inputed text is entirely matched in a item,
        # add a score of 0
        if long_sub == len(query):
            item['score'] = 0
    items_to_show = [(key, item) for key, item in items.items() if item['score'] <= max_score]
    
    items_to_show.sort(key=lambda x: x[1]['score'])    

    return items_to_show