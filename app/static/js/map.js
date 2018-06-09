/*jslint browser: true*/
/*global google*/

var map,
    latitude,
    longitude,
    from_to_bounds = [],
    markers = [];

function isLocationFree(search) {
    "use strict";
    var i,
        l = markers.length;

    for (i = 0; i < l; i += 1) {
        if ((Math.abs(markers[i].position.lat() - search[0]) < 1e-6)
                && (Math.abs(markers[i].position.lng() - search[1]) < 1e-6)) {
            return false;
        }
    }
    return true;
}

function processCityClear(id) {
    "use strict";
    delete from_to_bounds[id];
}

function setMapFormField(field, name, lat, lng) {
    "use strict";
    if (field === 'from' || field === 'to') {
        var selector = 'input#' + field,
            bounds = new google.maps.LatLngBounds(),
            suggestion = {
                'value': name,
                'data': {
                    'lat': lat,
                    'lng': lng
                }
            };

        $(selector).val(name);
        $(selector).parents('.form-group').removeClass('has-empty-value');
        processCitySelect(suggestion, selector, false);
        from_to_bounds[field] = new google.maps.LatLng(lat, lng);
        if (from_to_bounds.hasOwnProperty('from') && from_to_bounds.hasOwnProperty('to')) {
            bounds.extend(from_to_bounds.from);
            bounds.extend(from_to_bounds.to);
            map.fitBounds(bounds);
        }
    }
}

function addMarker(name, lat, lng) {
    "use strict";
    if (isLocationFree([lat, lng])) {
        var markerImage = new google.maps.MarkerImage('/static/img/dot.png',
                new google.maps.Size(16, 16), //size
                null,
                new google.maps.Point(8, 8)), // offset point

            marker = new google.maps.Marker({
                position: new google.maps.LatLng(lat, lng),
                icon: markerImage,
                map: map
            });

        google.maps.event.addListener(marker, 'mouseover', (function (marker) {
            return function () {
                var text = name;

                marker.infowindow = new google.maps.InfoWindow();
                marker.infowindow.setContent(
                    text +
                        '<br>' +
                        'Right Click=From  Left Click=To'
                );
                marker.infowindow.open(map, marker);
            };
        })(marker));

        google.maps.event.addListener(marker, 'mouseout', (function (marker) {
            return function () {
                marker.infowindow.close();
            };
        })(marker));

        google.maps.event.addListener(marker, 'click', (function () {
            return function () {
                setMapFormField('to', name, lat, lng);
            };
        })(marker));

        google.maps.event.addListener(marker, 'rightclick', (function () {
            return function () {
                setMapFormField('from', name, lat, lng);
            };
        })(marker));

        markers.push(marker);
    }
}

function processCitySelect(suggestion, el, find_closest_city) {
    "use strict";
    var bounds = new google.maps.LatLngBounds(),
        airport_name,
        string,
        i;

    /*jslint unparam: true*/
    $.ajax({
        url: '/ajax/airports?lat=' + suggestion.data.lat + '&lng=' + suggestion.data.lng + '&limit=' + 5 + '&find_closest_city=' + find_closest_city,
        type: 'GET',
        dataType: 'json',
        success: function (data, textStatus, jqXHR) {
            $(el).siblings('select').slideDown().find('option').remove();
            for (i = 0; i < data.airports.length; i += 1) {
                airport_name = data.airports[i].name || data.airports[i].airport_name;
                string = '<option value="' + data.airports[i].id + '">' + airport_name + '</option>';
                $(el).siblings('select').append(string);
            }
            if (find_closest_city && data.closest_city.value) {
                $(el).val(data.closest_city.value);
                addMarker(data.closest_city.value, data.closest_city.data.lat, data.closest_city.data.lng);
            }
        }
    });
    /*jslint unparam: false*/

    if (!find_closest_city && isLocationFree([suggestion.data.lat, suggestion.data.lng])) {
        from_to_bounds[$(el).attr('id')] = new google.maps.LatLng(suggestion.data.lat, suggestion.data.lng);

        addMarker(suggestion.value, suggestion.data.lat, suggestion.data.lng);

        if (from_to_bounds.hasOwnProperty('from')) {
            bounds.extend(from_to_bounds.from);
        }

        if (from_to_bounds.hasOwnProperty('to')) {
            bounds.extend(from_to_bounds.to);
        }

        if (from_to_bounds.hasOwnProperty('from') || from_to_bounds.hasOwnProperty('to')) {
            map.fitBounds(bounds);
        }
    }
}

/* Remove all markers from the map */
function clearMarkers() {
    "use strict";
    var i;
    for (i = 0; i < markers.length; i += 1) {
        markers[i].setMap(null);
    }
    markers.length = 0;
}

