#import sava
#import sant_joan
import load_map

def main():
	load_map.load_map("data/savassona/savassona.txt", False).save("templates/savassona.html")
#	load_map.load_map("data/sant_joan.txt", None, False).save("templates/sant_joan.html")

if __name__ == '__main__':
    main()