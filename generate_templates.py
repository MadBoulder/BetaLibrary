#import sava
#import sant_joan
import load_map

def main():
	# load_map.load_map("data/sant_joan.txt", None, False).save("templates/sant_joan.html")
	# load_map.load_map("data/savassona/savassona.txt", False).save("templates/savassona.html")
	with open('templates/savassona.html', 'w') as template:
	 	template.write(load_map.load_map("data/savassona/savassona.txt", True))
	with open('templates/sant_joan.html', 'w') as template:
	 	template.write(load_map.load_map("data/sant_joan/sant_joan.txt", True))

if __name__ == '__main__':
    main()