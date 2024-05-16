FROM umihico/aws-lambda-selenium-python:3.12.2-selenium4.20.0-chrome124.0.6367.91
RUN pip install boto3==1.34.98 pytz requests
COPY main.py ./
CMD [ "main.lambda_handler" ]
