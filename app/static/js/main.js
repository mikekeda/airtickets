/*jslint browser: true*/
/*global processCityClear, processCitySelect, google, map, initMap, clearMarkers*/

$(document).ready(function () {
    "use strict";

    function setActiveLink(link) {
        let aSelector = 'a[href="' + link + '"]',
            $link = $(aSelector);
        $("li.active > a").parent().removeClass("active");
        $link.parent("li").addClass("active");
    }

    $('[data-toggle="tooltip"]').tooltip();

    /* Process ajax links */
    $(document).on("click", "a.ajax-link", function (event) {
        event.preventDefault();
        if (!$(this).parent("li").hasClass("active")) {
            let $link = $(this);
            $.ajax({
                url: $link.attr("href") !== "/" ? "/ajax" + $link.attr("href") : "/ajax",
                dataType: "html"
            })
                .done(function (data) {
                    $("#content").html(data);
                    setActiveLink($link.attr("href"));
                    $(".modal-backdrop.in").remove();
                    history.pushState({content: data}, null, $link.attr("href"));
                    if ($link.attr("href") === "/") {
                        try {
                            initMap();
                        } catch (err) {
                            $('#content').append('<script defer src="https://maps.googleapis.com/maps/api/js?key=AIzaSyA9pDB24wh9HRbh6J8wQxpjE_e39AJ5CeM&callback=initMap">');
                        }
                    }
                })
                .fail(function () {
                    window.location.replace($link.attr("href"));
                });
        }
    });

    /* Back button */
    $(window).on("popstate", function (event) {
        if (event.originalEvent.state !== null && event.originalEvent.state.content !== null) {
            $("#content").html(event.originalEvent.state.content);
            setActiveLink(window.location.pathname);
            if (window.location.pathname === "/") {
                try {
                    initMap();
                } catch (err) {
                    $('#content').append('<script defer src="https://maps.googleapis.com/maps/api/js?key=AIzaSyCTbl1EudJoUWSj2XqQZ6tK_VLwT74ppt4&callback=initMap">');
                }
            }
        }
    });

    /* Process input clear */
    $(".has-clear input").on("change", function () {
        if ($(this).val() === "") {
            $(this).parents(".form-group").addClass("has-empty-value");
        } else {
            $(this).parents(".form-group").removeClass("has-empty-value");
        }
    }).trigger("change");

    $(".has-clear .form-control-clear").on("click", function () {
        let $input = $(this).parents(".form-group").find("input");

        $input.val("").trigger("change");

        // Trigger a "cleared" event on the input for extensibility purpose
        $input.trigger("cleared");
        if ($input.attr("id") === "from" || $input.attr("id") === "to") {
            $input.siblings("select").hide();
            $input.siblings("select").empty();
            processCityClear($input.attr("id"));
        }
    });

    /* Process autocomplete */
    /*jslint unparam: true*/
    $("input.ajax-autocomplete").each(function (index, el) {
        $(el).autocomplete({
            deferRequestBy: 300,
            serviceUrl: "/ajax/autocomplete/" + $(el).data("autocomplete-name"),
            onSearchStart: function (query) {
                $(el).siblings(".glyphicon-refresh").show();
            },
            onSearchComplete: function (query) {
                $(el).siblings(".glyphicon-refresh").hide();
            },
            onSearchError: function (query, jqXHR, textStatus, errorThrown) {
                $(el).siblings(".glyphicon-refresh").hide();
            },
            onSelect: function (suggestion) {
                if ($(el).attr("id") === "from" || $(el).attr("id") === "to") {
                    processCitySelect(suggestion, el, false);
                }
            },
            transformResult: function (response) {
                return {
                    suggestions: $.map($.parseJSON(response).suggestions, function (item) {
                        return {
                            value: item.value + " (" + item.data.country_code + ")",
                            data: item.data
                        };
                    })
                };
            }
        });
    });

    $("form#find-tickets").submit(function (event) {
        let i,
            j,
            k,
            s,
            $li,
            $container,
            $jsRoutes = $("#js-routes"),
            formData = $(this).serialize();
        event.preventDefault();
        $jsRoutes.empty();
        $(this).find('[type="submit"] i').show();

        if (formData) {
            /*jslint unparam: true*/
            $.ajax({
                url: "/ajax/routes?" + formData,
                type: "GET",
                dataType: "json",
                success: function (data) {
                    $jsRoutes.append('<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>');
                    $jsRoutes.children(".close").click(function (event) {
                        $jsRoutes.empty();
                    });

                    if (!$.isEmptyObject(data.routes)) {
                        for (i in data.routes) {
                            if (data.routes.hasOwnProperty(i)) {
                                $container = $("<ul />");
                                for (k = 0; k < data.routes[i].length; k += 1) {
                                    $li = $("<li />");
                                    $li.data("route", []);
                                    for (j = 0; j < data.routes[i][k].nodes.length; j += 1) {
                                        $li.data("route").push({
                                            lat: parseFloat(data.routes[i][k].nodes[j].latitude),
                                            lng: parseFloat(data.routes[i][k].nodes[j].longitude)
                                        });
                                        s = "<span>" + data.routes[i][k].nodes[j].airport_name + "</span>";
                                        if (j < data.routes[i][k].nodes.length - 1) {
                                            s += " - ";
                                        } else {
                                            s += " (" + parseInt(data.routes[i][k].total_distance, 10) + "km)";
                                        }
                                        $li.append(s);
                                    }
                                    $container.append($li);
                                }
                                s = "<h4>Routes with " + i + " transfers:</h4>";
                                $jsRoutes.append(s);
                                $jsRoutes.append($container);
                            }
                        }
                    } else {
                        $jsRoutes.append("<h4>No Routes</h4>");
                    }
                },
                complete: function (data, textStatus, jqXHR) {
                    $('#find-tickets [type="submit"] i').hide();
                }
            });
            /*jslint unparam: false*/
        } else {
            $('#find-tickets [type="submit"] i').hide();
        }
    });

    /* Process route hover (show the route on the map) */
    $("#js-routes").on({
        mouseenter: function () {
            let flightPath = new google.maps.Polyline({
                    path: $(this).data("route"),
                    geodesic: true,
                    strokeColor: "#FF0000",
                    strokeOpacity: 1.0,
                    strokeWeight: 2
                });
            $(this).data("flightPath", flightPath);
            flightPath.setMap(map);
        },
        mouseleave: function () {
            $(this).data("flightPath").setMap(null);
        }
    }, "li");

    /* Process input clear */
    $("#clean-map").on("click", function () {
        clearMarkers();
    });

});
