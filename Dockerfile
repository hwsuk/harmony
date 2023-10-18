FROM python:3.11.6-alpine3.18

COPY harmony_cogs /botapp/harmony_cogs
COPY harmony_config /botapp/harmony_config
COPY harmony_models /botapp/harmony_models
COPY harmony_services /botapp/harmony_services
COPY harmony_ui /botapp/harmony_ui
COPY harmony_scheduled /botapp/harmony_scheduled

ADD main.py /botapp
ADD requirements.txt /botapp
ADD verification_template.md /botapp

RUN pip install -r /botapp/requirements.txt

WORKDIR /botapp
CMD ["python3", "main.py"]
