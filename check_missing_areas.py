import utils.helpers


def main():
    sorted_zone_code_counts = utils.helpers.getMissingAreasCount()
    for zone_code, count in sorted_zone_code_counts:
        print(f'{zone_code}: {count}')


if __name__ == "__main__":
    main()