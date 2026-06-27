import sys
from src.database import DatabaseManager
from src.view_data import view_stored_data
from src.apify_pipeline import ApifyIngestionPipeline
from src.qa_generator import QAGenerator
from src.logger import get_logger

logger = get_logger(__name__)

def main():
    db = DatabaseManager()
    apify_pipeline = ApifyIngestionPipeline()
    qa_generator = QAGenerator()
    
    while True:
        print("\n====== Reddit Data Acquisition ======")
        print("1. Apify Ingestion (Fresh)")
        print("2. Apify Ingestion (Update)")
        print("3. Generate Q&A Pairs (from raw data)")
        print("4. View Stored Data")
        print("5. Delete Database")
        print("6. Exit")
        
        try:
            choice = input("Enter your choice (1-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
            
        if choice == "1":
            print("\nApify Ingestion (Fresh - clearing database first)...")
            db.clear_database()
            try:
                subreddit = input("Enter subreddit (default: news): ").strip() or "news"
                try:
                    limit = int(input("Enter post limit (default: 10): ").strip() or "10")
                except ValueError:
                    limit = 10
                apify_pipeline.run_full_ingestion(subreddit=subreddit, limit=limit)
            except Exception as e:
                logger.error(f"Apify ingestion failed: {e}", exc_info=True)
                
        elif choice == "2":
            print("\nApify Ingestion (Update - adding new data)...")
            try:
                subreddit = input("Enter subreddit (default: news): ").strip() or "news"
                try:
                    limit = int(input("Enter post limit (default: 10): ").strip() or "10")
                except ValueError:
                    limit = 10
                apify_pipeline.run_full_ingestion(subreddit=subreddit, limit=limit)
            except Exception as e:
                logger.error(f"Apify ingestion failed: {e}", exc_info=True)
                
        elif choice == "3":
            print("\nGenerating Q&A Pairs from raw data...")
            try:
                result = qa_generator.run_for_all_posts()
                print(f"\nQ&A Generation Results:")
                print(f"  Posts processed: {result['posts_processed']}")
                print(f"  Q&A pairs generated: {result['qa_pairs_generated']}")
            except Exception as e:
                logger.error(f"Q&A generation failed: {e}", exc_info=True)
                
        elif choice == "4":
            print("\nViewing Stored Data...")
            try:
                view_stored_data()
            except Exception as e:
                logger.error(f"Failed to view stored data: {e}", exc_info=True)
                
        elif choice == "5":
            confirm = input("Are you sure you want to delete all database collections? (y/N): ").strip().lower()
            if confirm in ("y", "yes"):
                print("\nDeleting Database...")
                db.clear_database()
                print("Database deleted successfully.")
            else:
                print("Deletion cancelled.")
                
        elif choice == "6":
            print("Exiting application. Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    logger.info("Initializing Application...")
    try:
        main()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)