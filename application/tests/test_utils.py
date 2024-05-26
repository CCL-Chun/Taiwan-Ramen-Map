import pytest
from unittest.mock import MagicMock
from freezegun import freeze_time
from utils import create_geojson_feature, calculate_ttl, find_youbike, get_messages
from datetime import datetime, timedelta
import pytz

# Mock current_weekday function to control the output
def mock_current_weekday():
    return "Monday"

@pytest.fixture
def mock_ramen_data():
    return {
        "name": "Ramen Place",
        "address": "123 Ramen St.",
        "location": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        "open_time": {
            "Monday": "11:00 - 21:00"
        },
        "overall_rating": {
            "mean": 4.5
        },
        "place_id": "123abc"
    }

@pytest.fixture
def mock_ramen_data_partial_1():
    return {
        "name": "Ramen Place",
        "location": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        # Missing address and open_time
        "overall_rating": {
            "mean": 4.5
        },
        "place_id": "123abc"
    }

@pytest.fixture
def mock_ramen_data_partial_2():
    return {
        "name": "Ramen Place",
        "address": "123 Ramen St.",
        "location": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        "open_time": {
            "Monday": "11:00 - 21:00"
        },
        # Missing overall_rating and place_id
    }

def test_create_geojson_feature(monkeypatch, mock_ramen_data):
    # Use monkeypatch to replace current_weekday with mock_current_weekday
    monkeypatch.setattr('utils.current_weekday', mock_current_weekday)

    expected_result = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        "properties": {
            "name": "Ramen Place",
            "address": "123 Ramen St.",
            "weekday": "Monday",
            "open": "11:00 - 21:00",
            "overall": 4.5,
            "id": "123abc"
        }
    }

    result = create_geojson_feature(mock_ramen_data)
    assert result == expected_result

def test_create_geojson_feature_partial_1(monkeypatch, mock_ramen_data_partial_1):
    # Use monkeypatch to replace current_weekday with mock_current_weekday
    monkeypatch.setattr('utils.current_weekday', mock_current_weekday)

    expected_result = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        "properties": {
            "name": "Ramen Place",
            "address": "暫無",
            "weekday": "Monday",
            "open": "不定",
            "overall": 4.5,
            "id": "123abc"
        }
    }

    result = create_geojson_feature(mock_ramen_data_partial_1)
    assert result == expected_result

def test_create_geojson_feature_partial_2(monkeypatch, mock_ramen_data_partial_2):
    # Use monkeypatch to replace current_weekday with mock_current_weekday
    monkeypatch.setattr('utils.current_weekday', mock_current_weekday)

    expected_result = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [121.5654, 25.033]
        },
        "properties": {
            "name": "Ramen Place",
            "address": "123 Ramen St.",
            "weekday": "Monday",
            "open": "11:00 - 21:00",
            "overall": "N/A",
            "id": "Ramen Place"
        }
    }

    result = create_geojson_feature(mock_ramen_data_partial_2)
    assert result == expected_result

def test_calculate_ttl_various_times():
    timezone = pytz.timezone('Asia/Taipei')

    # Test different times of the day
    test_times = [
        ("2024-05-18 00:00:00+08:00", 172800),  # Start of the day (48 hours)
        ("2024-05-18 18:30:00+08:00", 106200),  # Evening (29.5 hours)
        ("2024-05-18 23:59:59+08:00", 86401),   # One second before midnight (24 hours + 1 second)
        ("2024-05-19 12:00:00+08:00", 129600)   # Midnight (36 hours)
    ]

    for time_str, expected_ttl in test_times:
        with freeze_time(time_str):
            result = calculate_ttl()
            assert result == expected_ttl

@pytest.fixture
def mock_youbike_data():
    return [
        {
            "_id": "661e918ce9cb49952e539f26",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [121.54142, 25.01451]
            },
            "properties": {
                "sno": "500101024",
                "sna": "YouBike2.0_臺灣科技大學正門",
                "sarea": "大安區",
                "mday": "2024-05-18 15:43:21",
                "ar": "基隆路四段43號(臺灣科技大學正門旁小側門靠田徑場)",
                "sareaen": "Daan Dist.",
                "snaen": "YouBike2.0_NTUST(Main Gate)",
                "aren": "No. 43, Sec. 4, Keelung Rd."
            }
        },
        {
            "_id": "661e918ce9cb49952e539f11",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [121.5436, 25.02605]
            },
            "properties": {
                "sno": "500101001",
                "sna": "YouBike2.0_捷運科技大樓站",
                "sarea": "大安區",
                "mday": "2024-05-18 15:45:21",
                "ar": "復興南路二段235號前",
                "sareaen": "Daan Dist."
            }
        },
        {
            "_id": "661e918ce9cb49952e539f12",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [121.5446, 25.02705]
            },
            "properties": {
                "sno": "500101002",
                "sna": "YouBike2.0_捷運大安站",
                "sarea": "大安區",
                "mday": "2024-05-18 16:00:21",
                "ar": "復興南路二段236號前",
                "sareaen": "Daan Dist."
            }
        },
        {
            "_id": "661e918ce9cb49952e539f28",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [121.54062, 25.01137]
            },
            "properties": {
                "sno": "500101026",
                "sna": "YouBike2.0_公館公園",
                "sarea": "大安區",
                "mday": "2024-05-18 15:43:20",
                "ar": "羅斯福路四段113巷基隆路四段41巷口",
                "sareaen": "Daan Dist.",
                "snaen": "YouBike2.0_Gongguan Park"
            }
        },
        {
            "_id": "661e918ce9cb49952e539f29",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [121.54165, 25.01182]
            },
            "properties": {
                "sno": "500101027",
                "sna": "YouBike2.0_臺灣科技大學後門",
                "sarea": "大安區",
                "mday": "2024-05-18 15:45:21",
                "ar": "基隆路四段41巷68弄臺科帆船大樓旁",
                "sareaen": "Daan Dist.",
                "snaen": "YouBike2.0_NTUST(Main Gate)",
                "aren": "No. 43, Sec. 4, Keelung Rd."
            }
        }
    ]

def test_find_youbike(monkeypatch, mock_youbike_data):
    # Create a mock collection with a find method
    mock_collection = MagicMock()
    mock_collection.find.return_value.limit.return_value = mock_youbike_data

    # Test the function with the mock collection
    lat, lng = 25.014, 121.541
    nearest_station = find_youbike(mock_collection, lat, lng)
    
    expected_result = mock_youbike_data[0]
    assert nearest_station == expected_result

    # Test the function when no stations are found
    mock_collection.find.return_value.limit.return_value = []
    with pytest.raises(Exception, match=f"Find no YouBike stations around {lat},{lng}"):
        find_youbike(mock_collection, lat, lng)


@pytest.fixture
def mock_redis_messages():
    return [
        (b'message1', 1652954040),  # Timestamp for 2022-05-19 11:34:00
        (b'message2', 1652982300),  # Timestamp for 2022-05-19 19:45:00
    ]

def test_get_messages(monkeypatch, mock_redis_messages):
    # Create a mock Redis client with a zrange method
    mock_redis_client = MagicMock()
    mock_redis_client.zrange.return_value = mock_redis_messages

    # Define the room_id and date_key for the test
    room_id = "room123"
    date_key = "2022-05-19"
    redis_key = f"messages_{room_id}_{date_key}"

    # Test the function with the mock Redis client
    messages = get_messages(mock_redis_client, room_id, date_key)
    
    expected_result = mock_redis_messages
    assert messages == expected_result

    # Ensure the correct Redis key was used
    mock_redis_client.zrange.assert_called_with(redis_key, 0, -1, withscores=True)

