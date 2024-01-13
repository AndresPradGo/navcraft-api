"""
Schedule Clean Database Job

Module schedules a job that runs every 24 hours and cleans all 
the trial accounts from the database.

Usage: 
- Import the schedule_clean_db_job function, and run it in the main module.

"""
from datetime import datetime, timedelta

from sqlalchemy import and_
from apscheduler.schedulers.background import BackgroundScheduler


import models
from utils.db import Session


def schedule_clean_db_job():
    """
    This function create a scheduler and schedules a job that runs every 
    24 hours, and deletes all the trial accounts that are more than 24 hours old.
    """

    scheduler = BackgroundScheduler()
    scheduler.start()

    def cleanup_database():

        threshold_datetime = datetime.utcnow() - timedelta(hours=24)

        try:
            with Session() as db_session:
                db_session.query(models.User).filter(and_(
                    models.User.is_trial.is_(True),
                    models.User.created_at <= threshold_datetime
                )).delete()

                db_session.commit()
        except Exception as e:
            db_session.rollback()

    scheduler.add_job(cleanup_database, 'interval', hours=24)
