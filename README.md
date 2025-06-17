# certificates.dipy.org
Small webapp to manage DIPY certificates from the workshop



## Instructions for IU server

Activate environment
```terminal
source activate venv312
```
Install new package
```terminal
uv pip install -r requirement.txt
```
Start the app
```terminal
~/path/to/supervisor/supervisord -c supervisord.conf
```
Control the app
```terminal
supervisorctl restart/start/stop/status fastapi
```

In case of an update of supervisord.conf, restart supervisor:
```
supervisorctl reread
supervisorctl update
supervisorctl restart fastapi
```

## Create new environment

```terminal
uv venv venv312 --python 3.12
```
