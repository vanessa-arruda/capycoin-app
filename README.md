# Capycoin 🐾

Gamified financial education for kids to help them save money and have control of it in a gamefied way.
the activities will be chores and plays that will give them points that can be exchanged by rewards set by their parents.

## parents accounts:
- sets how many kids account will be related to their account (and approve the link after the kid creates profile - using email)
- sets points value for each activity
- sets which activities they turn available from the existent list available
- review and approve the activity the kids sent for review/approval
- sets the period for how long each activity is available for conclusion (like temporary quests in a game) and how many times they can do that activity per day/week/month.
- see the board with all current available activity
- see how many points and which activities the kids have right now.

## child accounts:
- child receives an invite to create their profile as kid (with their name, email and a capybara avatar)
- can list all available activities
- can choose which activity they wanna pick up
- can see all on going activity they chose
- see all completed activities they did
- can see list of rewards
- can exchange the points they have for the rewards available up to the total points available.
- can see all points they have
- gains level for each amount of activities completed, certain levels, unlock new special items for exchange.

## How to run

```bash
make install
make dev
```

## first steps
Step	What
1	    Set up  FastAPI app and simple hello world route
2	    Set up  database connection (SQLAlchemy + Supabase/PostgreSQL)
3	    Set up  configuration loader (.env variables)
4	    Set up  basic models (Parent, Child, Activity)
5	    Set up  basic API routers (like /parent, /child)
6	    Make simple Pydantic schemas (for request/response)