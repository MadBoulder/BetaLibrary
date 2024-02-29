import os

from datetime import datetime

def get_files(folders_to_parse, include_subfolders, file_extension):
    html_files = []
    for folder in folders_to_parse:
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if item.endswith(file_extension) and os.path.isfile(item_path):
                html_files.append(item_path)
            elif include_subfolders and os.path.isdir(item_path):
                subfolder_files = get_files([item_path], include_subfolders, file_extension)
                html_files.extend(subfolder_files)
    return html_files


def create_sitemap(xml_filename, html_files):
    with open(xml_filename, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for html_file in html_files:
            with open(html_file, "r", encoding="utf-8") as html:

                url = html_file.replace("\\", "/")  # Replace backslashes with slashes for URLs
                print(url)
                f.write(f'  <url>\n')
                f.write(f'    <loc>http://madboulder.org/{url}</loc>\n')
                last_modified_date = datetime.fromtimestamp(os.path.getmtime(html_file)).date()
                last_modified_date_str = last_modified_date.strftime('%Y-%m-%d')
                f.write(f'    <lastmod>{last_modified_date_str}</lastmod>\n')
                f.write(f'  </url>\n')

        f.write('</urlset>\n')


if __name__ == "__main__":
    sitemapFolders = ["templates", "templates/errors", "templates/policy", "templates/es"]
    create_sitemap("sitemap-main.xml", get_files(sitemapFolders, False, ".html"))
    create_sitemap("sitemap-zones.xml", get_files(["templates/zones"], True, ".html"))
    create_sitemap("sitemap-sectors.xml", get_files(["templates/sectors"], True, ".html"))
    create_sitemap("sitemap-problems.xml", get_files(["templates/problems"], True, ".html"))
    create_sitemap("sitemap-countries.xml", get_files(["templates/countries"], True, ".html"))
    create_sitemap("sitemap-states.xml", get_files(["templates/states"], True, ".html"))
    create_sitemap("sitemap-contributors.xml", get_files(["templates/contributors"], True, ".html"))
    create_sitemap("sitemap-pdfs.xml", get_files(["data/zones"], True, ".pdf"))
    
    
    print("Sitemaps created successfully!")