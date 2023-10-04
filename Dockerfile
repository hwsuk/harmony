FROM python:3.11.6-alpine3.18

ADD harmony_cogs /botapp
ADD harmony_config /botapp
ADD harmony_models /botapp
ADD harmony_services /botapp

ADD main.py /botapp
ADD requirements.txt /botapp
ADD verification_template.md /botapp

RUN pip install -r /botapp/requirements.txt

CMD ["python3", "/botapp/main.py"]
