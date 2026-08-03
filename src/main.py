import sys
import sqlite3
import requests
from src.database import DatabaseManager
from src.view_data import view_stored_data
from src.apify_pipeline import ApifyIngestionPipeline
from src.qa_generator import QAGenerator
from src.excel_exporter import export_to_excel
from src.logger import get_logger

logger = get_logger(__name__)

from src.processors.nlp_enrichment import NLPEnricher

def main():
    db = DatabaseManager()
    apify_pipeline = ApifyIngestionPipeline()
    qa_generator = QAGenerator()
    nlp_enricher = NLPEnricher()
    
    while True:
        print("\n====== Reddit Data Acquisition ======")
        print("1. Apify Ingestion (Fresh)")
        print("2. Apify Ingestion (Update)")
        print("3. Generate Q&A Pairs (from raw data)")
        print("4. Run NLP Enrichment (Sentiment & Keywords)")
        print("5. View Stored Data")
        print("6. Export to Excel")
        print("7. Force Re-Clean Data (HTML & Boilerplate)")
        print("8. Delete Database")
        print("9. Exit")
        
        try:
            choice = input("Enter your choice (1-9): ").strip()
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
            except (requests.RequestException, sqlite3.Error, KeyError, TypeError, ValueError) as e:
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
            except (requests.RequestException, sqlite3.Error, KeyError, TypeError, ValueError) as e:
                logger.error(f"Apify ingestion failed: {e}", exc_info=True)
                
        elif choice == "3":
            print("\nGenerating Q&A Pairs from raw data...")
            try:
                result = qa_generator.run_for_all_posts()
                print(f"\nQ&A Generation Results:")
                print(f"  Posts processed: {result['posts_processed']}")
                print(f"  Q&A pairs generated: {result['qa_pairs_generated']}")
            except (sqlite3.Error, KeyError, TypeError, ValueError) as e:
                logger.error(f"Q&A generation failed: {e}", exc_info=True)

        elif choice == "4":
            print("\nRunning NLP Enrichment (Sentiment Analysis & Keyword/Entity Extraction)...")
            try:
                result = nlp_enricher.enrich_database(db)
                print(f"\nNLP Enrichment Results:")
                print(f"  Posts enriched:    {result['posts_enriched']}")
                print(f"  Comments enriched: {result['comments_enriched']}")
            except Exception as e:
                logger.error(f"NLP enrichment failed: {e}", exc_info=True)
                
        elif choice == "5":
            print("\nViewing Stored Data...")
            try:
                view_stored_data()
            except (sqlite3.Error, UnicodeError) as e:
                logger.error(f"Failed to view stored data: {e}", exc_info=True)
                
        elif choice == "6":
            print("\nExporting Database to Excel...")
            try:
                filename = input("Enter output filename (default: reddit_data_export.xlsx): ").strip() or "reddit_data_export.xlsx"
                export_to_excel(filename)
            except (sqlite3.Error, OSError) as e:
                logger.error(f"Failed to export to Excel: {e}", exc_info=True)

        elif choice == "7":
            print("\nForce Re-cleaning Data (HTML entities & submission boilerplate)...")
            try:
                db.force_clean_existing_data()
                print("Data cleaning completed successfully.")
            except sqlite3.Error as e:
                logger.error(f"Data re-cleaning failed: {e}", exc_info=True)
                
        elif choice == "8":
            confirm = input("Are you sure you want to delete all database tables? (y/N): ").strip().lower()
            if confirm in ("y", "yes"):
                print("\nDeleting Database...")
                db.clear_database()
                print("Database deleted successfully.")
            else:
                print("Deletion cancelled.")
                
        elif choice == "9":
            print("Exiting application. Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 9.")

if __name__ == "__main__":
    logger.info("Initializing Application...")
    try:
        main()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)