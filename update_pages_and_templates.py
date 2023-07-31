from generate_pages import main as generate_pages_main
from generate_templates import main as generate_templates_main
from generate_problem_pages import main as generate_problem_pages_main
from generate_sector_pages import main as generate_sector_pages

if __name__ == "__main__":
    print("\nUpdating and adding templates\n")
    generate_templates_main()
    print("\nUpdating and adding zone pages\n")
    generate_pages_main()
    print("\nUpdating and adding problem pages\n")
    generate_problem_pages_main()
    print("\nUpdating and adding sector pages\n")
    generate_sector_pages()
