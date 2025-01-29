import sys
from handle_channel_data import updateData
from update_pages_and_templates import updatePages
from sitemap_generator import generate_sitemaps

def run_update_step(step_name, step_function):
    """Run a step of the update process with error handling"""
    print(f"\n{step_name}\n")
    try:
        step_function()
    except Exception as e:
        print(f"Error in {step_name}: {str(e)}")
        return False
    return True

if __name__ == "__main__":
    try:
        # Run each step and check for failures
        steps = [
            ("Handle Channel Data", updateData),
            ("Updating pages and templates", updatePages),
            ("Updating sitemap", generate_sitemaps)
        ]

        for step_name, step_function in steps:
            if not run_update_step(step_name, step_function):
                print(f"\nUpdate failed at step: {step_name}\n")
                sys.exit(1)

        print("\nUpdate completed successfully!\n")
        sys.exit(0)

    except Exception as e:
        print(f"\nUnexpected error during update: {str(e)}\n")
        sys.exit(1)
