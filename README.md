# certificates.dipy.org
Small webapp to manage DIPY certificates from the workshop



## Instructions for IU server

activate environment
> source activate venv312
install new package
> uv pip install -r requirement.txt
start the app
> ~/path/to/supervisor/supervisord -c supervisord.conf
control the app
> supervisorctl restart/start/stop/status fastapi

## Create new environment

uv venv venv312 --python 3.12
