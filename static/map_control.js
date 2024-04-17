// initialize the map
var map = L.map('map').setView([25.052430, 121.520270], 16);

L.tileLayer('https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', 
    {
        maxZoom : 24,
        attribution: '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }
).addTo(map);

L.marker([25.052430, 121.520270]).addTo(map)
    .bindPopup('A pretty CSS3 popup.<br> Easily customizable.')
    .openPopup();

// first view of the map
function firstView(){
    updateRamen();
}

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
            // Now you can use lat and lng to request backend service
            console.log('Finding parking lots around:', lat, lng);


        }
    });
});

// get bounds based on the view
function updateRamen(){
    // Get the current map bounds as a string of comma-separated values
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
                                        '">Find Parking</button>';
                        layer.bindPopup(popupContent);
                    }
                }
            }).addTo(map);
        });
};


// function findParking(lat,lng){
//     fetch(`/traffic/api/v1.0/parking?lat=${lat}&lng=${lng}`)
//         .then(response => response.json())
//         .then(parking_data => {

//         });
// }


firstView()
