from handle_channel_data import updateData as updateData
from update_pages_and_templates import updatePages
from sitemap_generator import generate_sitemaps as generate_sitemaps

if __name__ == "__main__":
    print("\nHandle Channel Data\n")
    updateData()

    print("\nUpdating pages and templates\n")
    updatePages()

    print("\nUpdating sitemap\n")
    generate_sitemaps()
    
    print("\nUpdate completed!\n")
