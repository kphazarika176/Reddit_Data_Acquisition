from src.database import DatabaseManager

db = DatabaseManager()

qa_pairs = list(db.qa_pairs.find().limit(15))
print(f'Total Q&A Pairs: {db.qa_pairs.count_documents({})}')
print()
for qa in qa_pairs:
    print(f'Q: {qa["question"]}')
    print(f'A: {qa["answer"][:70]}...')
    print(f'Post: {qa["post_id"]}')
    print()
