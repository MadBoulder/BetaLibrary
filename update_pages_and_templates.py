from generate_pages import main as generate_pages_main
from generate_maps import main as generate_maps_main
from generate_country_pages import main as generate_country_main
from generate_problem_pages import main as generate_problem_pages_main
from generate_sector_pages import main as generate_sector_pages

if __name__ == "__main__":
    print("\nUpdating and adding maps\n")
    generate_maps_main()
    print("\nUpdating and adding zone pages\n")
    generate_pages_main()
    print("\nUpdating and adding country and state pages\n")
    generate_country_main()
    print("\nUpdating and adding problem pages\n")
    generate_problem_pages_main()
    print("\nUpdating and adding sector pages\n")
    generate_sector_pages()
