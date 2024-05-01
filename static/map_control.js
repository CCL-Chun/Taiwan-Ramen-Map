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

    // Number of retries
    var maxRetries = 3;
    var retryCount = 0;
    // Function to fetch geolocation
    function fetchGeolocation() {
        var options = {
            enableHighAccuracy: true,
            timeout: 3000,
            maximumAge: 0
        };

        navigator.geolocation.getCurrentPosition(function(position) {
            defaultLat = position.coords.latitude;
            defaultLng = position.coords.longitude;
            init();
        }, function(error) {
            console.error("Error while fetching geolocation: ", error);
            retryCount++;
            if (retryCount < maxRetries) {
                // Retry fetching geolocation
                fetchGeolocation();
            } else {
                console.error("Maximum retries reached. Unable to fetch geolocation.");
                init(); // Initialize map with default location
            }
        }, options);
    }

    // check if user's geolocation is available
    if ("geolocation" in navigator) {
        // Attempt to fetch geolocation
        fetchGeolocation();
    } else {
        console.error("Geolocation is not supported by this browser.");
        init(); // Initialize map with default location
    }
});

function initializeMap(lat = 25.052430, lng = 121.520270) {

    let CartoDB_Voyager = L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        });

    let CartoDB_VoyagerLabelsUnder = L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        });

    let OpenStreetMap_HOT = L.tileLayer(
        'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Tiles style by <a href="https://www.hotosm.org/" target="_blank">Humanitarian OpenStreetMap Team</a> hosted by <a href="https://openstreetmap.fr/" target="_blank">OpenStreetMap France</a>'
        });

    // let Stadia_OSMBright = L.tileLayer(
    //     'https://tiles.stadiamaps.com/tiles/osm_bright/{z}/{x}/{y}{r}.{ext}', {
    //         minZoom: 0,
    //         maxZoom: 20,
    //         attribution: '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    //         ext: 'png'
    //     });

    let osmBike = L.tileLayer(
        'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', {
            maxZoom : 24,
            attribution: '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        });

    var OpenRailwayMap = L.tileLayer(
        'https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Map style: &copy; <a href="https://www.OpenRailwayMap.org">OpenRailwayMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
        });

    let startMarker = L.marker([lat, lng]).bindPopup('拉麵暴徒在此')
    startPoint = L.layerGroup([startMarker]);

    // default to 中山 if no geolocation
    map = L.map('map',{
        center: [lat, lng],
        zoom: 16,
        layers: [CartoDB_Voyager,startPoint,ramenLayer,parkingLayer,routesLayer,highlightedRouteLayer]
    });

    var baseMaps = {
        "CartoDB_Voyager": CartoDB_Voyager,
        "CartoDB_VoyagerLabelsUnder": CartoDB_VoyagerLabelsUnder,
        "OpenStreetMap_HOT": OpenStreetMap_HOT,
        // "Stadia_OSMBright": Stadia_OSMBright,
        "osmBike": osmBike
    };
    
    var overlayMaps = {
        "拉麵店": ramenLayer,
        "停車格": parkingLayer,
        "捷運/台鐵/高鐵": OpenRailwayMap,
        "規劃路線(完整)": routesLayer,
        "規劃路線(部分重點)": highlightedRouteLayer,
        "優化路線(結合YouBike)": bikeRoutesLayer
    };

    L.control.layers(baseMaps, overlayMaps).addTo(map);
    startMarker.openPopup();

    // create a home button
    let homeCoordinates = [lat, lng];
    let homeZoom = 16;
    map.addControl(
        new HomeControl({
            homeCoordinates: homeCoordinates,
            homeZoom: homeZoom,
            position: 'bottomright'
        }),
    );

    // move zoom controller to bottomright
    map.zoomControl.setPosition('bottomright');
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
                                        '<button class="find-parking btn-outline-primary btn-sm" lng=' + feature.geometry.coordinates[0] + 
                                            ' ' + 'lat=' + feature.geometry.coordinates[1] +
                                            '>附近停車位</button>' + '<br>' +
                                        '<button class="bring-me-here btn-outline-primary btn-sm" lng=' + feature.geometry.coordinates[0] + 
                                            ' ' + 'lat=' + feature.geometry.coordinates[1] +
                                            '>拉麵突進導航</button>' + '<br>' +
                                        '<button id=' + feature.properties.id + ' ' +
                                            'class="btn-outline-primary btn-sm" type="button" data-bs-toggle="offcanvas" ' +
                                            'data-bs-target="#offcanvasScrolling" aria-controls="offcanvasScrolling">' +
                                            '詳細資訊與現場情報</button>';
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
    var offcanvasElement = document.getElementById('offcanvasScrolling');

    document.body.addEventListener('click', function(event) {
        if (event.target.matches('[data-bs-toggle="offcanvas"]')) {
            var currentId = event.target.id;  // get the id attribute from the button
            offcanvasElement.setAttribute('data-current-id', currentId); // set the data-current-id attribute on the offcanvas before showing it
        
            fetch(`/ramen/api/v1.0/details?id=${currentId}`)
                .then(response => response.json())
                .then(ramen_details => {
                    document.getElementById('offcanvasScrollingLabel').textContent = ramen_details.name;
                    document.querySelector('.offcanvas-header img').setAttribute('src', ramen_details.img_base64);
                    document.querySelector('.offcanvas-body .official-site').innerHTML = `<a href="${ramen_details.website}" target="_blank">店家網站</a>`;;
                    document.querySelector('.offcanvas-body .address').textContent = "Address: " + ramen_details.address;
                    document.querySelector('.offcanvas-body .google-maps').innerHTML = `<a href="${ramen_details.google_maps}" target="_blank">在google地圖中顯示</a>`;

                    const openTimeContainer = document.querySelector('.offcanvas-body .open-time');
                    openTimeContainer.innerHTML = '';
                    for (const day in ramen_details.open_time) {
                        if (ramen_details.open_time.hasOwnProperty(day)) {
                            const openTime = ramen_details.open_time[day];
                            document.querySelector('.offcanvas-body .open-time').innerHTML += `<p>${day}: ${openTime}</p>`;
                        }
                    }

                    const overallRating = ramen_details.overall_rating;
                    const ratingDetails = `
                        <p>平均: ${overallRating.mean} / 5</p>
                        <p>5星: ${ramen_details.overall_rating.amount_5}</p>
                        <p>4星: ${ramen_details.overall_rating.amount_4}</p>
                        <p>3星: ${ramen_details.overall_rating.amount_3}</p>
                        <p>2星: ${ramen_details.overall_rating.amount_2}</p>
                        <p>1星: ${ramen_details.overall_rating.amount_1}</p>`;

                    document.querySelector('.offcanvas-body .overall-rating').innerHTML = ratingDetails;
                });

            var bsOffcanvas = new bootstrap.Offcanvas(offcanvasElement);
            bsOffcanvas.show(); // show the offcanvas

            // initialize or use existing Socket.IO connection
            if (!window.socket) {
                window.socket = io('https://ramentaiwan.info/');

                window.socket.on('connect', function() {
                    console.log('Socket.IO connected for ID:', currentId);
                    // use the ID to emit a message or join a specific room
                    window.socket.emit('join_room', { "id": currentId });
                });

                window.socket.on('server_response', function(data) {
                    var logElement = document.getElementById('log');
                    var div = document.createElement('div');
                    div.textContent = 'Received: ' + data.message;
                    logElement.appendChild(div);
                });
            }
        }
    });

    offcanvasElement.addEventListener('hidden.bs.offcanvas', function(event) {
        var currentId = this.getAttribute('data-current-id');
        var logElement = document.getElementById('log');

        if (window.socket) {
            window.socket.emit('leave_room', { "id": currentId });
            window.socket.disconnect();
            window.socket = null;
            console.log('Socket.IO disconnected for ID:', currentId);
        }

        logElement.innerHTML = ''; 
    });

    var formElement = document.getElementById('emit');
    var inputElement = document.getElementById('emit_data');

    formElement.addEventListener('submit', function(event) {
        var currentId = offcanvasElement.getAttribute('data-current-id');
        event.preventDefault();
        if (window.socket && window.socket.connected) {
            var messageToSend = inputElement.value;
            window.socket.emit('client_event', {
                "data": messageToSend,
                "id": currentId 
            });
            inputElement.value = '';  // clear the input after sending
        } else {
            console.error("Socket.IO connection not established.");
        }
    });
});
