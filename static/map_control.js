let map;
let routesLayer;
let highlightedRouteLayer;

// initialize the map
$(document).ready(function() {
    // default to 中山 if no geolocation
    let defaultLat = 25.052430;
    let defaultLng = 121.520270;
    // steps to init the map
    function init() {
        initializeMap(defaultLat, defaultLng);
        setupEventListeners();
        firstView();
    }

    // check if user's geolocation is available
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            defaultLat = position.coords.latitude;
            defaultLng = position.coords.longitude;
            init();
        }, function(error) {
            console.error("Error while fetching geolocation: ", error);
            init(); // initialize map with default location 中山
        });
    } else {
        console.error("Geolocation is not supported by this browser.");
        init(); // initialize map with default location 中山
    }
});

function initializeMap(lat = 25.052430, lng = 121.520270) { 
    // default to 中山 if no geolocation
    map = L.map('map').setView([lat, lng], 16);

    L.tileLayer('https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', 
        {
            maxZoom : 24,
            attribution: '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    ).addTo(map);

    L.marker([lat, lng]).addTo(map)
        .bindPopup('拉麵暴徒在此')
        .openPopup();
}

// first view of the map
function firstView(){
    updateRamen();
}

function setupEventListeners() {
    $('#navigation-button').on('click', function() {
        fetchAndDisplayRoutes();
    });

    // search for parking lots around ramen
    map.on('popupopen', function() {
        // use the map container to handle click event
        var popupContainer = map.getPane('popupPane');

        popupContainer.addEventListener('click', function(event) {
            // #find-parking only
            if (event.target.classList.contains('find-parking')) {
                // retrieve the coordinates from attributes
                var lng = event.target.getAttribute('lng');
                var lat = event.target.getAttribute('lat');
                console.log('Finding parking lots around:', lat, lng);
                // fetch from flask api and show on map layer
                findParking(lat, lng);
            }
        });
    });
}

// get bounds based on the view
function updateRamen(){
    if (map) {
        // get the current map center LatLng for api parameters
        var center = map.getCenter();
        var centerGeo = [center.lng, center.lat];

        fetch(`/ramen/api/v1.0/restaurants?center=${centerGeo}`)
            .then(response => response.json())
            .then(ramen_geojson => {
                L.geoJSON(ramen_geojson, {
                    onEachFeature: function (feature, layer) {
                        if (feature.properties) {
                            var popupContent = feature.properties.name +
                                        '<br>' + feature.properties.weekday + feature.properties.open +
                                        '<br>評分: ' + feature.properties.overall + ' / 5'+
                                        '<br>' + feature.properties.address + '<br>' + 
                                        '<button class="find-parking" lng=' + feature.geometry.coordinates[0] + 
                                            ' ' + 'lat=' + feature.geometry.coordinates[1] +
                                            '>Find Parking</button>';
                            layer.bindPopup(popupContent);
                        }
                    }
                }).addTo(map);
            });
    };
};

// set an icon for parking lots
var parkingIcon = L.icon({
    iconUrl: 'static/car_parking_icon.svg',
    iconSize: [20, 75],
    iconAnchor: [22, 94],
    popupAnchor: [-3, -76]
});

// find the parking lots around
function findParking(lat,lng){
    const roadParkType = {
        "01": "小型車",
        "02": "機車",
        "03": "身心障礙專用(汽車)",
        "04": "身心障礙專用(機車)",
        "09": "限時停車汽車",
        "10": "時段性禁停汽車",
        "11": "機慢車停放區",
        "15": "汽車停車彎",
        "18": "機慢車停放區(身心障礙專用)",
        "19": "時段性禁停機車",
        "20": "限時停車機車",
        "22": "汽機車彈性共用",
        "23": "大客車與小型車共用格位"
    }

    fetch(`/traffic/api/v1.0/parking?lat=${lat}&lng=${lng}`)
        .then(response => response.json())
        .then(parking_data => {
            var parkingLayer = L.geoJSON(parking_data, {
                pointToLayer: function(feature, latlng) {
                    return L.marker(latlng, {
                        icon: parkingIcon
                    });
                },
                onEachFeature: function (feature, layer) {
                    if (feature.properties.gatename) {
                        var popupContent = feature.properties.gatename +
                        '<br>' + feature.properties.opentime +
                        '<br>' + feature.properties.parknum +
                        '<br>' + feature.properties.feeb +
                        '<br>' + feature.properties.gadetype1
                    } else{
                        var popupContent = '路邊:' + roadParkType[feature.properties.pktype] +
                        '<br>' + feature.properties.pknos
                    }
                    layer.bindPopup(popupContent);
                }
            },{
                icon: parkingIcon
            });
            parkingLayer.addTo(map);
        });
}

function fetchAndDisplayRoutes() {
    // initialize layers
    if (!routesLayer) {
        routesLayer = L.layerGroup().addTo(map);
    } else {
        routesLayer.clearLayers(); // clear existing routes if already initialized
    }

    if (!highlightedRouteLayer) {
        highlightedRouteLayer = L.layerGroup().addTo(map);
    } else {
        highlightedRouteLayer.clearLayers(); // clear existing highlights if already initialized
    }

    // fetch the planned route 
    fetch('/traffic/api/v1.0/routes')
        .then(response => response.json())
        .then(data => {
            addAllRoutesToMap(data); // add polyline to the map without highlighting
            displaySegmentedNavigationInstructions(data); // display segmented instructions
        })
        .catch(error => console.error('Error fetching routes:', error));
}

function addAllRoutesToMap(routeData) {
    // add each sub-routes on routesLayer
    routeData.routes[0].legs[0].steps.forEach(step => {
        var lineCoordinates = step.polyline.geoJsonLinestring.coordinates.map(coord => [coord[1], coord[0]]);
        L.polyline(lineCoordinates, { color: 'blue' }).addTo(routesLayer);
    });
}

function displaySegmentedNavigationInstructions(routeData) {
    var instructionsContainer = $('#instructions-container');
    var steps = routeData.routes[0].legs[0].steps;
    var segments = routeData.routes[0].legs[0].stepsOverview.multiModalSegments;

    segments.forEach((segment, index) => {
        var segmentInstructions = segment.navigationInstruction.instructions;
        var instruction = $('<div class="instruction" data-segment-index="' + index + '">' + segmentInstructions + '</div>');
        instructionsContainer.append(instruction);

        instruction.on('click', function() {
            var segmentIndex = $(this).data('segment-index');
            highlightSegment(segmentIndex, segments, steps);
        });
    });
}

function highlightSegment(segmentIndex, segments, steps) {
    highlightedRouteLayer.clearLayers();
    var startIndex = segments[segmentIndex].stepStartIndex;
    var endIndex = segments[segmentIndex].stepEndIndex;

    var segmentCoordinates = [];
    for (var i = startIndex; i <= endIndex; i++) {
        var stepCoordinates = steps[i].polyline.geoJsonLinestring.coordinates.map(coord => [coord[1], coord[0]]);
        segmentCoordinates = segmentCoordinates.concat(stepCoordinates);
    }

    var polyline = L.polyline(segmentCoordinates, { color: 'red', weight: 5 }).addTo(highlightedRouteLayer);
    map.fitBounds(polyline.getBounds(),{maxZoom:20});
}

