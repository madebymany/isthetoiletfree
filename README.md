isthetoiletfree
===============

```
git remote add heroku git@heroku.com:isthetoiletfree.git
ssh pi@isthetoiletfree.local
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
* https://gist.github.com/howthebodyworks/176149
* http://raspberrywebserver.com/serveradmin/run-a-script-on-start-up.html
