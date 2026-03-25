import re
import utils.MadBoulderDatabase as MadBoulderDatabase

HOME_TEMPLATES = [
    'templates/home.html',
    'templates/es/home.html',
]

STAT_MARKERS = {
    'STAT_AREAS': MadBoulderDatabase.getAreasCount,
    'STAT_VIDEOS': MadBoulderDatabase.getVideoCount,
    'STAT_CONTRIBUTORS': MadBoulderDatabase.getContributorsCount,
}


def main():
    stats = {}
    for key, fn in STAT_MARKERS.items():
        stats[key] = fn()
        print(f"  {key}: {stats[key]}")

    for template_path in HOME_TEMPLATES:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for key, value in stats.items():
            # Replace: <!-- STAT_KEY -->OLD_VALUE+ with <!-- STAT_KEY -->NEW_VALUE+
            pattern = rf'(<!-- {key} -->)\S+?\+'
            replacement = rf'\g<1>{value}+'
            content = re.sub(pattern, replacement, content)

        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  Updated {template_path}")


if __name__ == '__main__':
    main()
