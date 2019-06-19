#import sava
#import sant_joan
import load_map

def main():
	load_map.load_map("data/savassona.txt", False).save("templates/savassona.html")
	load_map.load_map("data/sant_joan.txt", False).save("templates/sant_joan.html")
#    sava.get_savassona_map(False).save("templates/savassona.html")
#	 sant_joan.get_sant_joan_map(False).save("templates/sant_joan.html")

if __name__ == '__main__':
    main()