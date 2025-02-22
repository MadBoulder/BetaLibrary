/*!

Name: Open Weather
Dependencies: jQuery, OpenWeatherMap API
Author: Michael Lynch
Author URL: http://michaelynch.com
Date Created: August 28, 2013
Licensed under the MIT license

*/

// Source: https://github.com/michael-lynch/open-weather

;(function($) {

	$.fn.openWeather = function(options) {

		// return if no element was bound
		// so chained events can continue
		if(!this.length) {
			return this;
		}

		// define default parameters
		const defaults = {
			// Widget configuration params
			wrapperTarget: null,
			descriptionTarget: null,
			maxTemperatureTarget: null,
			minTemperatureTarget: null,
			windSpeedTarget: null,
			humidityTarget: null,
			sunriseTarget: null,
			sunsetTarget: null,
			placeTarget: null,
			forecastTarget: null,
			iconTarget: null,
			customIcons: null,
			// Query params
			units: 'c',
			windSpeedUnit: 'Mps',
			city: null,
			lat: null,
			lng: null,
			key: null,
			exclude: null,
			lang: 'en',
			query: 'weather', // default (weather) is current weather. Use onecall for forecast predictions
			success: function() {}, // Callbacks
			error: function(message) {}
		}

		const plugin = this; // define plugin
		const el = $(this); // define element
		plugin.settings = {} // define settings
		plugin.settings = $.extend({}, defaults, options); // merge defaults and options
		const s = plugin.settings; // define settings namespace

		// format time function
		const formatTime = function(unixTimestamp) {
			const milliseconds = unixTimestamp * 1000; // define milliseconds using unix time stamp
			const date = new Date(milliseconds); // create a new date using milliseconds
			let hours = date.getHours(); // define hours
			if(hours > 12) {
				// calculate remaining hours in the day
				let hoursRemaining = 24 - hours;
				// redefine hours as the reamining hours subtracted from a 12 hour day
				hours = 12 - hoursRemaining;
			}
			let minutes = date.getMinutes(); // define minutes
			minutes = minutes.toString(); // convert minutes to a string
			// if minutes has less than 2 characters
			if(minutes.length < 2) {
				minutes = 0 + minutes;
			}
			let time = hours + ':' + minutes; // construct time using hours and minutes
			return time;
		}
		
		const mapTemp = function(temp, units) {
			if(units == 'f') {
				// define temperature as fahrenheit
				return Math.round(((temp - 273.15) * 1.8) + 32) + '°F';

			} else {
				// define temperature as celsius
				return Math.round(temp - 273.15) + '°C';
			}
		} 
		const mapWind = function(wind, units) {
			return (units == 'km/h') ? wind*3.6 : wind;
		}
		// format icon function
		const mapCustomIconToURL = function(defaultIconFileName, timeOfDay) {
			return `/static/${s.customIcons}${timeOfDay}/${defaultIconFileName}.svg`;
		}

		// define basic api endpoint
		let apiURL = 'https://api.openweathermap.org/data/3.0/' + s.query + '?lang=' + s.lang;

		let weatherObj;

		let temperature;
		let minTemperature;
		let maxTemperature;
		let windSpeed;

		// if city isn't null
		if(s.city != null) {
			// define API url using city (and remove any spaces in city)
			apiURL += '&q=' + s.city;
		} else if(s.lat != null && s.lng != null) {
			// define API url using lat and lng
			apiURL += '&lat=' + s.lat + '&lon=' + s.lng;
		}
		if(s.key != null) {
			apiURL += '&appid=' + s.key;
		}
		if (s.exclude != null) {
			apiURL += '&exclude=' + s.exclude;
		}

		$.ajax({
			type: 'GET',
			url: apiURL,
			dataType: 'json',
			success: function(data) {
				console.log("Weather API call successful. Response data:", data);
				if(data) {
					// adjust data to expected format
					if (s.query.localeCompare('onecall') == 0) {
						data.main = {
							temp: data.current.temp,
							temp_min: data.daily[0].temp.min,
							temp_max: data.daily[0].temp.max,
							humidity: data.current.humidity,
						}; 
						data.wind = {
							speed: data.current.wind_speed
						};
						data.sys = {
							sunrise: data.current.sunrise,
							sunset: data.current.sunset
						};
					}

					if(s.units == 'f') {
						// define temperature as fahrenheit
						temperature = Math.round(((data.main.temp - 273.15) * 1.8) + 32) + '°F';
						// define min temperature as fahrenheit
						minTemperature = Math.round(((data.main.temp_min - 273.15) * 1.8) + 32) + '°F';
						// define max temperature as fahrenheit
						maxTemperature = Math.round(((data.main.temp_max - 273.15) * 1.8) + 32) + '°F';
					} else {
						// define temperature as celsius
						temperature = Math.round(data.main.temp - 273.15) + '°C';
						// define min temperature as celsius
						minTemperature = Math.round(data.main.temp_min - 273.15) + '°C';
						// define max temperature as celsius
						maxTemperature = Math.round(data.main.temp_max - 273.15) + '°C';
					}

					// if windSpeedUnit is km/h
					windSpeed = (s.windSpeedUnit == 'km/h') ? data.wind.speed*3.6 : data.wind.speed;

					weatherObj = {
						city: (s.query.localeCompare('weather') == 0) ? `${data.name}, ${data.sys.country}` : '',
						temperature: {
							current: temperature,
							min: minTemperature,
							max: maxTemperature,
							units: s.units.toUpperCase()
						},
						description: (s.query.localeCompare('weather') == 0) ? data.weather[0].description : data.current.weather[0].description,
						windspeed: `${Math.round(windSpeed)} ${ s.windSpeedUnit }`,
						humidity: `${data.main.humidity}%`,
						sunrise: `${formatTime(data.sys.sunrise)} AM`,
						sunset: `${formatTime(data.sys.sunset)} PM`
					};
					
					el.html(temperature);

					if(s.minTemperatureTarget != null) {
						$(s.minTemperatureTarget).text(minTemperature);
					}
					if(s.maxTemperatureTarget != null) {
						$(s.maxTemperatureTarget).text(maxTemperature);
					}
					$(s.descriptionTarget).text(weatherObj.description);
					icon = (s.query.localeCompare('weather') == 0) ? data.weather[0].icon : data.current.weather[0].icon;
					if (s.iconTarget != null && icon != null) {
						let iconURL;
						if(s.customIcons != null) {
							const defaultIconFileName = icon;
							let timeOfDay;
							// if default icon name contains the letter 'd'
							if(defaultIconFileName.indexOf('d') != -1) {
								timeOfDay = 'day';
							} else {
								timeOfDay = 'night';
							}
							$(s.wrapperTarget).addClass(timeOfDay);
							iconURL = mapCustomIconToURL(defaultIconFileName, timeOfDay);
						} else {
							iconURL = `https://openweathermap.org/img/wn/${icon}@2x.png`;
						}
						$(s.iconTarget).attr('src', iconURL);
					}
					if(s.placeTarget != null) {
						$(s.placeTarget).text(weatherObj.city);
					}
					if(s.windSpeedTarget != null) {
						$(s.windSpeedTarget).text(weatherObj.windspeed);
					}
					if(s.humidityTarget != null) {
						$(s.humidityTarget).text(weatherObj.humidity);
					}
					if(s.sunriseTarget != null) {
						$(s.sunriseTarget).text(weatherObj.sunrise);
					}
					if(s.sunsetTarget != null) {
						$(s.sunsetTarget).text(weatherObj.sunset);
					}
					s.success.call(this, weatherObj);
				}

				if (s.query.localeCompare('onecall') == 0) {
					moment.locale(s.lang);
					var elements = document.getElementById(s.widgetId).getElementsByClassName(s.forecastTarget);
					for (let elIndex = 0; elIndex < elements.length; elIndex++) {
						var element = elements[elIndex];
						var daysLength = data.daily.length-1;
						for (let day = 1; day < daysLength; day++) {
							var main_container = document.createElement("div");
							main_container.setAttribute('class', 'weather-forecast-container');
							element.appendChild(main_container)
							// Week day
							var weekday_span = document.createElement('span');
							weekday_span.setAttribute('class', 'text-capitalize');
							const weekday = moment.unix(data.daily[day].dt).format('dd');
							var textNode = document.createTextNode(weekday);
							weekday_span.appendChild(textNode);
							main_container.appendChild(weekday_span);
							//icon
							var weather_icon = document.createElement("div");
							weather_icon.id = 'day_' + day.toString();
							var img = document.createElement("img");
							const forecast = data.daily[day];
							if (s.customIcons != null) {
								img.src = mapCustomIconToURL(forecast.weather[0].icon, 'day');
							} else {
								img.src = `https://openweathermap.org/img/wn/${forecast.weather[0].icon}.png`;
							}
							img.setAttribute("class", "weather-forecast-day-icon");
							weather_icon.appendChild(img);
							main_container.appendChild(weather_icon);
							//forecast data
							var weekday_data_container = document.createElement("div");
							weekday_data_container.setAttribute('class', 'weather-forecast-day-stats');
							
							// Min, max temps
							var weekday_min_max = document.createElement("div");
							weekday_min_max.setAttribute('class', 'weather-forecast-day-stats-temp');
							var min_temp = document.createElement("div");
							min_temp.setAttribute('class', 'weather-min-temperature');
							var minTextNode = document.createTextNode(mapTemp(data.daily[day].temp.min));
							min_temp.appendChild(minTextNode);
							weekday_min_max.appendChild(min_temp);
							var max_temp = document.createElement("div");
							max_temp.setAttribute('class', 'weather-max-temperature');
							var maxTextNode = document.createTextNode(mapTemp(data.daily[day].temp.max));
							max_temp.appendChild(maxTextNode);
							weekday_min_max.appendChild(max_temp);
							weekday_data_container.appendChild(weekday_min_max);

							// humidity
							var weekday_humidity = document.createElement("div");
							weekday_humidity.setAttribute('class', 'weather-forecast-day-stats-item');
							var humidity_data = document.createElement("span");
							var humidity_icon = document.createElement("i");
							humidity_icon.setAttribute('class', 'fas fa-droplet');
							var textNodeHumidity = document.createTextNode('humidity');
							humidity_icon.appendChild(textNodeHumidity);
							var textNode = document.createTextNode(data.daily[day].humidity + '%');
							humidity_data.appendChild(textNode);
							weekday_humidity.appendChild(humidity_icon);
							weekday_humidity.appendChild(humidity_data);
							weekday_data_container.appendChild(weekday_humidity);

							// wind
							var weekday_wind = document.createElement("div");
							weekday_humidity.setAttribute('class', 'weather-forecast-day-stats-item');
							var wind_data = document.createElement("span");
							var wind_icon = document.createElement("i");
							wind_icon.setAttribute('class', 'fas fa-wind');
							var textNodeWind = document.createTextNode('air');
							wind_icon.appendChild(textNodeWind);
							var textNode = document.createTextNode(parseInt(mapWind(data.daily[day].wind_speed, s.windSpeedUnit)) + ' ' + s.windSpeedUnit);
							wind_data.appendChild(textNode);
							weekday_wind.appendChild(wind_icon);
							weekday_wind.appendChild(wind_data);
							weekday_data_container.appendChild(weekday_wind);

							main_container.appendChild(weekday_data_container);
						}
					}
				}
			},
			error: function(jqXHR, textStatus, errorThrown) {
				// Log any errors that occur during the API call
				console.error("Weather API call failed. Error:", textStatus);
				s.error.call(this, {
					error: textStatus
				});
			}
		});

		function checkDaysSinceRain(lat, lng, key, callback) {
			const daysToCheck = 5;
			let daysSinceRain = 0;

			const checkDay = (daysAgo) => {
				if (daysAgo > daysToCheck) {
					callback(daysSinceRain);
					return;
				}

				const dateToCheck = new Date();
				dateToCheck.setDate(dateToCheck.getDate() - daysAgo);
				const timestamp = Math.floor(dateToCheck.getTime() / 1000);

				const apiUrl = `https://api.openweathermap.org/data/3.0/onecall/timemachine?lat=${lat}&lon=${lng}&dt=${timestamp}&appid=${key}`;
				$.ajax({
					url: apiUrl,
					method: 'GET',
					success: function(data) {
						let dailyPrecipitation = 0;
						
						if (data.data && Array.isArray(data.data)) {
							data.data.forEach(entry => {
								if (entry.rain) {
									dailyPrecipitation += entry.rain['1h'] || 0;
								}
								if (entry.snow) {
									dailyPrecipitation += entry.snow['1h'] || 0;
								}
							});
						} else {
							console.error("Unexpected data structure: 'data' is not available or not an array.");
						}

						console.log(`Daily precipitation for ${daysAgo} days ago: ${dailyPrecipitation}`); // Log the precipitation amount

						if (dailyPrecipitation > 0) {
							callback(daysSinceRain);
						} else {
							daysSinceRain++;
							checkDay(daysAgo + 1);
						}
					},
					error: function(xhr) {
						console.log(`Error fetching data for day ${daysAgo}:`, xhr.responseText);
						callback(daysSinceRain);
					}
				});
			};

			checkDay(1);
		}

		this.each(function() {
			const instance = $(this);
			instance.data('openWeather', {
				settings: options,
				checkDaysSinceRain: function(cb) {
					checkDaysSinceRain(options.lat, options.lng, options.key, cb);
				}
			});
		});

		return this;
	}
})(jQuery);