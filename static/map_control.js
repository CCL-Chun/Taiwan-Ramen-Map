let map;
let ramenLayer = L.layerGroup();
let parkingLayer = L.layerGroup();
let routesLayer = L.layerGroup();
let highlightedRouteLayer = L.layerGroup();
let bikeRoutesLayer = L.layerGroup();
let layerControl;
let defaultLat;
let defaultLng;
let lastMoveLatLng;
let socket;

let HomeControl = L.Control.extend({
    options: {
        position: 'topleft'
    },

    onAdd: function (map) {
        var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');

        // Create a button element
        var button = L.DomUtil.create('a', 'leaflet-control-home leaflet-bar-part leaflet-bar-part-single', container);
        button.title = 'Go to Home';

        // Add class for the icon
        L.DomUtil.addClass(button, 'home-icon');

        // Add a click event listener to the button
        L.DomEvent.on(button, 'click', function (e) {
            map.setView(this.options.homeCoordinates, this.options.homeZoom);
        }, this);

        return container;
    }
});

// initialize the map
$(document).ready(function() {
    // default to 中山 if no geolocation
    defaultLat = 25.052430;
    defaultLng = 121.520270;
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

    let osmBike = L.tileLayer(
        'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', {
            maxZoom : 24,
            attribution: '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    );

    let startMarker = L.marker([lat, lng]).bindPopup('拉麵暴徒在此')
    startPoint = L.layerGroup([startMarker]);

    // default to 中山 if no geolocation
    map = L.map('map',{
        center: [lat, lng],
        zoom: 16,
        layers: [osmBike,startPoint,ramenLayer,parkingLayer,routesLayer,highlightedRouteLayer]
    });

    var baseMaps = {
        "基本單車道地圖": osmBike
    };
    
    var overlayMaps = {
        "拉麵店": ramenLayer,
        "停車格": parkingLayer,
        "規劃路線(完整)": routesLayer,
        "規劃路線(部分重點)": highlightedRouteLayer,
        "優化路線(結合YouBike)": bikeRoutesLayer
    };

    L.control.layers(baseMaps, overlayMaps).addTo(map);
    startMarker.openPopup();

    var homeCoordinates = [lat, lng];
    var homeZoom = 16;
    
    // create a home button
    map.addControl(new HomeControl({ homeCoordinates: homeCoordinates, homeZoom: homeZoom }));

    var pointA = [25.0384799,121.5323702];
    var pointB = [25.0471126,121.541689];
    L.polyline([pointA,pointB], { color: '#08F7F7', weight: 5, dashArray: '20 20'}).addTo(routesLayer);
}

// first view of the map
function firstView(){
    updateRamen();
}

function setupEventListeners() {
    $('#navigation-button').on('click', function() {
        console.log("start fetching traffic")
        fetch('/traffic/api/test')
        .then(response => response.json())
        .then(data => {
            addAllRoutesToMap(data); // add polyline to the map without highlighting
            displaySegmentedNavigationInstructions(data); // display segmented instructions
        })
        .catch(error => console.error('Error fetching routes:', error));
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

            // #bring-me-here only
            if (event.target.classList.contains('bring-me-here')) {
                // retrieve the coordinates from attributes
                var endLng = event.target.getAttribute('lng');
                var endLat = event.target.getAttribute('lat');
                console.log('Planning the routes to:', endLat, endLng);
                // fetch from flask api and show on map layer
                fetchAndDisplayRoutes(defaultLat, defaultLng, endLat, endLng);
            }
        });
    });

    // show the update button
    map.on('moveend', function() {
        var newLatLng = map.getCenter();
        if (lastMoveLatLng) {
            var distance = lastMoveLatLng.distanceTo(newLatLng);
            // Convert distance to kilometers
            var distanceInKm = distance / 1000;
            if (distanceInKm > 1) {
                displayUpdateRamenButton();
            }
        }
        else{
            lastMoveLatLng = map.getCenter();
        };
        lastMoveLatLng = newLatLng;
    });
}

// get bounds based on the view
function updateRamen(){
    if (map) {
        if (!ramenLayer) {
            ramenLayer = L.layerGroup().addTo(map);
        } else {
            ramenLayer.clearLayers(); // clear existing ramen if already initialized
        }
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
                                            '>附近停車位</button>' + '<br>' +
                                        '<button class="bring-me-here" lng=' + feature.geometry.coordinates[0] + 
                                            ' ' + 'lat=' + feature.geometry.coordinates[1] +
                                            '>拉麵突進導航</button>';
                            layer.bindPopup(popupContent);
                        }
                    }
                }).addTo(ramenLayer);
            });
    };
};

// button for update ramen
function displayUpdateRamenButton() {
    // Create a button element
    var button = L.DomUtil.create('button', 'leaflet-control-update-ramen leaflet-bar-part leaflet-bar-part-single');
    button.innerHTML = 'Update Ramen';
    button.title = 'Update Ramen';
    
    // Set CSS style for button positioning
    button.style.position = 'absolute';
    button.style.top = '10px';
    button.style.left = '50%';
    button.style.zIndex = 1000;

    // Add the button to the map
    map.getContainer().appendChild(button);
    
    // Add a click event listener to the button
    L.DomEvent.on(button, 'click', function () {
        // Call the updateRamen function
        updateRamen();
        // Remove the button from the map
        map.getContainer().removeChild(button);
    });
}

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
            L.geoJSON(parking_data, {
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
            }).addTo(parkingLayer);
        });
}

