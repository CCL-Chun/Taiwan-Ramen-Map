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
let newLatLng;
let socket;

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
            timeout: 1000,
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

    let HomeControl = L.Control.extend({
        options: {
            position: 'topleft'
        },
    
        onAdd: function (map) {
            var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    
            // Create a button element
            var button = L.DomUtil.create('a', 'leaflet-control-home leaflet-bar-part leaflet-bar-part-single', container);
            button.title = '回到現在位置';
    
            // Add class for the icon
            L.DomUtil.addClass(button, 'home-icon');
    
            // Add a click event listener to the button
            L.DomEvent.on(button, 'click', function (e) {
                map.setView(this.options.homeCoordinates, this.options.homeZoom);
                startMarker.openPopup();
            }, this);
    
            return container;
        }
    });

    // create a home button
    let homeCoordinates = [lat, lng];
    let homeZoom = 16;
    map.addControl(
        new HomeControl({
            homeCoordinates: homeCoordinates,
            homeZoom: homeZoom,
            position: 'bottomright'
        })
    );

    // move zoom controller to bottomright
    map.zoomControl.setPosition('bottomright');
}

// first view of the map
function firstView(){
    updateRamen();
}

function setupEventListeners() {
    // search for parking lots around ramen
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

    lastMoveLatLng = L.latLng(defaultLat, defaultLng);
    // show the update button
    map.on('moveend', function() {
        newLatLng = map.getCenter();
        
        if (lastMoveLatLng) {
            var distance = lastMoveLatLng.distanceTo(newLatLng);
            // Convert distance to kilometers
            var distanceInKm = distance / 1000;
            if (distanceInKm > 3) {
                displayUpdateRamenButton();
                lastMoveLatLng = newLatLng;
            }
        }
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
                                            ' ' + 'lat=' + feature.geometry.coordinates[1] + ' type="button" data-bs-toggle="offcanvas" ' +
                                            'data-bs-target="#instructions-wrapper" aria-controls="instructions-wrapper">' +
                                            '拉麵突進導航</button>' + '<br>' +
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
    // do noting when a update button is already there
    if (document.querySelector('.leaflet-control-update-ramen')) {
        return;
    };
    // Create a button element
    var button = L.DomUtil.create('button', 'btn btn-warning leaflet-control-update-ramen leaflet-bar-part leaflet-bar-part-single');
    button.innerHTML = 'Update Ramen';
    button.title = 'Update Ramen';
    // Set CSS style for button positioning
    button.style.position = 'absolute';
    button.style.top = '10px';
    button.style.left = '65%';
    button.style.zIndex = 1000;

    // Add the button to the map
    map.getContainer().appendChild(button);
    
    // Add a click event listener to the button
    L.DomEvent.on(button, 'click', function () {
        // Call the updateRamen function
        updateRamen();
        // Remove the button from the map
        map.getContainer().removeChild(button);
        // renew lastMoveLatLng
        lastMoveLatLng = newLatLng;
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
                        var popupContent = feature.properties.gatename + '<br>';
                        
                        if (feature.properties.opentime) {
                            popupContent += feature.properties.opentime + '<br>';
                        }
                    
                        if (feature.properties.parknum) {
                            popupContent += feature.properties.parknum + '<br>';
                        }
                    
                        if (feature.properties.feeb) {
                            popupContent += feature.properties.feeb + '<br>';
                        }
                    
                        if (feature.properties.gadetype1) {
                            popupContent += feature.properties.gadetype1;
                        }
                    } else{
                        var popupContent = '路邊:' + roadParkType[feature.properties.pktype]
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
            console.log(data);
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
        // add icon based on travelMode
        var iconClass = '';
        if (step.travelMode === 'WALK') {
            iconClass = 'bi bi-person-walking';
        } else if (step.travelMode === 'TRANSIT') {
            iconClass = 'bi bi-bus-front-fill';
        } else if (step.travelMode === 'YouBike2') {
            iconClass = 'bi bi-bicycle';
        }

        var icon = $('<i class="' + iconClass + '"></i>');
        instruction.prepend(icon); // prepend the icon before the instruction text

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
        youbikeSteps.forEach((step, index) => {
            var instructionText = (step.navigationInstruction && step.navigationInstruction.instructions) ? step.navigationInstruction.instructions : '走路';
            var instruction = $('<div class="instruction youbike" data-step-index="' + index + '">' + instructionText + '</div>');
            // add icon based on travelMode
            var iconClass = '';
            if (step.travelMode === 'WALK') {
                iconClass = 'bi bi-person-walking';
            } else if (step.travelMode === 'TRANSIT') {
                iconClass = 'bi bi-bus-front-fill';
            } else if (step.travelMode === 'YouBike2') {
                iconClass = 'bi bi-bicycle';
            }

            var icon = $('<i class="' + iconClass + '"></i>');
            instruction.prepend(icon); // prepend the icon before the instruction text

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
        if (event.target.matches('[data-bs-toggle="offcanvas"]') && event.target.getAttribute('data-bs-target') !== '#instructions-wrapper') {
            var currentId = event.target.id;  // get the id attribute from the button
            offcanvasElement.setAttribute('data-current-id', currentId); // set the data-current-id attribute on the offcanvas before showing it
        
            fetch(`/ramen/api/v1.0/details?id=${currentId}`)
                .then(response => response.json())
                .then(ramen_details => {
                    document.getElementById('offcanvasScrollingLabel').textContent = ramen_details.name;
                    document.querySelector('.offcanvas-header img').setAttribute('src', ramen_details.img_base64);
                    document.querySelector('.offcanvas-body .official-site').innerHTML = `<a href="${ramen_details.website}" target="_blank">店家網站</a>`;;
                    document.querySelector('.offcanvas-body .address').textContent = "地址: " + ramen_details.address;
                    document.querySelector('.offcanvas-body .google-maps').innerHTML = `<a href="${ramen_details.maps_url}" target="_blank">在google地圖中顯示</a>`;
                    
                    // open time
                    const openTimeContainer = document.querySelector('.offcanvas-body .open-time');
                    openTimeContainer.innerHTML = '';
                    
                    const chineseWeekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
                    let collapseContent = '';

                    chineseWeekdays.forEach(day => {
                            const openTime = ramen_details.open_time[day];
                            collapseContent += `<p>${day}: ${openTime}</p>`;
                    });

                    openTimeContainer.innerHTML = `
                        <button class="btn btn-outline-primary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#openingTimesCollapse" aria-expanded="false" aria-controls="openingTimesCollapse">
                            <span>營業時間 &#9660</sapn>
                        </button>
                        <div class="collapse" id="openingTimesCollapse">
                            ${collapseContent}
                        </div>
                    `;
                    
                    // ramen feature tags
                    const ramenFeaturesContainer = document.querySelector('.offcanvas-body .ramen-features');
                    ramenFeaturesContainer.innerHTML = '';
                    for (const features of ramen_details.features) {
                        ramenFeaturesContainer.innerHTML += `<span class="badge rounded-pill bg-info text-dark">${features}</span>&ensp;`;
                    };

                    // rating
                    const overallRating = ramen_details.overall_rating;
                    const totalReviews = overallRating.amount_5 + overallRating.amount_4 + overallRating.amount_3 + overallRating.amount_2 + overallRating.amount_1;
                    const meanRating = parseFloat(overallRating.mean);

                    const ratingDetails = `
                        <button class="btn btn-primary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#ratingCollapse" aria-expanded="false" aria-controls="ratingCollapse">
                            <span>評分: ${meanRating} &starf; </span>  
                            <span>看分佈  &#9662;</span>
                        </button>
                        <div class="collapse" id="ratingCollapse">
                            <div class="progress">
                                <div class="progress-bar bg-success" role="progressbar" style="width: ${(overallRating.amount_5 / totalReviews) * 100}%">
                                    5星: ${overallRating.amount_5}
                                </div>
                                <div class="progress-bar bg-info" role="progressbar" style="width: ${(overallRating.amount_4 / totalReviews) * 100}%">
                                    4星: ${overallRating.amount_4}
                                </div>
                                <div class="progress-bar bg-warning" role="progressbar" style="width: ${(overallRating.amount_3 / totalReviews) * 100}%">
                                    3星: ${overallRating.amount_3}
                                </div>
                                <div class="progress-bar bg-danger" role="progressbar" style="width: ${(overallRating.amount_2 / totalReviews) * 100}%">
                                    2星: ${overallRating.amount_2}
                                </div>
                                <div class="progress-bar bg-secondary" role="progressbar" style="width: ${(overallRating.amount_1 / totalReviews) * 100}%">
                                    1星: ${overallRating.amount_1}
                                </div>
                            </div>
                        </div>`;

                    document.querySelector('.offcanvas-body .overall-rating').innerHTML = ratingDetails;

                    // recommend
                    console.log(ramen_details.similar)
                    const recommendContainer = document.querySelector('.offcanvas-body .ramen-recommend');
                    recommendContainer.innerHTML = '';
                    for (const recommend of ramen_details.similar) {
                        recommendContainer.innerHTML += `<span class="badge bg-secondary text-light">${recommend}</span>&ensp;`;
                    };

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
                    // div.textContent = 'Received: ' + data.message;
                    div.innerHTML = data.time + '<br>' + "    " + data.message;
                    logElement.appendChild(div);
                });
            } else {
                bsOffcanvas.hide();
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


function toggleOffCanvasVisibility() {
    var offcanvasElement = document.getElementById('instructions-wrapper');
    var bsOffcanvas = new bootstrap.Offcanvas(offcanvasElement);

    if (offcanvasElement.classList.contains('show')) {
        bsOffcanvas.hide();
    } else {
        bsOffcanvas.show();
    }
}

document.getElementById('instructions-wrapper').addEventListener('shown.bs.offcanvas', function () {
    document.getElementById('toggleButton').style.display = 'none'; // Hide button when off-canvas is open
});

document.getElementById('offcanvasScrolling').addEventListener('shown.bs.offcanvas', function () {
    document.getElementById('toggleButton').style.left = '300px'; // Hide button when off-canvas is open
});

let offcanvasElements = document.querySelectorAll('.offcanvas');

// Loop through each element and attach the event listener
offcanvasElements.forEach(function(offcanvas) {
    offcanvas.addEventListener('hidden.bs.offcanvas', function () {
        // Assuming 'offcanvasScrolling' is a specific off-canvas you want to check
        var offcanvasDetails = document.getElementById('offcanvasScrolling');
        var toggleButton = document.getElementById('toggleButton');

        // Check if the specific off-canvas is still shown or not
        if (offcanvasDetails && offcanvasDetails.classList.contains('show')) {
            toggleButton.style.display = 'block'; // Show button when off-canvas is open
            toggleButton.style.left = '300px';
        } else {
            toggleButton.style.display = 'block'; // Show button when all off-canvas are closed
            toggleButton.style.left = '0px';
        }
    });
});

// Search functions
function performSearch() {
    var inputValue = document.getElementById('searchInput').value;
    var resultsList = document.getElementById('resultsList');

    if (inputValue.length > 1) {
        fetch(`/search/api/v1.0/name/autocomplete?query=${encodeURIComponent(inputValue)}`)
            .then(response => response.json())
            .then(data => {
                if (!resultsList) {
                    resultsList = document.createElement('ul');
                    resultsList.id = 'resultsList';
                    document.getElementById('searchContainer').appendChild(resultsList);
                }
                resultsList.innerHTML = '';
                resultsList.style.display = 'block';

                data.forEach(item => {
                    var li = document.createElement('li');
                    
                    // Create and append the name element
                    var nameSpan = document.createElement('span');
                    nameSpan.textContent = item.name;
                    nameSpan.className = 'ramen-name';
                    li.appendChild(nameSpan);

                    // Create and append the address element
                    var addressSpan = document.createElement('span');
                    addressSpan.textContent = item.address;
                    addressSpan.className = 'ramen-address';
                    li.appendChild(addressSpan);

                    // Set the place_id as an attribute and add click event
                    li.setAttribute('data-place-id', item.place_id);
                    li.addEventListener('click', function() {
                        let place_id = this.getAttribute('data-place-id');
                        console.log(place_id);
                        searchRamen(place_id);
                    });

                    resultsList.appendChild(li);
                });
            })
            .catch(error => console.error('Error fetching data:', error));
    } else {
        alert('請輸入至少兩個字');
    }
}

document.addEventListener('click', function(event) {
    var resultsList = document.getElementById('resultsList');
    if (resultsList && event.target !== document.getElementById('searchInput')) {
        // Check if the click is outside of resultsList
        if (!resultsList.contains(event.target)) {
            resultsList.style.display = 'none';
        }
    }
});

function searchRamen(place_id){
    if (map) {
        if (!ramenLayer) {
            ramenLayer = L.layerGroup().addTo(map);
        }

        fetch(`/ramen/api/v1.0/restaurants/searchone?place_id=${place_id}`)
            .then(response => response.json())
            .then(ramen_geojson => {
                var geoJSONLayer = L.geoJSON(ramen_geojson, {
                    onEachFeature: function (feature, layer) {
                        var popupContent = createPopupContent(feature);
                        layer.bindPopup(popupContent);
                    }
                }).addTo(ramenLayer);

                map.fitBounds(geoJSONLayer.getBounds());

                if (ramen_geojson.features.length > 0) {
                    var firstFeatureLayer = geoJSONLayer.getLayers()[0]; // Gets the first layer in the GeoJSON layer
                    firstFeatureLayer.openPopup(); // Open the popup
                }
            })
            .catch(error => console.error('Error fetching data:', error));
    };
};

function createPopupContent(feature) {
    return feature.properties.name +
        '<br>' + feature.properties.weekday + feature.properties.open +
        '<br>評分: ' + feature.properties.overall + ' / 5'+
        '<br>' + feature.properties.address + '<br>' + 
        '<button class="find-parking btn-outline-primary btn-sm" lng=' + feature.geometry.coordinates[0] + 
            ' ' + 'lat=' + feature.geometry.coordinates[1] +
            '>附近停車位</button>' + '<br>' +
        '<button class="bring-me-here btn-outline-primary btn-sm" lng=' + feature.geometry.coordinates[0] + 
            ' ' + 'lat=' + feature.geometry.coordinates[1] + ' type="button" data-bs-toggle="offcanvas" ' +
            'data-bs-target="#instructions-wrapper" aria-controls="instructions-wrapper">' +
            '拉麵突進導航</button>' + '<br>' +
        '<button id=' + feature.properties.id + ' ' +
            'class="btn-outline-primary btn-sm" type="button" data-bs-toggle="offcanvas" ' +
            'data-bs-target="#offcanvasScrolling" aria-controls="offcanvasScrolling">' +
            '詳細資訊與現場情報</button>';
}