import threading
import utils.helpers
import time
import statistics

NUM_RESULTS = 4

num_iterations = 10
execution_times = []

def test():
    for i in range(num_iterations):
        query = "your_query_here"  # Replace with your actual query
        start_time = time.time()
        search_results = search(query)
        end_time = time.time()
        elapsed_time = end_time - start_time
        execution_times.append(elapsed_time)
        print(f"Iteration {i + 1}: Search execution time: {elapsed_time} seconds")
        time.sleep(10)

    # Calculate and print the median execution time
    median_time = statistics.median(execution_times)
    print(f"Median execution time over {num_iterations} iterations: {median_time} seconds")

def search(query='can boquet'):
    search_results = {}
    print(f"Search request: {query}")
    if query:
        start_time = time.time()
        threads = []

        def search_zone():
            search_zone_start_time = time.time()
            search_results['zones'] = utils.helpers.search_zone(
                query, NUM_RESULTS, exact_match=True)
            search_zone_elapsed_time = time.time() - search_zone_start_time
            print(f"Search Zone execution time: {search_zone_elapsed_time} seconds")
        
        def search_sector():
            search_sector_start_time = time.time()
            search_results['sectors'] = utils.helpers.search_sector(
                query, NUM_RESULTS, exact_match=True)
            search_sector_elapsed_time = time.time() - search_sector_start_time
            print(f"Search Sector execution time: {search_sector_elapsed_time} seconds")

        def search_problem():
            search_problem_start_time = time.time()
            search_results['problems'] = utils.helpers.search_problem(
                query, NUM_RESULTS, exact_match=True)
            search_problem_elapsed_time = time.time() - search_problem_start_time
            print(f"Search Problem execution time: {search_problem_elapsed_time} seconds")

        def search_beta():
            search_beta_start_time = time.time()
            search_results['videos'] = [] 
            #utils.helpers.get_video_from_channel(#query, results=5)
            search_beta_elapsed_time = time.time() - search_beta_start_time
            print(f"Search Beta execution time: {search_beta_elapsed_time} seconds")


        search_zone_thread = threading.Thread(target=search_zone)
        search_sector_thread = threading.Thread(target=search_sector)
        search_problem_thread = threading.Thread(target=search_problem)
        search_beta_thread = threading.Thread(target=search_beta)

        threads.extend([search_zone_thread, search_sector_thread, search_problem_thread, search_beta_thread])

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_elapsed_time = time.time() - start_time
        print(f"Search execution time: {total_elapsed_time} seconds")


# start the server
if __name__ == '__main__':
    #test()
    search("can boquet")