function fetchAndDisplayRoutes(defaultLat, defaultLng, endLat, endLng) {
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
    fetch(`/traffic/api/v1.0/routes/combined?start_lat=${defaultLat}&start_lng=${defaultLng}&end_lat=${endLat}&end_lng=${endLng}`)
        .then(response => response.json())
        .then(data => {
            addAllRoutesToMap(data); // add polyline to the map without highlighting
            displaySegmentedNavigationInstructions(data); // display segmented instructions
        })
        .catch(error => console.error('Error fetching routes:', error));
}

function addAllRoutesToMap(routeData) {
    // Clear previous routes
    routesLayer.clearLayers();
    bikeRoutesLayer.clearLayers();
    // add each sub-routes on routesLayer
    var fastestIndex = routeData.prompt[0].fastest_index;
    routeData.routes[fastestIndex].legs[0].steps.forEach(step => {
        var lineCoordinates = step.polyline.geoJsonLinestring.coordinates.map(coord => [coord[1], coord[0]]);
        L.polyline(lineCoordinates, { color: '#0863F7', weight: 5,}).addTo(routesLayer);
    });

    // add combined route if routeData.youbike_improve is 1
    if (routeData.prompt[0].youbike_improve === 1) {
        var youbikeRoute = routeData.routes[fastestIndex].legs[1][1];
        youbikeRoute.steps.forEach(step => {
            var lineCoordinates = step.polyline.geoJsonLinestring.coordinates.map(coord => [coord[1], coord[0]]);
            L.polyline(lineCoordinates, { color: '#08F7F7', weight: 5 }).addTo(bikeRoutesLayer);
        });
    }
}

function displaySegmentedNavigationInstructions(routeData) {
    var mainInstructionsContainer = $('#main-instructions-container');
    var youbikeInstructionsContainer = $('#youbike-instructions-container');
    // clean up before adding new routes Navigation Instructions
    mainInstructionsContainer.empty();
    youbikeInstructionsContainer.empty();

    // display instructions for the main route
    var fastestIndex = routeData.prompt[0].fastest_index;
    var mainSteps = routeData.routes[fastestIndex].legs[0].steps;
    mainSteps.forEach((step, index) => {
        var instructionText = (step.navigationInstruction && step.navigationInstruction.instructions) ? step.navigationInstruction.instructions : '走路';
        var instruction = $('<div class="instruction" data-step-index="' + index + '">' + instructionText + '</div>');
        mainInstructionsContainer.append(instruction);

        instruction.on('click', function() {
            var stepIndex = $(this).data('step-index');
            highlightStep(stepIndex, mainSteps);
        });
    });

    // display YouBike route instructions
    if (routeData.prompt[0].youbike_improve === 1) {
        console.log("YouBike route get!")
        var youbikeSteps = routeData.routes[fastestIndex].legs[1][1].steps;
        console.log(youbikeSteps)
        youbikeSteps.forEach((step, index) => {
            var instructionText = step.navigationInstruction.instructions;
            var instruction = $('<div class="instruction youbike" data-step-index="' + index + '">' + instructionText + '</div>');
            youbikeInstructionsContainer.append(instruction);

            instruction.on('click', function() {
                var stepIndex = $(this).data('step-index');
                highlightStep(stepIndex, youbikeSteps);
            });
        });
    }
}

function highlightStep(stepIndex, steps) {
    highlightedRouteLayer.clearLayers();  // Clear previous highlights

    var stepCoordinates = steps[stepIndex].polyline.geoJsonLinestring.coordinates.map(coord => [coord[1], coord[0]]);
    var polyline = L.polyline(stepCoordinates, { color: 'red', weight: 5 }).addTo(highlightedRouteLayer);

    map.fitBounds(polyline.getBounds(), {maxZoom: 18});
}

// Event listener for opening the offcanvas
document.addEventListener('DOMContentLoaded', function() {
    var detailsButton = document.getElementById('details');
    var offcanvasElement = document.getElementById('offcanvasScrolling');

    detailsButton.addEventListener('click', function() {
        var currentId = this.getAttribute('data-id');  // get the data-id attribute from the button

        offcanvasElement.setAttribute('data-current-id', currentId); // set the data-current-id attribute on the offcanvas before showing it
        
        var bsOffcanvas = new bootstrap.Offcanvas(offcanvasElement);
        bsOffcanvas.show(); // show the offcanvas

        // retrieve the ID set after opened
        var currentId = offcanvasElement.getAttribute('data-current-id');

        // initialize or use existing Socket.IO connection
        if (!window.socket) {
            window.socket = io('http://127.0.0.1:5000');

            window.socket.on('connect', function() {
                console.log('Socket.IO connected for ID:', currentId);
            });

            window.socket.on('server_response', function(data) {
                var logElement = document.getElementById('log');
                var div = document.createElement('div');
                div.textContent = 'Received: ' + data.message;
                logElement.appendChild(div);
            });

            // use the ID to emit a message or join a specific room
            window.socket.emit('join_room', { id: currentId });
        }
    });

    offcanvasElement.addEventListener('hidden.bs.offcanvas', function(event) {
        var currentId = this.getAttribute('data-current-id');

        if (window.socket) {
            window.socket.emit('leave_room', { id: currentId });
            window.socket.disconnect();
            window.socket = null;
            console.log('Socket.IO disconnected for ID:', currentId);
        }
    });
});


document.addEventListener('DOMContentLoaded', function() {
    var formElement = document.getElementById('emit');
    var inputElement = document.getElementById('emit_data');

    formElement.addEventListener('submit', function(event) {
        event.preventDefault();
        if (window.socket && window.socket.connected) {
            var messageToSend = inputElement.value;
            window.socket.emit('client_event', { "data": messageToSend });
            inputElement.value = '';  // clear the input after sending
        } else {
            console.error("Socket.IO connection not established.");
        }
    });
});
