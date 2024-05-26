import pytest

def test_ramen_details_no_id(test_client):
    response = test_client.get('/api/v1.0/ramens/details')
    assert response.status_code == 400
    assert response.json == {'error': "Missing 'id' parameter"}

def test_ramen_details_id_not_found(test_client):
    response = test_client.get('/api/v1.0/ramens/details?id=nonexistent_id')
    # assert response.status_code == 404
    assert response.json == {'error': 'place id nonexistent_id not found'}

def test_ramen_details_success(test_client, test_app):
    mock_ramen_details = {
        "name": "二屋牡蠣拉麵",
        "maps_url": "https://short.url/maps",
        "img_base64": "data:image/png;base64,...",
        "open_time": {
            "星期六": ["11:30-21:30"],
            "星期日": ["11:30-21:30"],
            "星期一": ["11:30-21:30"],
            "星期二": ["11:30-21:30"],
            "星期三": ["11:30-21:30"],
            "星期四": ["11:30-21:30"],
            "星期五": ["11:30-21:30"]
        },
        "website": "https://www.facebook.com/Oyster2022/",
        "overall_rating": {
            "mean": "4.1",
            "amount_5": 1086,
            "amount_4": 546,
            "amount_3": 225,
            "amount_2": 78,
            "amount_1": 132
        },
        "address": "台北市大同區赤峰街35巷11號",
        "place_id": "ChIJX9SvkIiPQjQRiasOMpJ63b4",
        "features": ["醬油", "雞豚白湯", "雞豚魚介濃湯", "大食", "濃厚系", "雞豚魚介"],
        "top_similar": ["勝王", "許誠屋 | 日式拉麵・御膳 (無訂位服務)", "啤一拉麵 總店", "Menya kama 麺屋龜 (アム）", "仁王家 (原景星)"]
    }

    # Insert mock data into the mock database
    test_app.mongo_connection['ramen_info'].insert_one(mock_ramen_details)

    response = test_client.get('/api/v1.0/ramens/details?id=ChIJX9SvkIiPQjQRiasOMpJ63b4')

    expected_result = {
        "name": "二屋牡蠣拉麵",
        "open_time": {
            "星期六": ["11:30-21:30"],
            "星期日": ["11:30-21:30"],
            "星期一": ["11:30-21:30"],
            "星期二": ["11:30-21:30"],
            "星期三": ["11:30-21:30"],
            "星期四": ["11:30-21:30"],
            "星期五": ["11:30-21:30"]
        },
        "maps_url": "https://short.url/maps",
        "img_base64": "data:image/png;base64,...",
        "website": "https://www.facebook.com/Oyster2022/",
        "overall_rating": {
            "mean": "4.1",
            "amount_5": 1086,
            "amount_4": 546,
            "amount_3": 225,
            "amount_2": 78,
            "amount_1": 132
        },
        "address": "台北市大同區赤峰街35巷11號",
        "place_id": "ChIJX9SvkIiPQjQRiasOMpJ63b4",
        "features": ["醬油", "雞豚白湯", "雞豚魚介濃湯", "大食", "濃厚系", "雞豚魚介"],
        "similar": ["勝王", "許誠屋 | 日式拉麵・御膳 (無訂位服務)", "啤一拉麵 總店", "Menya kama 麺屋龜 (アム）", "仁王家 (原景星)"]
    }

    assert response.status_code == 200
    assert response.json == expected_result


# def test_autocomplete_success_1(test_client,mock_redis):
#     response = test_client.get('/api/v1.0/ramens/autocomplete?query=麵屋')
#     assert response.status_code == 200
#     assert response.json == ['麵屋武藏', '麵屋昕家', '羽都麵屋', '黑曜麵屋']

# def test_autocomplete_success_2(test_client, mock_redis):
#     response = test_client.get('/api/v1.0/ramens/autocomplete?query=拉麵')
#     assert response.status_code == 200
#     assert response.json == ['實正拉麵']

# def test_autocomplete_no_results(test_client, mock_redis):
#     response = test_client.get('/api/v1.0/ramens/autocomplete?query=一蘭')
#     assert response.status_code == 200
#     assert response.json == []
