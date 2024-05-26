![Static Badge](https://img.shields.io/badge/Python-3.12.2-blue?style=plastic&logo=python)
![Static Badge](https://img.shields.io/badge/Flask-2.3.1-orange?style=plastic&logo=flask)
![Static Badge](https://img.shields.io/badge/Socket.IO-4.7.4-white?style=plastic&logo=socket.io&labelColor=black)
![Static Badge](https://img.shields.io/badge/Redis--stack-7.2.0--v10-%23FF0000?style=plastic&logo=Redis&labelColor=white)
![Static Badge](https://img.shields.io/badge/Selenium-4.20.0-50C878?style=plastic&logo=selenium)
![Static Badge](https://img.shields.io/badge/Leaflet-1.9.4-blue?style=plastic&logo=leaflet&labelColor=green)
![Static Badge](https://img.shields.io/badge/Bootstrap-5.1.3-purple?style=plastic&logo=Bootstrap&labelColor=white)


# Taiwan Ramen Map

[Visit Taiwan Ramen Map](https://ramentaiwan.info)

## Table of Contents
- [Taiwan Ramen Map](#taiwan-ramen-map)
  - [Table of Contents](#table-of-contents)
  - [Objective](#objective)
  - [Features](#features)
  - [Infrastructure](#infrastructure)
  - [Deployment](#deployment)

## Objective
Taiwan Ramen Map is designed to provide an interactive and user-friendly platform for ramen enthusiasts and newcomers, offering real-time updates, dynamic searches, and similar ramen restaurant recommendations.

## Features
- **Real-time Report**: Users can report and view live restaurant conditions, such as the queue length, using Flask and Socket.IO.
  - ![demo](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/real-time-demo.gif)
- **Search by Name**: Fast query capability using RediSearch to reduce latency and lighten the load on MongoDB.
  - ![search-name-demo](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/search-name-demo.gif)
- **Dynamic Map**: Provides dynamic search for nearby ramen restaurants, displaying unique characteristics, store details, and nearby parking options using MongoDB for fast geospatial queries.
   - ![deom](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/dynamic-map-demo.gif)
- **Recommendation System**: Content-based filtering with text embeddings from user reviews and comments to recommend the top 5 related ramen restaurants.
  - <img width="397" alt="recommend-demo" src="https://github.com/CCL-Chun/Taiwan-Ramen-Map/assets/56715642/7545b416-ecd2-4263-a962-2e7f4c0c0d95">
- **Multi-vehicle Route Optimization**: Offers current fastest route planning considering public bike shares and other public transit options using a multi-stop and multi-vehicle route planner.
  - Route planner will show routes on map and cooperate with navigation instructions of each sub-route.
  - Route planner will suggest a combined route considering YouBike2.0 as vehicle if the origin plan needs bus change.
  - ![deom](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/4c2fc8a4250271334e2650294aed02075e2fe4d1/route-plan-demo.gif)

## Infrastructure
![Static Badge](https://img.shields.io/badge/MongoDB-lightgreen?style=plastic&logo=mongodb)
![Static Badge](https://img.shields.io/badge/Docker-blue?style=plastic&logo=docker&logoColor=white)
![Static Badge](https://img.shields.io/badge/nginx-white?style=plastic&logo=nginx&logoColor=%234CBB17)
![Static Badge](https://img.shields.io/badge/EC2-AWS-orange?style=plastic&logo=amazon-ec2)
![Static Badge](https://img.shields.io/badge/Lambda-AWS-orange?style=plastic&logo=aws-lambda)
![Static Badge](https://img.shields.io/badge/SQS-AWS-orange?style=plastic&logo=amazon-sqs)
![Static Badge](https://img.shields.io/badge/CloudWatch-AWS-orange?style=plastic&logo=amazon-cloudwatch)
![Static Badge](https://img.shields.io/badge/S3-AWS-orange?style=plastic&logo=amazon-s3)


![infra abstract](https://github.com/CCL-Chun/Taiwan-Ramen-Map/blob/8bdbff866b7f31ef8f4b279d5d70ce8d6d946e88/infra%E4%BB%8B%E7%B4%B92.png)
- **Data Pipeline Automation**: Automated data pipeline triggered by EventBridge to fetch ramen information and update recommendations based on new reviews using AWS Lambda, SQS, and EC2.
- **Service Monitoring**: Utilizes AWS CloudWatch to monitor application logs, service status, and alarm notifications.

## Deployment
1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/taiwan-ramen-map.git
   ```
2. 
