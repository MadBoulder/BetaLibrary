from generate_pages import main as generate_pages_main
from generate_templates import main as generate_templates_main

if __name__ == "__main__":
    print("\nUpdating and adding templates\n")
    generate_templates_main()
    print("\nUpdating and adding pages\n")
    generate_pages_main()
