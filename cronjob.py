# Package Scheduler.
from apscheduler.schedulers.blocking import BlockingScheduler

# Main cronjob function.
from getdata import main

# Create an instance of scheduler and add function.
scheduler = BlockingScheduler(timezone='utc')
scheduler.add_job(main, 'interval', seconds=600)

scheduler.start()