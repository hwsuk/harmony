FROM python:3.11.6-alpine3.18

COPY harmony_cogs /botapp/harmony_cogs
COPY harmony_config /botapp/harmony_config
COPY harmony_models /botapp/harmony_models
COPY harmony_services /botapp/harmony_services

ADD main.py /botapp
ADD requirements.txt /botapp
ADD verification_template.md /botapp

RUN pip install -r /botapp/requirements.txt
RUN ls -laR /botapp

CMD ["python3", "/botapp/main.py"]