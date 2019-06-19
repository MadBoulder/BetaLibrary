import sava
import sant_joan

def main():
    sava.get_savassona_map(False).save("templates/savassona.html")
    sant_joan.get_sant_joan_map(False).save("templates/sant_joan.html")

if __name__ == '__main__':
    main()