import os
from datetime import datetime
from typing import Dict, Any, List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from src.database import DatabaseManager
from src.logger import get_logger

logger = get_logger(__name__)

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Helper function to recursively flatten a dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def format_value(val: Any) -> Any:
    """Formats values for Excel cells (converting ObjectIds to strings, datetimes to readable string format)."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    # For PyMongo ObjectId or other non-primitive types
    if hasattr(val, "binary") or type(val).__name__ == "ObjectId":
        return str(val)
    return val

def export_to_excel(output_filename: str = "reddit_data_export.xlsx") -> str:
    """
    Reads data from MongoDB collections (reddit_posts, reddit_comments, qa_pairs),
    flattens the data, formats values, and generates a professionally styled Excel workbook
    saved in the project root directory.
    
    Returns:
        The absolute path to the generated Excel file.
    """
    logger.info("Initializing Excel export...")
    db = DatabaseManager()
    
    wb = Workbook()
    # Remove the default sheet created by openpyxl
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)
    
    # Define collection configurations with fixed column ordering to preserve order every export
    export_configs = [
        {
            "collection": db.reddit_posts,
            "sheet_name": "Reddit Posts",
            "columns": ["post_id", "subreddit", "title", "author", "score", "num_comments", "url", "created_utc", "inserted_at"]
        },
        {
            "collection": db.reddit_comments,
            "sheet_name": "Reddit Comments",
            "columns": ["comment_id", "post_id", "parent_id", "author", "body", "score", "depth", "created_utc", "inserted_at"]
        },
        {
            "collection": db.qa_pairs,
            "sheet_name": "Q&A Pairs",
            "columns": ["qa_id", "post_id", "question_comment_id", "answer_comment_id", "question", "answer", "inserted_at"]
        }
    ]
    
    # Define design styles
    header_font = Font(name="Calibri", size=11, bold=True, color="000000")
    header_fill = PatternFill(start_color="E6EDF2", end_color="E6EDF2", fill_type="solid")  # Sleek light blue/grey
    cell_font = Font(name="Calibri", size=11)
    
    counts = {}
    
    for config in export_configs:
        col = config["collection"]
        sheet_name = config["sheet_name"]
        fixed_cols = config["columns"]
        
        logger.info(f"Exporting collection '{col.name}' to worksheet '{sheet_name}'...")
        ws = wb.create_sheet(title=sheet_name)
        
        # 1. Freeze the header row
        ws.freeze_panes = "A2"
        
        # Fetch all documents
        documents = list(col.find({}))
        counts[sheet_name] = len(documents)
        
        # 2. Automatically generate column headers from document keys (formatted for humans)
        header_names = [col_key.replace("_", " ").title() for col_key in fixed_cols]
        ws.append(header_names)
        
        # 3. Format header row
        for col_idx in range(1, len(header_names) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="left", vertical="center")
            
        # 4. Write Data Rows
        for doc in documents:
            flat_doc = flatten_dict(doc)
            row_data = []
            for col_key in fixed_cols:
                # Retrieve from flat dictionary or fallback to raw doc key. Replace missing with empty string.
                val = flat_doc.get(col_key, doc.get(col_key, ""))
                row_data.append(format_value(val))
            ws.append(row_data)
            
            # Apply cell-level styles
            row_idx = ws.max_row
            for col_idx in range(1, len(fixed_cols) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = cell_font
                cell.alignment = Alignment(horizontal="left", vertical="center")
        
        # 5. Add Auto-filters to every worksheet
        max_col_letter = get_column_letter(len(fixed_cols))
        ws.auto_filter.ref = f"A1:{max_col_letter}{max(1, len(documents) + 1)}"
        
        # 6. Auto-adjust column widths based on cell content length
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            # Add padding and limit to max width of 50 to avoid oversized columns for long texts
            adjusted_width = min(max(max_len + 3, 12), 50)
            ws.column_dimensions[col_letter].width = adjusted_width
            
    # Resolve the project root path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    filepath = os.path.join(project_root, output_filename)
    
    # Save the Excel workbook
    wb.save(filepath)
    
    # Display the total number of exported records in the console
    print("\n====== MongoDB to Excel Export Summary ======")
    for sheet_name, count in counts.items():
        print(f"  {sheet_name:<16}: {count} records exported")
    print(f"Workbook successfully saved to: {filepath}\n")
    
    logger.info(f"Excel export completed successfully. Saved to: {filepath}")
    return filepath
