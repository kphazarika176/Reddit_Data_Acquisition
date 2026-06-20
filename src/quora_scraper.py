import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

from mongodb import posts_collection


def scrape_quora():
    """Scrape Q/A pairs from Reddit Q/A subreddits using web scraping"""
    
    # Q/A subreddits
    qa_subreddits = [
        "explainlikeimfive",  # ELI5
        "AskReddit",          # Popular Q/A
        "NoStupidQuestions",  # General Q/A
    ]
    
    # Topics to search for
    topics = ["AI", "india", "politics", "cricket", "economy", "news"]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for sub in qa_subreddits:
        for topic in topics:
            print(f"Scraping r/{sub} for topic: {topic}")
            
            try:
                # Search URL
                url = f"https://www.reddit.com/r/{sub}/search/?q={topic}&restrict_sr=on&sort=top&t=month"
                
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find post elements
                posts = soup.find_all('div', {'class': 'Post'})
                
                for post in posts[:5]:  # Limit to 5 posts per search
                    try:
                        # Extract question (post title)
                        title_elem = post.find('h3')
                        question = title_elem.text if title_elem else "No question"
                        
                        # Extract URL
                        link_elem = post.find('a', {'class': 'PostTitle'})
                        post_url = link_elem.get('href', '') if link_elem else ''
                        
                        # Extract score
                        score_elem = post.find('div', {'class': '_1rjv1d6'})
                        question_score = int(score_elem.text) if score_elem else 0
                        
                        # Create Q/A pair document
                        doc = {
                            "type": "qa_pair",
                            "question": question,
                            "answer": "Top comment data requires additional page load",
                            "question_author": "unknown",
                            "answer_author": "unknown",
                            "source": "reddit",
                            "platform": "reddit_qa",
                            "subreddit": sub,
                            "topic": topic,
                            "url": f"https://reddit.com{post_url}" if post_url.startswith('/') else post_url,
                            "question_score": question_score,
                            "answer_score": 0,
                            "created_at": datetime.utcnow(),
                        }
                        
                        posts_collection.insert_one(doc)
                        print(f"  Inserted Q/A: {question[:50]}...")
                        
                    except Exception as e:
                        print(f"  Error processing post: {e}")
                        continue
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"Error scraping r/{sub}: {e}")
                continue


# If you run this file directly
if __name__ == "__main__":
    scrape_quora()
