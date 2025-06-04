import utils.MadBoulderDatabase
import argparse

AFFILIATE_TAG = "bg_ref=CcTfpUnP2J"
CLIMB_EUROPE_DOMAIN = "climb-europe.com"

def main():
    parser = argparse.ArgumentParser(description="Check Climb-Europe affiliate links in area guides.")
    parser.add_argument('--only-with-link', action='store_true', help='Show only areas that have a Climb-Europe guide link')
    parser.add_argument('--only-without-link', action='store_true', help='Show only areas without any Climb-Europe guide link')
    args = parser.parse_args()

    areas = utils.MadBoulderDatabase.getAreasData()

    for areaCode, area in areas.items():
        area_name = area.get("name", "Unknown Area")
        guides = area.get("guides", [])
        climb_europe_links = []

        for guide in guides:
            links = guide.get("link", [])
            if isinstance(links, str):
                links = [links]
            for link in links:
                if CLIMB_EUROPE_DOMAIN in link:
                    climb_europe_links.append(link)

        has_link = bool(climb_europe_links)

        if args.only_with_link and not has_link:
            continue
        if args.only_without_link and has_link:
            continue

        if not has_link:
            print(f"{area_name} — No Climb-Europe guide link")
        else:
            for link in climb_europe_links:
                if AFFILIATE_TAG in link:
                    print(f"✔️ {area_name} — Affiliate link present ({link})")
                else:
                    print(f"❌ {area_name} — Climb-Europe link without affiliate ({link})")

if __name__ == "__main__":
    main()
