/*jslint browser: true*/
/*global processCityClear, processCitySelect, google, map*/

$(document).ready(function () {
    "use strict";

    function set_active_link(link) {
        var a_selector = 'a[href="' + link + '"]',
            $link = $(a_selector);
        $('li.active > a').parent().removeClass('active');
        $link.parent('li').addClass('active');
    }

    $('[data-toggle="tooltip"]').tooltip();

    /* Process ajax links */
    $(document).on('click', 'a.ajax-link', function (event) {
        event.preventDefault();
        if (!$(this).parent('li').hasClass("active")) {
            var $link = $(this);
            $.ajax({
                url: $link.attr("href") !== '/' ? '/ajax' + $link.attr("href") : '/ajax',
                dataType: 'html'
            })
                .done(function (data) {
                    $('#content').html(data);
                    set_active_link($link.attr("href"));
                    $(".modal-backdrop.in").remove();
                    history.pushState({content: data}, null, $link.attr("href"));
                })
                .fail(function () {
                    window.location.replace($link.attr("href"));
                });
        }
    });

    /* Back button */
    $(window).on("popstate", function (event) {
        if (event.originalEvent.state !== null && event.originalEvent.state.content !== null) {
            $('#content').html(event.originalEvent.state.content);
            set_active_link(window.location.pathname);
        }
    });

    /* Process input clear */
    $('.has-clear input').on('change', function () {
        if ($(this).val() === '') {
            $(this).parents('.form-group').addClass('has-empty-value');
        } else {
            $(this).parents('.form-group').removeClass('has-empty-value');
        }
    }).trigger('change');

    $('.has-clear .form-control-clear').on('click', function () {
        var $input = $(this).parents('.form-group').find('input');

        $input.val('').trigger('change');

        // Trigger a "cleared" event on the input for extensibility purpose
        $input.trigger('cleared');
        if ($input.attr('id') === "from" || $input.attr('id') === "to") {
            $input.siblings('select').hide();
            processCityClear($input.attr('id'));
        }
    });

    /* Process autocomplete */
    /*jslint unparam: true*/
    $('input.ajax-autocomplete').each(function (index, el) {
        $(el).autocomplete({
            serviceUrl: '/ajax/autocomplete/' + $(el).data('autocomplete-name'),
            onSelect: function (suggestion) {
                if ($(el).attr('id') === "from" || $(el).attr('id') === "to") {
                    processCitySelect(suggestion, el);
                }
            },
            transformResult: function (response) {
                return {
                    suggestions: $.map($.parseJSON(response).suggestions, function (item) {
                        return {
                            value: item.value + ' (' + item.data.country_code + ')',
                            data: item.data
                        };
                    })
                };
            }
        });
    });

    $('form#find-tickets').submit(function (event) {
        var i,
            j,
            k,
            s,
            $li,
            $container,
            $js_routes = $('#js-routes');
        event.preventDefault();
        $js_routes.empty();
        $(this).find('[type="submit"] i').show();

        /*jslint unparam: true*/
        $.ajax({
            url: '/ajax/routes?' + $(this).serialize(),
            type: 'GET',
            dataType: 'json'
        })
            .success(function (data, textStatus, jqXHR) {
                if (Object.keys(data.routes)) {
                    for (i in data.routes) {
                        if (data.routes.hasOwnProperty(i)) {
                            $container = $('<ul />');
                            for (k = 0; k < data.routes[i].length; k += 1) {
                                $li = $('<li />');
                                $li.data('route', []);
                                for (j = 0; j < data.routes[i][k].nodes.length; j += 1) {
                                    $li.data('route').push({
                                        lat: parseFloat(data.routes[i][k].nodes[j].latitude),
                                        lng: parseFloat(data.routes[i][k].nodes[j].longitude)
                                    });
                                    s = '<span>' + data.routes[i][k].nodes[j].airport_name + '</span>';
                                    if (j < data.routes[i][k].nodes.length - 1) {
                                        s += ' - ';
                                    } else {
                                        s += ' (' + parseInt(data.routes[i][k].total_distance, 10) + 'km)';
                                    }
                                    $li.append(s);
                                }
                                $container.append($li);
                            }
                            s = '<h4>Routes with ' + i + ' transfers:</h4>';
                            $js_routes.append(s);
                            $js_routes.append($container);
                        }
                    }
                }
                $('#find-tickets [type="submit"] i').hide();
            });
        /*jslint unparam: false*/
    });

    $('#js-routes').on({
        mouseenter: function () {
            var flightPath = new google.maps.Polyline({
                    path: $(this).data('route'),
                    geodesic: true,
                    strokeColor: '#FF0000',
                    strokeOpacity: 1.0,
                    strokeWeight: 2
                });
            $(this).data('flightPath', flightPath);
            flightPath.setMap(map);
        },
        mouseleave:  function () {
            $(this).data('flightPath').setMap(null);
        }
    }, 'li');

});
