isthetoiletfree
===============

Deploying the client:

```
git remote add pi pi@isthetoiletfree.local:isthetoiletfree.git
```

Deploying the server:

```
git remote add heroku git@heroku.com:isthetoiletfree.git
```

Import the database schema on Heroku:

```
heroku pg:psql < schema.sql
```

Running in development:

```
supervisorctl
stop ittf
start ittfdev
```

## Useful links

* http://serverfault.com/questions/96499/how-to-automatically-start-supervisord-on-linux-ubuntu
* http://raspberrywebserver.com/serveradmin/run-a-script-on-start-up.html
* http://monkeyhacks.com/raspberry-pi-as-private-git-server