/* Initialize google map */
function initMap() {
    "use strict";
    var xhr,
        timer,
        circle,
        language = window.navigator.userLanguages || window.navigator.languages,
        styles = [
            {
                "elementType": "geometry",
                "stylers": [
                    {
                        "hue": "#ff4400"
                    },
                    {
                        "saturation": -68
                    },
                    {
                        "lightness": -4
                    },
                    {
                        "gamma": 0.72
                    }
                ]
            },
            {
                "featureType": "road",
                "elementType": "labels.icon"
            },
            {
                "featureType": "landscape.man_made",
                "elementType": "geometry",
                "stylers": [
                    {
                        "hue": "#0077ff"
                    },
                    {
                        "gamma": 3.1
                    }
                ]
            },
            {
                "featureType": "water",
                "stylers": [
                    {
                        "hue": "#00ccff"
                    },
                    {
                        "gamma": 0.44
                    },
                    {
                        "saturation": -33
                    }
                ]
            },
            {
                "featureType": "poi.park",
                "stylers": [
                    {
                        "hue": "#44ff00"
                    },
                    {
                        "saturation": -23
                    }
                ]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [
                    {
                        "hue": "#007fff"
                    },
                    {
                        "gamma": 0.77
                    },
                    {
                        "saturation": 65
                    },
                    {
                        "lightness": 99
                    }
                ]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.stroke",
                "stylers": [
                    {
                        "gamma": 0.11
                    },
                    {
                        "weight": 5.6
                    },
                    {
                        "saturation": 99
                    },
                    {
                        "hue": "#0091ff"
                    },
                    {
                        "lightness": -86
                    }
                ]
            },
            {
                "featureType": "transit.line",
                "elementType": "geometry",
                "stylers": [
                    {
                        "lightness": -48
                    },
                    {
                        "hue": "#ff5e00"
                    },
                    {
                        "gamma": 1.2
                    },
                    {
                        "saturation": -23
                    }
                ]
            },
            {
                "featureType": "transit",
                "elementType": "labels.text.stroke",
                "stylers": [
                    {
                        "saturation": -64
                    },
                    {
                        "hue": "#ff9100"
                    },
                    {
                        "lightness": 16
                    },
                    {
                        "gamma": 0.47
                    },
                    {
                        "weight": 2.7
                    }
                ]
            }
        ],
        styledMap = new google.maps.StyledMapType(styles, {
            name: "Styled Map"
        }),
        mapOptions = {
            zoom: 5,
            maxZoom: 10,
            center: new google.maps.LatLng(-34.397, 150.644),
            mapTypeControlOptions: {
                mapTypeIds: [google.maps.MapTypeId.ROADMAP, 'map_style']
            }
        };

    map = new google.maps.Map(document.getElementById('map'), mapOptions);

    map.mapTypes.set('map_style', styledMap);
    map.setMapTypeId('map_style');

    console.log(language);

    from_to_bounds = [];
    markers = [];

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var initialLocation = new google.maps.LatLng(position.coords.latitude, position.coords.longitude),
                suggestion = {
                    data: {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    }
                };
            map.setCenter(initialLocation);
            processCitySelect(suggestion, '#from', true);
        });
    }

    google.maps.event.addListener(map, "mousemove", function (event) {
        clearTimeout(timer);

        if (circle) {
            circle.setMap(null);
            circle = null;
        }

        timer = setTimeout(function () {
            circle = new google.maps.Circle({
                map: map,
                radius: 3000000 / Math.pow(2, map.getZoom()),    // in metres
                center: new google.maps.LatLng(event.latLng.lat(), event.latLng.lng()),
                strokeColor: "#006DFC",
                strokeOpacity: 0.4,
                strokeWeight: 1,
                fillColor: "#006DFC",
                fillOpacity: 0.15
            });

            if (xhr && xhr.readyState !== 4) {
                xhr.abort();
            }

            /*jslint unparam: true*/
            xhr = $.ajax({
                url: '/ajax/get-cities',
                type: 'GET',
                data: {
                    'ne_lng': circle.getBounds().getNorthEast().lng(),
                    'ne_lat': circle.getBounds().getNorthEast().lat(),
                    'sw_lng': circle.getBounds().getSouthWest().lng(),
                    'sw_lat': circle.getBounds().getSouthWest().lat()
                },
                dataType: 'json',
                success: function (data, textStatus, jqXHR) {
                    var i;
                    for (i = 0; i < data.json_list.length; i += 1) {
                        addMarker(
                            data.json_list[i].city_names[0].toString(),
                            data.json_list[i].latitude,
                            data.json_list[i].longitude
                        );
                    }
                    if (circle) {
                        circle.setMap(null);
                        circle = null;
                    }
                }
            });
            /*jslint unparam: false*/

        }, 2000);
    });

    google.maps.event.addListener(map, "mouseout", function () {
        clearTimeout(timer);
    });
}
