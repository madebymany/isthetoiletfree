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

To manage the client:

```
sudo /etc/init.d/isthetoiletfree start|stop
```
