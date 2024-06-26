[![CI for Taiwan-Ramen-Map](https://img.shields.io/github/actions/workflow/status/CCL-Chun/Taiwan-Ramen-Map/CI.yml?style=plastic&label=CI
)](https://github.com/CCL-Chun/Taiwan-Ramen-Map/actions/workflows/CI.yml)
[![CD for Taiwan-Ramen-Map](https://img.shields.io/github/actions/workflow/status/CCL-Chun/Taiwan-Ramen-Map/deploy.yml?style=plastic&label=CD
)](https://github.com/CCL-Chun/Taiwan-Ramen-Map/actions/workflows/deploy.yml)
[![codecov](https://img.shields.io/codecov/c/github/CCL-Chun/Taiwan-Ramen-Map?token=WF853T4QT2&style=plastic&logo=codecov&color=red
)](https://codecov.io/github/CCL-Chun/Taiwan-Ramen-Map)
![Static Badge](https://img.shields.io/badge/Python-3.12.2-blue?style=plastic&logo=python)
![Static Badge](https://img.shields.io/badge/Flask-2.3.1-orange?style=plastic&logo=flask)
![Static Badge](https://img.shields.io/badge/Socket.IO-4.7.4-white?style=plastic&logo=socket.io&labelColor=black)
![Static Badge](https://img.shields.io/badge/Redis--stack-7.2.0--v10-%23FF0000?style=plastic&logo=Redis&labelColor=white)
![Static Badge](https://img.shields.io/badge/Selenium-4.20.0-50C878?style=plastic&logo=selenium)
![Static Badge](https://img.shields.io/badge/Leaflet-1.9.4-blue?style=plastic&logo=leaflet&labelColor=green)
![Static Badge](https://img.shields.io/badge/Bootstrap-5.1.3-purple?style=plastic&logo=Bootstrap&labelColor=white)


## Taiwan Ramen Map

[Visit Taiwan Ramen Map](https://ramentaiwan.info)

## Table of Contents
- [Taiwan Ramen Map](#taiwan-ramen-map)
- [Table of Contents](#table-of-contents)
- [Objective](#objective)
- [Infrastructure](#infrastructure)
- [Monitoring](#monitoring)
  - [data pipeline](#data-pipeline)
  - [web server](#web-server)
- [HTTP load test](#http-load-test)
  - [MongoDB connection (Secondary Node Preferred)](#mongodb-connection-secondary-node-preferred)
  - [MongoDB connection (Default Primary Node)](#mongodb-connection-default-primary-node)
- [Features](#features)
- [CI/CD](#cicd)
## Objective
Taiwan Ramen Map is designed to provide an interactive and user-friendly platform for ramen enthusiasts and newcomers, offering real-time updates, dynamic searches, and similar ramen restaurant recommendations.

## Infrastructure
![Static Badge](https://img.shields.io/badge/MongoDB-lightgreen?style=plastic&logo=mongodb)
![Static Badge](https://img.shields.io/badge/Docker-blue?style=plastic&logo=docker&logoColor=white)
![Static Badge](https://img.shields.io/badge/nginx-white?style=plastic&logo=nginx&logoColor=%234CBB17)
![Static Badge](https://img.shields.io/badge/EC2-AWS-orange?style=plastic&logo=amazon-ec2)
![Static Badge](https://img.shields.io/badge/Lambda-AWS-orange?style=plastic&logo=aws-lambda)
![Static Badge](https://img.shields.io/badge/SQS-AWS-orange?style=plastic&logo=amazon-sqs)
![Static Badge](https://img.shields.io/badge/CloudWatch-AWS-orange?style=plastic&logo=amazon-cloudwatch)
![Static Badge](https://img.shields.io/badge/S3-AWS-orange?style=plastic&logo=amazon-s3)

* infra abstract ![infra-abstract](https://github.com/CCL-Chun/Taiwan-Ramen-Map/assets/56715642/f62c9b5f-f8f1-43c8-aa97-c7a40efe240e)
- **Data Pipeline Automation**: Automated data pipeline triggered by EventBridge to fetch ramen information and update recommendations based on new reviews using AWS Lambda, SQS, and EC2.
- **Service Monitoring**: Utilizes AWS CloudWatch to monitor application logs, service status, and alarm notifications.


## Monitoring
### data pipeline
* Flow cahrt ![data-pipeline-1](https://github.com/CCL-Chun/Taiwan-Ramen-Map/assets/56715642/da229b12-de6b-4154-b759-3184792b8b4b)
* Dashboard ![CloudWatch LambdaCrawlerDashboard screenshot](https://github.com/CCL-Chun/Taiwan-Ramen-Map/assets/56715642/b8c557aa-08e6-4ae9-8b2e-d01eb81e0ce7)


### web server


## HTTP load test
HTTP load testing by [vegeta](https://github.com/tsenart/vegeta?tab=readme-ov-file)

Reading data from a secondary node is preferable because the primary node is responsible for handling write operations for the YouBike instant data every minute. Performing both read and write operations on the primary node simultaneously can lead to heavy loading on MongoDB, which may affect performance and stability. By offloading read operations to a secondary node, we can distribute the load more effectively and ensure smoother performance.

Additionally, I've observed that while reading from the primary node at a rate of 40 requests per second (rps), the number of connections increases significantly. However, this is not the case when reading from the secondary node. This indicates that the primary node's dual role in handling both reads and writes can lead to connection scaling issues, further supporting the strategy of reading from secondary nodes.
### MongoDB connection (Secondary Node Preferred)
```python
# connect to MongoDB and read from secondary node
MongoClient(uri, server_api=ServerApi('1'),readPreference='secondaryPreferred')
```
[Vegeta plot for test result](https://ccl-chun.github.io/Taiwan-Ramen-Map/vegeta_test/results_ramens_details_rps40_secondary.html)
```python
# vegeta report
Requests      [total, rate, throughput]         4800, 40.01, 39.99
Duration      [total, attack, wait]             2m0s, 2m0s, 43.295ms
Latencies     [min, mean, 50, 90, 95, 99, max]  37.832ms, 44.075ms, 42.226ms, 47.095ms, 53.153ms, 88.793ms, 333.181ms
Bytes In      [total, mean]                     6350400, 1323.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:4800
```
### MongoDB connection (Default Primary Node)
[Vegeta plot for test result](https://ccl-chun.github.io/Taiwan-Ramen-Map/vegeta_test/results_ramens_details_rps40.html)
```python
# vegeta report
Requests      [total, rate, throughput]         4800, 40.01, 39.98
Duration      [total, attack, wait]             2m0s, 2m0s, 100.148ms
Latencies     [min, mean, 50, 90, 95, 99, max]  55.743ms, 262.64ms, 88.694ms, 920.439ms, 1.319s, 2.048s, 3.318s
Bytes In      [total, mean]                     418569600, 87202.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:4800
```


## Features
- **Real-time Report**: Users can report and view live restaurant conditions, such as the queue length, using Flask and Socket.IO.
  - ![demo](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/real-time-demo.gif)
- **Search by Name**: Fast query capability using RediSearch to reduce latency and lighten the load on MongoDB.
  - ![search-name-demo](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/search-name-demo.gif)
- **Dynamic Map**: Provides dynamic search for nearby ramen restaurants, displaying unique characteristics, store details, and nearby parking options using MongoDB for fast geospatial queries.
  - ![Dynamic Map Demo](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/dynamic-map-demo.gif)
- **Recommendation System**: Content-based filtering with text embeddings from user reviews and comments to recommend the top 5 related ramen restaurants.
  - <img width="397" alt="recommend-demo" src="https://github.com/CCL-Chun/Taiwan-Ramen-Map/assets/56715642/7545b416-ecd2-4263-a962-2e7f4c0c0d95">
- **Multi-vehicle Route Optimization**: Offers current fastest route planning considering public bike shares and other public transit options using a multi-stop and multi-vehicle route planner.
  - Route planner will show routes on map and cooperate with navigation instructions of each sub-route.
  - Route planner will suggest a combined route considering YouBike2.0 as vehicle if the origin plan needs bus change.
  - ![deom](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/route-plan-demo.gif)

## CI/CD


* Test report had uploaded to [Codecov](https://codecov.io/github/CCL-Chun/Taiwan-Ramen-Map) during CI workflow [![codecov](https://img.shields.io/codecov/c/github/CCL-Chun/Taiwan-Ramen-Map?token=WF853T4QT2&style=plastic&logo=codecov&color=red
)](https://codecov.io/github/CCL-Chun/Taiwan-Ramen-Map)
```
---------- coverage: platform linux, python 3.12.2-final-0 -----------
Name                                                    Stmts   Miss  Cover
---------------------------------------------------------------------------
application/config.py                                      14      0   100%
application/server/__init__.py                             42     14    67%
application/server/controllers/__init__.py                  0      0   100%
application/server/controllers/ramen_controller.py         39     20    49%
application/server/controllers/search_controller.py        30     22    27%
application/server/controllers/socketio_controller.py      40     22    45%
application/server/controllers/traffic_controller.py      139    128     8%
application/server/models/Database.py                      14      7    50%
application/server/models/Redis.py                         20     13    35%
application/server/models/__init__.py                       0      0   100%
application/server/views.py                                19      7    63%
application/tests/__init__.py                               0      0   100%
application/tests/conftest.py                              52     27    48%
application/tests/integration/test_integration.py          15      0   100%
application/tests/test_utils.py                            65      0   100%
application/utils.py                                       87     58    33%
---------------------------------------------------------------------------
TOTAL                                                     576    318    45%
Coverage XML written to file coverage.xml
======================== 9 passed, 4 warnings in 0.33s =========================
```
