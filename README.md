isthetoiletfree
===============

```
git remote add heroku git@heroku.com:isthetoiletfree.git
ssh isthetoiletfree.local
```

Import the database schema on Heroku:

```
heroku pg:psql < schema.sql
```

To start the client (for now):

```
sudo screen -S isthetoiletfree -d -m $HOME/run.sh
```
