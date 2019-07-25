import load_map
import os

def main():
	"""
	"""
	areas = next(os.walk('data/'))[1] 
	all_data = ['data/' + area + '/' + area + '.txt' for area in areas]
	for area in areas:
		with open('templates/maps/'+area+'.html', 'w') as template:
			template.write(load_map.load_map('data/' + area + '/' + area + '.txt', True))

	with open('templates/maps/all.html', 'w') as template:
	 	template.write(load_map.load_general_map(all_data, True))

if __name__ == '__main__':
    main()