
import logging
from database_setup import engine, Base
from models import Subscription

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    logger.info("Starting migration...")
    try:
        # Create all tables defined in Base (only Subscription for now)
        Base.metadata.create_all(bind=engine)
        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
