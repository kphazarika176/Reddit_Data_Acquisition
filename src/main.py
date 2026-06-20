import sys
from src.pipeline import ContentPipeline
from src.database import DatabaseManager
from src.view_data import view_stored_data
from src.logger import get_logger

logger = get_logger(__name__)

def main():
    db = DatabaseManager()
    pipeline = ContentPipeline()
    
    while True:
        print("\n====== Reddit Data Acquisition ======")
        print("1. Fresh Scrape")
        print("2. Update Database")
        print("3. View Stored Data")
        print("4. Delete Database")
        print("5. Exit")
        
        try:
            choice = input("Enter your choice (1-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
            
        if choice == "1":
            print("\nPerforming Fresh Scrape (Clearing database first)...")
            db.clear_database()
            try:
                pipeline.run()
            except Exception as e:
                logger.error(f"Pipeline run failed: {e}", exc_info=True)
                
        elif choice == "2":
            print("\nUpdating Database (Scraping new data)...")
            try:
                pipeline.run()
            except Exception as e:
                logger.error(f"Pipeline run failed: {e}", exc_info=True)
                
        elif choice == "3":
            print("\nViewing Stored Data...")
            try:
                view_stored_data()
            except Exception as e:
                logger.error(f"Failed to view stored data: {e}", exc_info=True)
                
        elif choice == "4":
            confirm = input("Are you sure you want to delete all database collections? (y/N): ").strip().lower()
            if confirm in ("y", "yes"):
                print("\nDeleting Database...")
                db.clear_database()
                print("Database deleted successfully.")
            else:
                print("Deletion cancelled.")
                
        elif choice == "5":
            print("Exiting application. Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    logger.info("Initializing Application...")
    try:
        main()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)