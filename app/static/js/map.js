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
        if (markers[i][0] === search[0] && markers[i][1] === search[1]) {
            return false;
        }
    }
    return true;
}

function processCityClear(id) {
    "use strict";
    delete from_to_bounds[id];
}

function addMarker(name, lat, lng) {
    "use strict";
    if (isLocationFree([lat, lng])) {
        var infowindow = new google.maps.InfoWindow(),
            markerImage = new google.maps.MarkerImage('/static/img/dot.png',
                new google.maps.Size(16, 16), //size
                null,
                new google.maps.Point(8, 8)), // offset point

            marker = new google.maps.Marker({
                position: new google.maps.LatLng(lat, lng),
                icon: markerImage,
                map: map
            });

        google.maps.event.addListener(marker, 'click', (function (marker) {
            return function () {
                var text = name;
                infowindow.setContent(
                    text +
                        '<br>' +
                        '<button onclick="setMapFormField(\'from\', \'' + text + '\', \'' + lat + '\', \'' + lng + '\')">From</button>' +
                        '<button onclick="setMapFormField(\'to\', \'' + text + '\', \'' + lat + '\', \'' + lng + '\')">To</button>'
                );
                infowindow.open(map, marker);
            };
        })(marker));

        markers.push([lat, lng]);
    }
}

function processCitySelect(suggestion, el) {
    "use strict";
    var bounds = new google.maps.LatLngBounds(),
        airport_name,
        string,
        i;

    /*jslint unparam: true*/
    $.ajax({
        url: '/ajax/airports?lat=' + suggestion.data.lat + '&lng=' + suggestion.data.lng + '&limit=' + 5,
        type: 'GET',
        dataType: 'json'
    })
        .success(function (data, textStatus, jqXHR) {
            $(el).siblings('select').slideDown().find('option').remove();
            for (i = 0; i < data.json_list.length; i += 1) {
                airport_name = data.json_list[i].name || data.json_list[i].airport_name;
                string = '<option value="' + data.json_list[i].id + '">' + airport_name + '</option>';
                $(el).siblings('select').append(string);
            }
        });
    /*jslint unparam: false*/

    if (isLocationFree([suggestion.data.lat, suggestion.data.lng])) {
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
        processCitySelect(suggestion, selector);
        from_to_bounds[field] = new google.maps.LatLng(lat, lng);
        if (from_to_bounds.hasOwnProperty('from') && from_to_bounds.hasOwnProperty('to')) {
            bounds.extend(from_to_bounds.from);
            bounds.extend(from_to_bounds.to);
            map.fitBounds(bounds);
        }
    }
}

/* Initialize google map */
function initMap() {
    "use strict";
    var xhr,
        timer,
        circle,
        language = window.navigator.userLanguages || window.navigator.languages;
    map = new google.maps.Map(document.getElementById('map'), {
        center: {lat: -34.397, lng: 150.644},
        zoom: 5
    });

    console.log(language);

    from_to_bounds = [];
    markers = [];

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var initialLocation = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
            map.setCenter(initialLocation);
        });
    }

    google.maps.event.addListener(map, "mousemove", function (event) {
        clearTimeout(timer);

        if (null != circle) {
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
                dataType: 'json'
            })
                .success(function (data, textStatus, jqXHR) {
                    var i;
                    for (i = 0; i < data.json_list.length; i += 1) {
                        addMarker(
                            data.json_list[i].city_names[0].toString(),
                            data.json_list[i].latitude,
                            data.json_list[i].longitude
                        );
                    }
                    circle.setMap(null);
                    circle = null;
                });
            /*jslint unparam: false*/

        }, 2000);
    });

    google.maps.event.addListener(map, "mouseout", function () {
        clearTimeout(timer);
    });

}
